# This file is part of OnDA.
#
# OnDA is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# OnDA is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with OnDA.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Algorithms for the processing of crystallography data.

This module contains algorithms that carry out crystallography-related data processing
(peak finding, etc.).
"""
from __future__ import absolute_import, division, print_function

import numpy

from onda.algorithms.peakfinder8_extension import peakfinder_8
from onda.utils import hdf5, named_tuples


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
        bad_pixel_map_filename,  # type: str
        bad_pixel_map_hdf5_path,  # type: str
        radius_pixel_map,  # type: numpy.ndarray
    ):
        # type: (...) -> None
        """
        Peakfinder8 algorithm for peak detection.

        This class stores the parameters needed by the 'peakfinder8' algorithm, and
        performs peak finding on a detector data frame upon request. The 'peakfinder8'
        algorithm is described in the following publication:
        
        A. Barty, R. A. Kirian, F. R. N. C. Maia, M. Hantke, C. H. Yoon, T. A. White,
        and H. N. Chapman, "Cheetah: software for high-throughput reduction and
        analysis of serial femtosecond X-ray diffraction data", J Appl  Crystallogr,
        vol. 47, pp. 1118-1131 (2014).

        Arguments:

            max_num_peaks (int): the maximum number of peaks that will be retrieved
                from each data frame. Additional peaks will be ignored.

            asic_nx (int): the fs size in pixels of each detector's ASIC in the data
                frame.

            asic_ny (int): the ss size in pxiels of each detector's ASIC in the data
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

            bad_pixel_map_filename (str): the absolute or relative path to an HDF5 file
                containing a bad pixel map. The map should mark areas of the data frame
                that must be excluded from the peak search. Specifically:

                * The map must be a numpy array of the same shape as the data frame on
                  which the algorithm will be applied.

                * Each pixel in the map must have a value of either 0, meaning that
                  the corresponding pixel in the data frame must be ignored, or 1,
                  meaning that the corresponding pixel must be included in the search.

                * The map is only used to exclude areas from the peak search: the data
                  is not modified in any way.

            bad_pixel_map_hdf5_path (str): the internal HDF5 path to the data block
                where the bad pixel map is stored.

            radius_pixel_map (numpy.ndarray): a numpy array with radius information.

                * The array must have the same shape as the data frame on which the
                  algorithm will be applied.

                * Each element of the array must store the distance in pixels from
                  the center of the detector of the corresponding pixel in the data
                  frame.
        """
        self._max_num_peaks = max_num_peaks
        self._asic_nx = asic_nx
        self._asic_ny = asic_ny
        self._nasics_x = nasics_x
        self._nasics_y = nasics_y
        self._adc_thresh = adc_threshold
        self._minimum_snr = minimum_snr
        self._min_pixel_count = min_pixel_count
        self._max_pixel_count = max_pixel_count
        self._local_bg_radius = local_bg_radius
        self._radius_pixel_map = radius_pixel_map

        loaded_mask = hdf5.load_hdf5_data(
            hdf5_filename=bad_pixel_map_filename, hdf5_path=bad_pixel_map_hdf5_path
        )
        res_mask = numpy.ones(shape=loaded_mask.shape, dtype=numpy.int8)
        res_mask[numpy.where(self._radius_pixel_map < min_res)] = 0
        res_mask[numpy.where(self._radius_pixel_map > max_res)] = 0
        self._mask = loaded_mask * res_mask

    def find_peaks(self, data):
        # type (numpy.ndarray) -> named_tuples.PeakList
        """
        Finds peaks in a detector data frame.

        This function not only retrieves information about the position of the peaks in
        the data frame but also about their integrated intensity.

        Arguments:

            data (numpy.ndarray): the detector data frame on which the peak finding
                must be performed.

        Returns:

            :class:`~onda.utils.named_tuples.PeakList`: a named tuple with the
            information about the detected peaks.
        """
        peak_list = peakfinder_8(
            self._max_num_peaks,
            data.astype(numpy.float32),
            self._mask.astype(numpy.int8),
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
        return named_tuples.PeakList(*peak_list[0:3])
