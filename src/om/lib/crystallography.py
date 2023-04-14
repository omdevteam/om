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

from collections import deque
from typing import Any, Deque, Dict, List, Tuple, Union, cast

import numpy
from numpy.typing import NDArray

from om.algorithms.crystallography import Peakfinder8PeakDetection, TypePeakList
from om.lib.geometry import (
    DataVisualizer,
    GeometryInformation,
    TypePixelMaps,
    TypeVisualizationPixelMaps,
)
from om.lib.parameters import MonitorParameters, get_parameter_from_parameter_group


class CrystallographyPeakFinding:
    """
    See documentation for the `__init__` function.
    """

    def __init__(
        self,
        *,
        parameters: MonitorParameters,
        geometry_information: GeometryInformation,
    ) -> None:
        """
        TODO: Add documentation
        """

        crystallography_parameters = parameters.get_parameter_group(
            group="crystallography"
        )

        peakfinder_algorithm: str = get_parameter_from_parameter_group(
            group=crystallography_parameters,
            parameter="peakfinding_algorithm",
            parameter_type=str,
            default="peakfinder8",
        )

        if peakfinder_algorithm == "peakfinder8":
            self._peak_detection: Peakfinder8PeakDetection = Peakfinder8PeakDetection(
                parameters=parameters.get_parameter_group(
                    group="peakfinder8_peak_detection"
                ),
                radius_pixel_map=geometry_information.get_pixel_maps()["radius"],
                layout_info=geometry_information.get_layout_info(),
            )
        else:
            # Put PeakNet peak finder's initialization here

            self._peak_detection = Peakfinder8PeakDetection(
                parameters=parameters.get_parameter_group(
                    group="peakfinder8_peak_detection"
                ),
                radius_pixel_map=geometry_information.get_pixel_maps()["radius"],
                layout_info=geometry_information.get_layout_info(),
            )

        self._min_num_peaks_for_hit: int = get_parameter_from_parameter_group(
            group=crystallography_parameters,
            parameter="min_num_peaks_for_hit",
            parameter_type=int,
            required=True,
        )

        self._max_num_peaks_for_hit: int = get_parameter_from_parameter_group(
            group=crystallography_parameters,
            parameter="max_num_peaks_for_hit",
            parameter_type=int,
            required=True,
        )

    def find_peaks(
        self, detector_data: Union[NDArray[numpy.int_], NDArray[numpy.float_]]
    ) -> TypePeakList:
        """
        TODO: Add documentation.
        """

        peak_list: TypePeakList = self._peak_detection.find_peaks(data=detector_data)

        return peak_list


# class RadialProfileAnalysis:
#     """
#     See documentation of the '__init__' function.
#     """

#     def __init__(
#         self,
#         *,
#         radius_pixel_map: NDArray[numpy.float_],
#         swaxs_parameters: Dict[str, Any],
#     ) -> None:
#         """
#         #TODO: Add documentation.
#         """

#         self._radial_profile_analysis = RadialProfileAnalysisWithSampleDetection(
#             swaxs_parameters=swaxs_parameters, radius_pixel_map=radius_pixel_map
#         )

#         self._jet_threshold: float = get_parameter_from_parameter_group(
#             group=swaxs_parameters,
#             parameter="threshold_for_jet_hit",
#             parameter_type=float,
#             required=True,
#         )

#         self._subtract_background: bool = get_parameter_from_parameter_group(
#             group=swaxs_parameters,
#             parameter="subtract_background",
#             parameter_type=bool,
#             default=False,
#         )

#         if self._subtract_background:

#             background_vectors_filename: str = get_parameter_from_parameter_group(
#                 group=swaxs_parameters,
#                 parameter="background_vectors_npy_filename",
#                 parameter_type=str,
#                 required=True,
#             )

#             try:
#                 self._background_vectors: numpy.ndarray = numpy.atleast_2d(
#                     numpy.load(background_vectors_filename)
#                 )
#             except (IOError, OSError, KeyError) as exc:
#                 # TODO: type this
#                 exc_type, exc_value = sys.exc_info()[:2]
#                 raise RuntimeError(
#                     "The following error occurred while reading the {0} water "
#                     "profile file: {1}: {2}".format(
#                         background_vectors_filename,
#                         exc_type.__name__,  # type: ignore
#                         exc_value,
#                     )
#                 ) from exc

#     def analyze_radial_profile(
#         self, *, detector_data: numpy.ndarray
#     ) -> Tuple[numpy.ndarray, numpy.ndarray, numpy.ndarray, float, bool, bool]:
#         """
#         # TODO: Add documentation
#         """
#         radial: numpy.ndarray
#         errors: numpy.ndarray
#         radial, errors = self._radial_profile_analysis.compute_radial_profile(
#             data=detector_data
#         )

#         detector_data_sum: float = detector_data.sum()
#         frame_is_jet: bool = detector_data_sum > self._jet_threshold
#         if not frame_is_jet:
#             frame_is_droplet: bool = False
#         else:
#             frame_is_droplet = self._radial_profile_analysis.detect_sample(
#                 radial_profile=radial
#             )

#         if self._subtract_background:
#             coefficients = fit_by_least_squares(
#                 radial_profile=radial,
#                 vectors=self._background_vectors,
#                 start_bin=800,
#                 stop_bin=1000,
#             )
#             background: numpy.ndarray = radial * 0
#             for i in range(len(coefficients)):
#                 background += coefficients[i] * self._background_vectors[i]
#             subtracted_radial: numpy.ndarray = radial - background
#         else:
#             subtracted_radial = radial

#         return (
#             radial,
#             subtracted_radial,
#             errors,
#             detector_data_sum,
#             frame_is_droplet,
#             frame_is_jet,
#         )


class CrystallographyPlots:
    """
    See documentation for the `__init__` function.
    """

    def __init__(
        self,
        *,
        crystallography_parameters: Dict[str, Any],
        data_visualizer: DataVisualizer,
        pump_probe_experiment: bool,
        bin_size: int,
    ) -> None:
        self._pump_probe_experiment: bool = pump_probe_experiment
        self._bin_size: int = bin_size

        pixel_maps: TypePixelMaps = data_visualizer.get_pixel_maps()
        visualization_pixel_maps: TypeVisualizationPixelMaps = (
            data_visualizer.get_visualization_pixel_maps()
        )
        plot_shape: Tuple[
            int, int
        ] = data_visualizer.get_min_array_shape_for_visualization()

        self._flattened_visualization_pixel_map_y = visualization_pixel_maps[
            "y"
        ].flatten()
        self._flattened_visualization_pixel_map_x = visualization_pixel_maps[
            "x"
        ].flatten()
        self._radius_pixel_map = pixel_maps["radius"]
        self._data_shape: Tuple[int, ...] = self._radius_pixel_map.shape

        self._peakogram_intensity_bin_size: float = get_parameter_from_parameter_group(
            group=crystallography_parameters,
            parameter="peakogram_intensity_bin_size",
            parameter_type=float,
            default=100,
        )
        peakogram_num_bins_intensity: int = 300

        self._peakogram_radius_bin_size: float = get_parameter_from_parameter_group(
            group=crystallography_parameters,
            parameter="peakogram_radius_bin_size",
            parameter_type=float,
            default=5,
        )
        peakogram_num_bins_radius: int = int(
            self._radius_pixel_map.max()
            * self._bin_size
            / self._peakogram_radius_bin_size
        )

        self._peakogram: NDArray[numpy.float_] = numpy.zeros(
            (peakogram_num_bins_radius, peakogram_num_bins_intensity)
        )

        self._running_average_window_size: int = get_parameter_from_parameter_group(
            group=crystallography_parameters,
            parameter="running_average_window_size",
            parameter_type=int,
            required=True,
        )

        self._hit_rate_running_window: Deque[float] = deque(
            [0.0] * self._running_average_window_size,
            maxlen=self._running_average_window_size,
        )
        self._avg_hit_rate: int = 0
        self._num_hits: int = 0
        self._hit_rate_timestamp_history: Deque[float] = deque(
            5000 * [0.0], maxlen=5000
        )
        self._hit_rate_history: Deque[float] = deque(5000 * [0.0], maxlen=5000)

        self._hit_rate_running_window_dark: Deque[float] = deque()
        self._avg_hit_rate_dark: int = 0
        self._hit_rate_timestamp_history_dark: Deque[float] = deque()
        self._hit_rate_history_dark: Deque[float] = deque()

        if self._pump_probe_experiment:
            self._hit_rate_running_window_dark = deque(
                [0.0] * self._running_average_window_size,
                maxlen=self._running_average_window_size,
            )
            self._avg_hit_rate_dark = 0
            self._hit_rate_timestamp_history_dark = deque(5000 * [0.0], maxlen=5000)
            self._hit_rate_history_dark = deque(5000 * [0.0], maxlen=5000)

        self._virt_powd_plot_img: NDArray[numpy.int_] = cast(
            NDArray[numpy.int_], numpy.zeros(plot_shape, dtype=numpy.int_)
        )

    def update_plots(
        self,
        *,
        timestamp: float,
        peak_list: TypePeakList,
        frame_is_hit: bool,
        # data_shape: Tuple[int, ...],
        optical_laser_active: bool,
    ) -> Tuple[
        Deque[float],
        Deque[float],
        Deque[float],
        Deque[float],
        NDArray[numpy.int_],
        NDArray[numpy.float_],
        float,
        float,
        List[float],
        List[float],
    ]:
        if self._pump_probe_experiment:
            if optical_laser_active:
                self._hit_rate_running_window.append(float(frame_is_hit))
                avg_hit_rate: float = (
                    sum(self._hit_rate_running_window)
                    / self._running_average_window_size
                )
                self._hit_rate_timestamp_history.append(timestamp)
                self._hit_rate_history.append(avg_hit_rate * 100.0)
            else:
                self._hit_rate_running_window_dark.append(float(frame_is_hit))
                avg_hit_rate_dark: float = (
                    sum(self._hit_rate_running_window_dark)
                    / self._running_average_window_size
                )
                self._hit_rate_timestamp_history_dark.append(timestamp)
                self._hit_rate_history_dark.append(avg_hit_rate_dark * 100.0)
        else:
            self._hit_rate_running_window.append(float(frame_is_hit))
            avg_hit_rate = (
                sum(self._hit_rate_running_window) / self._running_average_window_size
            )
            self._hit_rate_timestamp_history.append(timestamp)
            self._hit_rate_history.append(avg_hit_rate * 100.0)

        if frame_is_hit:
            peakogram_max_intensity: float = (
                self._peakogram.shape[1] * self._peakogram_intensity_bin_size
            )
            peaks_max_intensity: float = max(peak_list["max_pixel_intensity"])
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
            peak_list["fs"],
            peak_list["ss"],
            peak_list["intensity"],
            peak_list["max_pixel_intensity"],
        ):
            peak_index_in_slab: int = int(round(peak_ss)) * self._data_shape[1] + int(
                round(peak_fs)
            )
            y_in_frame: float = self._flattened_visualization_pixel_map_y[
                peak_index_in_slab
            ]
            x_in_frame: float = self._flattened_visualization_pixel_map_x[
                peak_index_in_slab
            ]
            peak_list_x_in_frame.append(x_in_frame)
            peak_list_y_in_frame.append(y_in_frame)
            self._virt_powd_plot_img[int(y_in_frame), int(x_in_frame)] += peak_value

            peak_radius: float = (
                self._bin_size
                * cast(NDArray[numpy.float_], self._radius_pixel_map)[
                    int(round(peak_ss)), int(round(peak_fs))
                ]
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

        return (
            self._hit_rate_timestamp_history,
            self._hit_rate_history,
            self._hit_rate_timestamp_history_dark,
            self._hit_rate_history_dark,
            self._virt_powd_plot_img,
            self._peakogram,
            self._peakogram_radius_bin_size,
            self._peakogram_intensity_bin_size,
            peak_list_x_in_frame,
            peak_list_y_in_frame,
        )

    def clear_plots(self) -> None:
        """
        # TODO: Add documentation.
        """
        self._hit_rate_running_window = deque(
            [0.0] * self._running_average_window_size,
            maxlen=self._running_average_window_size,
        )
        self._avg_hit_rate = 0
        self._num_hits = 0
        self._hit_rate_timestamp_history = deque(5000 * [0.0], maxlen=5000)
        self._hit_rate_history = deque(5000 * [0.0], maxlen=5000)

        if self._pump_probe_experiment is True:
            self._hit_rate_running_window_dark = deque(
                [0.0] * self._running_average_window_size,
                maxlen=self._running_average_window_size,
            )
            self._avg_hit_rate_dark = 0
            self._hit_rate_timestamp_history_dark = deque(5000 * [0.0], maxlen=5000)
            self._hit_rate_history_dark = deque(5000 * [0.0], maxlen=5000)

        self._virt_powd_plot_img = numpy.zeros_like(
            self._virt_powd_plot_img, dtype=numpy.int32
        )

        self._peakogram = numpy.zeros_like(self._peakogram)


# class SwaxsPlots:
#     def __init__(
#         self,
#         *,
#         swaxs__parameters: Dict[str, Any],
#     ):
#         self._droplet_detection_enabled: Union[
#             bool, None
#         ] = get_parameter_from_parameter_group(
#             group=swaxs__parameters,
#             parameter="droplet_detection_enabled",
#             parameter_type=bool,
#             default=False,
#         )

#         if self._droplet_detection_enabled:

#             # self._save_radials: bool = self._monitor_params.get_param(
#             #     group="droplet_detection",
#             #     parameter="save_radials",
#             #     parameter_type=bool,
#             #     required=True,
#             # )

#             # if self._save_radials:
#             #     self._radials_filename: str = self._monitor_params.get_param(
#             #         group="droplet_detection",
#             #         parameter="radials_filename",
#             #         parameter_type=str,
#             #         required=True,
#             #     )

#             # droplet hit rate
#             self._droplet_hit_rate_running_window: Deque[float] = deque(
#                 [0.0] * self._running_average_window_size,
#                 maxlen=self._running_average_window_size,
#             )
#             self._avg_droplet_hit_rate: int = 0
#             self._droplet_hit_rate_timestamp_history: Deque[float] = deque(
#                 5000 * [0.0], maxlen=5000
#             )
#             self._droplet_hit_rate_history: Deque[float] = deque(
#                 5000 * [0.0], maxlen=5000
#             )

#             # self._q_to_save: List[numpy.ndarray] = []
#             # self._image_sum_to_save: List[float] = []
#             # self._radials_to_save: List[numpy.ndarray] = []
#             # self._errors_to_save: List[numpy.ndarray] = []
#             self._frame_is_droplet: List[bool] = []
#             self._frame_is_crystal: List[bool] = []
#             self._frame_is_jet: List[bool] = []
#             self._q: List[numpy.ndarrray] = None

#             # self._roi1_qmin: float = self._monitor_params.get_param(
#             #     group="droplet_detection",
#             #     parameter="roi1_qmin",
#             #     parameter_type=float,
#             #     required=True,
#             # )
#             # self._roi1_qmax: float = self._monitor_params.get_param(
#             #     group="droplet_detection",
#             #     parameter="roi1_qmax",
#             #     parameter_type=float,
#             #     required=True,
#             # )
#             # self._roi2_qmin: float = self._monitor_params.get_param(
#             #     group="droplet_detection",
#             #     parameter="roi2_qmin",
#             #     parameter_type=float,
#             #     required=True,
#             # )
#             # self._roi2_qmax: float = self._monitor_params.get_param(
#             #     group="droplet_detection",
#             #     parameter="roi2_qmax",
#             #     parameter_type=float,
#             #     required=True,
#             # )
#             # self._estimate_particle_size: float = self._monitor_params.get_param(
#             #     group="droplet_detection",
#             #     parameter="estimate_particle_size",
#             #     parameter_type=bool,
#             #     required=True,
#             # )
#             # self._use_guinier_peak: float = self._monitor_params.get_param(
#             #     group="droplet_detection",
#             #     parameter="use_guinier_peak",
#             #     parameter_type=bool,
#             #     required=False,
#             # )
#             # self._guinier_qmin: float = self._monitor_params.get_param(
#             #     group="droplet_detection",
#             #     parameter="guinier_qmin",
#             #     parameter_type=float,
#             #     required=False,
#             # )
#             # self._guinier_qmax: float = self._monitor_params.get_param(
#             #     group="droplet_detection",
#             #     parameter="guinier_qmax",
#             #     parameter_type=float,
#             #     required=False,
#             # )
