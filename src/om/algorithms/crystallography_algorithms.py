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
# Copyright 2020 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Algorithms for the processing of crystallography data.

This module contains algorithms that carry out crystallography-related data processing
(peak finding, etc.).
"""
from __future__ import absolute_import, division, print_function

from typing import Dict, List, Tuple, Union

import numpy  # type: ignore
from mypy_extensions import TypedDict

from om.lib.peakfinder8_extension import peakfinder_8

TypePeakList = TypedDict(
    "TypePeakList",
    {
        "num_peaks": int,
        "fs": List[float],
        "ss": List[float],
        "intensity": List[float],
        "num_pixels": List[float],
        "max_pixel_intensity": List[float],
        "snr": List[float],
    },
    total=True,
)


def get_peakfinder8_info(detector_type):
    # type: (str) -> Dict[str, int]
    """
    Retrieves the peakfinder8 information for a specific detector.

    Arguments:

        detector_type (str): The type of detector for which the information needs to
        be retrieved. The currently supported detectors are:

        * 'cspad': the CSPAD detector used at the CXI beamtime of the LCLS facility
          before 2020.

        * 'pilatus': the Pilatus detector used at the P11 beamtime of the LCLS
          facility.

    Returns:

        Dict[str, int]: a dictionary storing the peakfinder8 information.
    """
    if detector_type == "cspad":
        peakfinder8_info = {
            "asic_nx": 194,
            "asic_ny": 185,
            "nasics_x": 8,
            "nasics_y": 8,
        }  # type: Dict[str, int]
    elif detector_type == "pilatus":
        peakfinder8_info = {
            "asic_nx": 2463,
            "asic_ny": 2527,
            "nasics_x": 1,
            "nasics_y": 1,
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
    else:
        raise RuntimeError(
            "The peakfinder8 information for the {0} detector "
            "cannot be retrieved: detector type unknown"
        )

    return peakfinder8_info


class Peakfinder8PeakDetection(object):
    """
    See documentation of the '__init__' function.
    """

    def __init__(
        self,
        max_num_peaks,  # type: int
        asic_nx,  # type: int
        asic_ny,  # type: int
        nasics_x,  # type: int
        nasics_y,  # type: int
        adc_threshold,  # type: float
        minimum_snr,  # type: float
        min_pixel_count,  # type: int
        max_pixel_count,  # type: int
        local_bg_radius,  # type: int
        min_res,  # type: int
        max_res,  # type: int
        bad_pixel_map,  # type: Union[numpy.ndarray, None]
        radius_pixel_map,  # type: numpy.ndarray
    ):
        # type: (...) -> None
        """
        Peakfinder8 algorithm for peak detection.

        This class stores the parameters needed by the 'peakfinder8' algorithm, and
        detect peaks in a detector data frame upon request. The 'peakfinder8' algorithm
        is described in the following publication:

        A. Barty, R. A. Kirian, F. R. N. C. Maia, M. Hantke, C. H. Yoon, T. A. White,
        and H. N. Chapman, "Cheetah: software for high-throughput reduction and
        analysis of serial femtosecond X-ray diffraction data", J Appl  Crystallogr,
        vol. 47, pp. 1118-1131 (2014).

        Arguments:

            max_num_peaks (int): the maximum number of peaks that will be retrieved
                from each data frame. Additional peaks will be ignored.

            asic_nx (int): the fs size in pixels of each detector's ASIC in the data
                frame.

            asic_ny (int): the ss size in pixels of each detector's ASIC in the data
                frame.

            nasics_x (int): the number of ASICs along the fs axis of the data frame.

            nasics_y (int): the number of ASICs along the ss axis of the data frame.

            adc_threshold (float): the minimum ADC threshold for peak detection.

            minimum_snr (float): the minimum signal-to-noise ratio for peak detection.

            min_pixel_count (int): the minimum size of a peak in pixels.

            max_pixel_count (int): the maximum size of a peak in pixels.

            local_bg_radius (int): the radius for the estimation of the
                local background in pixels.

            min_res (int): the minimum resolution for a peak in pixels.

            max_res (int): the maximum resolution for a peak in pixels.

            bad_pixel_map (Union[numpy.ndarray, None): an array storing the a bad
                pixel map. The map should mark areas of the data frame that must be
                excluded from the peak search. If this argument is None, no area will
                be excluded from the search. Defaults to None.

                * The map must be a numpy array of the same shape as the data frame on
                  which the algorithm will be applied.

                * Each pixel in the map must have a value of either 0, meaning that
                  the corresponding pixel in the data frame must be ignored, or 1,
                  meaning that the corresponding pixel must be included in the search.

                * The map is only used to exclude areas from the peak search: the data
                  is not modified in any way.

            radius_pixel_map (numpy.ndarray): a numpy array with radius information.

                * The array must have the same shape as the data frame on which the
                  algorithm will be applied.

                * Each element of the array must store the distance in pixels from
                  the center of the detector of the corresponding pixel in the data
                  frame.
        """
        self._max_num_peaks = max_num_peaks  # type: int
        self._asic_nx = asic_nx  # type: int
        self._asic_ny = asic_ny  # type: int
        self._nasics_x = nasics_x  # type: int
        self._nasics_y = nasics_y  # type: int
        self._adc_thresh = adc_threshold  # type: float
        self._minimum_snr = minimum_snr  # type: float
        self._min_pixel_count = min_pixel_count  # type: int
        self._max_pixel_count = max_pixel_count  # type: int
        self._local_bg_radius = local_bg_radius  # type: int
        self._radius_pixel_map = radius_pixel_map  # type: numpy.ndarray
        self._min_res = min_res  # type: int
        self._max_res = max_res  # type: int
        self._mask = bad_pixel_map  # type: numpy.ndarray
        self._mask_initialized = False  # type: bool

    def find_peaks(self, data):
        # type: (numpy.ndarray) -> TypePeakList
        """
        Finds peaks in a detector data frame.

        This function not only retrieves information about the position of the peaks in
        the data frame but also about their integrated intensity.

        Arguments:

            data (numpy.ndarray): the detector data frame on which the peak finding
                must be performed.

        Returns:

            Dict: a dictionary with information about the Bragg peaks
            detected in a data frame. The dictionary has the following keys:

            - A key named "num_peaks" whose value is the number of peaks that were
              detected in the data frame.

            - A key named 'fs' whose value is a list of fractional fs indexes locating
              the detected peaks in the data frame.

            - A key named 'ss' whose value is a list of fractional ss indexes locating
              the detected peaks in the data frame.

            - A key named 'intensity' whose value is a list of integrated intensities
              for the detected peaks.

            - A key named 'num_pixels' whose value is is a list storing the number of
              pixels that make up each detected peak.

            - A key named 'max_pixel_intensity' whose value is a list storing, for each
              peak, the value of the pixel with the maximum intensity.

            - A key named 'snr' whose value is a list storing  the signal-to-noise
              ratio of each detected peak.
        """
        if not self._mask_initialized:
            if self._mask is None:
                self._mask = numpy.ones_like(data, dtype=numpy.int8)
            else:
                self._mask = self._mask.astype(numpy.int8)

            res_mask = numpy.ones(
                shape=self._mask.shape, dtype=numpy.int8
            )  # type: numpy.ndarray
            res_mask[numpy.where(self._radius_pixel_map < self._min_res)] = 0
            res_mask[numpy.where(self._radius_pixel_map > self._max_res)] = 0
            self._mask *= res_mask

        peak_list = peakfinder_8(
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
        )  # type: Tuple[List[float], ...]

        return {
            "num_peaks": len(peak_list[0]),
            "fs": peak_list[0],
            "ss": peak_list[1],
            "intensity": peak_list[2],
            "num_pixels": peak_list[3],
            "max_pixel_intensity": peak_list[4],
            "snr": peak_list[5],
        }
