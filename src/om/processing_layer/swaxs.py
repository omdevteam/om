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
# Copyright 2020 -2021 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
OnDA Monitor for Crystallography.

This module contains an OnDA Monitor for serial x-ray crystallography experiments.
"""
import collections
import sys
from typing import Any, Deque, Dict, List, Tuple, Union

import numpy
from numpy.typing import NDArray

from om.algorithms.crystallography import TypePeakList
from om.algorithms.generic import Binning, Correction
from om.lib.crystallography_collecting import CrystallographyPlots
from om.lib.crystallography_processing import CrystallographyPeakFinding
from om.lib.exceptions import OmMissingDependencyError
from om.lib.generic_collecting import EventCounter
from om.lib.geometry import GeometryInformation
from om.lib.parameters import MonitorParameters
from om.lib.rich_console import console, get_current_timestamp
from om.lib.zmq_collecting import ZmqDataBroadcaster, ZmqResponder
from om.protocols.processing_layer import OmProcessingBase

try:
    import msgpack  # type: ignore
except ImportError:
    raise OmMissingDependencyError(
        "The following required module cannot be imported: msgpack"
    )


class SwaxsProcessing(OmProcessingBase):
    """
    See documentation for the `__init__` function.
    """

    def __init__(self, *, monitor_parameters: MonitorParameters) -> None:
        """
        OnDA Monitor for Crystallography.

        # TODO: Documentation

        Arguments:

            monitor_parameters: An object storing OM's configuration
        """

        # Parameters
        self._monitor_params: MonitorParameters = monitor_parameters

        # Geometry
        self._geometry_info = GeometryInformation(
            geometry_filename=self._monitor_params.get_parameter(
                group="crystallography",
                parameter="geometry_file",
                parameter_type=str,
                required=True,
            ),
            geometry_format="crystfel",
        )

        # Binning
        binning_requested: Union[bool, None] = self._monitor_params.get_parameter(
            group="crystallography",
            parameter="binning",
            parameter_type=bool,
            default=False,
        )
        if binning_requested:
            self._binning: Union[Binning, None] = Binning(
                parameters=self._monitor_params.get_parameter_group(group="binning"),
            )
            self._binning_before_peak_finding = self._monitor_params.get_parameter(
                group="crystallography",
                parameter="binning_before_peakfinding",
                parameter_type=bool,
                default=True,
            )
        else:
            self._binning = None
            self._binning_before_peak_finding = None

        # Pump probe
        self._pump_probe_experiment: bool = self._monitor_params.get_parameter(
            group="crystallography",
            parameter="pump_probe_experiment",
            parameter_type=bool,
            default=False,
        )

    def initialize_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes the processing nodes for the Crystallography Monitor.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the correction and peak finding algorithms, plus some
        internal counters.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """

        # Correction
        self._correction = Correction(
            parameters=self._monitor_params.get_parameter_group(group="correction")
        )

        # Peak finding
        self._peak_finding: CrystallographyPeakFinding = CrystallographyPeakFinding(
            crystallography_parameters=self._monitor_params.get_parameter_group(
                group="crystallography"
            ),
            peak_finding_parameters=self._monitor_params.get_parameter_group(
                group="peakfinder8_peak_detection"
            ),
            pixel_maps=self._geometry_info.get_pixel_maps(),
            binning_algorithm=self._binning,
            binning_before_peak_finding=self._binning_before_peak_finding,
        )

        # Frame sending
        self._send_hit_frame: bool = False
        self._send_non_hit_frame: bool = False

        # Console
        console.print(f"{get_current_timestamp()} Processing node {node_rank} starting")
        sys.stdout.flush()

    def initialize_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes the collecting node for the Crystallography Monitor.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the data accumulation algorithms and the storage
        buffers used to compute statistics on the detected Bragg peaks. Additionally,
        it prepares the data broadcasting socket to send data to external programs.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """

        # Geometry
        self._geometry_is_optimized: bool = self._monitor_params.get_parameter(
            group="crystallography",
            parameter="geometry_is_optimized",
            parameter_type=bool,
            required=True,
        )

        self._pixel_size = self._geometry_info.get_pixel_size()

        self._detector_distance_offset: float = (
            self._geometry_info.get_detector_distance_offset()
        )

        # Data broadcast
        self._data_broadcast_socket: ZmqDataBroadcaster = ZmqDataBroadcaster(
            parameters=self._monitor_params.get_parameter_group(group="crystallography")
        )

        # Plots
        self._plots: CrystallographyPlots = CrystallographyPlots(
            crystallography_parameters=(
                self._monitor_params.get_parameter_group(group="crystallography")
            ),
            geometry_information=self._geometry_info,
            binning_algorithm=self._binning,
            pump_probe_experiment=self._pump_probe_experiment,
        )

        # Streaming to CrystFEL
        request_list_size: Union[int, None] = self._monitor_params.get_parameter(
            group="crystallography",
            parameter="external_data_request_list_size",
            parameter_type=int,
        )
        if request_list_size is None:
            request_list_size = 20
        self._request_list: Deque[Tuple[bytes, bytes]] = collections.deque(
            maxlen=request_list_size
        )

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

        # Event counting
        self._event_counter: EventCounter = EventCounter(
            om_parameters=self._monitor_params.get_parameter_group(
                group="crystallography"
            ),
            node_pool_size=node_pool_size,
        )

        # Console
        console.print(f"{get_current_timestamp()} Starting the monitor...")
        sys.stdout.flush()

    def process_data(
        self, *, node_rank: int, node_pool_size: int, data: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], int]:
        """
        Processes a detector data frame and extracts Bragg peak information.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function processes retrieved data events, calibrating and correcting the
        detector data frames and extracting the Bragg peak information. Finally, it
        prepares the Bragg peak data (and optionally, the detector frame data) for
        transmission to to the collecting node.

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

        # Correction
        processed_data: Dict[str, Any] = {}
        corrected_detector_data: NDArray[
            numpy.float_
        ] = self._correction.apply_correction(data=data["detector_data"])

        # Peak-finding
        data_for_peak_finding: Union[
            NDArray[numpy.float_], NDArray[numpy.int_]
        ] = corrected_detector_data
        data_to_send: Union[
            NDArray[numpy.float_], NDArray[numpy.int_]
        ] = corrected_detector_data

        if self._binning is not None:
            binned_detector_data = self._binning.bin_detector_data(
                data=corrected_detector_data
            )
            data_to_send = binned_detector_data
            if self._binning_before_peak_finding:
                data_for_peak_finding = binned_detector_data

        peak_list: TypePeakList
        frame_is_hit: bool
        peak_list, frame_is_hit = self._peak_finding.find_peaks(
            detector_data=data_for_peak_finding
        )

        # Data to send
        processed_data["timestamp"] = data["timestamp"]
        processed_data["frame_is_hit"] = frame_is_hit
        processed_data["detector_distance"] = data["detector_distance"]
        processed_data["beam_energy"] = data["beam_energy"]
        processed_data["event_id"] = data["event_id"]
        processed_data["frame_id"] = data["frame_id"]
        processed_data["data_shape"] = data_to_send.shape
        processed_data["peak_list"] = peak_list
        if self._pump_probe_experiment:
            processed_data["optical_laser_active"] = data["optical_laser_active"]

        # Frame sending
        if "requests" in data:
            if data["requests"] == "hit_frame":
                self._send_hit_frame = True
            if data["requests"] == "non_hit_frame":
                self._send_non_hit_frame = True

        if frame_is_hit:
            if self._send_hit_frame is True:
                processed_data["detector_data"] = data_to_send
                self._send_hit_frame = False
        else:
            if self._send_non_hit_frame is True:
                processed_data["detector_data"] = data_to_send
                self._send_non_hit_frame = False

        return (processed_data, node_rank)

    def wait_for_data(
        self,
        *,
        node_rank: int,
        node_pool_size: int,
    ) -> None:
        """
        Receives and handles requests from external programs.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function receives requests from external programs over a network socket
        and reacts according to the nature of the request, sending data back to the
        source of the request or modifying the internal behavior of the monitor.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        """
        self._handle_external_requests()

    def collect_data(
        self,
        *,
        node_rank: int,
        node_pool_size: int,
        processed_data: Tuple[Dict[str, Any], int],
    ) -> Union[Dict[int, Dict[str, Any]], None]:
        """
        Computes statistics on aggregated data and broadcasts them.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function collects Bragg peak information (and optionally, frame data) from
        the processing nodes. It computes a rolling average estimation of the hit rate
        and a virtual powder pattern. It then broadcasts the aggregated information
        over a network socket for visualization by external programs.

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
        return_dict: Dict[int, Dict[str, Any]] = {}

        # Event counting
        if received_data["frame_is_hit"] is True:
            self._event_counter.add_hit_event()
        else:
            self._event_counter.add_non_hit_event()

        # Streaming to CrystfEL
        if len(self._request_list) != 0:
            first_request = self._request_list[0]
            if received_data["frame_is_hit"] is True:
                data_to_send: Any = msgpack.packb(
                    {
                        "peak_list": received_data["peak_list"],
                        "beam_energy": received_data["beam_energy"],
                        "detector_distance": received_data["detector_distance"],
                        "event_id": received_data["event_id"],
                        "frame_id": received_data["frame_id"],
                        "timestamp": received_data["timestamp"],
                        "source": self._source,
                        "configuration_file": self._configuration_file,
                    },
                    use_bin_type=True,
                )
                self._responding_socket.send_data(
                    identity=first_request[0], message=data_to_send
                )
                _ = self._request_list.popleft()

        if self._pump_probe_experiment:
            optical_laser_active: bool = received_data["optical_laser_active"]
        else:
            optical_laser_active = False

        # Plots
        curr_hit_rate_timestamp_history: Deque[float]
        curr_hit_rate_history: Deque[float]
        curr_hit_rate_timestamp_history_dark: Union[Deque[float], None]
        curr_hit_rate_history_dark: Union[Deque[float], None]
        curr_virt_powd_plot_img: NDArray[numpy.int_]
        curr_peakogram: NDArray[numpy.int_]
        peak_list_x_in_frame: List[float]
        peak_list_y_in_frame: List[float]
        (
            curr_hit_rate_timestamp_history,
            curr_hit_rate_history,
            curr_hit_rate_timestamp_history_dark,
            curr_hit_rate_history_dark,
            curr_virt_powd_plot_img,
            curr_peakogram,
            peak_list_x_in_frame,
            peak_list_y_in_frame,
        ) = self._plots.update_plots(
            timestamp=received_data["timestamp"],
            peak_list=received_data["peak_list"],
            frame_is_hit=received_data["frame_is_hit"],
            data_shape=received_data["data_shape"],
            optical_laser_active=optical_laser_active,
        )

        if self._event_counter.should_broadcast_data():
            omdata_message: Dict[str, Any] = {
                "geometry_is_optimized": self._geometry_is_optimized,
                "timestamp": received_data["timestamp"],
                "hit_rate_timestamp_history": curr_hit_rate_timestamp_history,
                "hit_rate_history": curr_hit_rate_history,
                "virtual_powder_plot": curr_virt_powd_plot_img,
                "beam_energy": received_data["beam_energy"],
                "detector_distance": received_data["detector_distance"],
                "detector_distance_offset": self._detector_distance_offset,
                "pixel_size": self._pixel_size,
                "pump_probe_experiment": self._pump_probe_experiment,
                "start_timestamp": self._event_counter.get_start_timestamp(),
                "peakogram": curr_peakogram,
                # "peakogram_radius_bin_size": self._peakogram_radius_bin_size,
                # "peakogram_intensity_bin_size": self._peakogram_intensity_bin_size,
            }
            if self._pump_probe_experiment:
                omdata_message[
                    "hit_rate_timestamp_history_dark"
                ] = curr_hit_rate_timestamp_history_dark
                omdata_message["hit_rate_history_dark"] = curr_hit_rate_history_dark

            self._data_broadcast_socket.send_data(
                tag="omdata",
                message=omdata_message,
            )

        # Data broadcast
        if "detector_data" in received_data:
            # If detector frame data is found in the data received from the
            # processing node, it must be broadcasted to visualization programs.

            self._frame_data_img = (
                self._geometry_info.apply_visualization_geometry_to_data(
                    data=received_data["detector_data"]
                )
            )

            self._data_broadcast_socket.send_data(
                tag="omframedata",
                message={
                    "frame_data": self._frame_data_img,
                    "timestamp": received_data["timestamp"],
                    "peak_list_x_in_frame": peak_list_x_in_frame,
                    "peak_list_y_in_frame": peak_list_y_in_frame,
                },
            )
            self._data_broadcast_socket.send_data(
                tag="omtweakingdata",
                message={
                    "detector_data": received_data["detector_data"],
                    "timestamp": received_data["timestamp"],
                },
            )

        if self._event_counter.should_send_hit_frame():
            rank_for_request: int = self._event_counter.get_rank_for_frame_request()
            return_dict[rank_for_request] = {"requests": "hit_frame"}
        if self._event_counter.should_send_non_hit_frame():
            rank_for_request = self._event_counter.get_rank_for_frame_request()
            return_dict[rank_for_request] = {"requests": "non_hit_frame"}

        self._event_counter.report_speed()

        if return_dict:
            return return_dict
        return None

    def end_processing_on_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> Union[Dict[str, Any], None]:
        """
        Ends processing actions on the processing nodes.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function prints a message on the console and ends the processing.

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
        return None

    def end_processing_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Ends processing on the collecting node.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function prints a message on the console and ends the processing.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        console.print(
            f"{get_current_timestamp()} Processing finished. OM has processed "
            f"{self._event_counter.get_num_events()} events in total."
        )
        sys.stdout.flush()

    def _handle_external_requests(self) -> None:
        # This function handles external requests sent to the crystallography monitor
        # over the responding network socket. It either changes the state of the
        # monitor (resetting accumulated data, for example) or returns some data to the
        # requesting party.
        request: Union[
            Tuple[bytes, bytes], None
        ] = self._responding_socket.get_request()
        if request:
            if request[1] == b"next":
                self._request_list.append(request)
            elif request[1] == b"resetplots":
                console.print(
                    f"{get_current_timestamp()} OM Warning: Resetting plots.",
                    style="warning",
                )
                self._plots.clear_plots()

                self._responding_socket.send_data(identity=request[0], message=b"Ok")
            else:
                console.print(
                    f"{get_current_timestamp()} OM Warning: Could not understand "
                    f"request '{str(request[1])}'.",
                    style="warning",
                )
                self._responding_socket.send_data(identity=request[0], message=b"What?")
