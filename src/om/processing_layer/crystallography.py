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
OnDA Monitor for Crystallography.

This module contains an OnDA Monitor for Serial X-ray Crystallography experiments.
"""
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple, Union

import numpy
from numpy.typing import NDArray
from pydantic import BaseModel, Field, ValidationError, model_validator
from typing_extensions import Self

from om.algorithms.generic import Binning, BinningPassthrough
from om.lib.crystallography import CrystallographyPeakFinding, CrystallographyPlots
from om.lib.event_management import EventCounter
from om.lib.exceptions import OmConfigurationFileSyntaxError, OmMissingDependencyError
from om.lib.geometry import DataVisualizer, GeometryInformation
from om.lib.logging import log
from om.lib.zmq import ZmqDataBroadcaster, ZmqResponder
from om.typing import OmProcessingProtocol, TypePeakList, TypePixelMaps

try:
    import msgpack  # type: ignore
except ImportError:
    raise OmMissingDependencyError(
        "The following required module cannot be imported: msgpack"
    )


class _CrystallographyParameters(BaseModel):
    geometry_file: str
    geometry_is_optimized: bool
    post_processing_binning: bool = Field(default=False)
    min_num_peaks_for_hit: int
    max_num_peaks_for_hit: int
    external_data_request_list_size: int = Field(default=20)
    pump_probe_experiment: bool = Field(default=False)
    data_broadcast_url: Optional[str] = Field(default=None)
    responding_url: Optional[str] = Field(default=None)
    speed_report_interval: int
    data_broadcast_interval: int
    hit_frame_sending_interval: Optional[int] = Field(default=None)
    non_hit_frame_sending_interval: Optional[int] = Field(default=None)


class _OmParameters(BaseModel):
    source: str
    configuration_file: Path


class _MonitorParameters(BaseModel):
    crystallography: _CrystallographyParameters
    om: _OmParameters
    binning: Optional[Dict[str, Any]] = Field(default=None)

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


class CrystallographyProcessing(OmProcessingProtocol):
    """
    See documentation for the `__init__` function.
    """

    def __init__(self, *, parameters: Dict[str, Any]) -> None:
        """
        OnDA Monitor for Crystallography.

        This Processing class implements an OnDA Monitor for Serial Crystallography
        experiments. The monitor processes detector data frames, detecting Bragg peaks
        in each frame using the
        [`Peakfinder8PeakDetection`][om.algorithms.crystallography.Peakfinder8PeakDetection]
        algorithm, It retrieves information about the location, size, intensity, SNR
        and maximum pixel value of each peak. The monitor also calculates the evolution
        of the hit rate over time, and can additionally optionally collect examples of
        hit and non-hit calibrated detector data frames. All the information retrieved
        from the facility or extracted from the data is streamed to external programs
        (like
        [OM's Crystallography GUI][om.graphical_interfaces.crystallography_gui.CrystallographyGui]  # noqa: E501
        or
        [OM's Frame Viewer][om.graphical_interfaces.frame_viewer.FrameViewer]) for
        visualization.
        The monitor can also respond to requests for data or change of behavior from
        external programs (a control GUI, for example.)

        Arguments:

            monitor_parameters: An object storing OM's configuration parameters.
        """
        self._monitor_parameters: Dict[str, Any] = parameters

        try:
            self._parameters: _MonitorParameters = _MonitorParameters.model_validate(
                self._monitor_parameters
            )
        except ValidationError as exception:
            raise OmConfigurationFileSyntaxError(
                "Error parsing OM's configuration parameters: " f"{exception}"
            )

        # Geometry
        self._geometry_information = GeometryInformation.from_file(
            geometry_filename=self._parameters.crystallography.geometry_file
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

    def initialize_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes the processing nodes for the Crystallography Monitor.

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

        # Frame sending
        self._send_hit_frame: bool = False
        self._send_non_hit_frame: bool = False

        # Console
        log.info(f"Processing node {node_rank} starting")

    def initialize_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes the collecting node for the Crystallography Monitor.

        This function initializes the data accumulation algorithms and the storage
        buffers used to compute statistics on the aggregated data. Additionally,
        it prepares all the necessary network sockets.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """

        # Geometry
        self._detector_distance_offset: float = (
            self._geometry_information.get_detector_distance_offset()
        )

        self._pixel_size = self._geometry_information.get_pixel_size()
        pixel_maps: TypePixelMaps = self._geometry_information.get_pixel_maps()

        self._pixel_size /= self._post_processing_binning.get_bin_size()
        binned_pixel_maps = self._post_processing_binning.bin_pixel_maps(
            pixel_maps=pixel_maps
        )

        # Data visualizer
        self._data_visualizer: DataVisualizer = DataVisualizer(
            pixel_maps=binned_pixel_maps
        )

        # Data broadcast
        self._data_broadcast_socket: ZmqDataBroadcaster = ZmqDataBroadcaster(
            data_broadcast_url=self._parameters.crystallography.data_broadcast_url
        )

        # Plots
        self._plots: CrystallographyPlots = CrystallographyPlots(
            parameters=self._monitor_parameters,
            data_visualizer=self._data_visualizer,
            pump_probe_experiment=(
                self._parameters.crystallography.pump_probe_experiment
            ),
            bin_size=self._post_processing_binning.get_bin_size(),
        )

        # Streaming to CrystFEL
        self._request_list: Deque[Tuple[bytes, bytes]] = deque(
            maxlen=self._parameters.crystallography.external_data_request_list_size
        )

        self._responding_socket: ZmqResponder = ZmqResponder(
            responding_url=self._parameters.crystallography.responding_url
        )

        # Event counting
        self._event_counter: EventCounter = EventCounter(
            speed_report_interval=(
                self._parameters.crystallography.speed_report_interval
            ),
            data_broadcast_interval=(
                self._parameters.crystallography.data_broadcast_interval
            ),
            hit_frame_sending_interval=(
                self._parameters.crystallography.hit_frame_sending_interval
            ),
            non_hit_frame_sending_interval=(
                self._parameters.crystallography.non_hit_frame_sending_interval
            ),
            node_pool_size=node_pool_size,
        )

        # Console
        log.info("Starting the monitor...")

    def process_data(
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

        processed_data: Dict[str, Any] = {}

        # Peak-finding
        peak_list: TypePeakList = self._peak_detection.find_peaks(
            detector_data=data["detector_data"]
        )

        peak_list = self._post_processing_binning.bin_peak_positions(
            peak_list=peak_list
        )

        frame_is_hit: bool = (
            self._parameters.crystallography.min_num_peaks_for_hit
            < len(peak_list["intensity"])
            < self._parameters.crystallography.max_num_peaks_for_hit
        )

        # Data to send
        processed_data["timestamp"] = data["timestamp"]
        processed_data["frame_is_hit"] = frame_is_hit
        processed_data["detector_distance"] = data["detector_distance"]
        processed_data["beam_energy"] = data["beam_energy"]
        processed_data["event_id"] = data["event_id"]
        processed_data["peak_list"] = peak_list
        if self._parameters.crystallography.pump_probe_experiment:
            processed_data["optical_laser_active"] = data["optical_laser_active"]

        # Frame sending
        if "requests" in data:
            if data["requests"] == "hit_frame":
                self._send_hit_frame = True
            if data["requests"] == "non_hit_frame":
                self._send_non_hit_frame = True

        send_detector_data: bool = (frame_is_hit and self._send_hit_frame) or (
            not frame_is_hit and self._send_non_hit_frame
        )

        if send_detector_data:
            data_to_send: Union[NDArray[numpy.int_], NDArray[numpy.float_]] = data[
                "detector_data"
            ]

            data_to_send = self._post_processing_binning.bin_detector_data(
                data=data_to_send
            )

            processed_data["detector_data"] = data_to_send
            if frame_is_hit:
                self._send_hit_frame = False
            else:
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

        This function receives requests from external programs over a network socket
        and reacts according to the nature of the request, sending data back to the
        source of the request or modifying the internal behavior of the monitor.

        Please see the documentation of the base Protocol class for additional
        information about this method.

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
    ) -> Optional[Dict[int, Dict[str, Any]]]:
        """
        Computes statistics on aggregated data and broadcasts data to external programs.

        This function collects and accumulates frame- and peak-related information
        received from the processing nodes. It also computes a rolling average
        estimation of the hit rate evolution over time. Additionally, it uses the
        Bragg peak information to compute a virtual powder pattern and a peakogram plot.
        All the aggregated information (and optionally, examples of hit and non-hit
        detector data frames) is then broadcast to external programs for visualization.

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
                        "timestamp": received_data["timestamp"],
                        "source": self._parameters.om.source,
                        "configuration_file": self._parameters.om.configuration_file,
                    },
                    use_bin_type=True,
                )
                self._responding_socket.send_data(
                    identity=first_request[0], message=data_to_send
                )
                _ = self._request_list.popleft()

        if self._parameters.crystallography.pump_probe_experiment:
            optical_laser_active: bool = received_data["optical_laser_active"]
        else:
            optical_laser_active = False

        # Plots
        curr_hit_rate_timestamp_history: Deque[float]
        curr_hit_rate_history: Deque[float]
        curr_hit_rate_timestamp_history_dark: Optional[Deque[float]]
        curr_hit_rate_history_dark: Optional[Deque[float]]
        curr_virt_powd_plot_img: NDArray[numpy.int_]
        curr_peakogram: NDArray[numpy.float_]
        peakogram_radius_bin_size: float
        peakogram_intensity_bin_size: float
        peak_list_x_in_frame: List[float]
        peak_list_y_in_frame: List[float]
        (
            curr_hit_rate_timestamp_history,
            curr_hit_rate_history,
            curr_hit_rate_timestamp_history_dark,
            curr_hit_rate_history_dark,
            curr_virt_powd_plot_img,
            curr_peakogram,
            peakogram_radius_bin_size,
            peakogram_intensity_bin_size,
            peak_list_x_in_frame,
            peak_list_y_in_frame,
        ) = self._plots.update_plots(
            timestamp=received_data["timestamp"],
            peak_list=received_data["peak_list"],
            frame_is_hit=received_data["frame_is_hit"],
            optical_laser_active=optical_laser_active,
        )

        if self._event_counter.should_broadcast_data():
            omdata_message: Dict[str, Any] = {
                "geometry_is_optimized": (
                    self._parameters.crystallography.geometry_is_optimized
                ),
                "timestamp": received_data["timestamp"],
                "hit_rate_timestamp_history": curr_hit_rate_timestamp_history,
                "hit_rate_history": curr_hit_rate_history,
                "virtual_powder_plot": curr_virt_powd_plot_img,
                "beam_energy": received_data["beam_energy"],
                "detector_distance": received_data["detector_distance"],
                "detector_distance_offset": self._detector_distance_offset,
                "pixel_size": self._pixel_size,
                "pump_probe_experiment": (
                    self._parameters.crystallography.pump_probe_experiment
                ),
                "start_timestamp": self._event_counter.get_start_timestamp(),
                "peakogram": curr_peakogram,
                "peakogram_radius_bin_size": peakogram_radius_bin_size,
                "peakogram_intensity_bin_size": peakogram_intensity_bin_size,
            }
            if self._parameters.crystallography.pump_probe_experiment:
                omdata_message["hit_rate_timestamp_history_dark"] = (
                    curr_hit_rate_timestamp_history_dark
                )
                omdata_message["hit_rate_history_dark"] = curr_hit_rate_history_dark

            self._data_broadcast_socket.send_data(
                tag="omdata",
                message=omdata_message,
            )

        # Data broadcast
        if "detector_data" in received_data:
            # If detector frame data is found in the data received from the
            # processing node, it must be broadcasted to visualization programs.

            self._frame_data_img = self._data_visualizer.visualize_data(
                data=received_data["detector_data"],
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
            if self._post_processing_binning.is_passthrough():
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
    ) -> Optional[Dict[str, Any]]:
        """
        Ends processing on the processing nodes for the Crystallography Monitor.

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
        return None

    def end_processing_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Ends processing on the collecting node for the Crystallography Monitor.

        This function prints a message on the console and ends the processing.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        log.info(
            "Processing finished. OM has processed "
            f"{self._event_counter.get_num_events()} events in total."
        )

    def _handle_external_requests(self) -> None:
        # This function handles external requests sent to the crystallography monitor
        # over the responding network socket. It either changes the state of the
        # monitor (resetting accumulated data, for example) or returns some data to the
        # requesting party.
        request: Optional[Tuple[bytes, bytes]] = self._responding_socket.get_request()
        if request:
            if request[1] == b"next":
                self._request_list.append(request)
            elif request[1] == b"resetplots":
                log.warn("Resetting plots.")
                self._plots.clear_plots()

                self._responding_socket.send_data(identity=request[0], message=b"Ok")
            else:
                log.warn(
                    f"Could not understand the following request: {str(request[1])}.",
                )
                self._responding_socket.send_data(identity=request[0], message=b"What?")
