#    This file is part of OnDA.
#
#    OnDA is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    OnDA is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with OnDA.  If not, see <http://www.gnu.org/licenses/>.
#
#    Copyright 2014-2018 Deutsches Elektronen-Synchrotron DESY,
#    a research centre of the Helmholtz Association.
"""
Algorithms for the processing of crystallography data.

Specific crystallography arguments: peak finders, data accumulators,
etc.
"""
from __future__ import absolute_import, division, print_function

import h5py
import numpy
from future.utils import raise_from

from onda.algorithms.peakfinder8_extension import peakfinder_8
from onda.utils import named_tuples


##############################
# PEAKFINDER8 PEAK DETECTION #
##############################


class Peakfinder8PeakDetection(object):
    """
    Peakfinder8 algorithm for peak detection.

    See this paper for a description of the peakfinder8 algorithm:

    A. Barty, R. A. Kirian, F. R. N. C. Maia, M. Hantke, C. H.
    Yoon, T. A. White, and H. N. Chapman, "Cheetah: software for
    high-throughput reduction and analysis of serial femtosecond
    X-ray diffraction data", J Appl Crystallogr, vol. 47,
    pp. 1118-1131 (2014).
    """

    def __init__(
            self,
            max_num_peaks,
            asic_nx,
            asic_ny,
            nasics_x,
            nasics_y,
            adc_threshold,
            minimum_snr,
            min_pixel_count,
            max_pixel_count,
            local_bg_radius,
            min_res,
            max_res,
            bad_pixel_map_filename,
            bad_pixel_map_hdf5_path,
            radius_pixel_map
    ):
        """
        Initializes the Peakfinder8PeakDetection class.

        Args:

            max_num_peaks (int): maximum number of peaks that will be
                returned to the user. Additional peaks are ignored.

            asic_nx (int): fs size of each detector's ASIC.

            asic_ny (int): ss size of each detector's ASIC.

            nasics_x (int): number of ASICs along the fs axis of the
                data array.

            nasics_y (int): number of ASICs along the ss axis of the
                data array.

            adc_threshold (float): minimum adc threshold for peak
                detection.

            minimum_snr (float): minimum signal to noise ratio for peak
                detection.

            min_pixel_count (int): minimum size of the peak in pixels.

            max_pixel_count (int): maximum size of the peak in pixels.

            local_bg_radius (int): radius for the estimation of the
                local background.

            min_res (int): minimum resolution for the peak (in pixels).

            max_res (int): minimum resolution for the peak (in pixels).

            bad_pixel_map_filename (str): name of the file containing
                the bad pixel map. The map must have the same internal
                layout ("shape") as the data on which it is applied.
                The pixels should have a value of 0 or 1, with 0
                meaning that the pixel is bad and 1 meaning that the
                pixel should be processed. The map only excludes some
                regions from the peak finding, the input data is not
                modified in any way.

            bad_pixel_map_hdf5_path (str): internal HDF5 path of the
                data block where the bad pixel map (in "slab" format)
                is stored.

            radius_pixel_map (ndarray): a pixel map that, for each
                pixel in the data array, stores its distance (in
                pixels) from the center of the detector.
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

        try:
            with h5py.File(name=bad_pixel_map_filename, mode="r") as fhandle:
                loaded_mask = fhandle[bad_pixel_map_hdf5_path][:]
        except OSError:
            raise_from(
                RuntimeError(
                    "Error reading the {} HDF5 file.".
                    format(bad_pixel_map_filename)
                ),
                None
            )

        res_mask = numpy.ones(shape=loaded_mask.shape, dtype=numpy.int8)
        res_mask[numpy.where(self._radius_pixel_map < min_res)] = 0
        res_mask[numpy.where(self._radius_pixel_map > max_res)] = 0
        self._mask = loaded_mask * res_mask

    def find_peaks(
            self,
            data
    ):
        """
        Detects peaks in the data.

        The data provided by the user must be in "slab" format.

        Args:

            data (ndarray): the data (in "slab" format) on which
                the peak finding should be performed.

        Returns:

            PeakList: a named tuple with the detected peaks. The three
            fields, "ss", "fs" and "intensity", store the ss and fs
            coordinate of each peak in the data array, and its
            intensity.
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
            self._local_bg_radius
        )
        return named_tuples.PeakList(*peak_list[0:3])


####################
# DATA ACCUMULATOR #
####################


class DataAccumulator(object):
    """
    Algorithm to accumulate data for susequent bulk retrieval.

    Accumulates data until data has been added to the accumulator
    for a predefined numberof times (The accumulator is "full"), then
    returns all the accumulated data and empties the accumulator.
    """

    def __init__(
            self,
            num_events_to_accumulate
    ):
        """
        Initializes the DataAccumulator class.

        Args:

            num_events_to_accumulate (int): the number of times that
                data can be added to the accumulator before the
                accumulator is full.
        """
        self._n_events_to_accumulate = num_events_to_accumulate
        self._accumulator = []
        self._events_in_accumulator = 0


    def add_data(
            self,
            data
    ):
        """
        Adds data to the accumulator.

        When the accumulator is full, returns the accumulated data
        and empties the accumulator.

        Args:

            data: (Dict): a dictionary containing the data to be
                added to the accumulator.

        Returns:

            Union[List[Dict], None]: either a list containing the
            accumulated data (if the accumulator is full), otherwise
            None.
        """
        self._accumulator.append(data)
        self._events_in_accumulator += 1

        if self._events_in_accumulator == self._n_events_to_accumulate:
            data_to_return = self._accumulator
            self._accumulator = []
            self._events_in_accumulator = 0
            return data_to_return

        return None
