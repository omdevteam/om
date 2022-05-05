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
from itertools import cycle
from typing import Any, Deque, Dict, Iterator, List, Tuple, Union, cast

import numpy
from numpy.typing import NDArray

from om.algorithms import crystallography as cryst_algs
from om.algorithms import generic as gen_algs
from om.protocols import processing_layer as pl_protocols
from om.utils import crystfel_geometry, exceptions, parameters, zmq_monitor
from om.utils.crystfel_geometry import TypeDetector, TypePixelMaps
from om.utils.rich_console import console, get_current_timestamp

try:
    import msgpack  # type: ignore
except ImportError:
    raise exceptions.OmMissingDependencyError(
        "The following required module cannot be imported: msgpack"
    )


class CrystallographyProcessing(pl_protocols.OmProcessing):
    """
    See documentation for the `__init__` function.
    """

    def __init__(self, *, monitor_parameters: parameters.MonitorParams) -> None:
        """
        OnDA Monitor for Crystallography.

        This Processing class implements an OnDA Monitor for serial crystallography
        experiments. The monitor processes detector data frames, optionally applying
        detector calibration, dark correction and gain correction. It then detects
        Bragg peaks in each detector frame using the
        [Peakfinder8PeakDetection][om.algorithms.crystallography.Peakfinder8PeakDetection]
        algorithm, retrieving information about the location, size, intensity, SNR and
        maximum pixel value of each peak. Additionally, the monitor calculates the
        evolution of the hit rate over time. It can also optionally collect examples of
        hit and non-hit calibrated detector data frames. All the information is
        broadcast over a ZMQ socket for visualization by external programs like
        [OM's Crystallography GUI][om.graphical_interfaces.crystallography_gui.CrystallographyGui]
        or
        [OM's Frame Viewer][om.graphical_interfaces.crystallography_frame_viewer.CrystallographyFrameViewer].

        Arguments:

            monitor_parameters: An object storing OM's configuration parameters.
        """
        self._monitor_params = monitor_parameters

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
                radius_pixel_map=cast(NDArray[numpy.float_], self._pixelmaps["radius"]),
            )
        )

        binning: Union[bool, None] = self._monitor_params.get_parameter(
            group="crystallography",
            parameter="binning",
            parameter_type=bool,
        )
        if binning:
            self._binning: Union[gen_algs.Binning, None] = gen_algs.Binning(
                parameters=self._monitor_params.get_parameter_group(group="binning"),
            )
            binning_before_peakfinding: Union[
                bool, None
            ] = self._monitor_params.get_parameter(
                group="crystallography",
                parameter="binning_before_peakfinding",
                parameter_type=bool,
            )
            if binning_before_peakfinding is None:
                self._binning_before_peakfinding: bool = True
            else:
                self._binning_before_peakfinding = binning_before_peakfinding
            if self._binning_before_peakfinding:
                self._peak_detection.set_peakfinder8_info(
                    self._binning.get_binned_layout_info()
                )
                self._peak_detection.set_bad_pixel_map(
                    self._binning.bin_bad_pixel_map(
                        mask=self._peak_detection.get_bad_pixel_map()
                    )
                )
                self._peak_detection.set_radius_pixel_map(
                    cast(
                        NDArray[numpy.float_],
                        self._binning.bin_pixel_maps(pixel_maps=self._pixelmaps)[
                            "radius"
                        ],
                    )
                )
            self._data_shape = self._binning.get_binned_data_shape()
        else:
            self._binning = None

        pump_probe_experiment: Union[bool, None] = self._monitor_params.get_parameter(
            group="crystallography",
            parameter="pump_probe_experiment",
            parameter_type=bool,
        )
        if pump_probe_experiment is None:
            self._pump_probe_experiment: bool = False
        else:
            self._pump_probe_experiment = pump_probe_experiment

        self._send_hit_frame: bool = False
        self._send_non_hit_frame: bool = False

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

        binning: Union[bool, None] = self._monitor_params.get_parameter(
            group="crystallography",
            parameter="binning",
            parameter_type=bool,
        )
        if binning:
            self._binning = gen_algs.Binning(
                parameters=self._monitor_params.get_parameter_group(group="binning"),
            )
            self._pixelmaps = self._binning.bin_pixel_maps(pixel_maps=self._pixelmaps)
            self._data_shape = self._binning.get_binned_data_shape()
            self._bin_size: int = self._binning.get_bin_size()
        else:
            self._binning = None
            self._bin_size = 1

        pump_probe_experiment: Union[bool, None] = self._monitor_params.get_parameter(
            group="crystallography",
            parameter="pump_probe_experiment",
            parameter_type=bool,
        )
        if pump_probe_experiment is None:
            self._pump_probe_experiment = False
        else:
            self._pump_probe_experiment = pump_probe_experiment

        # Theoretically, the pixel size could be different for every module of the
        # detector. The pixel size of the first module is taken as the pixel size
        # of the whole detector.
        self._pixel_size: float = self._geometry["panels"][
            tuple(self._geometry["panels"].keys())[0]
        ]["res"]
        if self._binning is not None:
            self._pixel_size /= self._binning.get_bin_size()
        self._first_panel_coffset: float = self._geometry["panels"][
            list(self._geometry["panels"].keys())[0]
        ]["coffset"]

        peakogram_num_bins: int = 300
        peakogram_intensity_bin_size: Union[
            None, float
        ] = self._monitor_params.get_parameter(
            group="crystallography",
            parameter="peakogram_intensity_bin_size",
            parameter_type=float,
            required=False,
        )
        if peakogram_intensity_bin_size:
            self._peakogram_intensity_bin_size: float = peakogram_intensity_bin_size
        else:
            self._peakogram_intensity_bin_size = 100

        peakfinder_max_res: Union[None, int] = self._monitor_params.get_parameter(
            group="peakfinder8_peak_detection",
            parameter="max_res",
            parameter_type=int,
            required=False,
        )
        if peakfinder_max_res:
            self._peakogram_radius_bin_size: float = (
                peakfinder_max_res / peakogram_num_bins
            )
        else:
            self._peakogram_radius_bin_size = (
                cast(NDArray[numpy.float_], self._pixelmaps["radius"])
                / peakogram_num_bins
            )

        self._peakogram: NDArray[numpy.float_] = numpy.zeros(
            (peakogram_num_bins, peakogram_num_bins)
        )

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
        self._num_hits: int = 0
        self._hit_rate_timestamp_history: Deque[float] = collections.deque(
            5000 * [0.0], maxlen=5000
        )
        self._hit_rate_history: Deque[float] = collections.deque(
            5000 * [0.0], maxlen=5000
        )

        if self._pump_probe_experiment is True:
            self._hit_rate_running_window_dark: Deque[float] = collections.deque(
                [0.0] * self._running_average_window_size,
                maxlen=self._running_average_window_size,
            )
            self._avg_hit_rate_dark: int = 0
            self._hit_rate_timestamp_history_dark: Deque[float] = collections.deque(
                5000 * [0.0], maxlen=5000
            )
            self._hit_rate_history_dark: Deque[float] = collections.deque(
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
        pixelmap_x_int: NDArray[numpy.int_] = self._pixelmaps["x"].astype(int)
        self._visual_pixelmap_x: NDArray[numpy.int_] = (
            pixelmap_x_int + visual_img_shape[1] // 2 - 1
        ).flatten()
        pixelmap_y_int: NDArray[numpy.int_] = self._pixelmaps["y"].astype(int)
        self._visual_pixelmap_y: NDArray[numpy.int_] = (
            pixelmap_y_int + visual_img_shape[0] // 2 - 1
        ).flatten()
        self._virt_powd_plot_img: NDArray[numpy.int_] = numpy.zeros(
            visual_img_shape, dtype=numpy.int32
        )
        self._frame_data_img: NDArray[numpy.float_] = numpy.zeros(
            visual_img_shape, dtype=numpy.float32
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

        self._ranks_for_frame_request: Iterator[int] = cycle(range(1, node_pool_size))
        self._start_timestamp: float = time.time()

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

        self._num_events: int = 0
        self._old_time: float = time.time()
        self._time: Union[float, None] = None

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
            processed data that should be sent to the collecting node. The second entry
            is the OM rank number of the node that processed the information.
        """

        processed_data: Dict[str, Any] = {}
        corrected_detector_data: NDArray[
            numpy.float_
        ] = self._correction.apply_correction(data=data["detector_data"])
        if self._binning is not None and self._binning_before_peakfinding:
            binned_detector_data = self._binning.bin_detector_data(
                data=corrected_detector_data
            )
        else:
            binned_detector_data = corrected_detector_data

        peak_list: cryst_algs.TypePeakList = self._peak_detection.find_peaks(
            data=binned_detector_data
        )

        if self._binning is not None and not self._binning_before_peakfinding:
            binned_detector_data = self._binning.bin_detector_data(
                data=corrected_detector_data
            )
            i: int
            bin_size: int = self._binning.get_bin_size()
            for i in range(peak_list["num_peaks"]):
                peak_list["fs"][i] = (peak_list["fs"][i] + 0.5) / bin_size - 0.5
                peak_list["ss"][i] = (peak_list["ss"][i] + 0.5) / bin_size - 0.5

        if "requests" in data:
            if data["requests"] == "hit_frame":
                self._send_hit_frame = True
            if data["requests"] == "non_hit_frame":
                self._send_non_hit_frame = True

        frame_is_hit: bool = (
            self._min_num_peaks_for_hit
            < len(peak_list["intensity"])
            < self._max_num_peaks_for_hit
        )

        processed_data["timestamp"] = data["timestamp"]
        processed_data["frame_is_hit"] = frame_is_hit
        processed_data["detector_distance"] = data["detector_distance"]
        processed_data["beam_energy"] = data["beam_energy"]
        processed_data["event_id"] = data["event_id"]
        processed_data["frame_id"] = data["frame_id"]
        processed_data["data_shape"] = binned_detector_data.shape
        if self._pump_probe_experiment:
            processed_data["optical_laser_active"] = data["optical_laser_active"]

        if frame_is_hit:
            processed_data["peak_list"] = peak_list
            if self._send_hit_frame is True:
                processed_data["detector_data"] = binned_detector_data
                self._send_hit_frame = False
        else:
            processed_data["peak_list"] = {
                "fs": [],
                "ss": [],
                "intensity": [],
                "max_pixel_intensity": [],
            }
            if self._send_non_hit_frame is True:
                processed_data["detector_data"] = binned_detector_data
                self._send_non_hit_frame = False

        return (processed_data, node_rank)

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
        self._num_events += 1
        return_dict: Dict[int, Dict[str, Any]] = {}

        if received_data["frame_is_hit"] is True:
            self._num_hits += 1

        request: Union[
            Tuple[bytes, bytes], None
        ] = self._responding_socket.get_request()
        if request:
            self._request_list.append(request)

        if len(self._request_list) != 0:
            first_request = self._request_list[0]
            if first_request[1] == b"next":
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
            else:
                console.print(
                    f"{get_current_timestamp()} OM Warning: Could not understand "
                    f"request '{str(first_request[1])}'.",
                    style="warning",
                )
                _ = self._request_list.popleft()

        if self._pump_probe_experiment:
            if received_data["optical_laser_active"]:
                self._hit_rate_running_window.append(
                    float(received_data["frame_is_hit"])
                )
                avg_hit_rate: float = (
                    sum(self._hit_rate_running_window)
                    / self._running_average_window_size
                )
                self._hit_rate_timestamp_history.append(received_data["timestamp"])
                self._hit_rate_history.append(avg_hit_rate * 100.0)
            else:
                self._hit_rate_running_window_dark.append(
                    float(received_data["frame_is_hit"])
                )
                avg_hit_rate_dark: float = (
                    sum(self._hit_rate_running_window_dark)
                    / self._running_average_window_size
                )
                self._hit_rate_timestamp_history_dark.append(received_data["timestamp"])
                self._hit_rate_history_dark.append(avg_hit_rate_dark * 100.0)
        else:
            self._hit_rate_running_window.append(float(received_data["frame_is_hit"]))
            avg_hit_rate = (
                sum(self._hit_rate_running_window) / self._running_average_window_size
            )
            self._hit_rate_timestamp_history.append(received_data["timestamp"])
            self._hit_rate_history.append(avg_hit_rate * 100.0)

        if received_data["frame_is_hit"]:
            peakogram_max_intensity: float = (
                self._peakogram.shape[1] * self._peakogram_intensity_bin_size
            )
            peaks_max_intensity: float = max(
                received_data["peak_list"]["max_pixel_intensity"]
            )
            if peaks_max_intensity > peakogram_max_intensity:
                self._peakogram = numpy.concatenate(
                    (
                        self._peakogram,
                        numpy.zeros(
                            (
                                self._peakogram.shape[0],
                                int(
                                    (peaks_max_intensity - peakogram_max_intensity)
                                    // self._peakogram_intensity_bin_size
                                    + 1
                                ),
                            )
                        ),
                    ),
                    axis=1,
                )

        peak_list_x_in_frame: List[float] = []
        peak_list_y_in_frame: List[float] = []
        peak_fs: float
        peak_ss: float
        peak_value: float
        for peak_fs, peak_ss, peak_value, peak_max_pixel_intensity in zip(
            received_data["peak_list"]["fs"],
            received_data["peak_list"]["ss"],
            received_data["peak_list"]["intensity"],
            received_data["peak_list"]["max_pixel_intensity"],
        ):
            peak_index_in_slab: int = int(round(peak_ss)) * received_data["data_shape"][
                1
            ] + int(round(peak_fs))
            y_in_frame: float = self._visual_pixelmap_y[peak_index_in_slab]
            x_in_frame: float = self._visual_pixelmap_x[peak_index_in_slab]
            peak_list_x_in_frame.append(x_in_frame)
            peak_list_y_in_frame.append(y_in_frame)
            self._virt_powd_plot_img[y_in_frame, x_in_frame] += peak_value

            peak_radius: float = (
                self._bin_size
                * self._pixelmaps["radius"][int(round(peak_ss)), int(round(peak_fs))]
            )
            radius_index: int = int(peak_radius // self._peakogram_radius_bin_size)
            intensity_index: int = int(
                peak_max_pixel_intensity // self._peakogram_intensity_bin_size
            )
            if (
                radius_index < self._peakogram.shape[0]
                and intensity_index < self._peakogram.shape[1]
            ):
                self._peakogram[radius_index, intensity_index] += 1

        omdata_message: Dict[str, Any] = {
            "geometry_is_optimized": self._geometry_is_optimized,
            "timestamp": received_data["timestamp"],
            "hit_rate_timestamp_history": self._hit_rate_timestamp_history,
            "hit_rate_history": self._hit_rate_history,
            "virtual_powder_plot": self._virt_powd_plot_img,
            "beam_energy": received_data["beam_energy"],
            "detector_distance": received_data["detector_distance"],
            "first_panel_coffset": self._first_panel_coffset,
            "pixel_size": self._pixel_size,
            "pump_probe_experiment": self._pump_probe_experiment,
            "num_events": self._num_events,
            "num_hits": self._num_hits,
            "start_timestamp": self._start_timestamp,
            "peakogram": self._peakogram,
            "peakogram_radius_bin_size": self._peakogram_radius_bin_size,
            "peakogram_intensity_bin_size": self._peakogram_intensity_bin_size,
        }
        if self._pump_probe_experiment:
            omdata_message[
                "hit_rate_timestamp_history_dark"
            ] = self._hit_rate_timestamp_history_dark
            omdata_message["hit_rate_history_dark"] = self._hit_rate_history_dark
        if self._num_events % self._data_broadcast_interval == 0:
            self._data_broadcast_socket.send_data(
                tag="omdata",
                message=omdata_message,
            )

        if "detector_data" in received_data:
            # If detector frame data is found in the data received from the
            # processing node, it must be broadcasted to visualization programs.

            self._frame_data_img[self._visual_pixelmap_y, self._visual_pixelmap_x] = (
                received_data["detector_data"]
                .ravel()
                .astype(self._frame_data_img.dtype)
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

        if (
            self._hit_frame_sending_interval is not None
            and self._num_events % self._hit_frame_sending_interval == 0
        ):
            rank_for_request: int = next(self._ranks_for_frame_request)
            return_dict[rank_for_request] = {"requests": "hit_frame"}
        if (
            self._non_hit_frame_sending_interval is not None
            and self._num_events % self._non_hit_frame_sending_interval == 0
        ):
            rank_for_request = next(self._ranks_for_frame_request)
            return_dict[rank_for_request] = {"requests": "non_hit_frame"}

        if self._num_events % self._speed_report_interval == 0:
            now_time: float = time.time()
            time_diff: float = now_time - self._old_time
            events_per_second: float = float(self._speed_report_interval) / float(
                now_time - self._old_time
            )
            console.print(
                f"{get_current_timestamp()} Processed: {self._num_events} in "
                f"{time_diff:.2f} seconds ({events_per_second:.3f} Hz)"
            )
            sys.stdout.flush()
            self._old_time = now_time

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
            f"{self._num_events} events in total."
        )
        sys.stdout.flush()
