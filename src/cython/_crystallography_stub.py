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
# You should have received a copy of the GNU General Public License along with OnDA.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2020 -2023 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Peakfinder8 extension.

This module contains a peak-finding function based on Cheetah's 'peakfinder8' peak
detection algorithm.
"""
from typing import List, Tuple

import numpy
from numpy.typing import NDArray


def peakfinder_8(
    *,
    max_num_peaks: int,
    data: NDArray[numpy.float_],
    mask: NDArray[numpy.int_],
    pix_r: NDArray[numpy.float_],
    asic_nx: int,
    asic_ny: int,
    nasics_x: int,
    nasics_y: int,
    adc_thresh: float,
    hitfinder_min_snr: float,
    hitfinder_min_pix_count: int,
    hitfinder_max_pix_count: int,
    hitfinder_local_bg_radius: int,
) -> Tuple[
    int,
    List[float],
    List[float],
    List[float],
    List[float],
    List[float],
    List[float],
]:
    """
    Peakfinder8 peak detection.

    This function finds Bragg peaks in a detector data frame using the `peakfinder8`
    algorithm from the Cheetah software package. The `peakfinder8` peak
    detection algorithm is described in the following publication:

    A. Barty, R. A. Kirian, F. R. N. C. Maia, M. Hantke, C. H. Yoon, T. A. White,
    and H. N. Chapman, "Cheetah: software for high-throughput reduction and
    analysis of serial femtosecond x-ray diffraction data", J Appl  Crystallogr,
    vol. 47, pp. 1118-1131 (2014).

    Arguments:

        max_num_peaks: The maximum number of peaks that will be retrieved from each
            data frame. Additional peaks will be ignored.

        data: The detector data frame on which the peak finding will be performed (as
            a float32 numpy array).

        mask: A int8 numpy array storing a pixel map that can be used to exclude
            regions of the data frame from the peak search.

            * The array must have the same shape as the data frame on which the
            algorithm will be applied.

            * Each element in the array must have a value of either 0, meaning that the
            corresponding pixel in the data frame should be ignored, or 1, meaning
            that the corresponding pixel should be included in the peak search.

            * The map is only used to exclude areas from the peak search: the
            data is not modified in any way.

        pix_r: A float32 numpy array with radius information for the detector data
            frame.

            * The array must have the same shape as the data frame on which the
            algorithm will be applied.

            * Each element of the array must store, for the corresponding pixel in
            the data frame, its distance (in pixels) from the origin of the
            detector reference system (usually the center of the detector).

        asic_nx: The fs size, in pixels, of each detector panel in the data frame (Can
            be retrieved from a
            [TypePeakfinder8Info][om.algorithms.crystallography.TypePeakfinder8Info]
            dictionary).

        asic_ny: The ss size, in pixels, of each detector panel in the data frame (Can
            be retrieved from a
            [TypePeakfinder8Info][om.algorithms.crystallography.TypePeakfinder8Info]
            dictionary).

        nasics_x: The number of panels along the fs axis of the data frame (Can be
            retrieved from a
            [TypePeakfinder8Info][om.algorithms.crystallography.TypePeakfinder8Info]
            dictionary).

        nasics_y: The number of panels along the ss axis of the data frame (Can be
            retrieved from a
            [TypePeakfinder8Info][om.algorithms.crystallography.TypePeakfinder8Info]
            dictionary).

        adc_thresh: The minimum ADC threshold for peak detection.

        hitfinder_min_snr: The minimum signal-to-noise ratio for peak detection.

        hitfinder_min_pix_count: The minimum size of a peak (in pixels).

        hitfinder_max_pix_count: The maximum size of a peak (in pixels).

        hitfinder_local_bg_radius: The radius, in pixels, for the estimation of the
            local background.

    Returns:

        A tuple storing information about the detected peaks, with 7 entries.

            * The first entry stores the number of peaks that were detected in the data
            frame.

            * The second entry is a list storing the fractional fs indexes that locate
            the detected peaks in the data frame.

            * The third entry is a list storing the fractional ss indexes that locate
            the detected peaks in the data frame.

            * The fourth entry is a list storing the integrated intensities for the
            detected peaks.

            * The fifth entry is a list storing the number of pixels that make up each
            detected peak.

            * The sixth entry is a list storing, for each peak, the value of the pixel
            with the maximum intensity.

            * The seventh entry is a list storing the signal-to-noise ratio of each
            detected peak.
    """
    ...
