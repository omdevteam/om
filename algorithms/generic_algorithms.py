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


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import numpy
import scipy
import scipy.signal
import scipy.ndimage

import cfelpyutils.cfel_hdf5 as ch5


######################
# DARKCAL CORRECTION #
######################

class DarkCalCorrection:
    """DarkCal correction

    Implements DarkCal correction. Applies DarkCal correction to
    data, by simple subtraction. Optionally, a gain map can be also applied.
    """

    def __init__(self, filename, hdf5_group, apply_mask=False,
                 mask_filename=None, mask_hdf5_group=False,
                 gain_map_correction=False, gain_map_filename=None,
                 gain_map_hdf5_group=None):
        """Initializes the DarkCal correction algorithm.

        Args:

            filename (str): name of the hdf5 with dark calibration data

            hdf5_group (str): path of the dark calibration data within the hdf5 file.

            apply_mask (Optional[bool]): whether a mask should be applied (optional, if omitted no mask is applied).

            mask_filename (Optional[str]) : if the mask is applied, name of the hdf5 file with gain_map, otherwise
            ignored. This argument must be only be provided if the apply_mask argument is set to True.

            mask_hdf5_group (Optional[str]): if the mask is applied, internal hdf5 path of the data block containing
            the mask, otherwise ignored. This argument must be only be provided if the apply_mask argument is set to
            True.
         """

        # load the darkcals
        self._darkcal = ch5.load_nparray_from_hdf5_file(filename, hdf5_group)

        if apply_mask:
            self._mask = ch5.load_nparray_from_hdf5_file(mask_filename,
                                                         mask_hdf5_group)
        else:
            self._mask = True

    def apply_darkcal_correction(self, data_as_slab):
        """Applies the correction.

        Args:

            data_as_slab (numpy.ndarray): the data on which to apply the DarkCal correction, in 'slab' format.
        """

        return (data_as_slab * self._mask - self._darkcal)


######################
# RAW DATA AVERAGING #
######################

class RawDataAveraging:
    """Averages raw data.

    Accumulates raw data images and returns the average image when the required number of shots have been collected.
    """

    def __init__(self, accumulated_shots, slab_shape):
        """Initializes the raw data averaging algorithm.

        Args:

            accumulated_shots (int): the number images to accumulate before returning the average image.

            slab_shape (tuple): shape of the numpy.ndarray containing the data to be accumulated.
        """

        self._accumulated_shots = accumulated_shots
        self._slab_shape = slab_shape
        self._num_raw_data = 0
        self._avg_raw_data = numpy.zeros(slab_shape)

    def accumulate_raw_data(self, data_as_slab):
        """Accumulates peaks.

        Accumulates raw data images. When the number of images specified specified by the accumulated_shots class
        attribute is reached, the function returns the average image.

        Args:

            data_as_slab (numpy.ndarray): raw data image to add, in 'slab' format.

        Returns:

            avg_raw_data (tuple or None):  the average image if the number of images specified by the accumulated_shots
            class attribute has been reached, None otherwise.
        """

        if self._num_raw_data == self._accumulated_shots:
            self._num_raw_data = 0
            self._avg_raw_data.fill(0)

        self._avg_raw_data += (data_as_slab / self._accumulated_shots)
        self._num_raw_data += 1
        if self._num_raw_data == self._accumulated_shots:
            return self._avg_raw_data
        return None


########################
# OPTICAL LASER STATUS #
########################

class OpticalLaserStatus:
    """Informs about optical laser status (ON or OFF).

    Provides information about the optical laser status (ON or OFF) by inspecting the event codes for the event.
    """

    def __init__(self, laser_on_event_codes):
        """Initializes the optical laser status algorithm.

        Args:

            laser on event codes (tuple): tuple containing the event codes (as ints) that correspond to the optical
            laser being on. The optical laser is assumed to be on only if all event codes in the tuple are present in
            the list of event codes for a specific event.

            If the list of laser on event codes is set to None, the laser is reported as being always off.
        """

        self._laser_on_event_codes = laser_on_event_codes

    def is_optical_laser_on(self, event_codes):
        """Reports if optical laser is on.

        Inspects the provided event codes and reports if the optical laser is on.

        Designed to be run on the worker node.

        Args:

            event_codes (list): list of event codes to evaluate (list of int)

        Returns:

            laser_is_on (bool):  True if the optical laser is on according to the event codes, False otherwise.
        """

        return all(x in event_codes for x in self._laser_on_event_codes)

#######################
# MINIMA IN WAVEFORMS #
#######################


def _median_filter_course(f, window_size, steps):

    i = numpy.arange(f.shape[0])
    g = f[::steps]
    j = i[::steps]
    g = scipy.ndimage.median_filter(g, window_size)
    h = numpy.interp(i, j, g)
    return h


class FindMinimaInWaveforms:
    """Finds minima in waveforms.

    Finds minima (negative peaks) in 1d waveform data.
    """

    def __init__(self, threshold, estimated_noise_width, minimum_peak_width, background_subtraction=False):
        """Initializes the minima finding algorithm.

        Args:

            threshold (float): a negative number. The minimum value for a detected minimum to be
            reported. Only minima with a value lower (more negative) than this parameter are
            considered by the algorithm.

            estimated_noise_width (int): the size in pixel of a smoothing function that is applied
            to the data before the minima detection begins.

            minimum_peak_width (int): minimum width of a peak in number of data points. All
            minima found within the size specified by this parameter will be cosidered as belonging
            to the same peak. Only the minimum with the lowest value will be reported: all the
            other will be ignored.

            background_subtraction (boolean): If true, subtracts the low pass filtered signal (filtering with
            running median filter) from the signal as the first step in the algorithm
        """

        # Initialized on master
        self._threshold = threshold
        self._estimated_noise_width = estimated_noise_width
        self._minimum_peak_width = minimum_peak_width
        self._background_subtraction = background_subtraction
        self._background_filterSize = 200
        self._background_filterStep = 20

    def find_minima(self, waveform):
        """Finds minima in the waveform

        Designed to be run on worker nodes.

        Args:

            waveform  (numpy.ndarray): 1d array containing the waveform data

        Returns:

            peak_list (list of int): list containing the position of the
            minima in the waveform data array
        """

        if self._background_subtraction is True:
            s = waveform - _median_filter_course(waveform, self._background_filterSize, self._background_filterStep)
        else:
            s = waveform.copy()

        window = numpy.ones(self._estimated_noise_width, dtype=numpy.float) / float(self._estimated_noise_width)
        s = numpy.convolve(s.astype(numpy.float), window, mode='same')

        ds = numpy.gradient(s)
        dds = numpy.gradient(ds)

        peak_locations = numpy.where((numpy.diff(numpy.sign(ds)) > 0) * (dds[:-1] > 0))[0]

        offset = numpy.mean(s)
        t = numpy.where(s[peak_locations] - offset < -abs(self._threshold))
        peak_locations = peak_locations[t]

        # reject peaks that are too close together
        # when two peaks are too close together
        # keep the more negative peaks
        peak_list = list(peak_locations)

        while True:
            peaks_temp = []
            any_too_close = False

            for i in range(len(peak_list)):
                # if peak i is too close to peaks i-1 or i+1
                # then add peak i if it has the smallest value
                p0 = peak_list[i]
                v0 = s[p0]

                n = []
                if i > 0 and (p0 - peak_list[i - 1]) < self._minimum_peak_width:
                    n.append(s[peak_list[i - 1]])

                if i < len(peak_list) - 1 and (peak_list[i + 1] - p0) < self._minimum_peak_width:
                    n.append(s[peak_list[i + 1]])

                if numpy.all([v0 < v for v in n]):
                    peaks_temp.append(p0)
                else:
                    any_too_close = True

            peak_list = list(peaks_temp)
            if any_too_close is False:
                break

        return peak_list


################################################
# MINIMA IN WAVEFORMS, WITH POLYNOMIAL FITTING #
################################################

class FindMinimaInWaveformsPolyFit:
    """Finds minima in waveforms and fits a polynomial to the minima for increased accuracy

    Finds minima (negative peaks) in 1d waveform data. The algorithm fits a polynomial to the values
    of the waveform around the detected minima, with the goal of increasing minima location accuracy
    """

    def __init__(self, threshold, sigma_threshold, peak_width, background_subtraction=False):
        """Initializes the minima finding algorithm.

        Args:

            threshold (float): a negative number. The minimum value for a detected minimum to be
            reported. Only minima with a value lower (more negative) than this parameter are
            considered by the algorithm.

            sigma_threshold (float): a float. The number of standard deviations of the waveform
            below the median value to look for peaks. Only minima with a value lower (more negative) than this
            parameter are considered by the algorithm.

            peak_width (int): width of a peak in number of data points. All
            minima found within the size specified by this parameter will be cosidered as belonging
            to the same peak. Only the minimum with the lowest value will be reported: all the
            other will be ignored.

            background_subtraction (boolean): If true, subtracts the low pass filtered signal (filtering with
            running median filter) from the signal as the first step in the algorithm
        """

        # Initialized on worker
        self._threshold = threshold
        self._sigma_threshold = sigma_threshold
        self._minimum_peak_width = peak_width
        self._background_subtraction = background_subtraction

    def find_minima(self, waveform):
        """Finds minima in the waveform

        Designed to be run on worker nodes.

        Args:

            waveform  (numpy.ndarray): 1d array containing the waveform data

        Returns:

            peak_list (list of int): list containing the position of the
            minima in the waveform data array
        """
        if self._background_subtraction is True:
            filter_size = 501
            lowpass = scipy.signal.medfilt(waveform,
                                           filter_size)
            lowpass[0:(filter_size + 1) / 2] = lowpass[(
                                                      filter_size - 1) / 2]
            lowpass[-(filter_size + 1) / 2:] = lowpass[-(filter_size - 1) / 2]
            waveform = waveform - lowpass

        # get mean and std-deviation of waveform
        std = numpy.std(waveform)
        median = numpy.median(waveform)

        # 5 sigma outlier rejection
        a = waveform[numpy.abs(waveform - median) < 5 * abs(std)]
        std = numpy.std(a)
        median = numpy.median(a)

        # calculate the signal threshold
        threshold = median - self._sigma_threshold * std

        # find minimum values below threshold
        peaks = scipy.ndimage.filters.minimum_filter1d(waveform, size=self._minimum_peak_width)
        peaks = numpy.where((peaks == waveform) * (waveform < threshold))[0]

        if len(peaks) == 0:
            return []

        # remove saturated peaks
        peak_list = list(peaks)

        while True:
            peaks_temp = []
            any_too_close = False

            for i in range(len(peak_list)):
                # if peak i is too close to peaks i-1 or i+1
                # then add peak i if it has the smallest value
                p0 = peak_list[i]
                v0 = waveform[p0]

                n = []
                if i > 0 and (p0 - peak_list[i - 1]) < self._minimum_peak_width:
                    n.append(waveform[peak_list[i - 1]])

                if i < len(peak_list) - 1 and (peak_list[i + 1] - p0) < self._minimum_peak_width:
                    n.append(waveform[peak_list[i + 1]])

                if numpy.all([v0 < v for v in n]):
                    peaks_temp.append(p0)
                else:
                    any_too_close = True

            peak_list = list(peaks_temp)
            if any_too_close is False:
                break

        peaks = list(peak_list)

        peaks_poly = []
        # fit polynomial in the neighbourhood of the peak
        for p in peaks:
            x = p - self._minimum_peak_width / 2. + numpy.arange(self._minimum_peak_width * 0.9)
            x = numpy.rint(x).astype(numpy.int)
            if (x[0] > 0) and (x[-1] < len(waveform)):
                y = waveform[x]
                poly = numpy.polyfit(x, y, 2)
                # check that we have an 'up-right' parabola
                if poly[0] > 0:
                    # find minimum of polynomials
                    poly_min = -poly[1] / (2. * poly[0])
                    peaks_poly.append(poly_min)

        return peaks_poly

