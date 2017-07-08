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

from collections import namedtuple

import numpy
import scipy.ndimage as ndimage

from ondacython.lib.streakfinder_extension import StreakDetectionClass
from ondacython.lib.peakfinder8_extension import peakfinder_8, peakfinder_8_with_pixel_information
import cfelpyutils.cfel_hdf5 as ch5

PeakList = namedtuple('PeakList', ['fs', 'ss', 'intensity'])
_InternalListOfPeaks = namedtuple('_InternalListOfPeaks', ['ss', 'fs'])
_Offset = namedtuple('_Offset', ['ss', 'fs'])


#########################
# SIMPLE PEAK DETECTION #
#########################

class SimplePeakDetection:
    """Peak finding using a simple threshold-based algorithm.

    Implements a simple threshold-based peak finding algorithm. The algorithm finds peaks by thresholding the input
    data, identifying 'islands' of pixels with values above the threshold, and using as peak location the center of
    mass of the 'islands' (computed with a window of predefined size).
    """

    def __init__(self, threshold, window_size):
        """Initializes the peakfinder.

        Args:

            threshold (float): threshold for peak detection.

            window_size (int): edge size of the window used to determine the center of mass of each peak (the window
            is centered around the pixel with highest intensity).
        """

        self._threshold = threshold
        self._peak_window_size = window_size
        self._neighborhood = ndimage.morphology.generate_binary_structure(2, 5)

    def find_peaks(self, raw_data):
        """Finds peaks.

        Performs the peak finding.

        Designed to be run on worker nodes.

        Args:

            raw_data (numpy.ndarray): the data on which peak finding is performed, in 'slab' format.

        Returns:

            peak_list (tuple):  the peak list, as a tuple of three

            lists: ([peak_x], [peak_y], [peak_value]). The first two contain the coordinates of the peaks in the
            input data array, the third the intensity of the peaks. All are lists of float numbers.
        """

        local_max = ndimage.filters.maximum_filter(
            raw_data, footprint=self._neighborhood)
        data_as_slab_peak = (raw_data == local_max)
        data_as_slab_thresh = (raw_data > self._threshold)
        data_as_slab_peak[data_as_slab_thresh == 0] = 0
        internal_list_of_peaks = _InternalListOfPeaks(numpy.where(data_as_slab_peak == 1))
        peak_values = raw_data[internal_list_of_peaks]

        if len([0]) > 10000:
            print('Silly number of peaks {0}'.format(len(internal_list_of_peaks.ss)))
            peak_list = ([], [], [])
        elif len(internal_list_of_peaks[0]) != 0:
            subpixel_x = []
            subpixel_y = []
            for x_peak, y_peak in zip(internal_list_of_peaks.ss, internal_list_of_peaks.fs):
                peak_window = raw_data[x_peak - self._peak_window_size:x_peak + self._peak_window_size + 1,
                                       y_peak - self._peak_window_size:y_peak + self._peak_window_size + 1]
                if peak_window.shape[0] != 0 and peak_window.shape[1] != 0:
                    offset = _Offset(ndimage.measurements.center_of_mass(peak_window))
                    offset_x = offset.ss - self._peak_window_size
                    offset_y = offset.fs - self._peak_window_size
                    subpixel_x.append(x_peak + offset_x)
                    subpixel_y.append(y_peak + offset_y)
                else:
                    subpixel_x.append(x_peak)
                    subpixel_y.append(y_peak)

            peak_list = PeakList(subpixel_x, subpixel_y, peak_values)
        else:
            peak_list = PeakList([], [], [])

        return peak_list


####################
# PEAK ACCUMULATOR #
####################

class PeakAccumulator:
    """Accumulates found peaks

    Accumulates peaks provided by the user until a predefinel number of additions have been reached, then it returns the
    full list of accumulated peaks.
    """

    def __init__(self, accumulated_shots):
        """Initializes the accumulator

        Args:

                accumulated_shots(int): the number of peak additions to accumulate before returning the peak list
        """

        self._accumulated_shots = accumulated_shots
        self._accumulator = PeakList([], [], [])
        self._events_in_accumulator = 0

    def accumulate_peaks(self, peak_list):
        """Accumulates peaks.

        Accumulates peaks. The peaks are added to an internal list of peaks. When peaks have been added to the list for
        a numer of times specified by the accumulated_shots algorithm parameter, the function returns the accumulated
        peak list to the user and empties it.

        Designed to be run on the master node.

        Args:

            peak_list (PeakList): list of peaks to be added to the internal list. The peak list should be a tuple of
            three lists, containing, in order, the fs coordinate of the peaks, their respective ss coordinate , and
            their intensity.

        Returns:

            peak_list (tuple or None):  the accumulated peak_list if peaks have been added to the list for the number
            of times specified by the accumulated_shots parameter, None otherwise. If returned, the peak list is a tuple
            of three lists, containing, in order, the fs coordinate of the peaks, their respective ss coordinate , and
            their intensity.
        """

        self._accumulator.fs.extend(peak_list.fs)
        self._accumulator.ss.extend(peak_list.ss)
        self._accumulator.intensity.extend(peak_list.intensity)
        self._events_in_accumulator += 1

        if self._events_in_accumulator == self._accumulated_shots:
            peak_list_to_return = self._accumulator
            self._accumulator = PeakList([], [], [])
            self._events_in_accumulator = 0
            return peak_list_to_return
        return None


##############################
# PEAKFINDER8 PEAK DETECTION #
##############################

class Peakfinder8PeakDetection:
    """Peak finding using cheetah's peakfinder8 algorithm.

    Implements peak finding using the peakfinder8 algorithm from Cheetah.
    """

    def __init__(self, max_num_peaks, asic_nx, asic_ny, nasics_x,
                 nasics_y, adc_threshold, minimum_snr, min_pixel_count,
                 max_pixel_count, local_bg_radius, min_res,
                 max_res, mask_filename, mask_hdf5_path, pixelmap_radius):
        """Initializes the peakfinder.

        Args:

            max_num_peaks (int): maximum number of peaks that will be returned by the algorithm.

            asic_nx (int): fs size of a detector's ASIC.

            asic_ny (int): ss size of a detector's ASIC.

            nasics_x (int): number of ASICs in the slab in the fs direction.

            nasics_y (int): number of ASICs in the slab in the ss direction.

            adc_threshold (float): minimum adc threshold for peak detection.

            minimum_snr (float): minimum signal to noise for peak detection.

            min_pixel_count (int): minimum size of the peak in pixels.

            max_pixel_count (int): maximum size of the peak in pixels.

            local_bg_radius (int): radius for the estimation of the local background.

            min_res (int): minimum resolution for a peak to be considered (in pixels).

            max_res (int): minimum resolution for a peak to be considered (in pixels).

            mask_filename (str): filename of the file containing the mask.

            mask_hdf5_path (str): internal hdf5 path of the data block containing the mask.

            pixelmap_radius (numpy.ndarray): pixelmap in 'slab' format listing for each pixel the distance from the
            center of the detector, in pixels.
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
        self._pixelmap_radius = pixelmap_radius
        self._mask = ch5.load_nparray_from_hdf5_file(mask_filename, mask_hdf5_path)

        res_mask = numpy.ones(self._mask.shape, dtype=numpy.int8)
        res_mask[numpy.where(pixelmap_radius < min_res)] = 0
        res_mask[numpy.where(pixelmap_radius > max_res)] = 0

        self._mask *= res_mask


    def find_peaks(self, raw_data):
        """Finds peaks.

        Performs the peak finding.

        Args:

            raw_data (numpy.ndarray): the data on which peak finding is performed, in 'slab' format.

        Returns:

            peak_list (tuple list float, list float, list float): the peak list, as a tuple of three lists:
            ([peak_x], [peak_y], [peak_value]). The first two contain the coordinates of the peaks in the input data
            array, the third the intensity of the peaks. All are lists of float numbers.
        """

        peak_list = peakfinder_8(self._max_num_peaks,
                                 raw_data.astype(numpy.float32),
                                 self._mask.astype(numpy.int8),
                                 self._pixelmap_radius,
                                 self._asic_nx, self._asic_ny,
                                 self._nasics_x, self._nasics_y,
                                 self._adc_thresh, self._minimum_snr,
                                 self._min_pixel_count, self._max_pixel_count,
                                 self._local_bg_radius)

        return PeakList(*peak_list[0:3])

    ################################################
    # PEAKFINDER8 PEAK DETECTION WITH OUTLIER MASK #
    ################################################

    class Peakfinder8PeakDetectionWithPixelInformation:
        """Peak finding using cheetah's peakfinder8 algorithm. Also returns a pixel classification mask.

        Implements peak finding using the peakfinder8 algorithm from Cheetah. Additionally, fills an array provided
        by the user with pixel information. After the peak finding is performed, the pixel information mask shows
        whether a pixel has been classified as background, it belongs to a peak or it belongs to an outlier (a
        collection of pixels rejected as a peak because of its size).
        """

        def __init__(self, max_num_peaks, asic_nx, asic_ny, nasics_x,
                     nasics_y, adc_threshold, minimum_snr, min_pixel_count,
                     max_pixel_count, local_bg_radius, min_res,
                     max_res, mask_filename, mask_hdf5_path, pixelmap_radius):
            """Initializes the peakfinder.

            Args:

                max_num_peaks (int): maximum number of peaks that will be returned by the algorithm.

                asic_nx (int): fs size of a detector's ASIC.

                asic_ny (int): ss size of a detector's ASIC.

                nasics_x (int): number of ASICs in the slab in the fs direction.

                nasics_y (int): number of ASICs in the slab in the ss direction.

                adc_threshold (float): minimum adc threshold for peak detection.

                minimum_snr (float): minimum signal to noise for peak detection.

                min_pixel_count (int): minimum size of the peak in pixels.

                max_pixel_count (int): maximum size of the peak in pixels.

                local_bg_radius (int): radius for the estimation of the local background.

                min_res (int): minimum resolution for a peak to be considered (in pixels).

                max_res (int): minimum resolution for a peak to be considered (in pixels).

                mask_filename (str): filename of the file containing the mask.

                mask_hdf5_path (str): internal hdf5 path of the data block containing the mask.

                pixelmap_radius (numpy.ndarray): pixelmap in 'slab' format listing for each pixel the distance from the
                center of the detector, in pixels.
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
            self._pixelmap_radius = pixelmap_radius
            self._mask = ch5.load_nparray_from_hdf5_file(mask_filename, mask_hdf5_path)

            res_mask = numpy.ones(self._mask.shape, dtype=numpy.int8)
            res_mask[numpy.where(pixelmap_radius < min_res)] = 0
            res_mask[numpy.where(pixelmap_radius > max_res)] = 0

            self._mask *= res_mask


        def find_peaks(self, raw_data, outlier_mask):
            """Finds peaks.

            Performs the peak finding.

            Args:

                raw_data (numpy.ndarray): the data on which peak finding is performed, in 'slab' format.

                outlier_mask (numpy.ndarray): an array of int with the same shape and size as raw_data. After
                the function call, this array contains

            Returns:

                peak_list (tuple list float, list float, list float): the peak list, as a tuple of three lists:
                ([peak_x], [peak_y], [peak_value]). The first two contain the coordinates of the peaks in the input data
                array, the third the intensity of the peaks. All are lists of float numbers.
            """

            peak_list = peakfinder_8_with_pixel_information(self._max_num_peaks,
                                                            raw_data.astype(numpy.float32),
                                                            self._mask.astype(numpy.int8),
                                                            self._pixelmap_radius,
                                                            self._asic_nx, self._asic_ny,
                                                            self._nasics_x, self._nasics_y,
                                                            self._adc_thresh, self._minimum_snr,
                                                            self._min_pixel_count, self._max_pixel_count,
                                                            self._local_bg_radius, outlier_mask)

            return PeakList(*peak_list[0:3])


####################
# STREAK DETECTION #
####################

class StreakDetection:
    """Streak detection.

    Implements streak finding and masking.
    """


    def __init__(self, filter_length, min_filter_length, filter_step,
                 sigma_factor, streak_elongation_min_steps_count,
                 streak_elongation_radius_factor,
                 streak_pixel_mask_radius,
                 pixels_to_check_x, pixels_to_check_y,
                 background_estimation_regions_upper_left_corner_x,
                 background_estimation_regions_upper_left_corner_y,
                 background_estimation_regions_lower_right_corner_x,
                 background_estimation_regions_lower_right_corner_y,
                 asic_nx, asic_ny, nasics_x, nasics_y,
                 pixel_map_x, pixel_map_y, mask_filename,
                 mask_hdf5_path):
        """Initializes the peakfinder.

        Args:

            role (str): node role ('worker' or 'master')

            filter_length (int): length of the radial filter with which the image is prefiltered.

            min_filter_length (int): Minimum amount of non-masked pixels in the radial filter with which the image is
            prefiltered.

            float filter_step (float): size of the step through the radial filter.

            sigma_factor(float): minimum number of stddev above the mean for the pixel to be part of a streak.

            streak_elongation_min_steps_count (int): number of steps to keep searching for a streak after it
            apparently ends.

            streak_elongation_radius_factor (float): maximum distance in pixels from the center to keep searching for
            a streak after it apparently ends.

            streak_pixel_mask_radius (int): Radius  of the mask around the streak in pixels.

            pixels_to_check_x (numpy.ndarray): array (of ints) with fs coordinates (in the array containing raw_data
            in slab format) of pixels where streaks could originate

            pixels_to_check_y (numpy.ndarray): array (of ints) with ss coordinates (in the array containing raw_data
            in slab format) of pixels where streaks could originate

            background_estimation_regions_upper_left_corner_x (numpy.ndarray): array (of ints) with fs coordinates
            (in the array containing raw_data in slab format) of the top left corners of areas used to estimate
            the background signal level

            background_estimation_regions_upper_left_corner_y (numpy.ndarray): array (of ints) with ss coordinates
            (in the array containing raw_data in slab format) of the top left corners of areas used to estimate
            the background signal level

            background_estimation_regions_lower_right_corner_x (numpy.ndarray): array (of ints) with fs coordinates
            (in the array containing raw_data in slab format) of the bottom right corners of areas used to estimate
            the background signal level

            background_estimation_regions_lower_right_corner_y(numpy.ndarray): array (of ints) with ss coordinates
            (in the array containing raw_data in slab format) of the bottom right corners of areas used to estimate
            the background signal level

            asic_nx (int): fs size of a detector's ASIC.

            asic_ny (int): ss size of a detector's ASIC.

            nasics_x (int): number of ASICs in the slab in the fs direction.

            nasics_y (int): number of ASICs in the slab in the ss direction.

            pixel_map_x (numpy.ndarray): pixel_map for x coordinate

            pixel_map_y (numpy.ndarray): pixel_map for y coordinate

            mask_filename (str): filename of the file containing the mask.

            mask_hdf5_path (str): internal hdf5 path of the data block containing the mask.
        """

        self.mask = ch5.load_nparray_from_hdf5_file(mask_filename,
                                                    mask_hdf5_path)

        self.streak_detection = StreakDetectionClass(
            min_filter_length,
            filter_length, filter_step,
            sigma_factor,
            streak_elongation_min_steps_count,
            streak_elongation_radius_factor,
            streak_pixel_mask_radius,
            pixels_to_check_x, pixels_to_check_y,
            background_estimation_regions_upper_left_corner_x,
            background_estimation_regions_upper_left_corner_y,
            background_estimation_regions_lower_right_corner_x,
            background_estimation_regions_lower_right_corner_y,
            asic_nx, asic_ny, nasics_x, nasics_y,
            pixel_map_x, pixel_map_y, self.mask)

    def find_streaks(self, data, streak_mask):
        """Finds streaks.

        Performs the strek finding.

        Designed to be run on worker nodes.

        Args:

            data (numpy.ndarray): the data on which to perform streak-finding.

            streak_mask (numpy.ndarray): an array with the same shape as the data. After the function returns,
            this array will contain the mask generated by the streak finder.
        """

        self.streak_mask[self.streak_mask > 0] = -1
        self.streak_mask += -1
        self.streak_detection.find_streaks(data, streak_mask, self.mask)
