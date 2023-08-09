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
import sys
from itertools import islice
from typing import Any, Deque, Dict, Tuple, Union

import numpy
from numpy.typing import NDArray

from om.algorithms.generic import Binning, BinningPassthrough
from om.lib.cheetah import HDF5Writer
from om.lib.event_management import EventCounter
from om.lib.geometry import DataVisualizer, GeometryInformation, TypePixelMaps
from om.lib.parameters import MonitorParameters, get_parameter_from_parameter_group
from om.lib.radial_profile import RadialProfileAnalysis, RadialProfileAnalysisPlots
from om.lib.rich_console import console, get_current_timestamp
from om.lib.zmq import ZmqDataBroadcaster
from om.protocols.processing_layer import OmProcessingProtocol


class SwaxsProcessing(OmProcessingProtocol):
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
        self._radial_parameters: Dict[
            str, Any
        ] = self._monitor_params.get_parameter_group(group="radial")

        # Geometry
        self._geometry_information = GeometryInformation.from_file(
            geometry_filename=get_parameter_from_parameter_group(
                group=self._radial_parameters,
                parameter="geometry_file",
                parameter_type=str,
                required=True,
            )
        )

        # Post-processing binning
        binning_requested = get_parameter_from_parameter_group(
            group=self._radial_parameters,
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
        # Radial Profile Analysis

        # Sample detection
        self._total_intensity_jet_threshold: float = get_parameter_from_parameter_group(
            group=self._radial_parameters,
            parameter="total_intensity_jet_threshold",
            parameter_type=float,
            required=True,
        )
        self._radial_profile_analysis: RadialProfileAnalysis = RadialProfileAnalysis(
            geometry_information=self._geometry_information,
            radial_parameters=self._monitor_params.get_parameter_group(group="radial"),
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

        # Data broadcast
        self._data_broadcast_socket: ZmqDataBroadcaster = ZmqDataBroadcaster(
            parameters=self._monitor_params.get_parameter_group(group="radial")
        )

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

        # Plots
        self._plots: RadialProfileAnalysisPlots = RadialProfileAnalysisPlots(
            radial_parameters=self._monitor_params.get_parameter_group(group="radial"),
        )

        # Data to send
        self._num_radials_to_send = get_parameter_from_parameter_group(
            group=self._radial_parameters,
            parameter="num_radials_to_send",
            parameter_type=int,
            required=True,
        )

        # Event counting
        self._event_counter: EventCounter = EventCounter(
            om_parameters=self._monitor_params.get_parameter_group(group="radial"),
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
        processed_data: Dict[str, Any] = {}

        radial_profile: NDArray[numpy.float_]
        errors: NDArray[numpy.float_]
        q: NDArray[numpy.float_]
        sample_detected: bool
        roi1_intensity: float
        roi2_intensity: float
        rg: float
        detector_data_sum: float
        (
            radial_profile,
            errors,
            q,
            sample_detected,
            roi1_intensity,
            roi2_intensity,
            rg,
            detector_data_sum,
        ) = self._radial_profile_analysis.analyze_radial_profile(
            data=data["detector_data"],
            beam_energy=data["beam_energy"],
            detector_distance=data["detector_distance"],
            downstream_intensity=data["post_sample_intensity"],
        )

        # detector_data_sum: float = data["detector_data"].sum()

        processed_data["radial_profile"] = radial_profile
        processed_data["detector_data_sum"] = detector_data_sum
        processed_data["q"] = q
        processed_data["downstream_intensity"] = data["post_sample_intensity"]
        processed_data["roi1_intensity"] = roi1_intensity
        processed_data["roi2_intensity"] = roi2_intensity
        processed_data["sample_detected"] = sample_detected
        processed_data["timestamp"] = data["timestamp"]
        processed_data["detector_distance"] = data["detector_distance"]
        processed_data["beam_energy"] = data["beam_energy"]
        processed_data["event_id"] = data["event_id"]
        processed_data["rg"] = rg

        # Frame sending
        if "requests" in data:
            if data["requests"] == "hit_frame":
                self._send_hit_frame = True
            if data["requests"] == "non_hit_frame":
                self._send_non_hit_frame = True

        send_detector_data: bool = (sample_detected and self._send_hit_frame) or (
            not sample_detected and self._send_non_hit_frame
        )

        if send_detector_data:
            data_to_send: Union[NDArray[numpy.int_], NDArray[numpy.float_]] = data[
                "detector_data"
            ]

            data_to_send = self._post_processing_binning.bin_detector_data(
                data=data_to_send
            )

            processed_data["detector_data"] = data_to_send
            if sample_detected:
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
        pass

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
        received_data: Dict[str, Any] = processed_data[0]
        return_dict: Dict[int, Dict[str, Any]] = {}

        q_history: Deque[NDArray[numpy.float_]]
        radials_history: Deque[NDArray[numpy.float_]]
        image_sum_history: Deque[float]
        downstream_intensity_history: Deque[float]
        roi1_intensity_history: Deque[float]
        roi2_intensity_history: Deque[float]
        hit_rate_history: Deque[float]
        rg_history: Deque[float]
        cumulative_hits_radial: NDArray[numpy.float_]
        (
            q_history,
            radials_history,
            image_sum_history,
            downstream_intensity_history,
            roi1_intensity_history,
            roi2_intensity_history,
            hit_rate_history,
            rg_history,
            cumulative_hits_radial
        ) = self._plots.update_plots(
            radial_profile=received_data["radial_profile"],
            detector_data_sum=received_data["detector_data_sum"],
            q=received_data["q"],
            downstream_intensity=received_data["downstream_intensity"],
            roi1_intensity=received_data["roi1_intensity"],
            roi2_intensity=received_data["roi2_intensity"],
            sample_detected=received_data["sample_detected"],
            rg=received_data["rg"],
        )

        # Event counting
        if received_data["sample_detected"] is True:
            self._event_counter.add_hit_event()
        else:
            self._event_counter.add_non_hit_event()

        if self._event_counter.should_broadcast_data():
            message: Dict[str, Any] = {
                "q": received_data["q"],
                "radial_profile": received_data["radial_profile"],
                "radial_stack": numpy.array(
                    list(
                        islice(
                            radials_history,
                            (len(radials_history) - self._num_radials_to_send)
                            if (len(q_history) - self._num_radials_to_send) > 0
                            else 0,
                            len(q_history),
                        )
                    )
                ),
                "cumulative_hits_radial": numpy.array(cumulative_hits_radial),
                "downstream_monitor_history": numpy.array(downstream_intensity_history),
                "roi1_int_history": numpy.array(roi1_intensity_history),
                "roi2_int_history": numpy.array(roi2_intensity_history),
                "hit_rate_history": numpy.array(hit_rate_history),
                "image_sum_history": numpy.array(image_sum_history),
                "rg_history": numpy.array(rg_history),
                "timestamp": received_data["timestamp"],
                "detector_distance": received_data["detector_distance"],
                "beam_energy": received_data["beam_energy"],
            }
            message["recent_radial_average"] = numpy.mean(
                message["radial_stack"], axis=0
            )

            self._data_broadcast_socket.send_data(
                tag="omdata",
                message=message,
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
                    "peak_list_x_in_frame": [],
                    "peak_list_y_in_frame": [],
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


class SwaxsCheetahProcessing(OmProcessingProtocol):
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
        self._radial_parameters: Dict[
            str, Any
        ] = self._monitor_params.get_parameter_group(group="radial")

        # Geometry
        self._geometry_information = GeometryInformation.from_file(
            geometry_filename=get_parameter_from_parameter_group(
                group=self._radial_parameters,
                parameter="geometry_file",
                parameter_type=str,
                required=True,
            )
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
        # Radial Profile Analysis

        # Sample detection
        self._total_intensity_jet_threshold: float = get_parameter_from_parameter_group(
            group=self._radial_parameters,
            parameter="total_intensity_jet_threshold",
            parameter_type=float,
            required=True,
        )
        self._radial_profile_analysis: RadialProfileAnalysis = RadialProfileAnalysis(
            geometry_information=self._geometry_information,
            radial_parameters=self._monitor_params.get_parameter_group(group="radial"),
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
        # Plots
        self._plots: RadialProfileAnalysisPlots = RadialProfileAnalysisPlots(
            radial_parameters=self._monitor_params.get_parameter_group(group="radial"),
        )

        # File Writing
        self._writer = HDF5Writer(
            node_rank=node_rank,
            cheetah_parameters=self._monitor_params.get_parameter_group(
                group="radial_cheetah"
            ),
        )

        # Event counting
        self._event_counter: EventCounter = EventCounter(
            om_parameters=self._monitor_params.get_parameter_group(group="radial"),
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
        processed_data: Dict[str, Any] = {}

        mask = self._radial_profile_analysis._radial_profile_bad_pixel_map
        print(mask.sum(), mask.size)

        radial_profile: NDArray[numpy.float_]
        q: NDArray[numpy.float_]
        sample_detected: bool
        roi1_intensity: float
        roi2_intensity: float
        rg: float
        detector_data_sum: float
        (
            radial_profile,
            q,
            sample_detected,
            roi1_intensity,
            roi2_intensity,
            rg,
            detector_data_sum,
        ) = self._radial_profile_analysis.analyze_radial_profile(
            data=data["detector_data"],
            beam_energy=data["beam_energy"],
            detector_distance=data["detector_distance"],
            downstream_intensity=data["post_sample_intensity"],
        )

        # detector_data_sum: float = data["detector_data"].sum()

        processed_data["radial_profile"] = radial_profile
        processed_data["detector_data_sum"] = detector_data_sum
        processed_data["q"] = q
        processed_data["downstream_intensity"] = data["post_sample_intensity"]
        processed_data["roi1_intensity"] = roi1_intensity
        processed_data["roi2_intensity"] = roi2_intensity
        processed_data["sample_detected"] = sample_detected
        processed_data["timestamp"] = data["timestamp"]
        processed_data["detector_distance"] = data["detector_distance"]
        processed_data["beam_energy"] = data["beam_energy"]
        processed_data["event_id"] = data["event_id"]
        processed_data["rg"] = rg

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
        pass

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
        received_data: Dict[str, Any] = processed_data[0]
        return_dict: Dict[int, Dict[str, Any]] = {}

        q_history: Deque[NDArray[numpy.float_]]
        radials_history: Deque[NDArray[numpy.float_]]
        image_sum_history: Deque[float]
        downstream_intensity_history: Deque[float]
        roi1_intensity_history: Deque[float]
        roi2_intensity_history: Deque[float]
        (
            q_history,
            radials_history,
            image_sum_history,
            downstream_intensity_history,
            roi1_intensity_history,
            roi2_intensity_history,
            hit_rate_history,
            rg_history,
        ) = self._plots.update_plots(
            radial_profile=received_data["radial_profile"],
            detector_data_sum=received_data["detector_data_sum"],
            q=received_data["q"],
            downstream_intensity=received_data["downstream_intensity"],
            roi1_intensity=received_data["roi1_intensity"],
            roi2_intensity=received_data["roi2_intensity"],
            sample_detected=received_data["sample_detected"],
            rg=received_data["rg"],
            frame_sum=received_data["frame_sum"],
        )

        # Event counting
        if received_data["sample_detected"] is True:
            self._event_counter.add_hit_event()
        else:
            self._event_counter.add_non_hit_event()

        # File writing
        data_to_write: Dict[str, Any] = {
            "q": received_data["q"],
            "radial": received_data["radial_profile"],
            "detector_data_sum": received_data["detector_data_sum"],
            "timestamp": received_data["timestamp"],
            "sample_detected": received_data["sample_detected"],
            "detector_distance": received_data["detector_distance"],
            "beam_energy": received_data["beam_energy"],
            "event_id": received_data["event_id"],
        }
        self._writer.write_frame(processed_data=data_to_write)

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
        # Sort frames and write final list files
        # Write final status
        self._writer.close()

        console.print(
            f"{get_current_timestamp()} Processing finished. OM has processed "
            f"{self._event_counter.get_num_events()} events in total."
        )
        sys.stdout.flush()
