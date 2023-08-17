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
Classes and function for processing of crystallography data.

This module contains classes and functions that perform common data processing
operations for Serial Crystallography (peak finding, radial profile analysis, plot
generation, etc.).
"""
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
        monitor_parameters: MonitorParameters,
        geometry_information: GeometryInformation,
    ) -> None:
        """
        Crystallography Bragg peak detection.

        This class stores all the information required to perform crystallography Bragg
        peak detection on a detector data frame, using one of the strategies available
        in OM.

        After the class has been initialized, it can be invoked to detect peaks in a
        data frame.

        Arguments:

            monitor_parameters: An object storing OM's configuration parameters. The
                set of parameters must include a group called `crystallography`, which
                in turn must contain the following entries:

                * `peakfinding_algorithm`: The detection strategy that should be used
                  to detect the Bragg peaks in a detector data frame. Currently, the
                  following strategies are available:

                    - `peakfinder8_peak_detection`: Instructs OM to use the
                      `peakfinder8` peak detection strategy. If this strategy is
                      selected, the set of OM's configuration parameters must include a
                      parameter group called `peakfinder8_peak_detection` with the
                      entries required to fine-tune the peak-finding strategy. Please
                      refer to the documentation of the
                      [Peakfinder8PeakDetection][om.algorithms.crystallography.Peakfinder8PeakDetection]
                      algorithm).

                * `min_num_peaks_for_hit`: The minimum number of peaks that must be
                  identified in a detector data frame for the related data event to be
                  considered a hit.

                * `max_num_peaks_for_hit`: The maximum number of peaks that must be
                  identified in a detector data frame for the related data event to be
                  considered a hit.
        """
        crystallography_parameters = monitor_parameters.get_parameter_group(
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
                crystallography_parameters=monitor_parameters.get_parameter_group(
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
        Finds peaks in a detector data frame.

        This function detects peaks in the provided detector data frame, using the
        strategy that was selected when the class was initialized. The function returns
        information about the location, size and intensity of the peaks.

        Arguments:

            detector_data: The detector data frame on which the peak-finding operation
                must be performed.

        Returns:

            A dictionary storing information about the detected peaks.
        """
        peak_list: TypePeakList = self._peak_detection.find_peaks(data=detector_data)

        return peak_list


class CrystallographyPlots:
    """
    See documentation for the `__init__` function.
    """

    def __init__(
        self,
        *,
        parameters: Dict[str, Any],
        data_visualizer: DataVisualizer,
        pump_probe_experiment: bool,
        bin_size: int,
    ) -> None:
        """
        Plots for crystallography data.

        This class stores all the information needed to generate and update three
        plots that summarize the state of a Serial Crystallography experiment: a
        Virtual Powder Pattern plot, a Hit Rate History plot and a Peakogram plot.
        Separate Hit Rate History plots for dark and pumped events can be generated for
        pump-probe experiment.

        After the class has been initialized, data event information can be added, and
        the updated plots can be retrieved and sent to external programs for
        visualization.

        Arguments:

            parameters: A set of OM configuration parameters collected together in a
                parameter group. The parameter group must contain the following
                entries:

                * `peakogram_intensity_bin_size`: The size, in ADU units, for each of
                  the intensity bins in the Peakogram plot.

                * `peakogram_radius_bin_size`: The size, in degrees, for each of the
                  radius bins in the Peakogram plot.

                * `running_average_window_size`: The size, in number of processed
                  events, of the running window used to compute the smoothed Hit Rate
                  History plot.
        """
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
            group=parameters,
            parameter="peakogram_intensity_bin_size",
            parameter_type=float,
            default=100,
        )
        peakogram_num_bins_intensity: int = 300

        self._peakogram_radius_bin_size: float = get_parameter_from_parameter_group(
            group=parameters,
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
            group=parameters,
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

        self._virtual_powder_plot_img: NDArray[numpy.int_] = cast(
            NDArray[numpy.int_], numpy.zeros(plot_shape, dtype=numpy.int_)
        )

    def update_plots(
        self,
        *,
        timestamp: float,
        peak_list: TypePeakList,
        frame_is_hit: bool,
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
        """
        Updates and recovers the crystallography data plots.

        This function uses the provided information to update all the crystallography
        data plots generated by this class. The function assumes that all the provided
        information refers to the same data event.

        After updating the data plots, the function returns all the information needed
        to display them in a graphical interface, in the format of a tuple containing
        the following entries:

        * A list of timestamps for the events in the Hit Rate History plot. For
          pump-probe experiments, this list only includes events with an active optical
          laser.

        * The Hit Rate for all the events in the Hit Rate History plot. For pump-probe
          experiments, this list only includes events with an active optical laser.

        * A list of timestamps for events without an active optical laser in
          pump-probe experiments. For non-pump-probe experiments, this list just stores
          zero values.

        * The Hit Rate for all the events without an active optical laser in the
          Hit Rate History plot of a pump-probe experiment. For non-pump-probe
          experiments, this list just stores zero values.

        * A 2D array storing the pixel values of a Virtual Powder Plot image.

        * A 2D array storing the pixel values of a Peakogram Plot image.

        * The size, in degrees, for each of the radius bins in the Peakogram plot

        * The size, in ADU units, for each of the intensity bins in the Peakogram
          plot.

        * A list storing the x visualization coordinate of each Bragg peak identified
          in the data event provided to the update function . The coordinate refers to
          an array storing the assembled detector image, with the origin in the top
          left corner of the image.

        * A list storing the y visualization coordinate of each Bragg peak identified
          in the data event provided to the update function . The coordinate refers to
          an array storing the assembled detector image, with the origin in the top
          left corner of the image.

        Arguments:

            timestamp: The timestamp of the event to which the provided data is
                attached.float,

            peak_list: Information about the Bragg peaks identified in the detector data
                frame attached to the data event.

            frame_is_hit: Whether the data event should be considered a hit, or not.

            optical_laser_active: Whether the optical laser is active or not in the
                provided data event. This information is only relevant for pump-probe
                experiments.

        Returns:

            The information needed to display the plots in a graphical interface.
        """

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
            self._virtual_powder_plot_img[
                int(y_in_frame), int(x_in_frame)
            ] += peak_value

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
            self._virtual_powder_plot_img,
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

        self._virtual_powder_plot_img = numpy.zeros_like(
            self._virtual_powder_plot_img, dtype=numpy.int32
        )

        self._peakogram = numpy.zeros_like(self._peakogram)
