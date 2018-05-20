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
"""
Algorithms for the processing of crystallography data.

Exports:

    Namedtuples:

        PeakList: list of detected peaks.

    Classes:

        Peakfinder8PeakDetection: peak detection using the peakfinder8
            algorithm from the Cheetah software package.

        PeakAccumulator: Accumulation of peak information for
            subsequent bulk retrieval
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from collections import namedtuple

import h5py
import numpy
from future.utils import raise_from

from ondacython.lib.peakfinder8_extension import (  # pylint: disable=E0611
    peakfinder_8
)


PeakList = namedtuple(  # pylint: disable=C0103
    typename='PeakList',
    field_names=['fs', 'ss', 'intensity']
)
"""
List of peaks detected in the data.

A namedtuple that stores the a list of peaks detected in the detector
data. The first two fields, named 'fs' and 'ss' respectively, are lists
storing the the fs and ss and ss coordinates of all peaks. The third
field, named 'intensity', stores the integrated intensity of the peaks.
"""


##############################
# PEAKFINDER8 PEAK DETECTION #
##############################

class Peakfinder8PeakDetection(object):
    """
    Detect peaks.

    Use Cheetah's peakfinder8 to detect peaks in the data provided by
    the user (which must be in 'slab' format). See this paper for a
    descrition of the peakfinder8 algorithm:

    A. Barty, R. A. Kirian, F. R. N. C. Maia, M. Hantke, C. H. Yoon,
    T. A. White, and H. N. Chapman, 'Cheetah: software for
    high-throughput reduction and analysis of serial femtosecond X-ray
    diffraction data', J Appl Crystallogr, vol. 47, pp. 1118-1131
    (2014).
    """
    def __init__(self,
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
                 radius_pixel_map):
        """
        Initialize the Peakfinder8PeakDetection class.

        Args:

            max_num_peaks (int): maximum number of peaks that will be
                returned to the user. Additional peaks are ignored.

            asic_nx (int): fs size of a detector's ASIC.

            asic_ny (int): ss size of a detector's ASIC.

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
                layout ('shape') as the data on which it is applied.
                The pixels should have a value of 0 or 1, with 0
                meaning that the pixel is bad and 1 meaning that the
                pixel should be processed. The map only excludes some
                regions from the peak finding, the input data is not
                modified in any way.

            bad_pixel_map_hdf5_path (str): internal HDF5 path of the
                data block where the bad pixel map (in 'slab' format)
                is stored.

           radius_pixel_map (ndarray): a pixel map that, for each pixel
                in the data array, stores its distance (in pixels) from
                the center of the detector.
        """
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

        # Load the bad pixel map from file (raise an exception in case
        # of failure), then create the internal mask that will be used
        # to exclude regions of the detector from the peak finding. The
        # internal map includes the bad pixel map, but also excludes
        # from the peak finding additional areas according to the
        # resolution limits specified by the input parameters.
        try:
            with h5py.File(name=bad_pixel_map_filename, mode='r') as fhandle:
                loaded_mask = fhandle[bad_pixel_map_hdf5_path][:]
        except OSError:
            raise_from(
                exc=RuntimeError(
                    "Error reading the {} HDF5 file.".format(
                        bad_pixel_map_filename
                    )
                ),
                source=None
            )

        res_mask = numpy.ones(shape=loaded_mask.shape, dtype=numpy.int8)
        res_mask[numpy.where(self._radius_pixel_map < min_res)] = 0
        res_mask[numpy.where(self._radius_pixel_map > max_res)] = 0
        self._mask = loaded_mask * res_mask

    def find_peaks(self,
                   data):
        """
        Detect peaks.

        Perform the peak finding on the data provided by the user.

        Args:

            data (ndarray): the data (in 'slab' format) on which the
                peak finding should be performed.

        Returns:

            PeakList: a PeakList tuple with the detected peaks.
        """
        # Call the cython-wrapped peakfinder8 function, then wrap the
        # returned peaks into a tuple and return it.
        peak_list = peakfinder_8(
            self._max_num_peaks,
            data.astype(numpy.float32),  # pylint: disable=E1101
            self._mask.astype(numpy.int8),
            self._radius_pixel_map,
            self._asic_nx, self._asic_ny,
            self._nasics_x, self._nasics_y,
            self._adc_thresh, self._minimum_snr,
            self._min_pixel_count, self._max_pixel_count,
            self._local_bg_radius
        )

        return PeakList(*peak_list[0:3])


####################
# PEAK ACCUMULATOR #
####################

class PeakAccumulator:
    """
    Accumulate peak information for susequent bulk retrieval.

    Accumulate peak information until the accumulator is full. Allow
    the user to add peaks to the accumulator for a predefined number of
    times, determined when the algorithm is instantiated. Then return
    the full list of accumulated peaks and empty the accumulator.
    """

    def __init__(self, num_events_to_accumulate):
        """
        Initialize the PeakAccumulator class.

        Args:

            num_events_to_accumulate (int): the number of times that
                peaks can be added to the accumulator before the full
                list of accumulated peaks is returned.
        """
        # Store the input argument as an attribute.
        self._n_events_to_accumulate = num_events_to_accumulate

        # Initialize the tuple that will store the accumulated peaks,
        # and the counter of accumulated events.
        self._accumulator = PeakList([], [], [])
        self._events_in_accumulator = 0

    def accumulate_peaks(self, peak_list):
        """
        Accumulate peaks.

        Add the peaks to the internal list of peaks. If peaks have been
        added to the accumulator for the specified number of times,
        return the accumulated peak list and empty the accumulator.

        Args:

            peak_list (PeakList): PeakList tuple with the list of peaks
                to be added to the accumulator.

        Returns:

            Union[PeakList, None]: a PeakList tuple with the
            accumulated peaks if peaks have been added to the
            accumulator for the predefined number of times, otherwise
            None.
        """
        # Add the peak data to the interal lists and update the
        # internal counter.
        self._accumulator.fs.extend(peak_list.fs)
        self._accumulator.ss.extend(peak_list.ss)
        self._accumulator.intensity.extend(peak_list.intensity)
        self._events_in_accumulator += 1

        # Check if the internal counter reached the number of additions
        # specified by the user. If it did, return the peak list, and
        # reset the accumulator. Otherwise just return None.
        if self._events_in_accumulator == self._n_events_to_accumulate:
            peak_list_to_return = self._accumulator
            self._accumulator = PeakList([], [], [])
            self._events_in_accumulator = 0
            return peak_list_to_return

        return None
