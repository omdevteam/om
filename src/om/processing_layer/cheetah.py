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
Cheetah

This module contains Cheetah, a data-processing program for Serial X-ray
Crystallography, based on OM but not designed to be run in real time.
"""


from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, Optional, Tuple, Type, TypeVar, Union

import msgpack  # type: ignore
import numpy
from numpy.typing import NDArray
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
from typing_extensions import Self

from om.algorithms.crystallography import PeakList
from om.algorithms.generic import Binning, BinningPassthrough
from om.lib.cheetah import (
    CheetahClassSumsAccumulator,
    CheetahClassSumsCollector,
    CheetahListFilesWriter,
    CheetahStatusFileWriter,
    FrameListData,
    HDF5Writer,
)
from om.lib.crystallography import CrystallographyPeakFinding
from om.lib.event_management import EventCounter
from om.lib.exceptions import OmConfigurationFileSyntaxError
from om.lib.geometry import DetectorLayoutInformation, GeometryInformation
from om.lib.logging import log
from om.lib.protocols import OmProcessingProtocol
from om.lib.zmq import ZmqResponder

T = TypeVar("T")


class _CheetahParameters(BaseModel):
    processed_directory: str
    status_file_update_interval: int
    responding_url: Optional[str] = Field(default=None)
    external_data_request_list_size: int = Field(default=20)

    @field_validator("status_file_update_interval")
    def check_status_file_update_interval(cls: Self, v: int) -> int:
        if v < 1:
            raise ValueError(
                "The following entry in the configuration file must have a value of 1 "
                "or higher: cheetah/status_file_update_interval"
            )
        return v


class _CrystallographyParameters(BaseModel):
    geometry_file: str
    post_processing_binning: bool = Field(default=False)
    min_num_peaks_for_hit: int
    max_num_peaks_for_hit: int
    speed_report_interval: int


class _OmParameters(BaseModel):
    source: str
    configuration_file: Path


class _MonitorParameters(BaseModel):
    cheetah: _CheetahParameters
    crystallography: _CrystallographyParameters
    om: _OmParameters
    binning: Dict[str, Any]

    @model_validator(mode="after")
    def check_binning_parameters(self) -> Self:
        if (
            self.crystallography.post_processing_binning is True
            and self.binning is None
        ):
            raise ValueError(
                "When post processing binning is requested, the following section must "
                "be present in OM's configuration parameters: binning"
            )
        return self


class OmCheetahMixin:

    def __new__(cls: Type[T], *args: Any, **kwargs: Any) -> T:
        if cls is OmCheetahMixin:
            raise TypeError(
                f"{cls.__name__} is a Mixin class and should not be instantiated"
            )
        return object.__new__(cls)

    def __init__(self, *, parameters: Dict[str, Any]) -> None:
        """
        Cheetah.

        This Processing class implements the Cheetah software package. This program
        processes detector data frames, detecting Bragg peaks in each frame using the
        [`Peakfinder8PeakDetection`][om.algorithms.crystallography.Peakfinder8PeakDetection]
        algorithm. It retrieves information about the location, size, intensity, SNR
        and maximum pixel value of each peak, and then saves the calibrated and
        corrected detector data, plus all the information retrieved from the facility
        or extracted from the data, in multi-event HDF5 files. Cheetah can also
        compute, and write to HDF5 sum files, sums of detector data frames, together
        with their corresponding virtual powder patterns. Separate sums are computed
        for hit and non-hit frames.

        Arguments:

            monitor_parameters: An object storing OM's configuration parameters.
        """

        self._monitor_parameters = parameters

        try:
            self._parameters: _MonitorParameters = _MonitorParameters.model_validate(
                self._monitor_parameters
            )
        except ValidationError as exception:
            raise OmConfigurationFileSyntaxError(
                "Error parsing OM's configuration parameters: " f"{exception}"
            )

        # Processed data directory
        if not Path(self._parameters.cheetah.processed_directory).exists():
            Path(self._parameters.cheetah.processed_directory).mkdir()

        # Geometry
        self._geometry_information = GeometryInformation.from_file(
            geometry_filename=self._parameters.crystallography.geometry_file
        )

    def _common_initialize_processing_node(
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
        # Peak detection
        self._peak_detection: CrystallographyPeakFinding = CrystallographyPeakFinding(
            parameters=self._monitor_parameters,
            geometry_information=self._geometry_information,
        )

        # Post-processing binning
        if self._parameters.crystallography.post_processing_binning:
            self._post_processing_binning: Union[Binning, BinningPassthrough] = Binning(
                parameters=self._monitor_parameters["binning"],
                layout_info=self._geometry_information.get_layout_info(),
            )
        else:
            self._post_processing_binning = BinningPassthrough(
                layout_info=self._geometry_information.get_layout_info()
            )

        # Processed data shape
        layout_info: DetectorLayoutInformation = (
            self._post_processing_binning.get_binned_layout_info()
        )
        self._processed_data_shape: Tuple[int, int] = (
            layout_info.asic_ny * layout_info.nasics_y,
            layout_info.asic_nx * layout_info.nasics_x,
        )

        # An array to store processed data converted to float32 (required by CrystFEL)
        self._float_detector_data: NDArray[numpy.float_] = numpy.zeros(
            self._processed_data_shape, dtype=numpy.float32
        )

        # Class sums accumulation
        self._class_sum_accumulator: CheetahClassSumsAccumulator = (
            CheetahClassSumsAccumulator(
                parameters=self._monitor_parameters,
                num_classes=2,
            )
        )

    def _common_initialize_collecting_node(
        self, node_rank: int, node_pool_size: int
    ) -> None:
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
            speed_report_interval=(
                self._parameters.crystallography.speed_report_interval
            ),
            node_pool_size=node_pool_size,
        )

        # Status file
        self._status_file_writer: CheetahStatusFileWriter = CheetahStatusFileWriter(
            parameters=self._monitor_parameters,
        )
        self._status_file_writer.update_status(status="Not finished")

        # List files
        self._list_files_writer: CheetahListFilesWriter = CheetahListFilesWriter(
            parameters=self._monitor_parameters,
        )

        # Class sums collection
        self._class_sum_collector: CheetahClassSumsCollector = (
            CheetahClassSumsCollector(
                parameters=self._monitor_parameters, num_classes=2
            )
        )

    def common_process_data(  # noqa: C901
        self, *, node_rank: int, node_pool_size: int, data: Dict[str, Any]
    ) -> Tuple[Union[NDArray[numpy.float_], NDArray[numpy.int_]], PeakList, bool]:
        """
        Processes a detector data frame.

        This function processes retrieved data events, extracting the Bragg peak
        information. It also prepares the reduced data (and optionally, the detector
        frame data) to be transmitted to the collecting node.

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
        peak_list: PeakList = self._peak_detection.find_peaks(
            detector_data=data["detector_data"]
        )
        frame_is_hit: bool = (
            self._parameters.crystallography.min_num_peaks_for_hit
            < peak_list.num_peaks
            < self._parameters.crystallography.max_num_peaks_for_hit
        )

        # Binning
        peak_list = self._post_processing_binning.bin_peak_positions(
            peak_list=peak_list
        )
        binned_detector_data: Union[NDArray[numpy.float_], NDArray[numpy.int_]] = (
            self._post_processing_binning.bin_detector_data(data=data["detector_data"])
        )

        # Add data to the class sums
        self._class_sum_accumulator.add_frame(
            class_number=int(frame_is_hit),
            frame_data=binned_detector_data,
            peak_list=peak_list,
        )

        return (binned_detector_data, peak_list, frame_is_hit)

    def _common_collect_data(  # noqa: C901
        self,
        *,
        processed_data: Tuple[Dict[str, Any], int],
    ) -> Optional[Dict[str, Any]]:
        """
        Computes statistics on aggregated data and broadcasts data to external programs.

        This function collects and accumulates frame- and peak-related information
        received from the processing nodes, and streams it to external programs.
        Optionally, it computes the sums of hit and non-hit detector frames and the
        corresponding virtual powder patterns, and saves them to files. Additionally,
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
        received_data: Dict[str, Any] = processed_data[0]

        # Collect class sums
        if received_data["class_sums"] is not None:
            self._class_sum_collector.add_sums(class_sums=received_data["class_sums"])

        # End processing
        if "end_processing" in received_data:
            return None

        # Event counting
        if received_data["frame_is_hit"] is True:
            self._event_counter.add_hit_event()
        else:
            self._event_counter.add_non_hit_event()

        return received_data

    def _common_end_processing_on_processing_node(
        self,
        *,
        node_rank: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Ends processing on the processing nodes for Cheetah.

        This function prints a message on the console, closes the output HDF5 files
        and ends the processing.

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
        # Send last class sums to the collecting node
        return {
            "class_sums": self._class_sum_accumulator.get_sums_for_sending(
                disregard_counter=True
            ),
            "end_processing": True,
        }


class CheetahProcessing(OmCheetahMixin, OmProcessingProtocol):
    """
    See documentation for the `__init__` function.
    """

    def initialize_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes the processing nodes for Cheetah.

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
        self._common_initialize_processing_node(
            node_rank=node_rank, node_pool_size=node_pool_size
        )

        # HDF5 file writer
        self._file_writer: HDF5Writer = HDF5Writer(
            parameters=self._monitor_parameters,
            node_rank=node_rank,
        )

        log.info(f"Processing node {node_rank} starting")

    def initialize_collecting_node(self, node_rank: int, node_pool_size: int) -> None:
        """
        Initializes the collecting node for Cheetah.

        This function initializes the data accumulation algorithms, the storage buffers
        used to compute statistics on the processed data, and some internal counters.
        Additionally, it prepares all the file writers.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        self._common_initialize_collecting_node(
            node_rank=node_rank, node_pool_size=node_pool_size
        )

        # Console
        log.info("Starting the monitor...")

    def process_data(  # noqa: C901
        self, *, node_rank: int, node_pool_size: int, data: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], int]:
        """
        Processes a detector data frame and saves the extracted data to HDF5 file.

        This function processes retrieved data events, extracting the Bragg peak
        information. It saves the frame-related processed data in an output HDF5 file,
        if a frame is identified as a hit. Finally, it prepares the reduced data
        (and optionally, the detector frame data) for transmission to the collecting
        node.

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
        binned_detector_data, peak_list, frame_is_hit = self.common_process_data(
            node_rank=node_rank, node_pool_size=node_pool_size, data=data
        )

        # Saving data to HDF5 file
        if frame_is_hit:
            data_to_write: Dict[str, Any] = {
                "detector_data": binned_detector_data,
                "event_id": data["event_id"],
                "timestamp": data["timestamp"],
                "beam_energy": data["beam_energy"],
                "detector_distance": data["detector_distance"],
                "peak_list": peak_list,
            }
            if "optical_laser_active" in data.keys():
                data_to_write["optical_laser_active"] = data["optical_laser_active"]
            if "lcls_extra" in data.keys():
                data_to_write["lcls_extra"] = data["lcls_extra"]
            self._file_writer.write_frame(processed_data=data_to_write)

        # Data to send to the collecting node
        processed_data = {
            "timestamp": data["timestamp"],
            "frame_is_hit": frame_is_hit,
            "event_id": data["event_id"],
            "peak_list": peak_list,
            "class_sums": self._class_sum_accumulator.get_sums_for_sending(),
        }
        if frame_is_hit:
            processed_data["filename"] = self._file_writer.get_current_filename()
            processed_data["index"] = self._file_writer.get_num_written_frames()
        else:
            processed_data["filename"] = "---"
            processed_data["index"] = -1

        return (processed_data, node_rank)

    def wait_for_data(
        self,
        *,
        node_rank: int,
        node_pool_size: int,
    ) -> None:
        """
        Receives and handles requests from external programs.

        This function is not used in Cheetah, and therefore does nothing.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        """
        pass

    def collect_data(  # noqa: C901
        self,
        *,
        node_rank: int,
        node_pool_size: int,
        processed_data: Tuple[Dict[str, Any], int],
    ) -> Optional[Dict[int, Dict[str, Any]]]:
        """
        Computes statistics on aggregated data and saves them to files.

        This function collects and accumulates frame- and peak-related information
        received from the processing nodes.  Optionally, it computes the sums of hit
        and non-hit detector frames and the corresponding virtual powder patterns, and
        saves them to file. Additionally, this function writes information about the
        processing statistics (number of processed events, number of found hits and the
        elapsed time) to a status file at regular intervals. External programs can
        inspect the file to determine the advancement of the data processing.

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

        received_data: Optional[Dict[str, Any]] = self._common_collect_data(
            processed_data=processed_data
        )

        if received_data is None:
            return None

        # Write frame and peaks data to list files
        frame_data: FrameListData = FrameListData(
            received_data["timestamp"],
            received_data["event_id"],
            int(received_data["frame_is_hit"]),
            received_data["filename"],
            received_data["index"],
            received_data["peak_list"]["num_peaks"],
            numpy.mean(received_data["peak_list"]["intensity"]),
        )
        self._list_files_writer.add_frame(
            frame_data=frame_data, peak_list=received_data["peak_list"]
        )

        # Update status file
        num_events: int = self._event_counter.get_num_events()
        if num_events % self._parameters.cheetah.status_file_update_interval == 0:
            self._status_file_writer.update_status(
                status="Not finished",
                num_frames=num_events,
                num_hits=self._event_counter.get_num_hits(),
            )
            self._list_files_writer.flush_files()

        self._event_counter.report_speed()

        return None

    def _common_end_processing_on_processing_node(
        self,
        *,
        node_rank: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Ends processing on the processing nodes for Cheetah.

        This function prints a message on the console, closes the output HDF5 files
        and ends the processing.

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
        log.info(f"Processing node {node_rank} shutting down.")
        self._file_writer.close()
        return self._common_end_processing_on_processing_node(node_rank=node_rank)

    def end_processing_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Ends processing on the collecting node for Cheetah.

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

        log.info(
            "Processing finished. OM has processed "
            f"{self._event_counter.get_num_events()} events in total."
        )


class StreamingCheetahProcessing(OmCheetahMixin, OmProcessingProtocol):
    """
    See documentation for the `__init__` function.
    """

    def initialize_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes the processing nodes for Cheetah.

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
        self._common_initialize_processing_node(
            node_rank=node_rank, node_pool_size=node_pool_size
        )

        log.info(f"Processing node {node_rank} starting")

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
        self._common_initialize_collecting_node(
            node_rank=node_rank, node_pool_size=node_pool_size
        )

        # Streaming to CrystFEL
        self._request_list: Deque[Tuple[bytes, bytes]] = deque(
            maxlen=self._parameters.cheetah.external_data_request_list_size
        )

        self._responding_socket: ZmqResponder = ZmqResponder(
            responding_url=self._parameters.cheetah.responding_url
        )

        # Console
        log.info("Starting the monitor...")

    def process_data(  # noqa: C901
        self, *, node_rank: int, node_pool_size: int, data: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], int]:
        """
        Processes a detector data frame.

        This function processes retrieved data events, extracting the Bragg peak
        information. It also prepares the reduced data (and optionally, the detector
        frame data) to be transmitted to the collecting node.

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
        binned_detector_data, peak_list, frame_is_hit = self.common_process_data(
            node_rank=node_rank, node_pool_size=node_pool_size, data=data
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
    ) -> Optional[Dict[int, Dict[str, Any]]]:
        """
        Computes statistics on aggregated data and broadcasts data to external programs.

        This function collects and accumulates frame- and peak-related information
        received from the processing nodes, and streams it to external programs.
        Optionally, it computes the sums of hit and non-hit detector frames and the
        corresponding virtual powder patterns, and saves them to files. Additionally,
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
        received_data: Optional[Dict[str, Any]] = self._common_collect_data(
            processed_data=processed_data
        )

        if received_data is None:
            return None

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
                    "source": self._parameters.om.source,
                    "configuration_file": self._parameters.om.configuration_file,
                },
                use_bin_type=True,
            )
            self._responding_socket.send_data(
                identity=last_request[0], message=data_to_send
            )
            _ = self._request_list.pop()

        # Write frame and peaks data to list files
        frame_data: FrameListData = FrameListData(
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
        if num_events % self._parameters.cheetah.status_file_update_interval == 0:
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
    ) -> Optional[Dict[str, Any]]:
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
        log.info(f"Processing node {node_rank} shutting down.")
        return self._common_end_processing_on_processing_node(node_rank=node_rank)

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

        log.info(
            "Processing finished. OM has processed "
            f"{self._event_counter.get_num_events()} events in total."
        )

    def _handle_external_requests(self) -> None:
        # This function handles external requests sent to the crystallography monitor
        # over the responding network socket.
        request: Optional[Tuple[bytes, bytes]] = self._responding_socket.get_request()
        if request:
            if request[1] == b"next":
                self._request_list.append(request)
            else:
                log.warning(
                    f"OM Warning: Could not understand request '{str(request[1])}'."
                )
                self._responding_socket.send_data(identity=request[0], message=b"What?")
