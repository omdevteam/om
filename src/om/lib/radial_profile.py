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
Radial average algorithms.

This module contains algorithms that perform data processing operations on radial
profile information computed from collected detector data frames.
"""

from collections import deque
from typing import Any, Deque, Dict, Tuple, Union, cast

import numpy
from numpy.typing import NDArray
from scipy import constants, stats  # type: ignore

from om.algorithms.generic import RadialProfile
from om.lib.geometry import GeometryInformation
from om.lib.hdf5 import parse_parameters_and_load_hdf5_data
from om.lib.parameters import get_parameter_from_parameter_group


def _fit_by_least_squares(
    *,
    radial_profile: NDArray[numpy.float_],
    vectors: NDArray[numpy.float_],
    start_bin: Union[int, None] = None,
    stop_bin: Union[int, None] = None,
) -> NDArray[numpy.float_]:
    # This function fits a set of linearly combined vectors to a radial profile,
    # using a least-squares-based approach. The fit only takes into account the
    # range of radial bins defined by the xmin and xmax arguments.
    if start_bin is None:
        start_bin = 0
    if stop_bin is None:
        stop_bin = len(radial_profile)
    a: NDArray[numpy.float_] = numpy.nan_to_num(numpy.atleast_2d(vectors).T)
    b: NDArray[numpy.float_] = numpy.nan_to_num(radial_profile)
    a = a[start_bin:stop_bin]
    b = b[start_bin:stop_bin]
    coefficients: NDArray[numpy.float_]
    coefficients, _, _, _ = numpy.linalg.lstsq(a, b, rcond=None)
    return coefficients


def _calc_rg_by_guinier(
    q: NDArray[numpy.float_],
    radial: NDArray[numpy.float_],
    nb: Union[int, None] = None,
    ne: Union[int, None] = None,
) -> float:
    # Calculates Rg by fitting Guinier equation to data.
    # Uses only desired q range in input arrays.
    if nb is None:
        nb = 0
    if ne is None:
        ne = len(q)
    i: int = 0
    while True:
        try:
            m: float
            m, _ = stats.linregress(q[nb:ne] ** 2, numpy.log(radial[nb:ne]))[:2]
        except:
            m = 0.0
        if m < 0.0:
            break
        else:
            # the slope should be negative
            # if the slope is positive, shift the region
            # forward by one point and try again
            nb += 5
            ne += 5
            i += 1
            if i > 10:
                # try ten times shifting, then give up
                m = 0.0
                break
    rg: float = (-3 * m) ** (0.5)
    return rg


def _calc_rg_by_guinier_peak(
    q: NDArray[numpy.float_],
    radial: NDArray[numpy.float_],
    exp: int = 1,
    nb: Union[int, None] = None,
    ne: Union[int, None] = None,
) -> float:
    # Roughly estimate Rg using the Guinier peak method.
    # Uses only desired q range in input arrays.
    # (exp is the exponent in q^exp * I(q))
    d: int = exp
    if ne is None:
        ne = len(q)
    qs: NDArray[numpy.float_] = q[nb:ne]
    Is: NDArray[numpy.float_] = radial[nb:ne]
    qdI: NDArray[numpy.float_] = qs**d * Is
    try:
        # fit a quick quadratic for smoothness, ax^2 + bx + c
        a: float
        b: float
        a, b, _ = numpy.polyfit(qs, qdI, 2)
        # get the peak position
        qpeak: float = -b / (2 * a)
    except:
        # if polyfit fails, just grab the maximum position
        qpeaki: int = numpy.argmax(qdI)
        qpeak = qs[qpeaki]
    # calculate Rg from the peak position
    rg: float = (3.0 * d / 2.0) ** 0.5 / qpeak
    return rg


class RadialProfileAnalysis:
    """
    See documentation of the '__init__' function.
    """

    def __init__(
        self,
        *,
        geometry_information: GeometryInformation,
        radial_parameters: Dict[str, Any],
    ) -> None:
        """
        Algorithm for aqueous droplet detection.

        #TODO: Documentation

        Arguments:

            sample_detection_enabled: Whether to apply or not droplet detection.

            save_radials: Whether or not to save radials and droplet detection results
                in an hdf5 file. This should be False if running on shared memory, but
                can be True when accessing data on disk, and can be useful for
                creating pure sample and water profiles.

            sample_peak_min_i: The minimum radial distance from the center of the
                detector reference system defining the sample peak (in pixels).

            sample_peak_max_i: The maximum radial distance from the center of the
                detector reference system defining the sample peak (in pixels).

            water_peak_min_i: The minimum radial distance from the center of the
                detector reference system defining the water peak (in pixels).

            water_peak_max_i: The maximum radial distance from the center of the
                detector reference system defining the water peak (in pixels).

            sample_profile: The radial profile for pure sample.

            water_profile: The radial profile for pure water or buffer.

            threshold:

        #TODO: Fix documentation
        """

        self._background_subtraction: bool = get_parameter_from_parameter_group(
            group=radial_parameters,
            parameter="background_subtraction",
            parameter_type=bool,
            required=True,
        )

        if self._background_subtraction:
            self._background_profile_vectors: NDArray[numpy.float_] = cast(
                NDArray[numpy.float_],
                parse_parameters_and_load_hdf5_data(
                    parameters=radial_parameters,
                    hdf5_filename_parameter="background_profile_filename",
                    hdf5_path_parameter="background_profile_hdf5_path",
                ),
            )

            self._background_subtraction_min_bin: Union[
                int, None
            ] = get_parameter_from_parameter_group(
                group=radial_parameters,
                parameter="background_subtraction_min_fit_bin",
                parameter_type=int,
            )

            self._background_subtraction_max_bin: Union[
                int, None
            ] = get_parameter_from_parameter_group(
                group=radial_parameters,
                parameter="background_subtraction_max_fit_bin",
                parameter_type=int,
            )

        # Sample detection
        self._total_intensity_jet_threshold: float = get_parameter_from_parameter_group(
            group=radial_parameters,
            parameter="total_intensity_jet_threshold",
            parameter_type=float,
            required=True,
        )

        self._roi1_qmin: float = get_parameter_from_parameter_group(
            group=radial_parameters,
            parameter="roi1_qmin",
            parameter_type=float,
            required=True,
        )
        self._roi1_qmax: float = get_parameter_from_parameter_group(
            group=radial_parameters,
            parameter="roi1_qmax",
            parameter_type=float,
            required=True,
        )
        self._roi2_qmin: float = get_parameter_from_parameter_group(
            group=radial_parameters,
            parameter="roi2_qmin",
            parameter_type=float,
            required=True,
        )
        self._roi2_qmax: float = get_parameter_from_parameter_group(
            group=radial_parameters,
            parameter="roi2_qmax",
            parameter_type=float,
            required=True,
        )

        self._sample_detection: bool = get_parameter_from_parameter_group(
            group=radial_parameters,
            parameter="sample_detection",
            parameter_type=bool,
            default=False,
        )

        if self._sample_detection:
            # TODO: Make q-min, q-max
            self._first_peak_min_bin: int = get_parameter_from_parameter_group(
                group=radial_parameters,
                parameter="first_peak_min_bin",
                parameter_type=int,
                required=True,
            )
            self._first_peak_max_bin: int = get_parameter_from_parameter_group(
                group=radial_parameters,
                parameter="first_peak_max_bin",
                parameter_type=int,
                required=True,
            )
            self._second_peak_min_bin: int = get_parameter_from_parameter_group(
                group=radial_parameters,
                parameter="second_peak_min_bin",
                parameter_type=int,
                required=True,
            )
            self._second_peak_max_bin: int = get_parameter_from_parameter_group(
                group=radial_parameters,
                parameter="second_peak_max_bin",
                parameter_type=int,
                required=True,
            )
            self._ratio_threshold_min: float = get_parameter_from_parameter_group(
                group=radial_parameters,
                parameter="minimum_first_to_second_peak_ratio_for_sample",
                parameter_type=float,
                required=True,
            )
            self._ratio_threshold_max: float = get_parameter_from_parameter_group(
                group=radial_parameters,
                parameter="maximum_first_to_second_peak_ratio_for_sample",
                parameter_type=float,
                required=True,
            )

        self._estimate_particle_size: float = get_parameter_from_parameter_group(
            group=radial_parameters,
            parameter="estimate_particle_size",
            parameter_type=bool,
            required=True,
        )

        if self._estimate_particle_size:
            self._use_guinier_peak: float = get_parameter_from_parameter_group(
                group=radial_parameters,
                parameter="use_guinier_peak",
                parameter_type=bool,
                required=False,
            )
            self._guinier_qmin: float = get_parameter_from_parameter_group(
                group=radial_parameters,
                parameter="guinier_qmin",
                parameter_type=float,
                required=True,
            )
            self._guinier_qmax: float = get_parameter_from_parameter_group(
                group=radial_parameters,
                parameter="guinier_qmax",
                parameter_type=float,
                required=True,
            )

        self._coffset = geometry_information.get_detector_distance_offset()
        self._pixel_size = geometry_information.get_pixel_size()

        self._radial_profile = RadialProfile(
            radius_pixel_map=geometry_information.get_pixel_maps()["radius"],
            radial_parameters=radial_parameters,
        )

        self._radial_bin_labels = self._radial_profile.get_radial_bin_labels()
        self._radial_bin_centers = self._radial_profile.calculate_profile(
            data=self._radial_bin_labels
        )

    def analyze_radial_profile(
        self,
        *,
        data: Union[NDArray[numpy.float_], NDArray[numpy.int_]],
        beam_energy: float,
        detector_distance: float,
        downstream_intensity: float,
    ) -> Tuple[
        NDArray[numpy.float_],
        NDArray[numpy.float_],
        NDArray[numpy.float_],
        bool,
        float,
        float,
        float,
    ]:
        """
        Calculate radial profile from a detector data frame.

        This function calculates a radial profile based on the detector data frame
        provided to the function as input.

        Arguments:

            data: the detector data frame from which the radial profile will be
                calculated.

        Returns:

            A radial profile whose value is the average radial intensity calculated
            from the data frame.

        #TODO: Fix documentation
        """

        radial_profile: NDArray[numpy.float_] = self._radial_profile.calculate_profile(
            data=data
        )

        radial_profile_mask: Union[
            NDArray[numpy.bool_], bool
        ] = self._radial_profile.get_mask()

        errors: NDArray[numpy.float_]
        errors, _, _ = stats.binned_statistic(
            self._radial_bin_labels[radial_profile_mask].ravel(),
            data[radial_profile_mask].ravel(),
            "std",
        )

        if self._background_subtraction:
            coefficients = _fit_by_least_squares(
                radial_profile=radial_profile,
                vectors=self._background_profile_vectors,
                start_bin=self._background_subtraction_min_bin,
                stop_bin=self._background_subtraction_max_bin,
            )
            background_fit: NDArray[numpy.float_] = radial_profile * 0
            index: int
            for index in range(len(coefficients)):
                background_fit += (
                    coefficients[index] * self._background_profile_vectors[index]
                )

            radial_profile = radial_profile - background_fit

        wavelength: float = (
            constants.c * constants.h / (beam_energy * constants.electron_volt)
        )
        real_detector_distance: float = detector_distance * 1e-3 + self._coffset
        theta: NDArray[numpy.float_] = (
            numpy.arctan(
                self._pixel_size * self._radial_bin_centers / real_detector_distance
            )
            * 0.5
        )
        q: NDArray[numpy.float_] = (
            numpy.sin(theta) * 4 * numpy.pi / wavelength
        ) * 1e-10

        # grab the intensities from the regions of interest, e.g. water ring and low q
        # ring normalize by the downstream monitor
        roi1_intensity: float = (
            numpy.mean(
                radial_profile[
                    numpy.where((q >= self._roi1_qmin) & (q <= self._roi1_qmax))
                ]
            )
            #/ downstream_intensity
        )
        roi2_intensity: float = (
            numpy.mean(
                radial_profile[
                    numpy.where((q >= self._roi2_qmin) & (q <= self._roi2_qmax))
                ]
            )
            #/ downstream_intensity
        )

        frame_has_jet: bool = data.sum() > self._total_intensity_jet_threshold

        if frame_has_jet:
            if self._sample_detection:
                # first_profile_mean: numpy.float_ = numpy.mean(
                #     radial_profile[self._first_peak_min_bin : self._first_peak_max_bin]
                # )
                # second_profile_mean: numpy.float_ = numpy.mean(
                #     radial_profile[self._first_peak_min_bin : self._first_peak_max_bin]
                # )
                # first_to_second_peak_ratio = float(
                #     first_profile_mean / second_profile_mean
                # )
                first_to_second_peak_ratio = float(
                    roi1_intensity / roi2_intensity
                )
                sample_detected: bool = (
                    # Having a threshold maximum helps filtering out nozzle hits too
                    (first_to_second_peak_ratio > self._ratio_threshold_min)
                    and (first_to_second_peak_ratio < self._ratio_threshold_max)
                )
            else:
                sample_detected = False

            if self._estimate_particle_size:
                q_index: NDArray[numpy.int_] = numpy.where(
                    (q >= self._guinier_qmin) & (q <= self._guinier_qmax)
                )
                if len(q_index[0]) != 0:
                    q_min_index: numpy.int_ = numpy.min(q_index)
                    q_max_index: numpy.int_ = numpy.max(q_index)
                    if self._use_guinier_peak:
                        # try to estimate Rg using Guinier Peak method
                        rg: float = _calc_rg_by_guinier_peak(
                            q, radial_profile, nb=q_min_index, ne=q_max_index
                        )
                    else:
                        # try to estimate Rg using standard Guinier plot
                        rg = _calc_rg_by_guinier(
                            q, radial_profile, nb=q_min_index, ne=q_max_index
                        )
                else:
                    rg = 0.0
            else:
                rg = 0.0
        else:
            return (
                radial_profile,
                errors,
                q,
                False,
                roi1_intensity,
                roi2_intensity,
                0.6,
            )
        return (
            radial_profile,
            errors,
            q,
            sample_detected,
            roi1_intensity,
            roi2_intensity,
            rg,
        )


class RadialProfileAnalysisPlots:
    """
    See documentation for the `__init__` function.
    """

    def __init__(
        self,
        *,
        radial_parameters: Dict[str, Any],
    ) -> None:
        """
        #TODO: Documentation.
        """
        self._radius_bin_size: bool = get_parameter_from_parameter_group(
            group=radial_parameters,
            parameter="radius_bin_size",
            parameter_type=float,
        )

        self._running_average_window_size: int = get_parameter_from_parameter_group(
            group=radial_parameters,
            parameter="running_average_window_size",
            parameter_type=int,
            required=True,
        )

        self._hit_rate_history: Union[Deque[bool], None] = None
        self._q_history: Union[Deque[NDArray[numpy.float_]], None] = None
        self._radials_history: Union[Deque[NDArray[numpy.float_]], None] = None
        self._image_sum_history: Union[Deque[float], None] = None
        self._downstream_intensity_history: Union[Deque[float], None] = None
        self._roi1_intensity_history: Union[Deque[float], None] = None
        self._roi2_intensity_history: Union[Deque[float], None] = None
        self._rg_history: Union[Deque[float], None] = None

    def update_plots(
        self,
        *,
        radial_profile: NDArray[numpy.float_],
        detector_data_sum: float,
        q: NDArray[numpy.float_],
        downstream_intensity: float,
        roi1_intensity: float,
        roi2_intensity: float,
        sample_detected: bool,
        rg: float,
    ) -> Tuple[
        Deque[NDArray[numpy.float_]],
        Deque[NDArray[numpy.float_]],
        Deque[float],
        Deque[float],
        Deque[float],
        Deque[float],
        Deque[bool],
        Deque[float],
    ]:
        """
        #TODO: Documentation.
        """

        if self._hit_rate_history is None:
            num_radial_bins: int = len(radial_profile)

            self._hit_rate_history = deque(
                [False] * self._running_average_window_size,
                maxlen=self._running_average_window_size,
            )
            self._q_history = deque(
                [numpy.zeros(num_radial_bins)] * self._running_average_window_size,
                maxlen=self._running_average_window_size,
            )
            self._radials_history = deque(
                [numpy.zeros(num_radial_bins)] * self._running_average_window_size,
                maxlen=self._running_average_window_size,
            )
            self._image_sum_history = deque(
                [0.0] * self._running_average_window_size,
                maxlen=self._running_average_window_size,
            )
            self._downstream_intensity_history = deque(
                [0.0] * self._running_average_window_size,
                maxlen=self._running_average_window_size,
            )
            self._roi1_intensity_history = deque(
                [0.0] * self._running_average_window_size,
                maxlen=self._running_average_window_size,
            )
            self._roi2_intensity_history = deque(
                [0.0] * self._running_average_window_size,
                maxlen=self._running_average_window_size,
            )
            self._rg_history = deque(
                [0.0] * self._running_average_window_size,
                maxlen=self._running_average_window_size,
            )

        self._q_history.append(q)
        self._radials_history.append(radial_profile)
        self._image_sum_history.append(detector_data_sum)
        self._downstream_intensity_history.append(downstream_intensity)
        self._roi1_intensity_history.append(roi1_intensity)
        self._roi2_intensity_history.append(roi2_intensity)
        self._hit_rate_history.append(sample_detected)
        self._rg_history.append(rg)

        return (
            self._q_history,
            self._radials_history,
            self._image_sum_history,
            self._downstream_intensity_history,
            self._roi1_intensity_history,
            self._roi2_intensity_history,
            self._hit_rate_history,
            self._rg_history,
        )

    def clear_plots(self) -> None:
        """
        # TODO: Add documentation.
        """
        self._hit_rate_history = deque([], maxlen=self._running_average_window_size)
        self._q_history = deque([], maxlen=self._running_average_window_size)
        self._radials_history = deque([], maxlen=self._running_average_window_size)
        self._image_sum_history = deque([], maxlen=self._running_average_window_size)
        self._downstream_intensity_history = deque(
            [], maxlen=self._running_average_window_size
        )
        self._roi1_intensity_history = deque(
            [], maxlen=self._running_average_window_size
        )
        self._roi2_intensity_history = deque(
            [], maxlen=self._running_average_window_size
        )
        self._rg_history = deque([], maxlen=self._running_average_window_size)
