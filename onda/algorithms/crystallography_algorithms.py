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

'''
Algorithms for the processing of crystallography data.
'''

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from collections import namedtuple

import h5py
import numpy
from future.utils import raise_from

from ondacython.lib.peakfinder8_extension import peakfinder_8

PeakList = namedtuple('PeakList', ['fs', 'ss', 'intensity'])
'''
A namedtuple used for peak lists.

All fields in the tuple are lists. The first two fields store the
fs and ss coordinates of the detected peaks (in the 'slab' format data array).
The third field stores the intensities of the the peaks.
'''

# Namedtuple used internally to store peak coordinates in the data.
# array.
_InternalListOfPeaks = namedtuple('_InternalListOfPeaks', ['ss', 'fs'])

# Namedtuple used internally to store an offset in the data array.
_Offset = namedtuple('_Offset', ['ss', 'fs'])


##############################
# PEAKFINDER8 PEAK DETECTION #
##############################

class Peakfinder8PeakDetection(object):
    '''
    Detect peaks.

    Use Cheetah's peakfinder8 to detect peaks in the data provided by
    the user (which must be in 'slab' format). See this paper for a descrition
    of the peakfinder8 algorithm:

    A. Barty, R. A. Kirian, F. R. N. C. Maia, M. Hantke, C. H. Yoon,
    T. A. White, and H. N. Chapman, “Cheetah: software for high-throughput
    reduction and analysis of serial femtosecond X-ray diffraction data”,
    J Appl Crystallogr, vol. 47, pp. 1118–1131 (2014).
    '''

    def __init__(self, max_num_peaks, asic_nx, asic_ny, nasics_x,
                 nasics_y, adc_threshold, minimum_snr, min_pixel_count,
                 max_pixel_count, local_bg_radius, min_res,
                 max_res, bad_pixel_map_filename, bad_pixel_map_hdf5_group,
                 radius_pixel_map):
        '''
        Initialize the Peakfinder8PeakDetection class.

        Args:

            max_num_peaks (int): maximum number of peaks that will be returned
                to the user. Additional peaks are ignored.

            asic_nx (int): fs size of a detector's ASIC.

            asic_ny (int): ss size of a detector's ASIC.

            nasics_x (int): number of ASICs along the fs axis of the
                data array.

            nasics_y (int): number of ASICs along the ss axis of the
                data array.

            adc_threshold (float): minimum adc threshold for peak detection.

            minimum_snr (float): minimum signal to noise ratio for peak
                detection.

            min_pixel_count (int): minimum size of the peak in pixels.

            max_pixel_count (int): maximum size of the peak in pixels.

            local_bg_radius (int): radius for the estimation of the local
                background.

            min_res (int): minimum resolution for the peak (in pixels).

            max_res (int): minimum resolution for the peak (in pixels).

            bad_pixel_map_filename (str): name of the file containing the
                bad pixel map.

            bad_pixel_map_hdf5_path (str): internal HDF5 path of the data
                block where the bad pixel map (in 'slab' format) is stored.

           radius_pixel_map (ndarray): a pixel map that, for each pixel in
                the data array, stores its distance (in pixels) from the
                center of the detector.
        '''

        # Read arguments and store them in attributes.
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

        # Load the bad pixel map.
        try:
            with h5py.File(name=bad_pixel_map_filename, mode='r') as fhandle:
                self._mask = fhandle[bad_pixel_map_hdf5_group]
        except OSError:
            raise_from(
                exc=RuntimeError(
                    'Error reading the {} HDF5 file.'.format(
                        bad_pixel_map_filename
                    )
                ),
                source=None
            )

        # Create the internal mask used to filter peaks according to
        # resolution.
        res_mask = numpy.ones(self._mask.shape, dtype=numpy.int8)
        res_mask[numpy.where(self._radius_pixel_map < min_res)] = 0
        res_mask[numpy.where(self._radius_pixel_map > max_res)] = 0

        # Combine the internal mask with the loaded bad pixel map.
        self._mask *= res_mask

    def find_peaks(self, data):
        '''
        Detect peaks.

        Perform the peak finding on the data provided by the user.

        Args:

            data (ndarray): the data (in 'slab' format) on which the peak
                finding should be performed.

        Returns:

            PeakList: a :onj:`PeakList` tuple with the detected peaks.
        '''

        # Call the cython-wrapped peakfinder8 function.
        peak_list = peakfinder_8(self._max_num_peaks,
                                 data.astype(numpy.float32),
                                 self._mask.astype(numpy.int8),
                                 self._radius_pixel_map,
                                 self._asic_nx, self._asic_ny,
                                 self._nasics_x, self._nasics_y,
                                 self._adc_thresh, self._minimum_snr,
                                 self._min_pixel_count, self._max_pixel_count,
                                 self._local_bg_radius)

        # Wrap the returned peaks into a PeakList tuple and return it.
        return PeakList(*peak_list[0:3])


####################
# PEAK ACCUMULATOR #
####################

class PeakAccumulator:
    '''
    Accumulate peaks, then return them.

    Allow the user to add peaks to the accumulator for a predefined number of
    times, then return the full list of accumulated peaks and empty the
    accumulator.
    '''

    def __init__(self, num_events_to_accumulate):
        '''
        Initialize the PeakAccumulator class.

        Args:

            num_events_to_accumulate (int): the number of times that
                peaks can be added to the accumulator before the full
                list of accumulated peaks is returned.
        '''

        # Store the input argument as an attribute.
        self._n_events_to_accumulate = num_events_to_accumulate

        # Initialize the tuple that will store the accumulated peaks.
        self._accumulator = PeakList([], [], [])

        # Initialize the counter for the accumulated events.
        self._events_in_accumulator = 0

    def accumulate_peaks(self, peak_list):
        '''
        Accumulate peaks.

        Add the peaks to the internal list of peaks. If peaks have been added
        to the accumulator for the specified number of times, return the
        accumulated peak list and empty the accumulator.

        Args:

            peak_list (PeakList): list of peaks to be added to the accumulator.

        Returns:

            Union[PeakList, None]: the accumulated peak list, if peaks have
            been added to the accumulator for the predefined number of times,
            otherwise None.
        '''

        # Add the peak data to the interal lists.
        self._accumulator.fs.extend(peak_list.fs)
        self._accumulator.ss.extend(peak_list.ss)
        self._accumulator.intensity.extend(peak_list.intensity)

        # Update the internal counter.
        self._events_in_accumulator += 1

        # Check if the internal counter reached the number of additions
        # specified by the user. If it did, return the peak list, and
        # reset the accumulator.
        if self._events_in_accumulator == self._n_events_to_accumulate:
            peak_list_to_return = self._accumulator
            self._accumulator = PeakList([], [], [])
            self._events_in_accumulator = 0
            return peak_list_to_return

        # If the internal counter did not reach the number of additions
        # specified by the user, just return None.
        return None
