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
import time
from typing import Any, Deque, Dict, List, Tuple, Union

import numpy  # type: ignore

from om.algorithms import crystallography as cryst_algs
from om.algorithms import generic as gen_algs
from om.processing_layer import base as pl_base
from om.utils import crystfel_geometry, exceptions, parameters, zmq_monitor
from om.utils.crystfel_geometry import TypeDetector, TypePixelMaps

try:
    import msgpack  # type: ignore
except ImportError:
    raise exceptions.OmMissingDependencyError(
        "The following required module cannot be imported: msgpack"
    )


class CrystallographyProcessing(pl_base.OmProcessing):
    """
    See documentation for the `__init__` function.

    Base class: [`OmProcessing`][om.processing_layer.base.OmProcessing]
    """

    def __init__(self, *, monitor_parameters: parameters.MonitorParams) -> None:
        """
        OnDA real-time Monitor for serial x-ray crystallography experiments.

        This class contains an OnDA Monitor that processes detector data frames,
        optionally applying detector calibration, dark correction and gain correction.
        The Monitor then detects Bragg peaks in each detector frame using the
        'peakfinder8' peak detection algorithm from the Cheetah software package. It
        retrieves information about the location, size and intensity of each peak.
        Additionally, it calculates the evolution of the hit rate over time. It
        broadcasts all this information over a network socket for visualization by
        other programs. This OnDA Monitor can also optionally broadcast calibrated and
        corrected detector data frames to be displayed by an external program.

        This class is a subclass of the
        [OmProcessing][om.processing_layer.base.OmProcessing] base class.

        Arguments:

          monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.
        """
        self._monitor_params = monitor_parameters

    def initialize_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes the OM processing nodes for the Crystallography Monitor.

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

        self._pixelmaps: TypePixelMaps = (
            crystfel_geometry.pixel_maps_from_geometry_file(
                filename=self._monitor_params.get_parameter(
                    group="crystallography",
                    parameter="geometry_file",
                    parameter_type=str,
                    required=True,
                )
            )
        )

        self._correction = gen_algs.Correction(
            parameters=self._monitor_params.get_parameter_group(group="correction")
        )

        self._peak_detection: cryst_algs.Peakfinder8PeakDetection = (
            cryst_algs.Peakfinder8PeakDetection(
                parameters=self._monitor_params.get_parameter_group(
                    group="peakfinder8_peak_detection"
                ),
                radius_pixel_map=self._pixelmaps["radius"],
            )
        )

        self._min_num_peaks_for_hit: int = self._monitor_params.get_parameter(
            group="crystallography",
            parameter="min_num_peaks_for_hit",
            parameter_type=int,
            required=True,
        )
        self._max_num_peaks_for_hit: int = self._monitor_params.get_parameter(
            group="crystallography",
            parameter="max_num_peaks_for_hit",
            parameter_type=int,
            required=True,
        )

        self._calculate_radial_profile: Union[
            bool, None
        ] = self._monitor_params.get_param(
            group="crystallography",
            parameter="calculate_radial_profile",
            parameter_type=bool,
            required=False,
        )
        if self._calculate_radial_profile is None:
            self._calculate_radial_profile = False
        if self._calculate_radial_profile:
            self._radial_profile: gen_algs.RadialProfile = gen_algs.RadialProfile(
                radius_pixel_map=self._pixelmaps["radius"],
                parameters=self._monitor_params.get_parameter_group(
                    group="radial_profile"
                ),
            )
        self._hit_frame_sending_interval: Union[
            int, None
        ] = self._monitor_params.get_parameter(
            group="crystallography",
            parameter="hit_frame_sending_interval",
            parameter_type=int,
        )
        self._non_hit_frame_sending_interval: Union[
            int, None
        ] = self._monitor_params.get_parameter(
            group="crystallography",
            parameter="non_hit_frame_sending_interval",
            parameter_type=int,
        )

        self._hit_frame_sending_counter: int = 0
        self._non_hit_frame_sending_counter: int = 0

        print("Processing node {0} starting.".format(node_rank))
        sys.stdout.flush()

    def initialize_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes the OM collecting node for the Crystallography Monitor.

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
        self._speed_report_interval: int = self._monitor_params.get_parameter(
            group="crystallography",
            parameter="speed_report_interval",
            parameter_type=int,
            required=True,
        )

        self._data_broadcast_interval: int = self._monitor_params.get_parameter(
            group="crystallography",
            parameter="data_broadcast_interval",
            parameter_type=int,
            required=True,
        )

        self._geometry_is_optimized: bool = self._monitor_params.get_parameter(
            group="crystallography",
            parameter="geometry_is_optimized",
            parameter_type=bool,
            required=True,
        )

        geometry: TypeDetector
        self._geometry, _, __ = crystfel_geometry.load_crystfel_geometry(
            filename=self._monitor_params.get_parameter(
                group="crystallography",
                parameter="geometry_file",
                parameter_type=str,
                required=True,
            )
        )
        self._pixelmaps = crystfel_geometry.compute_pix_maps(geometry=self._geometry)

        # Theoretically, the pixel size anc coffsetcould be different for every panel
        # of the detector. Currently, the pixel size and coffset of the first module
        # are taken as the pixel size and coffset of the whole detector.
        self._pixel_size: float = self._geometry["panels"][
            tuple(self._geometry["panels"].keys())[0]
        ]["res"]
        self._first_panel_coffset: float = self._geometry["panels"][
            list(self._geometry["panels"].keys())[0]
        ]["coffset"]

        self._running_average_window_size: int = self._monitor_params.get_parameter(
            group="crystallography",
            parameter="running_average_window_size",
            parameter_type=int,
            required=True,
        )
        self._hit_rate_running_window: Deque[float] = collections.deque(
            [0.0] * self._running_average_window_size,
            maxlen=self._running_average_window_size,
        )
        self._avg_hit_rate: int = 0
        self._hit_rate_timestamp_history: Deque[float] = collections.deque(
            5000 * [0.0], maxlen=5000
        )
        self._hit_rate_history: Deque[float] = collections.deque(
            5000 * [0.0], maxlen=5000
        )

        y_minimum: int = (
            2
            * int(max(abs(self._pixelmaps["y"].max()), abs(self._pixelmaps["y"].min())))
            + 2
        )
        x_minimum: int = (
            2
            * int(max(abs(self._pixelmaps["x"].max()), abs(self._pixelmaps["x"].min())))
            + 2
        )
        visual_img_shape: Tuple[int, int] = (y_minimum, x_minimum)
        self._img_center_x: int = int(visual_img_shape[1] / 2)
        self._img_center_y: int = int(visual_img_shape[0] / 2)
        self._visual_pixelmap_x: numpy.ndarray = (
            numpy.array(self._pixelmaps["x"], dtype=numpy.int)
            + visual_img_shape[1] // 2
            - 1
        ).flatten()
        self._visual_pixelmap_y: numpy.ndarray = (
            numpy.array(self._pixelmaps["y"], dtype=numpy.int)
            + visual_img_shape[0] // 2
            - 1
        ).flatten()
        self._virt_powd_plot_img: numpy.ndarray = numpy.zeros(
            visual_img_shape, dtype=numpy.int32
        )
        self._frame_data_img: numpy.ndarray = numpy.zeros(
            visual_img_shape, dtype=numpy.float32
        )

        self._data_broadcast_socket: zmq_monitor.ZmqDataBroadcaster = (
            zmq_monitor.ZmqDataBroadcaster(
                parameters=self._monitor_params.get_parameter_group(
                    group="crystallography"
                )
            )
        )

        self._responding_socket: zmq_monitor.ZmqResponder = zmq_monitor.ZmqResponder(
            parameters=self._monitor_params.get_parameter_group(group="crystallography")
        )

        self._num_events: int = 0
        self._old_time: float = time.time()
        self._time: Union[float, None] = None

        print("Starting the monitor...")
        sys.stdout.flush()

    def process_data(
        self, *, node_rank: int, node_pool_size: int, data: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], int]:
        """
        Processes a detector data frame and extracts Bragg peak information.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function performs calibration and correction of a detector data frame and
        extracts Bragg peak information. Finally, it prepares the Bragg peak data (and
        optionally, the detector frame data) for transmission to to the collecting
        node.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

            data: A dictionary containing the data retrieved by OM for the frame being
                processed.

                * The dictionary keys must match the entries in the 'required_data'
                  list found in the 'om' parameter group in the configuration file.

                * The corresponding dictionary values must store the retrieved data.

        Returns:

            A tuple whose first entry is a dictionary storing the data that should be
            sent to the collecting node, and whose second entry is the OM rank number
            of the node that processed the information.
        """
        processed_data: Dict[str, Any] = {}
        corrected_detector_data: numpy.ndarray = self._correction.apply_correction(
            data=data["detector_data"]
        )
        peak_list: cryst_algs.TypePeakList = self._peak_detection.find_peaks(
            data=corrected_detector_data
        )
        frame_is_hit: bool = (
            self._min_num_peaks_for_hit
            < len(peak_list["intensity"])
            < self._max_num_peaks_for_hit
        )
        if self._calculate_radial_profile:
            processed_data["radial_average"] = self._radial_profile.calculate_profile(
                corrected_detector_data
            )

        processed_data["timestamp"] = data["timestamp"]
        processed_data["frame_is_hit"] = frame_is_hit
        processed_data["detector_distance"] = data["detector_distance"]
        processed_data["beam_energy"] = data["beam_energy"]
        processed_data["event_id"] = data["event_id"]
        processed_data["frame_id"] = data["frame_id"]
        processed_data["data_shape"] = data["detector_data"].shape
        if frame_is_hit:
            processed_data["peak_list"] = peak_list
            if self._hit_frame_sending_interval is not None:
                self._hit_frame_sending_counter += 1
                if self._hit_frame_sending_counter == self._hit_frame_sending_interval:
                    # If the frame is a hit, and if the 'hit_sending_interval'
                    # attribute says that the detector frame data should be sent to
                    # the collecting node, adds the data to the 'processed_data'
                    # dictionary (and resets the counter).
                    processed_data["detector_data"] = corrected_detector_data
                    self._hit_frame_sending_counter = 0
        else:
            # If the frame is not a hit, sends an empty peak list.
            processed_data["peak_list"] = {"fs": [], "ss": [], "intensity": []}
            if self._non_hit_frame_sending_interval is not None:
                self._non_hit_frame_sending_counter += 1
                if (
                    self._non_hit_frame_sending_counter
                    == self._non_hit_frame_sending_interval
                ):
                    # If the frame is a not a hit, and if the 'hit_sending_interval'
                    # attribute says that the detector frame data should be sent to
                    # the collecting node, adds the data to the 'processed_data'
                    # dictionary (and resets the counter).
                    processed_data["detector_data"] = corrected_detector_data
                    self._non_hit_frame_sending_counter = 0

        return (processed_data, node_rank)

    def collect_data(
        self,
        *,
        node_rank: int,
        node_pool_size: int,
        processed_data: Tuple[Dict[str, Any], int],
    ) -> None:
        """
        Computes statistics on aggregated Bragg peak data broadcasts them.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function collects the Bragg peak information from the processing nodes and
        computes the average hit rate and a virtual powder pattern. It then broadcasts
        this information over a network socket for visualization by external programs.
        This function also broadcasts any detector frame data received from the
        processing nodes.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

            processed_data (Tuple[Dict, int]): a tuple whose first entry is a
                dictionary storing the data received from a processing node, and whose
                second entry is the OM rank number of the node that processed the
                information.
        """
        received_data: Dict[str, Any] = processed_data[0]
        self._num_events += 1

        if received_data["frame_is_hit"] is True:
            request: Union[str, None] = self._responding_socket.get_request()
            if request is not None:
                if request == "next":
                    message: Any = msgpack.packb(
                        {
                            "peak_list": received_data["peak_list"],
                            "beam_energy": received_data["beam_energy"],
                            "detector_distance": received_data["detector_distance"],
                            "event_id": received_data["event_id"],
                            "frame_id": received_data["frame_id"],
                            "timestamp": received_data["timestamp"],
                        },
                        use_bin_type=True,
                    )
                    self._responding_socket.send_data(message=message)
                else:
                    print("OM Warning: Could not understand request '{}'.")

        self._hit_rate_running_window.append(float(received_data["frame_is_hit"]))
        avg_hit_rate: float = (
            sum(self._hit_rate_running_window) / self._running_average_window_size
        )
        self._hit_rate_timestamp_history.append(received_data["timestamp"])
        self._hit_rate_history.append(avg_hit_rate * 100.0)

        peak_list_x_in_frame: List[float] = []
        peak_list_y_in_frame: List[float] = []
        peak_fs: float
        peak_ss: float
        peak_value: float
        for peak_fs, peak_ss, peak_value in zip(
            received_data["peak_list"]["fs"],
            received_data["peak_list"]["ss"],
            received_data["peak_list"]["intensity"],
        ):
            peak_index_in_slab: int = int(round(peak_ss)) * received_data["data_shape"][
                1
            ] + int(round(peak_fs))
            y_in_frame: float = self._visual_pixelmap_y[peak_index_in_slab]
            x_in_frame: float = self._visual_pixelmap_x[peak_index_in_slab]
            peak_list_x_in_frame.append(y_in_frame)
            peak_list_y_in_frame.append(x_in_frame)
            self._virt_powd_plot_img[y_in_frame, x_in_frame] += peak_value

        if self._num_events % self._data_broadcast_interval == 0:
            self._data_broadcast_socket.send_data(
                tag="view:omdata",
                message={
                    "geometry_is_optimized": self._geometry_is_optimized,
                    "timestamp": received_data["timestamp"],
                    "hit_rate_timestamp_history": self._hit_rate_timestamp_history,
                    "hit_rate_history": self._hit_rate_history,
                    "virtual_powder_plot": self._virt_powd_plot_img,
                    "beam_energy": received_data["beam_energy"],
                    "detector_distance": received_data["detector_distance"],
                    "first_panel_coffset": self._first_panel_coffset,
                    "pixel_size": self._pixel_size,
                },
            )

            if "detector_data" in received_data:
                # If detector frame data is found in the data received from the
                # processing node, it must be broadcasted to visualization programs.

                self._frame_data_img[
                    self._visual_pixelmap_y, self._visual_pixelmap_x
                ] = (
                    received_data["detector_data"]
                    .ravel()
                    .astype(self._frame_data_img.dtype)
                )

                self._data_broadcast_socket.send_data(
                    tag="view:omframedata",
                    message={
                        "frame_data": self._frame_data_img,
                        "timestamp": received_data["timestamp"],
                        "peak_list_x_in_frame": peak_list_x_in_frame,
                        "peak_list_y_in_frame": peak_list_y_in_frame,
                    },
                )
                self._data_broadcast_socket.send_data(
                    tag="view:omtweakingdata",
                    message={
                        "detector_data": received_data["detector_data"],
                        "timestamp": received_data["timestamp"],
                    },
                )

            if "radial_average" in received_data:
                self._data_broadcast_socket.send_data(
                    tag="view:omradialaverage",
                    message={
                        "radial_average": received_data["radial_average"],
                        "timestamp": received_data["timestamp"],
                    },
                )

        if self._num_events % self._speed_report_interval == 0:
            now_time: float = time.time()
            speed_report_msg: str = (
                "Processed: {0} in {1:.2f} seconds "
                "({2:.2f} Hz)".format(
                    self._num_events,
                    now_time - self._old_time,
                    (
                        float(self._speed_report_interval)
                        / float(now_time - self._old_time)
                    ),
                )
            )
            print(speed_report_msg)
            sys.stdout.flush()
            self._old_time = now_time

    def end_processing_on_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
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

            A dictionary storing information to be sent to the processing node
            (Optional: if this function returns nothing, no information is transferred
            to the processing node.

        """
        print("Processing node {0} shutting down.".format(node_rank))
        sys.stdout.flush()

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
        print(
            "Processing finished. OM has processed {0} events in total.".format(
                self._num_events
            )
        )
        sys.stdout.flush()
