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
Algorithms for the processing of crystallography data.

This module contains algorithms that perform crystallography-related data processing
(peak finding, etc.). In addition, it also contains several typed dictionaries that
store data needed or produced by these algorithms.
"""
from typing import List, Tuple, Union

import numpy  # type: ignore
from mypy_extensions import TypedDict

from om.lib.peakfinder8_extension import peakfinder_8  # type: ignore


class TypePeakfinder8Info(TypedDict, total=True):
    """
    Detector layout information for the peakfinder8 algorithm.

    Base class: `TypedDict`

    This typed dictionary is used to store information about the data layout in a
    detector data frame, in the format needed by the [Peakfinder8PeakDetection]
    [om.algorithms.crystallography.Peakfinder8PeakDetection] algorithm. This
    information is usually retrieved via the [get_peakfinder8_info]
    [om.algorithms.crystallography.get_peakfinder8_info] function.

    Attributes:

        asic_nx: The fs size in pixels of each detector panel in the data frame.

        asic_ny: The ss size in pixels of each detector panel in the data frame.

        nasics_x: The number of detector panels along the fs axis of the data frame.

        nasics_y: The number of detector panels along the ss axis of the data frame.
    """

    asic_nx: int
    asic_ny: int
    nasics_x: int
    nasics_y: int


class TypePeakList(TypedDict, total=True):
    """
    Detected peaks information.

    This typed dictionary is used to store information about a set of peaks that
    were detected in a data frame.

    Attributes:

        num_peaks: The number of peaks that were detected in the data frame.

        fs: A list of fractional fs indexes that locate the detected peaks in the data
            frame.

        ss: A list of fractional ss indexes that locate the detected peaks in the data
            frame.

        intensity: A list of integrated intensities for the detected peaks.

        num_pixels: A list storing the number of pixels that make up each detected
            peak.

        max_pixel_intensity: A list storing, for each peak, the value of the pixel with
            the maximum intensity.

        snr: A list storing  the signal-to-noise ratio of each detected peak.
    """

    num_peaks: int
    fs: List[float]
    ss: List[float]
    intensity: List[float]
    num_pixels: List[float]
    max_pixel_intensity: List[float]
    snr: List[float]


def get_peakfinder8_info(detector_type: str) -> TypePeakfinder8Info:
    """
    Gets the peakfinder8 information for a detector.

    This function retrieves, for a supported detector type, the data layout information
    required by the [Peakfinder8PeakDetection]
    [om.algorithms.crystallography.Peakfinder8PeakDetection] algorithm.

    Arguments:

        detector_type: The type of detector for which the information needs to be
            retrieved. The following detector types are currently supported:

            * 'cspad': The CSPAD detector used at the CXI beamline of the LCLS facility
              before 2020.

            * 'pilatus': The Pilatus detector used at the P11 beamline of the PETRA III
              facility.

            * 'jungfrau1M': The 1M version of the Jungfrau detector used at the PETRA
              III facility.

            * 'jungfrau4M': The 4M version of the Jungfrau detector used at the CXI
              beamline of the LCLS facility.

            * 'epix10k2M': The 2M version of the Epix10KA detector used at the MFX
              beamline of the LCLS facility.

            * 'rayonix': The Rayonix detector used at the MFX beamline of the LCLS
              facility.

    Returns:

        A [TypePeakfinder8Info][om.algorithms.crystallography.TypePeakfinder8Info]
        dictionary storing the data layout information.
    """
    if detector_type == "cspad":
        peakfinder8_info: TypePeakfinder8Info = {
            "asic_nx": 194,
            "asic_ny": 185,
            "nasics_x": 8,
            "nasics_y": 8,
        }
    elif detector_type == "pilatus":
        peakfinder8_info = {
            "asic_nx": 2463,
            "asic_ny": 2527,
            "nasics_x": 1,
            "nasics_y": 1,
        }
    elif detector_type == "jungfrau1M":
        peakfinder8_info = {
            "asic_nx": 1024,
            "asic_ny": 512,
            "nasics_x": 1,
            "nasics_y": 2,
        }
    elif detector_type == "jungfrau4M":
        peakfinder8_info = {
            "asic_nx": 1024,
            "asic_ny": 512,
            "nasics_x": 1,
            "nasics_y": 8,
        }
    elif detector_type == "epix10k2M":
        peakfinder8_info = {
            "asic_nx": 384,
            "asic_ny": 352,
            "nasics_x": 1,
            "nasics_y": 16,
        }
    elif detector_type == "rayonix":
        peakfinder8_info = {
            "asic_nx": 1920,
            "asic_ny": 1920,
            "nasics_x": 1,
            "nasics_y": 1,
        }
    else:
        raise RuntimeError(
            "The peakfinder8 information for the {0} detector "
            "cannot be retrieved: detector type unknown"
        )

    return peakfinder8_info


class Peakfinder8PeakDetection:
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        max_num_peaks: int,
        asic_nx: int,
        asic_ny: int,
        nasics_x: int,
        nasics_y: int,
        adc_threshold: float,
        minimum_snr: float,
        min_pixel_count: int,
        max_pixel_count: int,
        local_bg_radius: int,
        min_res: int,
        max_res: int,
        bad_pixel_map: Union[numpy.ndarray, None],
        radius_pixel_map: numpy.ndarray,
    ) -> None:
        """
        Peakfinder8 algorithm for peak detection.

        This algorithm stores the parameters required to find peaks in a detector data
        frame using the 'peakfinder8' strategy, and performs peak finding on a data
        frame upon request. The 'peakfinder8' peak detection strategy is described in
        the following publication:

        A. Barty, R. A. Kirian, F. R. N. C. Maia, M. Hantke, C. H. Yoon, T. A. White,
        and H. N. Chapman, "Cheetah: software for high-throughput reduction and
        analysis of serial femtosecond x-ray diffraction data", J Appl  Crystallogr,
        vol. 47, pp. 1118-1131 (2014).

        Arguments:

            max_num_peaks: The maximum number of peaks that will be retrieved from each
                data frame. Additional peaks will be ignored.

            asic_nx: The fs size in pixels of each detector panel in the data frame
                (Can be retrieved from a [TypePeakfinder8Info]
                [om.algorithms.crystallography.TypePeakfinder8Info] dictionary).

            asic_ny: The ss size in pixels of each detector panel in the data frame
                (Can be retrieved from a [TypePeakfinder8Info]
                [om.algorithms.crystallography.TypePeakfinder8Info] dictionary).

            nasics_x: The number of panels along the fs axis of the data frame
                (Can be retrieved from a [TypePeakfinder8Info]
                [om.algorithms.crystallography.TypePeakfinder8Info] dictionary).

            nasics_y: The number of panels along the ss axis of the data frame
                (Can be retrieved from a [TypePeakfinder8Info]
                [om.algorithms.crystallography.TypePeakfinder8Info] dictionary).

            adc_threshold: The minimum ADC threshold for peak detection.

            minimum_snr: The minimum signal-to-noise ratio for peak detection.

            min_pixel_count: The minimum size of a peak in pixels.

            max_pixel_count: The maximum size of a peak in pixels.

            local_bg_radius: The radius for the estimation of the local background in
                pixels.

            min_res: The minimum resolution for a peak in pixels.

            max_res: The maximum resolution for a peak in pixels.

            bad_pixel_map: An array storing a bad pixel map. The map can be used to
                mark areas of the data frame that must be excluded from the peak
                search. If the value of this argument is None, no area will be excluded
                from the search. Defaults to None.

                * The map must be a numpy array of the same shape as the data frame on
                  which the algorithm will be applied.

                * Each pixel in the map must have a value of either 0, meaning that
                  the corresponding pixel in the data frame should be ignored, or 1,
                  meaning that the corresponding pixel should be included in the
                  search.

                * The map is only used to exclude areas from the peak search: the data
                  is not modified in any way.

            radius_pixel_map: A numpy array with radius information.

                * The array must have the same shape as the data frame on which the
                  algorithm will be applied.

                * Each element of the array must store, for the corresponding pixel in
                  the data frame, the distance in pixels from the origin
                  of the detector reference system (usually the center of the
                  detector).
        """
        self._max_num_peaks: int = max_num_peaks
        self._asic_nx: int = asic_nx
        self._asic_ny: int = asic_ny
        self._nasics_x: int = nasics_x
        self._nasics_y: int = nasics_y
        self._adc_thresh: float = adc_threshold
        self._minimum_snr: float = minimum_snr
        self._min_pixel_count: int = min_pixel_count
        self._max_pixel_count: int = max_pixel_count
        self._local_bg_radius: int = local_bg_radius
        self._radius_pixel_map: numpy.ndarray = radius_pixel_map
        self._min_res: int = min_res
        self._max_res: int = max_res
        self._mask: numpy.ndarray = bad_pixel_map
        self._mask_initialized: bool = False

    def find_peaks(self, data: numpy.ndarray) -> TypePeakList:
        """
        Finds peaks in a detector data frame.

        This function detects peaks in a data frame, and returns information about
        their location, size and intensity.

        Arguments:

            data: The detector data frame on which the peak finding must be performed.

        Returns:

            A [TypePeakList][om.algorithms.crystallography.TypePeakList] dictionary
            with information about the detected peaks.
        """
        if not self._mask_initialized:
            if self._mask is None:
                self._mask = numpy.ones_like(data, dtype=numpy.int8)
            else:
                self._mask = self._mask.astype(numpy.int8)

            res_mask: numpy.ndarray = numpy.ones(
                shape=self._mask.shape, dtype=numpy.int8
            )
            res_mask[numpy.where(self._radius_pixel_map < self._min_res)] = 0
            res_mask[numpy.where(self._radius_pixel_map > self._max_res)] = 0
            self._mask *= res_mask

        peak_list: Tuple[List[float], ...] = peakfinder_8(
            self._max_num_peaks,
            data.astype(numpy.float32),
            self._mask,
            self._radius_pixel_map,
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

        return {
            "num_peaks": len(peak_list[0]),
            "fs": peak_list[0],
            "ss": peak_list[1],
            "intensity": peak_list[2],
            "num_pixels": peak_list[4],
            "max_pixel_intensity": peak_list[5],
            "snr": peak_list[6],
        }
