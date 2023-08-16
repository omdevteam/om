# This file is part of OM.
#
# OM is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# OM is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with OM.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2020 -2023 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Cheetah Streaming.

This module contains a specific version of Cheetah, a data-processing program for
Serial X-ray Crystallography. Compare to Cheetah, this version processes data frames,
but does not save the extracted data to files: it sends it to external programs for
further processing.
"""
import pathlib
import sys
from collections import deque
from typing import Any, Deque, Dict, Tuple, Union

import numpy
from numpy.typing import NDArray

from om.algorithms.crystallography import TypePeakList
from om.algorithms.generic import Binning, BinningPassthrough
from om.lib.cheetah import (
    CheetahClassSumsAccumulator,
    CheetahClassSumsCollector,
    CheetahListFilesWriter,
    CheetahStatusFileWriter,
    TypeFrameListData,
)
from om.lib.crystallography import CrystallographyPeakFinding
from om.lib.event_management import EventCounter
from om.lib.exceptions import OmMissingDependencyError
from om.lib.geometry import GeometryInformation, TypeDetectorLayoutInformation
from om.lib.parameters import MonitorParameters, get_parameter_from_parameter_group
from om.lib.rich_console import console, get_current_timestamp
from om.lib.zmq import ZmqResponder
from om.protocols.processing_layer import OmProcessingProtocol

try:
    import msgpack  # type: ignore
except ImportError:
    raise OmMissingDependencyError(
        "The following required module cannot be imported: msgpack"
    )

try:
    import msgpack_numpy  # type: ignore
except ImportError:
    raise OmMissingDependencyError(
        "The following required module cannot be imported: msgpack_numpy"
    )
msgpack_numpy.patch()


class StreamingCheetahProcessing(OmProcessingProtocol):
    """
    See documentation for the `__init__` function.
    """

    def __init__(self, *, monitor_parameters: MonitorParameters) -> None:
        """
        Cheetah Streaming.

        This Processing class implements the Cheetah Streaming software package. Cheetah
        Streaming processes detector data frames, detecting Bragg peaks in each frame
        using the
        [Peakfinder8PeakDetection][om.algorithms.crystallography.Peakfinder8PeakDetection]
        algorithm. It retrieves information about the location, size, intensity, SNR
        and maximum pixel value of each peak, and then streams the information
        retrieved from the facility or extracted from the data to external programs
        for further processing. Optionally, it can also broadcast full detector data
        frames. Cheetah Streaming can also compute, and write to HDF5 sum files, sums
        of detector data frames (calculating separate sums for hit and non-hit frames).
        The sums can saved together with their corresponding Virtual Powder patterns.
        Cheetah Streaming can also respond to requests for data or change of behavior
        from external programs (a control GUI, for example.)

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        Arguments:

            monitor_parameters: An object storing OM's configuration parameters.
        """

        # Parameters
        self._monitor_params: MonitorParameters = monitor_parameters
        self._cheetah_parameters = self._monitor_params.get_parameter_group(
            group="cheetah"
        )
        crystallography_parameters = self._monitor_params.get_parameter_group(
            group="crystallography"
        )

        # Processed data directory
        processed_directory_path: pathlib.Path = pathlib.Path(
            get_parameter_from_parameter_group(
                group=self._cheetah_parameters,
                parameter="processed_directory",
                parameter_type=str,
                required=True,
            )
        )
        if not processed_directory_path.exists():
            processed_directory_path.mkdir()

        # Geometry
        self._geometry_information = GeometryInformation.from_file(
            geometry_filename=get_parameter_from_parameter_group(
                group=crystallography_parameters,
                parameter="geometry_file",
                parameter_type=str,
                required=True,
            )
        )

        # Post-processing binning
        binning_requested = get_parameter_from_parameter_group(
            group=crystallography_parameters,
            parameter="post_processing_binning",
            parameter_type=bool,
            default=False,
        )
        if binning_requested:
            self._post_processing_binning: Union[Binning, BinningPassthrough] = Binning(
                parameters=self._monitor_params.get_parameter_group(group="binning"),
                layout_info=self._geometry_information.get_layout_info(),
            )
        else:
            self._post_processing_binning = BinningPassthrough(
                layout_info=self._geometry_information.get_layout_info()
            )

        # Processed data shape
        layout_info: TypeDetectorLayoutInformation = (
            self._post_processing_binning.get_binned_layout_info()
        )
        self._processed_data_shape: Tuple[int, int] = (
            layout_info["asic_ny"] * layout_info["nasics_y"],
            layout_info["asic_nx"] * layout_info["nasics_x"],
        )

    def initialize_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes the processing nodes for Cheetah Streaming.

        This function initializes all the required algorithms (peak finding, binning,
        etc.), plus some internal counters.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """

        # Peak finding
        self._peak_detection: CrystallographyPeakFinding = CrystallographyPeakFinding(
            monitor_parameters=self._monitor_params,
            geometry_information=self._geometry_information,
        )
        self._min_num_peaks_for_hit: int = get_parameter_from_parameter_group(
            group=self._monitor_params.get_parameter_group(group="crystallography"),
            parameter="min_num_peaks_for_hit",
            parameter_type=int,
            required=True,
        )
        self._max_num_peaks_for_hit: int = get_parameter_from_parameter_group(
            group=self._monitor_params.get_parameter_group(group="crystallography"),
            parameter="max_num_peaks_for_hit",
            parameter_type=int,
            required=True,
        )

        # Class sums accumulation
        self._class_sum_accumulator: CheetahClassSumsAccumulator = (
            CheetahClassSumsAccumulator(
                cheetah_parameters=self._cheetah_parameters,
            )
        )

        # An array to store processed data converted to float32 (required by CrystFEL)
        self._float_detector_data: NDArray[numpy.float_] = numpy.zeros(
            self._processed_data_shape, dtype=numpy.float32
        )

        console.print(f"{get_current_timestamp()} Processing node {node_rank} starting")
        sys.stdout.flush()

    def initialize_collecting_node(self, node_rank: int, node_pool_size: int) -> None:
        """
        Initializes the collecting node for Cheetah.

        This function initializes the data accumulation algorithms, the storage buffers
        used to compute aggregated statistics on the processed data, and some internal
        counters. Additionally, it prepares all the necessary network sockets.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        # Event counting
        self._event_counter: EventCounter = EventCounter(
            om_parameters=self._monitor_params.get_parameter_group(
                group="crystallography"
            ),
            node_pool_size=node_pool_size,
        )

        # Status file
        self._status_file_writer: CheetahStatusFileWriter = CheetahStatusFileWriter(
            parameters=self._cheetah_parameters,
        )
        self._status_file_update_interval: int = self._monitor_params.get_parameter(
            group="cheetah",
            parameter="status_file_update_interval",
            parameter_type=int,
            required=True,
        )
        if self._status_file_update_interval < 1:
            # TODO: raise exception
            pass
        self._status_file_writer.update_status(status="Not finished")

        # List files
        self._list_files_writer: CheetahListFilesWriter = CheetahListFilesWriter(
            cheetah_parameters=self._cheetah_parameters
        )

        # Class sums collection
        self._class_sum_collector: CheetahClassSumsCollector = (
            CheetahClassSumsCollector(
                cheetah_parameters=self._cheetah_parameters, num_classes=2
            )
        )

        # Streaming to CrystFEL
        request_list_size: Union[int, None] = self._monitor_params.get_parameter(
            group="crystallography",
            parameter="external_data_request_list_size",
            parameter_type=int,
        )
        if request_list_size is None:
            request_list_size = 20
        self._request_list: Deque[Tuple[bytes, bytes]] = deque(maxlen=request_list_size)

        self._responding_socket: ZmqResponder = ZmqResponder(
            parameters=self._monitor_params.get_parameter_group(group="crystallography")
        )

        self._source: str = self._monitor_params.get_parameter(
            group="om",
            parameter="source",
            parameter_type=str,
            required=True,
        )

        self._configuration_file: str = self._monitor_params.get_parameter(
            group="om",
            parameter="configuration_file",
            parameter_type=str,
            required=True,
        )

        # Console
        console.print(f"{get_current_timestamp()} Starting the monitor...")
        sys.stdout.flush()

    def process_data(  # noqa: C901
        self, *, node_rank: int, node_pool_size: int, data: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], int]:
        """
        Processes a detector data frame.

        This function processes retrieved data events, extracting the Bragg peak
        information. It prepares the reduced data (and optionally, the detector frame
        data) to be transmitted to the collecting node.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

            data: A dictionary containing the data that OM retrieved for the detector
                data frame being processed.

                * The dictionary keys describe the Data Sources for which OM has
                  retrieved data. The keys must match the source names listed in the
                  `required_data` entry of OM's `om` configuration parameter group.

                * The corresponding dictionary values must store the the data that OM
                  retrieved for each of the Data Sources.

        Returns:

            A tuple with two entries. The first entry is a dictionary storing the
                processed data that should be sent to the collecting node. The second
                entry is the OM rank number of the node that processed the information.
        """
        # Peak-finding
        peak_list: TypePeakList = self._peak_detection.find_peaks(
            detector_data=data["detector_data"]
        )
        frame_is_hit: bool = (
            self._min_num_peaks_for_hit
            < peak_list["num_peaks"]
            < self._max_num_peaks_for_hit
        )

        # Binning
        peak_list = self._post_processing_binning.bin_peak_positions(
            peak_list=peak_list
        )
        binned_detector_data: Union[
            NDArray[numpy.float_], NDArray[numpy.int_]
        ] = self._post_processing_binning.bin_detector_data(data=data["detector_data"])

        # Add data to the class sums
        self._class_sum_accumulator.add_frame(
            class_number=int(frame_is_hit),
            frame_data=binned_detector_data,
            peak_list=peak_list,
        )

        # Data to send to the collecting node
        processed_data = {
            "timestamp": data["timestamp"],
            "frame_is_hit": frame_is_hit,
            "event_id": data["event_id"],
            "beam_energy": data["beam_energy"],
            "detector_distance": data["detector_distance"],
            "peak_list": peak_list,
            "class_sums": self._class_sum_accumulator.get_sums_for_sending(),
        }
        if frame_is_hit:
            # Convert processed data to float32 for streaming to CrystFEL
            self._float_detector_data[:] = binned_detector_data
            processed_data["detector_data"] = self._float_detector_data[:]

        return (processed_data, node_rank)

    def wait_for_data(
        self,
        *,
        node_rank: int,
        node_pool_size: int,
    ) -> None:
        """
        Receives and handles requests from external programs.

        This function receives requests from external programs over a network socket
        and reacts according to the nature of the request, sending data back to the
        source of the request or modifying the internal behavior of Cheetah Streaming.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        """
        self._handle_external_requests()

    def collect_data(  # noqa: C901
        self,
        *,
        node_rank: int,
        node_pool_size: int,
        processed_data: Tuple[Dict[str, Any], int],
    ) -> Union[Dict[int, Dict[str, Any]], None]:
        """
        Computes statistics on aggregated data and broadcasts data to external programs.

        This function collects and accumulates frame- and peak-related information
        received from the processing nodes, and streams it to external programs.
        Optionally, it computes the sums of hit and non-hit detector frames and the
        corresponding virtual powder patterns, and saves them to file. Additionally,
        this function writes information about the processing statistics (number of
        processed events, number of found hits and the elapsed time) to a status file
        at regular intervals. External programs can inspect the file to determine the
        advancement of the data processing.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

            processed_data (Tuple[Dict, int]): A tuple whose first entry is a
                dictionary storing the data received from a processing node, and whose
                second entry is the OM rank number of the node that processed the
                information.
        """
        self._handle_external_requests()
        received_data: Dict[str, Any] = processed_data[0]

        # Collect class sums
        if received_data["class_sums"] is not None:
            self._class_sum_collector.add_sums(class_sums=received_data["class_sums"])

        if "end_processing" in received_data:
            return None

        if received_data["frame_is_hit"] is True:
            self._event_counter.add_hit_event()
        else:
            self._event_counter.add_non_hit_event()

        # Stream hits to CrystFEL
        if received_data["frame_is_hit"]:
            # Wait for a request to the responding socket.
            while len(self._request_list) == 0:
                self._handle_external_requests()

            last_request: Tuple[bytes, bytes] = self._request_list[-1]
            data_to_send: Any = msgpack.packb(
                {
                    "detector_data": received_data["detector_data"],
                    "peak_list": received_data["peak_list"],
                    "beam_energy": received_data["beam_energy"],
                    "detector_distance": received_data["detector_distance"],
                    "event_id": received_data["event_id"],
                    "timestamp": received_data["timestamp"],
                    "source": self._source,
                    "configuration_file": self._configuration_file,
                },
                use_bin_type=True,
            )
            self._responding_socket.send_data(
                identity=last_request[0], message=data_to_send
            )
            _ = self._request_list.pop()

        # Write frame and peaks data to list files
        frame_data: TypeFrameListData = TypeFrameListData(
            received_data["timestamp"],
            received_data["event_id"],
            int(received_data["frame_is_hit"]),
            "",
            -1,
            received_data["peak_list"]["num_peaks"],
            numpy.mean(received_data["peak_list"]["intensity"]),
        )
        self._list_files_writer.add_frame(
            frame_data=frame_data, peak_list=received_data["peak_list"]
        )

        # Update status file
        num_events: int = self._event_counter.get_num_events()
        if num_events % self._status_file_update_interval == 0:
            self._status_file_writer.update_status(
                status="Not finished",
                num_frames=num_events,
                num_hits=self._event_counter.get_num_hits(),
            )
            self._list_files_writer.flush_files()

        self._event_counter.report_speed()

        return None

    def end_processing_on_processing_node(
        self,
        *,
        node_rank: int,
        node_pool_size: int,
    ) -> Union[Dict[str, Any], None]:
        """
        Ends processing on the processing nodes for Cheetah Streaming.

        This function prints a message on the console and ends the processing.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        Returns:

            Usually nothing. Optionally, a dictionary storing information to be sent to
                the processing node.
        """
        console.print(
            f"{get_current_timestamp()} Processing node {node_rank} shutting down."
        )
        sys.stdout.flush()

        # Send last class sums to the collecting node
        return {
            "class_sums": self._class_sum_accumulator.get_sums_for_sending(
                disregard_counter=True
            ),
            "end_processing": True,
        }

    def end_processing_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Ends processing on the collecting node for Cheetah Streaming.

        This function prints a message on the console, writes the final information in
        the sum and status files, closes the files and ends the processing.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        # Save final accumulated class sums
        self._class_sum_collector.save_sums()

        # Sort frames and write final list files
        self._list_files_writer.sort_frames_and_close_files()

        # Write final status
        self._status_file_writer.update_status(
            status="Finished",
            num_frames=self._event_counter.get_num_events(),
            num_hits=self._event_counter.get_num_hits(),
        )

        console.print(
            f"{get_current_timestamp()} Processing finished. OM has processed "
            f"{self._event_counter.get_num_events()} events in total."
        )
        sys.stdout.flush()

    def _handle_external_requests(self) -> None:
        # This function handles external requests sent to the crystallography monitor
        # over the responding network socket.
        request: Union[
            Tuple[bytes, bytes], None
        ] = self._responding_socket.get_request()
        if request:
            if request[1] == b"next":
                self._request_list.append(request)
            else:
                console.print(
                    f"{get_current_timestamp()} OM Warning: Could not understand "
                    f"request '{str(request[1])}'.",
                    style="warning",
                )
                self._responding_socket.send_data(identity=request[0], message=b"What?")
