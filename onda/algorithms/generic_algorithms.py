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
Generic algorithms to be used across different types of experiment.
'''

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import h5py
import numpy
from future.utils import raise_from
from scipy.ndimage import median_filter


######################
# DARKCAL CORRECTION #
######################

class DarkCalCorrection(object):
    '''
    Apply dark calibration correction.

    Subtract the dark calibration correction from the data. Optionally, apply
    a mask and a gain map.
    '''

    def __init__(self, darkcal_filename, darkcal_hdf5_path, mask_filename=None,
                 mask_hdf5_path=False, gain_map_filename=None,
                 gain_map_hdf5_path=None):
        '''
        Initialize the DarkCalCorrection class.

        Args:

            darkcal_filename (str): name of the file containing the dark
                calibration data.

            darkcal_hdf5_path (str): internal HDF5 path of the data
                block where the dark calibration information (in 'slab'
                format) is stored.

            mask_filename (Optional[str]): if the argument is the name of a
                file containing a binary mask, the mask will be loaded and
                applied. If the argument is None, no mask will be applied.
                Defaults to None.

            mask_hdf5_path (Optional[str]): if the mask_filename argument is
                provided, and a mask is applied, this argument is the internal
                HDF5 path where the mask (in 'slab' format) is stored. The
                argument is otherwise ignored. Defaults to None.

            gain_map_filename (Optional[str]): if the argument is the name of a
                file containing a gain map, the map will be loaded and
                applied. If the argument is None, no map will be applied.
                Defaults to None.

            mask_hdf5_path (Optional[str]): if the gain_map_filename argument
                is provided, and a gain map is applied, this argument is the
                internal HDF5 path of the data block where the gain map (in
                'slab' format) is stored. The argument is otherwise ignored.
                Defaults to None.
        '''

        # Load the dark calibration data from the file and store it in
        # an attribute.
        try:
            with h5py.File(name=darkcal_filename, mode='r') as fhandle:
                self._darkcal = fhandle[darkcal_hdf5_path]
        except OSError:
            raise_from(
                exc=RuntimeError(
                    'Error reading the {} HDF5 file.'.format(
                        darkcal_filename
                    )
                ),
                source=None
            )

        # If the mask_filename argument is not None, load the mask data from
        # the file and store it in an attribute. Otherwise, set the attribute
        # to True (equivalent to an all-ones mask).
        if mask_filename:
            try:
                with h5py.File(name=mask_filename, mode='r') as fhandle:
                    self._darkcal = fhandle[mask_hdf5_path]
            except OSError:
                raise_from(
                    exc=RuntimeError(
                        'Error reading the {} HDF5 file.'.format(
                            mask_filename
                        )
                    ),
                    source=None
                )
        else:
            self._mask = True

        # If the gain_map_filename argument is not None, load the gain map data
        # from the file and store it in an attribute. Otherwise, set the
        # attribute to True (equivalent to an all-ones map).
        if gain_map_filename:
            try:
                with h5py.File(name=gain_map_filename, mode='r') as fhandle:
                    self._gain_map = fhandle[gain_map_hdf5_path]
            except OSError:
                raise_from(
                    exc=RuntimeError(
                        'Error reading the {} HDF5 file.'.format(
                            mask_filename
                        )
                    ),
                    source=None
                )
        else:
            self._gain_map = True

    def apply_darkcal_correction(self, data):
        """Apply the correction.

        Optionally apply the user-provided mask and gain map. Multiply the data
        with the mask first, then subtract the darkcal and finally multiply
        the result with the gain map.

        Args:

            data (ndarray): the data (in 'slab' format) on which the
                corrections should be applied.
        """

        # Apply the corrections and return the corrected data.
        return (data * self._mask - self._darkcal) * self._gain_map


######################
# RAW DATA AVERAGING #
######################

class RawDataAveraging(object):
    '''
    Accumulate and average raw detector data.

    Accumulate raw detector data (in 'slab' format) until a predefined number
    of data entries has been added to the accumulator, then return the average
    of the accumulated data and empty the accumulator.
    '''

    def __init__(self, num_events_to_accumulate, slab_shape):
        '''
        Initialize the RawDataAveraging class.

        Args:

            num_events_to_accumulate (int): the number raw detector data items
                to accumulate before returning the average data.

            slab_shape (tuple): numpy shape-like tuple describing the size of
                the data that will accumulated.
        '''

        # Store some arguments as attributes
        self._n_events_to_accumulate = num_events_to_accumulate
        self._slab_shape = slab_shape

        # Initialize the counter for the accumulated entries.
        self._num_raw_data = 0

        # Initialize the empty array that will store the accumulated data.
        self._avg_raw_data = numpy.zeros(slab_shape)

    def add_data(self, data):
        '''
        Add raw detector_data .

        Add the provided raw detector data to the accumulator. If the the
        predefined number of entries has been added to the accumulator, return
        the average of the accumulated data.

        Args:

            data (ndarray): raw detector data (in 'slab' format) to be added
                to the accumulator.

        Returns:

            Union[ndarray, None]: the average of the accumulated data
            if the predefined number of data entries has been reached, None
            otherwise.
        '''

        # Add the data provided by the user to the interal array, already
        # normalizing it in the process.
        self._avg_raw_data += (data / self._n_events_to_accumulate)

        # Update the internal counter.
        self._num_raw_data += 1

        # Check if the internal counter reached the number of additions
        # specified by the user. If it did, copy the averaged data to a
        # new array to return them, and reset the internal array.
        if self._num_raw_data == self._n_events_to_accumulate:
            data_to_be_returned = self._avg_raw_data.copy()
            self._num_raw_data = 0
            self._avg_raw_data.fill(0)
            return data_to_be_returned

        # If the internal counter did not reach the number of additions
        # specified by the user, just return None.
        return None


#######################
# MINIMA IN WAVEFORMS #
#######################

class FindMinimaInWaveforms(object):
    '''
    Find minima in waveforms.

    Perform peak finding on 1d waveform data where the signal has a negative
    sign. Peaks are defined as local minima of the waveform. A moving-window
    smoothing function is applied to the data before the peak finding.
    '''

    def __init__(self, threshold, estimated_noise_width, minimum_peak_width,
                 background_subtraction=False):
        '''
        Initialize the FindMinimaInWaveform class.

        Args:

            threshold (float): a negative number. The minimum negative signal
                strength (over the signal baseline) for a detected minimum
                to be considered a peak.

            estimated_noise_width (int): the width (in pixel) of the
                moving-window smoothing function that will be applied to the
                data before the peak detection.

            minimum_peak_width (int): minimum width of a peak (in number of
                data points). All minima found within the range (in data
                points) specified by this parameter will be considered as
                belonging to the same peak. The position of the minimum with
                the highest negative strength will be reported as the position
                of the detected peak.

            background_subtraction (bool): If true, a low-pass filtered version
                of the data will be subtracted from the original data before
                the smoothing function is applied. The low pass filtered
                version of the data will be generated by filtering the original
                data with a running median filter.
        '''

        # Read some arguments and store them in attributes.
        self._threshold = threshold
        self._minimum_peak_width = minimum_peak_width
        self._background_subtraction = background_subtraction

        # Set some hardcoded values used for the median filter that is
        # optionally applied to the data.
        self._backgr_filter_win_size = 200
        self._backgr_filter_step = 20

        # Createan array that will be used to smooth out the data.
        self._smoothing_array = numpy.ones(
            shape=estimated_noise_width,
            dtype=numpy.float
        ) / float(estimated_noise_width)

    def find_minima(self, data):
        '''
        Finds minima in the waveform.

        Args:

            waveform  (ndarray): 1d array containing the waveform data.

        Returns:

            list: list of int numbers. Each field in the list is the
            position (the index along the axis of the data array) of a
            detected peak.
        '''

        # If the background subtraction was requested, apply it to the data,
        if self._background_subtraction is True:

            # Create an index for the data.
            index = numpy.arange(data.shape[0])

            # Slice the data and the index according to the step size.
            sliced_data = data[::self._backgr_filter_step]
            sliced_index = index[::self._backgr_filter_step]

            # Call the median filter function.
            sliced_data = median_filter(
                input=sliced_data,
                size=self._backgr_filter_win_size
            )

            # Interpolate the filtered data.
            interpolated_data = numpy.interp(
                x=index,
                xp=sliced_index,
                fp=sliced_data
            )

            # Subtract the filtered data from the data.
            bck_subtr_data = data - interpolated_data
        else:

            # If the background subtraction was not requested, just make
            # a copy of the data.
            bck_subtr_data = data.copy()

        # Convolve data with the smoothing array.
        smooth_data = numpy.convolve(
            a=bck_subtr_data.astype(numpy.float32),
            v=self._smoothing_array,
            mode='same'
        )

        # Compute first and second derivative of the smoothed data.
        d_smooth_data = numpy.gradient(smooth_data)
        dd_smooth_data = numpy.gradient(d_smooth_data)

        # Find peaks by analyzing the first and second derivatives.
        peak_locations = numpy.where(
            (
                numpy.diff(numpy.sign(d_smooth_data)) > 0
            ) * (
                dd_smooth_data[:-1] > 0
            )
        )[0]

        # Filter peaks according to the negative threshold provided by the
        # user.
        offset = numpy.mean(smooth_data)
        filtered_peaks = numpy.where(
            smooth_data[peak_locations] - offset < -abs(self._threshold)
        )
        peak_locations = peak_locations[filtered_peaks]

        # Remove peaks that are too close. For each group of peaks that
        # lie too close to each other, take the peak with the strongest
        # negative strength.

        # Convert ndarray containing the peak locations to a list.
        peak_list = list(peak_locations)

        # Create a flag that records if any peak that lies to close to
        # another one has been found. True until proven false.
        any_too_close = True

        while any_too_close is True:

            # Create a list to store the new list of peaks that will
            # be generated by the code in this loop.
            temp_peak_list = []

            # Set the any_too_close flag to False.
            any_too_close = False

            # Create a list of peaks that are too close.

            # Iterate over the peak list.
            for p_index, p_position in enumerate(peak_list):

                # Create an internal list of peak values.
                internal_pl = []

                if p_index > 0:

                    # If the current peak is not the first one, compute
                    # the distance between the current peak and the
                    # previous one.
                    p_dist_prev = p_position - peak_list[p_index - 1]

                    # If the peaks are too close, append to the internal
                    # list the value of the previous peak.
                    if p_dist_prev < self._minimum_peak_width:
                        internal_pl.append(
                            smooth_data[peak_list[p_index - 1]]
                        )

                if p_index < len(peak_list) - 1:

                    # If the current peak is not the last one, compute
                    # the distance between the current peak and the next
                    # one.
                    p_dist_next = peak_list[p_index + 1] - p_position

                    # If the peaks are too close, append to the internal
                    # list the value of the next peak.
                    if p_dist_next < self._minimum_peak_width:
                        internal_pl.append(
                            smooth_data[peak_list[p_index + 1]]
                        )

                # If the value of the current peak is lower than all the values
                # of the peaks that surround it,add the peak to the new
                # peak list.
                if numpy.all(
                        [smooth_data[p_position] < v for v in internal_pl]
                ):
                    temp_peak_list.append(p_position)
                else:
                    # If not, another passage of the while loop is required
                    any_too_close = True

            # Set the new peak list as the peak list to be used in the next
            # iteration of the 'while' loop.
            peak_list = list(temp_peak_list)

        # If no peaks that lie to close to each other rare left in the peak
        # list, return the list.
        return peak_list
