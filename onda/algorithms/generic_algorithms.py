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
Generic algorithms.

This module contains the implementation of several generic algorithms
for the processing of detector data (dark calibration correction,
data averaging, etc.).
"""
from __future__ import absolute_import, division, print_function

import h5py
import numpy
from future.utils import raise_from
from scipy.ndimage import median_filter


######################
# DARKCAL CORRECTION #
######################

class DarkCalCorrection(object):
    """
    See __init__ for documentation.
    """

    def __init__(self,
                 darkcal_filename,
                 darkcal_hdf5_path,
                 mask_filename=None,
                 mask_hdf5_path=False,
                 gain_map_filename=None,
                 gain_map_hdf5_path=None):
        """
        Apply dark calibration correction on frame data.

        Optionally, apply a mask and a gain map

        Args:

            darkcal_filename (str): name of the file containing the
                dark calibration data.

            darkcal_hdf5_path (str): internal HDF5 path of the data
                block where the dark calibration information (in 'slab'
                format) is stored.

            mask_filename (Optional[str]): if the argument is
                the name of a file containing a binary mask, the mask
                will be loaded and applied. If the argument is None, no
                mask will be applied. Defaults to None.

            mask_hdf5_path (Optional[str]): if the mask_filename
                argument is provided, and a mask is applied, this
                argument is the internal HDF5 path of the data block
                where the mask (in 'slab' format) is stored. The
                argument is otherwise ignored. Defaults to None.

            gain_map_filename (Optional[str]): if the argument is the
                name of a file containing a gain map, the map will be
                loaded and applied. If the argument is None, no map
                will be applied. Defaults to None.

            mask_hdf5_path (Optional[str]): if the gain_map_filename
                argument is provided, and a gain map is applied, this
                argument is the internal HDF5 path of the data block
                where the gain map (in 'slab' format) is stored. The
                argument is otherwise ignored. Defaults to None.
        """
        try:
            with h5py.File(
                name=darkcal_filename,
                mode='r'
            ) as fhandle:
                self._darkcal = fhandle[darkcal_hdf5_path][:]
        except OSError:
            raise_from(
                exc=RuntimeError(
                    "Error reading the {} HDF5 file.".format(
                        darkcal_filename
                    )
                ),
                cause=None
            )

        if mask_filename:
            try:
                with h5py.File(
                    name=mask_filename,
                    mode='r'
                ) as fhandle:
                    self._darkcal = fhandle[mask_hdf5_path]
            except OSError:
                raise_from(
                    exc=RuntimeError(
                        "Error reading the {} HDF5 file.".format(
                            mask_filename
                        )
                    ),
                    cause=None
                )
        else:

            # True here is equivalent to an all-ones mask.
            self._mask = True

        if gain_map_filename:
            try:
                with h5py.File(
                    name=gain_map_filename,
                    mode='r'
                ) as fhandle:
                    self._gain_map = fhandle[gain_map_hdf5_path]
            except OSError:
                raise_from(
                    exc=RuntimeError(
                        "Error reading the {} HDF5 file.".format(
                            mask_filename
                        )
                    ),
                    cause=None
                )
        else:
            # True here is equivalent to an all-ones map.
            self._gain_map = True

    def apply_darkcal_correction(self,
                                 data):
        """
        Apply the correction.

        Optionally, also apply the user-provided mask and gain map.

        Args:

            data (numpy.ndarray): the data (in 'slab' format) on which
                the corrections should be applied.

        Returns:

            numpy.ndarray: the corrected data.

        """
        return (data * self._mask - self._darkcal) * self._gain_map


########################
# FRAME DATA AVERAGING #
########################

class FrameDataAveraging(object):
    """
    See __init__ for documentation.
    """

    def __init__(self,
                 num_events_to_average,
                 slab_shape):
        """
        Accumulate and average detector frame data.

        Accumulate detector frame data (in 'slab' format) until the
        accumulator is full (i.e.: a predefined number of data entries
        has been added to the accumulator), then return the average of
        the accumulated data and empty the accumulator.

        Args:

            num_events_to_accumulate (int): the number of raw detector
                data items to accumulate before the accumulator is
                full.

            slab_shape (Tuple[int, int]): numpy shape-like tuple
                describing the size of the data that will go in the
                accumulator.
        """
        self._num_events_to_average = num_events_to_average
        self._slab_shape = slab_shape

        # Initialize the counter for the accumulated entries and the
        # array that will store the accumulated data.
        self._num_averaged_events = 0
        self._avg_frame_data = numpy.zeros(slab_shape)

    def add_data(self, data):
        """
        Add raw detector_data.

        If the accumulator is full, return the average of the
        accumulated data and empty the accumulator.

        Args:

            data (numpy.ndarray): raw detector data (in 'slab' format)
                to be added to the accumulator.

        Returns:

            Union[numpy.ndarray, None]: the average of the accumulated
            data if the accumulator is full, None otherwise.
        """
        # Add the frame data and normalize in a single step.
        self._avg_frame_data += (data / self._num_events_to_average)
        self._num_averaged_events += 1

        if self._num_averaged_events == self._num_events_to_average:
            data_to_be_returned = self._avg_frame_data.copy()
            self._num_averaged_events = 0
            self._avg_frame_data.fill(0)
            return data_to_be_returned

        # Otherwise return none.
        return None


#######################
# MINIMA IN WAVEFORMS #
#######################

class FindMinimaInWaveforms(object):
    """
    See __init__ for documentation.
    """

    def __init__(self,
                 threshold,
                 estimated_noise_width,
                 minimum_peak_width,
                 background_subtraction=False):
        """
        Find minima in waveforms.

        Perform peak finding on 1d waveform data, after applying a
        moving-window smoothing function. The waveform signal is
        expected to have a negative sign, and peaks are minima in the
        waveform.

        Args:

            threshold (float): a negative number. The minimum negative
                signal strength (over the signal baseline) for a
                detected minimum to be considered a peak.

            estimated_noise_width (int): the width (in pixel) of the
                moving-window smoothing function that will applied
                to the data before peak detection.

            minimum_peak_width (int): minimum width of a peak (in
                number of data points). All minima found within the
                range (in data points) specified by this parameter will
                be considered as belonging to the same peak. The
                position of the minimum with the highest negative
                strength will be reported as the position of the
                detected peak.

            background_subtraction (bool): If true, a low-pass filtered
                version of the data will be subtracted from the
                original data before the smoothing function is applied.
                The low pass filtered version of the data will be
                generated by filtering the original data with a running
                median filter.
        """
        self._threshold = threshold
        self._minimum_peak_width = minimum_peak_width
        self._background_subtraction = background_subtraction

        # Set some hardcoded values used for the median filter that is
        # optionally applied to the data.
        self._backgr_filter_win_size = 200
        self._backgr_filter_step = 20

        self._smoothing_array = numpy.ones(
            shape=estimated_noise_width,
            dtype=numpy.float
        ) / float(estimated_noise_width)

    def find_minima(self, data):
        """
        Find minima in the waveform.

        Args:

            waveform (numpy.ndarray): 1-dimensional numpy array
                containing the waveform data.

        Returns:

            List[int]: list of int numbers, where each entry in the
            list is the position (the index along the axis of the data
            array) of a detected peak.
        """

        if self._background_subtraction is True:

            # Index array for the data.
            index = numpy.arange(data.shape[0])
            sliced_data = data[::self._backgr_filter_step]
            sliced_index = index[::self._backgr_filter_step]

            # Apply the median filter, then interpolate the filtered
            # data.
            sliced_data = median_filter(
                input=sliced_data,
                size=self._backgr_filter_win_size
            )

            interpolated_data = numpy.interp(
                x=index,
                xp=sliced_index,
                fp=sliced_data
            )

            # Finally subtract the filtered data from the data.
            background_subtracted_data = data - interpolated_data
        else:
            background_subtracted_data = data.copy()

        # Convolve data with the smoothing array.
        smoothed_data = numpy.convolve(
            a=background_subtracted_data.astype(  # pylint: disable=E1101
                numpy.float32
            ),
            v=self._smoothing_array,
            mode='same'
        )

        # Compute first and second derivative of the smoothed data.
        d_smoothed_data = numpy.gradient(smoothed_data)
        dd_smoothed_data = numpy.gradient(d_smoothed_data)

        # Use the derivatives to locate the peaks.
        peak_locations = numpy.where(
            (
                numpy.diff(numpy.sign(d_smoothed_data)) > 0
            ) * (
                dd_smoothed_data[:-1] > 0
            )
        )[0]

        # Filter peaks according to the negative threshold provided by
        # the user.
        intensity_offset = numpy.mean(smoothed_data)
        filtered_peaks = numpy.where(
            smoothed_data[peak_locations] - intensity_offset <
            (-abs(self._threshold))
        )
        peak_list = list(peak_locations[filtered_peaks])

        # Remove peaks that are too close. For each group of peaks that
        # lie too close to each other, take the peak with the strongest
        # negative strength.

        # In order to do this, create a flag that records if any peak
        # that lies to close to another one has been found. Set this
        # flag initially to True until the condition has been proven
        # false.
        any_too_close = True
        while any_too_close is True:

            temp_peak_list = []
            for peak_index, peak_postion in enumerate(peak_list):

                # Create an internal list of peak values.
                internal_peak_list = []

                if peak_index > 0:

                    # If the current peak is not the first one, compute
                    # the distance between the current peak and the
                    # previous one. If the peaks are too close, append
                    # to the internal list the value of the previous
                    # peak.
                    dist_from_prev_peak = (
                        peak_postion -
                        peak_list[peak_index - 1]
                    )
                    if dist_from_prev_peak < self._minimum_peak_width:
                        internal_peak_list.append(
                            smoothed_data[peak_list[peak_index - 1]]
                        )

                if peak_index < len(peak_list) - 1:

                    # If the current peak is not the last one, compute
                    # the distance between the current peak and the
                    # next one. If the peaks are too close, append to
                    # the internal list the value of the next peak.
                    dist_to_next_peak = (
                        peak_list[peak_index + 1] -
                        peak_postion
                    )
                    if dist_to_next_peak < self._minimum_peak_width:
                        internal_peak_list.append(
                            smoothed_data[peak_list[peak_index + 1]]
                        )

                if numpy.all(
                        [
                            smoothed_data[peak_postion] < v
                            for v in internal_peak_list
                        ]
                ):

                    # If the value of the current peak is lower than
                    # all the values of the peaks that surround it, add
                    # the peak to the temporary list of detected peaks.
                    temp_peak_list.append(peak_postion)

                    # To exit the loop.
                    any_too_close = False
                else:

                    # To stay into the loop (reduntant peaks must still
                    # be removed).
                    any_too_close = True

            # Set the list of the detected peaks (used in the next
            # iteration of the 'while' loop) to the current temporary
            # list of the detected peaks.
            peak_list = temp_peak_list

        return peak_list
