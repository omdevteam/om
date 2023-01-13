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

import sys
from typing import Any, Dict, Tuple, Union, cast

import numpy
from numpy.typing import NDArray

from om.algorithms.crystallography import (
    Peakfinder8PeakDetection,
    RadialProfileAnalysisWithSampleDetection,
    TypePeakList,
    fit_by_least_squares,
)
from om.algorithms.generic import Binning
from om.library.geometry import TypePixelMaps
from om.library.parameters import get_parameter_from_parameter_group


class CrystallographyPeakFinding:
    """
    See documentation for the `__init__` function.
    """

    def __init__(
        self,
        *,
        crystallography_parameters: Dict[str, Any],
        peak_finding_parameters: Dict[str, Any],
        pixel_maps: TypePixelMaps,
        binning_algorithm: Union[Binning, None],
        binning_before_peak_finding: Union[bool, None],
    ) -> None:
        """
        TODO: Add documentation
        """

        self._peak_detection: Peakfinder8PeakDetection = Peakfinder8PeakDetection(
            parameters=peak_finding_parameters,
            radius_pixel_map=cast(NDArray[numpy.float_], pixel_maps["radius"]),
        )
        self._binning: Union[Binning, None] = binning_algorithm
        if self._binning is not None:

            self._binning_before_peak_finding: Union[
                bool, None
            ] = binning_before_peak_finding
            self._bin_size: int = self._binning.get_bin_size()

            if binning_before_peak_finding:
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
                        self._binning.bin_pixel_maps(pixel_maps=pixel_maps)["radius"],
                    )
                )

            # self._data_shape = binning_algorithm.get_binned_data_shape()

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

    def find_peaks(self, detector_data: numpy.ndarray) -> Tuple[TypePeakList, bool]:
        """
        TODO: Add documentation.
        """

        peak_list: TypePeakList = self._peak_detection.find_peaks(data=detector_data)

        if self._binning is not None and not self._binning_before_peak_finding:
            peak_index: int
            for peak_index in range(peak_list["num_peaks"]):
                peak_list["fs"][peak_index] = (
                    peak_list["fs"][peak_index] + 0.5
                ) / self._bin_size - 0.5
                peak_list["ss"][peak_index] = (
                    peak_list["ss"][peak_index] + 0.5
                ) / self._bin_size - 0.5

        frame_is_hit: bool = (
            self._min_num_peaks_for_hit
            < len(peak_list["intensity"])
            < self._max_num_peaks_for_hit
        )

        if not frame_is_hit:
            peak_list["num_peaks"] = 0
            peak_list["fs"] = []
            peak_list["ss"] = []
            peak_list["intensity"] = []
            peak_list["max_pixel_intensity"] = []
            peak_list["num_pixels"] = []
            peak_list["max_pixel_intensity"] = []

        return (peak_list, frame_is_hit)


class RadialProfileAnalysis:
    """
    See documentation of the '__init__' function.
    """

    def __init__(
        self,
        *,
        radius_pixel_map: NDArray[numpy.float_],
        swaxs_parameters: Dict[str, Any],
    ) -> None:
        """
        #TODO: Add documentation.
        """

        self._radial_profile_analysis = RadialProfileAnalysisWithSampleDetection(
            swaxs_parameters=swaxs_parameters, radius_pixel_map=radius_pixel_map
        )

        self._jet_threshold: float = get_parameter_from_parameter_group(
            group=swaxs_parameters,
            parameter="threshold_for_jet_hit",
            parameter_type=float,
            required=True,
        )

        self._subtract_background: bool = get_parameter_from_parameter_group(
            group=swaxs_parameters,
            parameter="subtract_background",
            parameter_type=bool,
            default=False,
        )

        if self._subtract_background:

            background_vectors_filename: str = get_parameter_from_parameter_group(
                group=swaxs_parameters,
                parameter="background_vectors_npy_filename",
                parameter_type=str,
                required=True,
            )

            try:
                self._background_vectors: numpy.ndarray = numpy.atleast_2d(
                    numpy.load(background_vectors_filename)
                )
            except (IOError, OSError, KeyError) as exc:
                # TODO: type this
                exc_type, exc_value = sys.exc_info()[:2]
                raise RuntimeError(
                    "The following error occurred while reading the {0} water profile "
                    "file: {1}: {2}".format(
                        background_vectors_filename,
                        exc_type.__name__,  # type: ignore
                        exc_value,
                    )
                ) from exc

    def analyze_radial_profile(
        self, *, detector_data: numpy.ndarray
    ) -> Tuple[numpy.ndarray, numpy.ndarray, numpy.ndarray, float, bool, bool]:
        """
        # TODO: Add documentation
        """
        radial: numpy.ndarray
        errors: numpy.ndarray
        radial, errors = self._radial_profile_analysis.compute_radial_profile(
            data=detector_data
        )

        detector_data_sum: float = detector_data.sum()
        frame_is_jet: bool = detector_data_sum > self._jet_threshold
        if not frame_is_jet:
            frame_is_droplet: bool = False
        else:
            frame_is_droplet = self._radial_profile_analysis.detect_sample(
                radial_profile=radial
            )

        if self._subtract_background:
            coefficients = fit_by_least_squares(
                radial_profile=radial,
                vectors=self._background_vectors,
                start_bin=800,
                stop_bin=1000,
            )
            background: numpy.ndarray = radial * 0
            for i in range(len(coefficients)):
                background += coefficients[i] * self._background_vectors[i]
            subtracted_radial: numpy.ndarray = radial - background
        else:
            subtracted_radial = radial

        return (
            radial,
            subtracted_radial,
            errors,
            detector_data_sum,
            frame_is_droplet,
            frame_is_jet,
        )
