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
Algorithms for the processing of crystallography data.

This module contains algorithms that perform data processing operations for Serial
Crystallography. Additionally, it contains the definitions of several typed
dictionaries that store data produced or required by these algorithms.
"""


import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import numpy
from numpy.typing import NDArray
from pydantic import BaseModel, Field, ValidationError, model_validator
from typing_extensions import Self

from om.algorithms.common import PeakList
from om.lib.exceptions import OmConfigurationFileSyntaxError
from om.lib.files import load_hdf5_data
from om.lib.geometry import DetectorLayoutInformation
from om.lib.protocols import OmPeakDetectionProtocol

from ._crystallography_cython import peakfinder_8  # type: ignore


class _Peakfinder8PeakDetectionParameters(BaseModel):
    max_num_peaks: int
    adc_threshold: float
    minimum_snr: float
    min_pixel_count: int
    max_pixel_count: int
    local_bg_radius: int
    min_res: int
    max_res: int
    fast_mode: bool = Field(default=False)
    num_pixel_per_bin_in_radial_statistics: int = Field(default=100)
    bad_pixel_map_filename: Optional[Path] = Field(default=None)
    bad_pixel_map_hdf5_path: Optional[str] = Field(default=None)

    @model_validator(mode="after")
    def check_hd5_path(self) -> Self:
        if (
            self.bad_pixel_map_filename is not None
            and self.bad_pixel_map_hdf5_path is None
        ):
            raise ValueError(
                "If the bad_pixel_map_filename parameter is specified, "
                "the bad_pixel_map_hdf5_path must also be provided"
            )
        return self


class Peakfinder8PeakDetection(OmPeakDetectionProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        radius_pixel_map: NDArray[numpy.float_],
        layout_info: DetectorLayoutInformation,
        parameters: Dict[str, Any],
    ) -> None:
        """
        Peakfinder8 algorithm for peak detection.

        This algorithm stores all the parameters required to detect Bragg peaks in a
        detector data frame using the `peakfinder8` strategy, described in the
        following publication:

        A. Barty, R. A. Kirian, F. R. N. C. Maia, M. Hantke, C. H. Yoon, T. A. White,
        and H. N. Chapman, "Cheetah: software for high-throughput reduction and
        analysis of serial femtosecond x-ray diffraction data", J Appl  Crystallogr,
        vol. 47, pp. 1118-1131 (2014).

        After the algorithm has been initialized, it can be invoked to detect peaks in
        a data frame.

        Arguments:

            radius_pixel_map: A pixel map storing radius information for the detector
                data frame on which the algorithm is applied.

                * The array must have the same shape as the data frame on which the
                  algorithm is applied.

                * Each element of the array must store, for the corresponding pixel in
                  the data frame, its distance (in pixels) from the origin of the
                  detector reference system (usually the center of the detector).

            layout_info: An object storing information about the internal layout of the
                detector data frame on which the algorithm is applied (number and size
                of ASICs, etc.).

            parameters: A set of OM configuration parameters collected together in a
                parameter group. The parameter group must contain the following
                entries:

                * `max_num_peaks`: The maximum number of peaks that the algorithm
                   should retrieve from each  data frame. Additional peaks will be
                   ignored.

                * `adc_threshold`: The minimum ADC threshold for peak detection.

                * `minimum_snr`: The minimum signal-to-noise ratio for peak detection.

                * `min_pixel_count`: The minimum size of a peak in pixels.

                * `max_pixel_count`: The maximum size of a peak in pixels.

                * `local_bg_radius`: The radius, in pixels, for the estimation of the
                  local background.

                * `min_res`: The minimum distance at which a peak can be located, in
                   pixels, from the center of the detector.

                * `max_res`: The maximum distance at which a peak can be located, in
                   pixels, from the center of the detector.

                * `bad_pixel_map_filename`: The relative or absolute path to an HDF5
                   file containing a bad pixel map. The map can be used to exclude
                   regions of the data frame from the peak search. If the value of this
                   entry is None, the peak search extends to the full frame. Defaults
                   to None.

                    - The map must be a numpy array with the same shape as the data
                      frame on which the algorithm is applied.

                    - Each pixel in the map must have a value of either 0, meaning that
                      the corresponding pixel in the data frame should be ignored, or
                      1, meaning that the corresponding pixel should be included in the
                      peak search.

                    - The map is only used to exclude areas from the peak search: the
                      data is not modified in any way.

                * `bad_pixel_map_hdf5_path`: The internal HDF5 path to the data block
                  where the bad pixel map data is located. Defaults to None.

                    * If the `bad_pixel_map_filename` entry is not None, this entry
                      must also be provided, and cannot be None. Otherwise it is
                      ignored.

        """
        try:
            self._parameters: _Peakfinder8PeakDetectionParameters = (
                _Peakfinder8PeakDetectionParameters.model_validate(parameters)
            )
        except ValidationError as exception:
            raise OmConfigurationFileSyntaxError(
                "Error parsing parameters for the Peakfinder8PeakDetection algorithm: "
                f"{exception}"
            )

        self._asic_nx: int = layout_info.asic_nx
        self._asic_ny: int = layout_info.asic_ny
        self._nasics_x: int = layout_info.nasics_x
        self._nasics_y: int = layout_info.nasics_y
        self._max_num_peaks: float = self._parameters.max_num_peaks
        self._adc_thresh: float = self._parameters.adc_threshold
        self._minimum_snr: float = self._parameters.minimum_snr
        self._min_pixel_count: int = self._parameters.min_pixel_count
        self._max_pixel_count: int = self._parameters.max_pixel_count
        self._local_bg_radius: int = self._parameters.local_bg_radius
        self._min_res: int = self._parameters.min_res
        self._max_res: int = self._parameters.max_res

        if (
            self._parameters.bad_pixel_map_filename is not None
            and self._parameters.bad_pixel_map_hdf5_path is not None
        ):
            self._bad_pixel_map: Optional[NDArray[numpy.int_]] = cast(
                Optional[NDArray[numpy.int_]],
                load_hdf5_data(
                    hdf5_filename=self._parameters.bad_pixel_map_filename,
                    hdf5_path=self._parameters.bad_pixel_map_hdf5_path,
                ),
            )
        else:
            self._bad_pixel_map = None

        self._mask: Optional[NDArray[numpy.int_]] = None
        self._radius_pixel_map: NDArray[numpy.float_] = radius_pixel_map

        self._radial_stats_pixel_index: Union[None, NDArray[numpy.int_]] = None
        self._radial_stats_radius: Union[None, NDArray[numpy.int_]] = None
        self._radial_stats_num_pixels: int = 0

        if self._parameters.fast_mode is True:

            self._compute_radial_stats_pixels(
                num_pixels_per_bin=(
                    self._parameters.num_pixel_per_bin_in_radial_statistics
                )
            )

    def _compute_radial_stats_pixels(self, *, num_pixels_per_bin: int) -> None:
        radius_pixel_map_as_int: NDArray[numpy.int_] = (
            numpy.rint(self._radius_pixel_map).astype(int).ravel()
        )
        peak_index: List[int] = []
        radius: List[int] = []
        idx: NDArray[numpy.int_]
        for idx in numpy.split(
            numpy.argsort(radius_pixel_map_as_int, kind="mergesort"),
            numpy.cumsum(numpy.bincount(radius_pixel_map_as_int)[:-1]),
        ):
            if len(idx) < num_pixels_per_bin:
                peak_index.extend(idx)
                radius.extend(radius_pixel_map_as_int[(idx,)])
            else:
                idx_sample = random.sample(list(idx), num_pixels_per_bin)
                peak_index.extend(idx_sample)
                radius.extend(radius_pixel_map_as_int[(idx_sample,)])
        self._radial_stats_pixel_index = numpy.array(peak_index).astype(numpy.int32)
        self._radial_stats_radius = numpy.array(radius).astype(numpy.int32)
        self._radial_stats_num_pixels = self._radial_stats_pixel_index.shape[0]

    def set_layout_info(self, layout_info: DetectorLayoutInformation) -> None:
        self._asic_nx = layout_info.asic_nx
        self._asic_ny = layout_info.asic_ny
        self._nasics_x = layout_info.nasics_x
        self._nasics_y = layout_info.nasics_y

    def get_bad_pixel_map(self) -> Optional[NDArray[numpy.int_]]:
        return self._bad_pixel_map

    def set_bad_pixel_map(self, bad_pixel_map: Optional[NDArray[numpy.int_]]) -> None:
        self._bad_pixel_map = bad_pixel_map

    def set_radius_pixel_map(self, radius_pixel_map: NDArray[numpy.float_]) -> None:
        self._radius_pixel_map = radius_pixel_map.astype(numpy.float32)
        if self._parameters.fast_mode is True:
            self._compute_radial_stats_pixels(
                num_pixels_per_bin=self._num_pixels_per_bin
            )

    def get_adc_thresh(self) -> float:
        """
        Gets the minimum ADC threshold for peak detection.

        This function returns the minimum ADC threshold currently used by the algorithm
        to detect peaks.

        Returns:

            The minimum ADC threshold currently used by the algorithm.
        """
        return self._adc_thresh

    def set_adc_thresh(self, *, adc_thresh: float) -> None:
        """
        Sets the current minimum ADC threshold for peak detection.

        This function sets the minimum ADC threshold used by the algorithm to detect
        peaks. Any future call to the
        [`find_peaks`][om.algorithms.crystallography.Peakfinder8PeakDetection.find_peaks]
        method will use, for the `adc_thresh` parameter, the value provided here.

        Arguments:

            adc_thresh: The new value of the minimum ADC threshold for peak detection.
        """
        self._adc_thresh = adc_thresh

    def get_minimum_snr(self) -> float:
        """
        Gets the current minimum signal-to-noise ratio for peak detection.

        This function returns the minimum signal-to-noise ratio currently used by the
        algorithm to detect peaks.

        Returns:

            The minimum signal-to-noise ratio currently used by the algorithm.
        """
        return self._minimum_snr

    def set_minimum_snr(self, *, minimum_snr: float) -> None:
        """
        Sets the minimum signal-to-noise ratio for peak detection.

        This function sets the minimum signal-to-noise ratio used by the algorithm to
        detect peaks. Any future call to the
        [`find_peaks`][om.algorithms.crystallography.Peakfinder8PeakDetection.find_peaks]
        method will use, for the `minimum_snr` algorithm parameter, the value provided
        here.

        Arguments:

            minimum_snr: The new value of the minimum signal-to-noise ratio for peak
                detection.
        """
        self._minimum_snr = minimum_snr

    def get_min_pixel_count(self) -> int:
        """
        Gets the current minimum size for a peak in pixels.

        This function returns the minimum size, in pixels, that the algorithm currently
        expects a peak to have.

        Returns:

            The current minimum size, in pixels, for a peak.
        """
        return self._min_pixel_count

    def set_min_pixel_count(self, *, min_pixel_count: int) -> None:
        """
        Sets the minimum size for a peak in pixels.

        This function sets the minimum size, in pixels, that the algorithm expects a
        peak to have. Any future call to the
        [`find_peaks`][om.algorithms.crystallography.Peakfinder8PeakDetection.find_peaks]
        method will use, for the `min_pixel_count` parameter, the value provided here.

        Arguments:

            min_pixel_count: The new minimum size for a peak in pixels.
        """
        self._min_pixel_count = min_pixel_count

    def get_max_pixel_count(self) -> int:
        """
        Gets the current maximum size for a peak in pixels.

        This function returns the maximum size, in pixels, that the algorithm currently
        expects a peak to have.

        Returns:

            The current maximum size, in pixels, for a peak.
        """
        return self._max_pixel_count

    def set_max_pixel_count(self, *, max_pixel_count: int) -> None:
        """
        Sets the maximum size for a peak in pixels.

        This function sets the maximum size, in pixels, that the algorithm expects a
        peak to have. Any future call to the
        [`find_peaks`][om.algorithms.crystallography.Peakfinder8PeakDetection.find_peaks]
        method will use, for the `max_pixel_count` parameter, the value provided here.

        Arguments:

            max_pixel_count: The new maximum size for a peak in pixels.
        """
        self._max_pixel_count = max_pixel_count

    def get_local_bg_radius(self) -> int:
        """
        Gets the radius, in pixels, currently used to estimate the local background.

        This function returns the radius, in pixels, currently used by the algorithm to
        estimate the local background.

        Returns:

            The radius, in pixels, currently used for the estimation of the local
                background.
        """
        return self._local_bg_radius

    def set_local_bg_radius(self, *, local_bg_radius: int) -> None:
        """
        Sets the radius, in pixels, for the estimation of the local background.

        This function sets the radius, in pixels, used by the algorithm to estimate the
        local background. Any future call to the
        [`find_peaks`][om.algorithms.crystallography.Peakfinder8PeakDetection.find_peaks]
        method will use, for the `local_bg_radius` parameter, the value provided here.

        Arguments:

            local_bg_radius: The new radius, in pixels, to be used for the estimation
                of the local background.
        """
        self._local_bg_radius = local_bg_radius

    def get_min_res(self) -> int:
        """
        Gets the minimum distance for a peak from the detector's center in pixels.

        This function returns the minimum distance from the center of the detector, in
        pixels, that the algorithm currently expects a peak to have.

        Returns:

            The current minimum distance, in pixels, for a peak from the detector's
            center.
        """
        return self._min_res

    def set_min_res(self, *, min_res: int) -> None:
        """
        Sets the minimum distance for a peak from the detector's center in pixels.

        This function sets the minimum distance from the center of the detector, in
        pixels, that the algorithm expects a peak to have. Any future call to the
        [`find_peaks`][om.algorithms.crystallography.Peakfinder8PeakDetection.find_peaks]
        method will use, for the `min_res` parameter, the value provided here.

        Arguments:

            min_res: The new minimum distance, in pixels, from the detector's center
                for a peak.
        """
        self._min_res = min_res
        self._mask = None

    def get_max_res(self) -> int:
        """
        Gets the maximum distance for a peak from the detector's center in pixels.

        This function returns the maximum distance from the center of the detector, in
        pixels, that the algorithm currently expects a peak to have.

        Returns:

            The current maximum distance, in pixels, for a peak from the detector's
            center.
        """
        return self._max_res

    def set_max_res(self, max_res: int) -> None:
        """
        Sets the maximum distance for a peak from the detector's center in pixels.

        This function sets the maximum distance from the center of the detector, in
        pixels, that the algorithm expects a peak to have. Any future call to the
        [`find_peaks`][om.algorithms.crystallography.Peakfinder8PeakDetection.find_peaks]
        method will use, for the `min_res` parameter, the value provided here.

        Arguments:

            max_res: The new maximum distance, in pixels, from the detector's center
                for a peak.
        """
        self._max_res = max_res
        self._mask = None

    def find_peaks(
        self, *, data: Union[NDArray[numpy.int_], NDArray[numpy.float_]]
    ) -> PeakList:
        """
        Finds peaks in a detector data frame.

        This function detects peaks in a provided detector data frame, and returns
        information about their location, size and intensity.

        Arguments:

            data: The detector data frame on which the peak-finding operation must be
                performed.

        Returns:

            A [`TypePeakList`][om.algorithms.crystallography.TypePeakList] dictionary
                with information about the detected peaks.
        """
        if self._mask is None:
            if self._bad_pixel_map is None:
                self._mask = numpy.ones_like(data, dtype=numpy.int8)
            else:
                self._mask = self._bad_pixel_map.astype(numpy.int8)

            self._mask[numpy.where(self._radius_pixel_map < self._min_res)] = 0
            self._mask[numpy.where(self._radius_pixel_map > self._max_res)] = 0

        peak_list: Tuple[List[float], ...] = peakfinder_8(
            self._max_num_peaks,
            data.astype(numpy.float32),
            self._mask,
            self._radius_pixel_map,
            self._radial_stats_num_pixels,
            self._radial_stats_pixel_index,
            self._radial_stats_radius,
            int(self._parameters.fast_mode),
            self._asic_nx,
            self._asic_ny,
            self._nasics_x,
            self._nasics_y,
            self._adc_thresh,
            self._minimum_snr,
            self._min_pixel_count,
            self._max_pixel_count,
            self._local_bg_radius,
        )

        return PeakList(
            num_peaks=len(peak_list[0]),
            fs=peak_list[0],
            ss=peak_list[1],
            intensity=peak_list[2],
            num_pixels=peak_list[4],
            max_pixel_intensity=peak_list[5],
            snr=peak_list[6],
        )
