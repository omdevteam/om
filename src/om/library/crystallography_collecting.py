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

import collections
from typing import Any, Deque, Dict, List, Tuple, Union, cast

import numpy
from numpy.typing import NDArray

from om.algorithms.crystallography import TypePeakList
from om.algorithms.generic import Binning
from om.library.geometry import (
    GeometryInformation,
    TypePixelMaps,
    compute_min_size,
    compute_visualization_pix_maps,
)
from om.library.parameters import get_parameter_from_parameter_group


class CrystallographyPlots:
    """
    See documentation for the `__init__` function.
    """

    def __init__(
        self,
        *,
        crystallography_parameters: Dict[str, Any],
        geometry_information: GeometryInformation,
        binning_algorithm: Union[Binning, None],
        pump_probe_experiment: bool,
    ) -> None:

        self._pump_probe_experiment: bool = pump_probe_experiment

        if binning_algorithm:
            self._pixel_maps: TypePixelMaps = binning_algorithm.bin_pixel_maps(
                pixel_maps=geometry_information.get_pixel_maps()
            )

            self._data_shape = binning_algorithm.get_binned_data_shape()
            self._bin_size: int = binning_algorithm.get_bin_size()
        else:
            self._bin_size = 1
            self._pixel_maps = geometry_information.get_pixel_maps()
        visual_pixel_maps: TypePixelMaps = compute_visualization_pix_maps(
            pixel_maps=self._pixel_maps
        )
        self._visual_pixel_maps_x: numpy.ndarray = visual_pixel_maps["x"].flatten()
        self._visual_pixel_maps_y: numpy.ndarray = visual_pixel_maps["y"].flatten()
        visual_img_shape: Tuple[int, int] = compute_min_size(
            pixel_maps=self._pixel_maps
        )

        peakogram_num_bins: int = 300
        self._peakogram_intensity_bin_size: float = get_parameter_from_parameter_group(
            group=crystallography_parameters,
            parameter="peakogram_intensity_bin_size",
            parameter_type=float,
            default=100,
        )

        self._peakogram_radius_bin_size: float = (
            get_parameter_from_parameter_group(
                group=crystallography_parameters,
                parameter="peakogram_radius_bin_size",
                parameter_type=int,
                required=True,
            )
            / peakogram_num_bins
        )

        self._peakogram: NDArray[numpy.float_] = numpy.zeros(
            (peakogram_num_bins, peakogram_num_bins)
        )

        self._running_average_window_size: int = get_parameter_from_parameter_group(
            group=crystallography_parameters,
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

        self._hit_rate_running_window_dark: Union[Deque[float], None] = None
        self._hit_rate_timestamp_history_dark: Union[Deque[float], None] = None
        self._hit_rate_history_dark: Union[Deque[float], None] = None
        if self._pump_probe_experiment:
            self._hit_rate_running_window_dark = collections.deque(
                [0.0] * self._running_average_window_size,
                maxlen=self._running_average_window_size,
            )
            self._avg_hit_rate_dark: int = 0
            self._hit_rate_timestamp_history_dark = collections.deque(
                5000 * [0.0], maxlen=5000
            )
            self._hit_rate_history_dark = collections.deque(5000 * [0.0], maxlen=5000)

        self._virt_powd_plot_img: NDArray[numpy.int_] = numpy.zeros(
            visual_img_shape, dtype=numpy.int32
        )

    def update_plots(
        self,
        *,
        timestamp: float,
        peak_list: TypePeakList,
        frame_is_hit: bool,
        data_shape: Tuple[int, ...],
        optical_laser_active: bool,
    ) -> Tuple[
        Deque[float],
        Deque[float],
        Union[Deque[float], None],
        Union[Deque[float], None],
        numpy.ndarray,
        numpy.ndarray,
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
            peak_index_in_slab: int = int(round(peak_ss)) * data_shape[1] + int(
                round(peak_fs)
            )
            y_in_frame: float = self._visual_pixel_maps_y[peak_index_in_slab]
            x_in_frame: float = self._visual_pixel_maps_x[peak_index_in_slab]
            peak_list_x_in_frame.append(x_in_frame)
            peak_list_y_in_frame.append(y_in_frame)
            self._virt_powd_plot_img[int(y_in_frame), int(x_in_frame)] += peak_value

            peak_radius: float = (
                self._bin_size
                * cast(NDArray[numpy.float_], self._pixel_maps["radius"])[
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
            peak_list_x_in_frame,
            peak_list_y_in_frame,
        )

    def clear_plots(self) -> None:
        """
        # TODO: Add documentation.
        """
        self._hit_rate_running_window = collections.deque(
            [0.0] * self._running_average_window_size,
            maxlen=self._running_average_window_size,
        )
        self._avg_hit_rate = 0
        self._num_hits = 0
        self._hit_rate_timestamp_history = collections.deque(5000 * [0.0], maxlen=5000)
        self._hit_rate_history = collections.deque(5000 * [0.0], maxlen=5000)

        if self._pump_probe_experiment is True:
            self._hit_rate_running_window_dark = collections.deque(
                [0.0] * self._running_average_window_size,
                maxlen=self._running_average_window_size,
            )
            self._avg_hit_rate_dark = 0
            self._hit_rate_timestamp_history_dark = collections.deque(
                5000 * [0.0], maxlen=5000
            )
            self._hit_rate_history_dark = collections.deque(5000 * [0.0], maxlen=5000)

        self._virt_powd_plot_img = numpy.zeros_like(
            self._virt_powd_plot_img, dtype=numpy.int32
        )

        self._peakogram = numpy.zeros_like(self._peakogram)


class SwaxsPlots:
    def __init__(
        self,
        *,
        swaxs__parameters: Dict[str, Any],
    ):
        self._droplet_detection_enabled: Union[
            bool, None
        ] = get_parameter_from_parameter_group(
            group=swaxs__parameters,
            parameter="droplet_detection_enabled",
            parameter_type=bool,
            default=False,
        )

        if self._droplet_detection_enabled:

            # self._save_radials: bool = self._monitor_params.get_param(
            #     group="droplet_detection",
            #     parameter="save_radials",
            #     parameter_type=bool,
            #     required=True,
            # )

            # if self._save_radials:
            #     self._radials_filename: str = self._monitor_params.get_param(
            #         group="droplet_detection",
            #         parameter="radials_filename",
            #         parameter_type=str,
            #         required=True,
            #     )

            # droplet hitrate
            self._droplet_hit_rate_running_window: Deque[float] = collections.deque(
                [0.0] * self._running_average_window_size,
                maxlen=self._running_average_window_size,
            )
            self._avg_droplet_hit_rate: int = 0
            self._droplet_hit_rate_timestamp_history: Deque[float] = collections.deque(
                5000 * [0.0], maxlen=5000
            )
            self._droplet_hit_rate_history: Deque[float] = collections.deque(
                5000 * [0.0], maxlen=5000
            )

            # self._q_tosave: List[numpy.ndarray] = []
            # self._image_sum_tosave: List[float] = []
            # self._radials_tosave: List[numpy.ndarray] = []
            # self._errors_tosave: List[numpy.ndarray] = []
            self._frame_is_droplet: List[bool] = []
            self._frame_is_crystal: List[bool] = []
            self._frame_is_jet: List[bool] = []
            self._q: List[numpy.ndarrray] = None

            # self._roi1_qmin: float = self._monitor_params.get_param(
            #     group="droplet_detection",
            #     parameter="roi1_qmin",
            #     parameter_type=float,
            #     required=True,
            # )
            # self._roi1_qmax: float = self._monitor_params.get_param(
            #     group="droplet_detection",
            #     parameter="roi1_qmax",
            #     parameter_type=float,
            #     required=True,
            # )
            # self._roi2_qmin: float = self._monitor_params.get_param(
            #     group="droplet_detection",
            #     parameter="roi2_qmin",
            #     parameter_type=float,
            #     required=True,
            # )
            # self._roi2_qmax: float = self._monitor_params.get_param(
            #     group="droplet_detection",
            #     parameter="roi2_qmax",
            #     parameter_type=float,
            #     required=True,
            # )
            # self._estimate_particle_size: float = self._monitor_params.get_param(
            #     group="droplet_detection",
            #     parameter="estimate_particle_size",
            #     parameter_type=bool,
            #     required=True,
            # )
            # self._use_guinier_peak: float = self._monitor_params.get_param(
            #     group="droplet_detection",
            #     parameter="use_guinier_peak",
            #     parameter_type=bool,
            #     required=False,
            # )
            # self._guinier_qmin: float = self._monitor_params.get_param(
            #     group="droplet_detection",
            #     parameter="guinier_qmin",
            #     parameter_type=float,
            #     required=False,
            # )
            # self._guinier_qmax: float = self._monitor_params.get_param(
            #     group="droplet_detection",
            #     parameter="guinier_qmax",
            #     parameter_type=float,
            #     required=False,
            # )