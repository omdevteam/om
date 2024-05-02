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
Radial average algorithms.

This module contains classes and functions that perform common data processing
operations on radial profile information computed from detector data frames.
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


def _cumulative_moving_average(new_radial, previous_cumulative_avg, num_events):
    return ((previous_cumulative_avg * num_events) + new_radial) / (num_events + 1)


def _calc_rg_by_guinier(
    q,
    radial,
    nb=None,
    ne=None,
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
        except:  # noqa: E722
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
    q,
    radial,
    exp=1,
    nb=None,
    ne=None,
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
    except:  # noqa: E722
        # if polyfit fails, just grab the maximum position
        qpeaki: int = numpy.argmax(qdI)
        qpeak = qs[qpeaki]
    # calculate Rg from the peak position
    rg: float = (3.0 * d / 2.0) ** 0.5 / qpeak
    return rg


def _sphere_form_factor(radius, q_mags, check_divide_by_zero=True):
    # By Rick Kirian and Joe Chen
    # Copied from reborn.simulate.form_factors with permission.
    # Form factor :math:`f(q)` for a sphere of radius :math:`r`, at given :math:`q`
    # magnitudes.  The formula is
    #
    #    f(q) = 4 * pi * (sin(qr) - qr * cos(qr)) / q^3
    #
    # When q = 0, the following limit is used:
    #
    #    f(0) = 4 / 3  * pi * r^3
    #
    # The formula can be found, for example, in Table A.1 of |Guinier|.  There are no
    # approximations in this formula beyond the 1st Born approximation; it is not a
    # small-angle formula.
    #
    # Note that you need to multiply this by the electron density of the sphere if you
    # want reasonable amplitudes.
    # E.g., water molecules have 10 electrons, a molecular weight of 18 g/mol and a
    # density of 1 g/ml, so you can google search the electron density of water, which
    # is 10*(1 g/cm^3)/(18 g/6.022e23) = 3.346e29 per m^3 .
    qr = q_mags * radius
    if check_divide_by_zero is True:
        amp = numpy.zeros_like(qr)
        amp[qr == 0] = (4 * numpy.pi * radius**3) / 3
        w = qr != 0
        amp[w] = (
            4
            * numpy.pi
            * radius**3
            * (numpy.sin(qr[w]) - qr[w] * numpy.cos(qr[w]))
            / qr[w] ** 3
        )
    else:
        amp = (
            4 * numpy.pi * radius**3 * (numpy.sin(qr) - qr * numpy.cos(qr)) / qr**3
        )
    return amp


class _SphericalDroplets:
    # By Rick Kirian and Joe Chen
    # Copied from reborn.analysis.optimize with permission.
    def __init__(self, q=None, r=None):
        if q is None:
            q = numpy.linspace(0, 1e10, 517)
        if r is None:
            r = numpy.linspace(
                50, 3000, 20
            )  # set of spherical radii to test in angstroms
        self.q = q.copy()
        self.r = r.copy()  # radius range of sphere to scan through

        self.N = len(self.r)
        self.I_R_precompute = numpy.zeros((self.N, len(self.q)))
        for i in range(self.N):
            self.I_R_precompute[i, :] = (
                _sphere_form_factor(
                    radius=self.r[i], q_mags=self.q, check_divide_by_zero=True
                )
            ) ** 2

    def fit_profile(self, I_D, mask=None):
        if mask is None:
            mask = numpy.ones_like(I_D)

        w = mask > 0

        A_save = numpy.zeros(self.N)
        error_vec = numpy.zeros(self.N)
        for i in range(self.N):
            I_R = self.I_R_precompute[i, :]
            A = numpy.sum(I_D[w] * I_R[w]) / numpy.sum(I_R[w] ** 2)
            diff_sq = (A * I_R[w] - I_D[w]) ** 2
            error_vec[i] = numpy.sum(diff_sq)
            A_save[i] = A

        ind_min = numpy.argmin(error_vec)

        A_min = A_save[ind_min]
        r_min = self.r[ind_min]
        e_min = error_vec[ind_min]
        I_R_min = self.I_R_precompute[ind_min, :]

        r_dic = dict(
            A_min=A_min, e_min=e_min, error_vec=error_vec, I_R_min=I_R_min.copy()
        )

        return r_min, r_dic


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
        Radial profile analysis.

        This class stores all the information required to compute radial profiles
        from detector data frames, and to analyze them. The analysis performed by this
        class includes optional subtraction of a background profile, detection of a
        sample droplet (by comparing the intensity of two specific regions of the
        radial profile), and estimation of the size of the sample droplet.

        After the class has been initialized, it can be invoked to compute the radial
        profile of a data frame, and to analyze it.

        Arguments:

            radial_parameters: A set of OM configuration parameters collected together
                in a parameter group. The parameter group must contain the following
                entries:

                * `background_subtraction`: Whether a background profile should be
                  subtracted from the radial profile being analyzed. if the value of
                  this parameter is true, a set of vectors describing the background
                  profile are fitted to the profile being analyzed, within a specified
                  region of the radial profile. The background profile is then
                  subtracted, and all subsequent analysis steps are performed on the
                  background-subtracted radial profile. Defaults to False.

                * `background_profile_filename`: The relative or absolute path to an
                  HDF5 containing vectors that describe a background profile.

                  - The vectors must be saved in the file in the format of a 2D array,
                    with each row storing a single 1D vector.

                  If the value of the `background_subtraction` parameter is True, this
                  parameter must be provided and cannot be None.

                * `background_profile_hdf5_path`: The internal HDF5 path to the data
                  block storing information about the background profile.

                  If the value of the `background_subtraction` parameter is True, this
                  parameter must be provided and cannot be None.

                * `background_subtraction_min_fit_bin`: The start radial bin for the
                  region where the background profile is fitted to radial profile being
                  analyzed.

                  If the value of the `background_subtraction` parameter is True, this
                  parameter must be provided and cannot be None.

                * `background_subtraction_max_fit_bin`: The end radial bin for the
                  region where the background profile is fitted to radial profile being
                  analyzed.

                  If the value of the `background_subtraction` parameter is True, this
                  parameter must be provided and cannot be None.

                * `sample_detection`: Whether sample droplet detection should be part
                  of the analysis carried out by this class. Defaults to False.

                * `total_intensity_jet_threshold`: An intensity threshold used to
                  determine if a liquid jet is present in the area irradiated by the
                  beam. If the total intensity recorded in the detector data frame is
                  below this threshold, no jet, and therefore no sample is assumed to
                  be present in the detector frame.

                  If the value of the `sample_detection` parameter is True, this
                  parameter must be provided and cannot be None.

                * `roi1_qmin`: Start, in q coordinates, of the first region of interest
                  in the radial profile for the detection of a sample droplet.

                  If the value of the `sample_detection` parameter is True, this
                  parameter must be provided and cannot be None.

                * `roi1_qmax`: End, in q coordinates, of the first region of interest
                  in the radial profile for the detection of a sample droplet.

                  If the value of the `sample_detection` parameter is True, this
                  parameter must be provided and cannot be None.

                * `roi2_qmin`: Start, in q coordinates, of the second region of
                  interest in the radial profile for the detection of a sample droplet.

                  If the value of the `sample_detection` parameter is True, this
                  parameter must be provided and cannot be None.

                * `roi2_qmax`: End, in q coordinates, of the second region of interest
                  in the radial profile for the detection of a sample droplet.

                  If the value of the `sample_detection` parameter is True, this
                  parameter must be provided and cannot be None.

                * `"minimum_roi1_to_roi2_intensity_ratio_for_sample`: minimum ratio
                  the intensities recorded in the first and second regions of interest
                  must have for a sample droplet to be detected in the detector frame.

                  If the value of the `sample_detection` parameter is True, this
                  parameter must be provided and cannot be None.

                * `"maximum_roi1_to_roi2_intensity_ratio_for_sample`: maximum ratio
                  the intensities recorded in the first and second regions of interest
                  must have for a sample droplet to be detected in the detector frame.

                  If the value of the `sample_detection` parameter is True, this
                  parameter must be provided and cannot be None.

                * `estimate_particle_size`: Whether the analysis should include an
                  estimation of the sample droplet size, if a droplet was detected in
                  the detector frame. Defaults to False.

                * `size_estimation_method`: The strategy that should be used to
                  estimate the size of a sample droplet. This parameter can currently
                  have one of the following values:

                  - `guinier`: The droplet size is estimated using the Guinier method.

                  - `peak`: The droplet size is estimated using the Guinier peak
                    method.

                  - `sphere`: The droplet size is estimated using the Sphere method
                    from the Reborn software package.

                  If the value of the `sample_detection` parameter is True, this
                  parameter must be provided and cannot be None.
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

        self._sample_detection: bool = get_parameter_from_parameter_group(
            group=radial_parameters,
            parameter="sample_detection",
            parameter_type=bool,
            default=False,
        )

        if self._sample_detection:
            self._total_intensity_jet_threshold: float = (
                get_parameter_from_parameter_group(
                    group=radial_parameters,
                    parameter="total_intensity_jet_threshold",
                    parameter_type=float,
                    required=True,
                )
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

            self._ratio_threshold_min: float = get_parameter_from_parameter_group(
                group=radial_parameters,
                parameter="minimum_roi1_to_roi2_intensity_ratio_for_sample",
                parameter_type=float,
                required=True,
            )
            self._ratio_threshold_max: float = get_parameter_from_parameter_group(
                group=radial_parameters,
                parameter="maximum_roi1_to_roi2_intensity_ratio_for_sample",
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
            self._size_estimation_method: str = get_parameter_from_parameter_group(
                group=radial_parameters,
                parameter="size_estimation_method",
                parameter_type=str,
                default="guinier",
            )

            self._guinier_qmin: float = get_parameter_from_parameter_group(
                group=radial_parameters,
                parameter="roi2_qmin",
                parameter_type=float,
                default=0.0,
            )
            self._guinier_qmax: float = get_parameter_from_parameter_group(
                group=radial_parameters,
                parameter="guinier_qmax",
                parameter_type=float,
                default=0.1,
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

        self._radial_profile_bad_pixel_map: Union[
            NDArray[numpy.bool_], None
        ] = self._radial_profile.get_bad_pixel_map()

        # initialize spherical droplets
        self._spherical_droplets: Union[_SphericalDroplets, None] = None

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
        Calculate and analyze a radial profile from a detector data frame.

        This function calculates and analyzes the radial profile of the provided
        detector data frame.


        Arguments:

            data: the detector data frame for which the radial profile must be computed
                and analyzed.

        Returns:

            A radial profile whose value is the average radial intensity calculated
            from the data frame.
        """

        radial_profile: NDArray[numpy.float_] = self._radial_profile.calculate_profile(
            data=data
        )

        errors: NDArray[numpy.float_]
        errors, _, _ = stats.binned_statistic(
            self._radial_bin_labels[self._radial_profile_bad_pixel_map].ravel(),
            data[self._radial_profile_bad_pixel_map].ravel(),
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
            # / downstream_intensity
        )
        roi2_intensity: float = (
            numpy.mean(
                radial_profile[
                    numpy.where((q >= self._roi2_qmin) & (q <= self._roi2_qmax))
                ]
            )
            # / downstream_intensity
        )

        frame_sum = data.mean()
        frame_has_jet: bool = frame_sum > self._total_intensity_jet_threshold
        if frame_has_jet:
            if self._sample_detection:
                first_to_second_peak_ratio = float(roi1_intensity / roi2_intensity)
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
                    if self._size_estimation_method == "sphere":
                        # try to estimate radius using spherical droplets
                        if self._spherical_droplets is None:
                            # For the first frame, instantiate the class with the now
                            # known q values.
                            # Note: this assumes q does not change frame to frame.
                            self._spherical_droplets = _SphericalDroplets(q=q)
                            # Can add r=set of radii later
                            # Note: this is r, radius, not rg
                        r, _ = self._spherical_droplets.fit_profile(
                            I_D=radial_profile, mask=None
                        )
                        rg = r
                        # for simplicity since rg is returned below for guinier
                        # stuff.
                    elif self._size_estimation_method == "peak":
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
                frame_sum,
            )
        return (
            radial_profile,
            errors,
            q,
            sample_detected,
            roi1_intensity,
            roi2_intensity,
            rg,
            frame_sum,
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

        self._num_radials_to_send: int = get_parameter_from_parameter_group(
            group=radial_parameters,
            parameter="num_radials_to_send",
            parameter_type=int,
            required=True,
        )

        self._num_hits_in_cum_radial_avg: int = get_parameter_from_parameter_group(
            group=radial_parameters,
            parameter="num_hits_in_cum_radial_avg",
            parameter_type=int,
        )

        self._num_events_to_plot: int = 5000

        self._hit_rate_running_window: Deque[float] = deque(
            [0.0] * self._running_average_window_size,
            maxlen=self._running_average_window_size,
        )
        self._avg_hit_rate: int = 0
        self._num_hits: int = 0
        self._hit_rate_timestamp_history: Deque[float] = deque(
            self._num_events_to_plot * [0.0], maxlen=self._num_events_to_plot
        )
        # self._hit_rate_history: Deque[float] = deque(5000 * [0.0], maxlen=5000)

        self._hit_rate_history: Union[Deque[NDArray[numpy.float_]], None] = None
        self._q_history: Union[Deque[NDArray[numpy.float_]], None] = None
        self._radials_history: Union[Deque[NDArray[numpy.float_]], None] = None
        self._image_sum_history: Union[Deque[float], None] = None
        self._downstream_intensity_history: Union[Deque[float], None] = None
        self._roi1_intensity_history: Union[Deque[float], None] = None
        self._roi2_intensity_history: Union[Deque[float], None] = None
        self._rg_history: Union[Deque[float], None] = None
        self._cumulative_hits_radial = None

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
                [False] * self._num_events_to_plot,
                maxlen=self._num_events_to_plot,
            )
            self._hit_rate_running_window: Deque[float] = deque(
                [0.0] * self._running_average_window_size,
                maxlen=self._running_average_window_size,
            )
            self._q_history = deque(
                [numpy.zeros(num_radial_bins)] * self._num_radials_to_send,
                maxlen=self._num_radials_to_send,
            )
            self._radials_history = deque(
                [numpy.zeros(num_radial_bins)] * self._num_radials_to_send,
                maxlen=self._num_radials_to_send,
            )
            self._image_sum_history = deque(
                [0.0] * self._num_events_to_plot,
                maxlen=self._num_events_to_plot,
            )
            self._downstream_intensity_history = deque(
                [0.0] * self._num_events_to_plot,
                maxlen=self._num_events_to_plot,
            )
            self._roi1_intensity_history = deque(
                [0.0] * self._num_events_to_plot,
                maxlen=self._num_events_to_plot,
            )
            self._roi2_intensity_history = deque(
                [0.0] * self._num_events_to_plot,
                maxlen=self._num_events_to_plot,
            )
            self._rg_history = deque(
                [0.0] * self._num_events_to_plot,
                maxlen=self._num_events_to_plot,
            )
            # for the first event, the cumulative radial will just be the radial of that first event
            self._cumulative_hits_radial = radial_profile

        self._hit_rate_running_window.append(float(sample_detected))
        avg_hit_rate = (
            sum(self._hit_rate_running_window) / self._running_average_window_size
        )
        # self._hit_rate_timestamp_history.append(timestamp)
        self._hit_rate_history.append(avg_hit_rate * 100.0)

        self._q_history.append(q)
        self._radials_history.append(radial_profile)
        self._image_sum_history.append(detector_data_sum)
        self._downstream_intensity_history.append(downstream_intensity)
        self._roi1_intensity_history.append(roi1_intensity)
        self._roi2_intensity_history.append(roi2_intensity)
        # self._hit_rate_history.append(sample_detected)
        self._rg_history.append(rg)
        # only add to cumulative radial if a hit, i.e. sample detected
        if sample_detected:
            self._num_hits += 1
            if self._num_hits > self._num_hits_in_cum_radial_avg:
                # reset cumulative hits radial every N hits
                self._cumulative_hits_radial = radial_profile
            else:
                self._cumulative_hits_radial = _cumulative_moving_average(
                    new_radial=radial_profile,
                    previous_cumulative_avg=self._cumulative_hits_radial,
                    num_events=self._num_hits,
                )

        return (
            self._q_history,
            self._radials_history,
            self._image_sum_history,
            self._downstream_intensity_history,
            self._roi1_intensity_history,
            self._roi2_intensity_history,
            self._hit_rate_history,
            self._rg_history,
            self._cumulative_hits_radial,
        )

    def clear_plots(self) -> None:
        """
        # TODO: Add documentation.
        """
        # self._hit_rate_history = deque([], maxlen=self._running_average_window_size)
        self._hit_rate_running_window = deque(
            [0.0] * self._running_average_window_size,
            maxlen=self._running_average_window_size,
        )
        self._avg_hit_rate = 0
        self._num_hits = 0
        self._hit_rate_timestamp_history = deque(
            self._num_events_to_plot * [0.0], maxlen=self._num_events_to_plot
        )
        self._hit_rate_history = deque(
            self._num_events_to_plot * [0.0], maxlen=self._num_events_to_plot
        )

        self._q_history = deque([], maxlen=self._num_radials_to_send)
        self._radials_history = deque([], maxlen=self._num_radials_to_send)
        self._image_sum_history = deque([], maxlen=self._num_events_to_plot)
        self._downstream_intensity_history = deque([], maxlen=self._num_events_to_plot)
        self._roi1_intensity_history = deque([], maxlen=self._num_events_to_plot)
        self._roi2_intensity_history = deque([], maxlen=self._num_events_to_plot)
        self._rg_history = deque([], maxlen=self._num_events_to_plot)
