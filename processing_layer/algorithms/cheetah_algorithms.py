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

from cfelpyutils.cfel_hdf5 import load_nparray_from_hdf5_file

try:
    from peakfinder8_extension import peakfinder_8
    from peakfinder9_extension import peakfinder_9
    from streakfinder_extension import StreakDetectionClass
except:
    raise RuntimeError('Error importing cheetah wrappers. Make sure that they are compiled for the correct ' +
                       'python version.')


##############################
# PEAKFINDER8 PEAK DETECTION #
##############################

class Peakfinder8PeakDetection:
    """Peak finding using cheetah's peakfinder8 algorithm.

    Implements peak finding using the peakfinder8 algorithm from Cheetah.
    """

    def __init__(self, role, max_num_peaks, asic_nx, asic_ny, nasics_x,
                 nasics_y, adc_threshold, minimum_snr, min_pixel_count,
                 max_pixel_count, local_bg_radius, accumulated_shots, min_res,
                 max_res, mask_filename, mask_hdf5_path, pixelmap_radius):
        """Initializes the peakfinder.

        Args:

            role (str): node role ('worker' or 'master')

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

            accumulated_shots (int): the number of accumulated shots before the peak list is returned.

            min_res (int): minimum resolution for a peak to be considered (in pixels).

            max_res (int): minimum resolution for a peak to be considered (in pixels).

            mask_filename (str): filename of the file containing the mask.

            mask_hdf5_path (str): internal hdf5 path of the data block containing the mask.

            pixelmap_radius (numpy.ndarray): pixelmap in 'slab' format listing for each pixel the distance from the
            center of the detector, in pixels.
        """

        if role == 'master':

            self.accumulated_shots = accumulated_shots
            self.accumulator = ([], [], [])
            self.events_in_accumulator = 0

        # Initialized on worker
        if role == 'worker':

            self.max_num_peaks = max_num_peaks
            self.asic_nx = asic_nx
            self.asic_ny = asic_ny
            self.nasics_x = nasics_x
            self.nasics_y = nasics_y
            self.adc_thresh = adc_threshold
            self.minimum_snr = minimum_snr
            self.min_pixel_count = min_pixel_count
            self.max_pixel_count = max_pixel_count
            self.local_bg_radius = local_bg_radius
            self.pixelmap_radius = pixelmap_radius
            self.mask = load_nparray_from_hdf5_file(mask_filename, mask_hdf5_path)

            res_mask = numpy.ones(self.mask.shape, dtype=numpy.int8)
            res_mask[numpy.where(pixelmap_radius < min_res)] = 0
            res_mask[numpy.where(pixelmap_radius > max_res)] = 0

            self.mask *= res_mask

    def find_peaks(self, raw_data):
        """Finds peaks.

        Performs the peak finding.

        Designed to be run on worker nodes.

        Args:

            raw_data (numpy.ndarray): the data on which peak finding is performed, in 'slab' format.

        Returns:

            peak_list (tuple list float, list float, list float): the peak list, as a tuple of three lists:
            ([peak_x], [peak_y], [peak_value]). The first two contain the coordinates of the peaks in the input data
            array, the third the intensity of the peaks. All are lists of float numbers.
        """

        peak_list = peakfinder_8(self.max_num_peaks,
                                 raw_data.astype(numpy.float32),
                                 self.mask.astype(numpy.int8),
                                 self.pixelmap_radius,
                                 self.asic_nx, self.asic_ny,
                                 self.nasics_x, self.nasics_y,
                                 self.adc_thresh, self.minimum_snr,
                                 self.min_pixel_count, self.max_pixel_count,
                                 self.local_bg_radius)

        return peak_list

    def accumulate_peaks(self, peak_list):
        """Accumulates peaks.

        Accumulates peaks. The peaks are added to an internal list of peaks. When peaks have been added to the list for
        a numer of times specified by the accumulated_shots algorithm parameter, the function returns the accumulated
        peak list to the user and empties it.

        Designed to be run on the master node.

        Args:

            peak_list (tuple): list of peaks (as returned by the peak_find function) to be added to the internal list.

        Returns:

            peak_list (tuple or None):  the accumulated peak_list if peaks have been added to the list for the number
            of times specified by the accumulated_shots parameter, None otherwise.
        """

        self.accumulator[0].extend(peak_list[0])
        self.accumulator[1].extend(peak_list[1])
        self.accumulator[2].extend(peak_list[2])
        self.events_in_accumulator += 1

        if self.events_in_accumulator == self.accumulated_shots:
            peak_list_to_return = self.accumulator
            self.accumulator = ([], [], [])
            self.events_in_accumulator = 0
            return peak_list_to_return
        return None


##############################
# PEAKFINDER9 PEAK DETECTION #
##############################

class Peakfinder9PeakDetection:
    """Peak finding using cheetah's peakfinder9 algorithm.

    Implements peak finding using the peakfinder9 algorithm from Cheetah.
    """

    def __init__(self, role, max_num_peaks, asic_nx, asic_ny, nasics_x,
                 nasics_y, sigma_factor_biggest_pixel, sigma_factor_peak_pixel,
                 sigma_factor_whole_peak, minimum_sigma,
                 minimum_peak_oversize_over_neighbours,
                 window_radius, accumulated_shots, min_res, max_res,
                 mask_filename, mask_hdf5_path, pixelmap_radius):
        """Initializes the peakfinder.

        Args:

            role (str): node role ('worker' or 'master')

            max_num_peaks (int): maximum number of peaks that will be returned by the algorithm.

            asic_nx (int): fs size of a detector's ASIC.

            asic_ny (int): ss size of a detector's ASIC.

            nasics_x (int): number of ASICs in the slab in the fs direction.

            nasics_y (int): number of ASICs in the slab in the ss direction.

            sigma_factor_biggest_pixel (float): minimum number of stddev above the mean for the brightest pixel in a
            peak.

            sigma_factor_peak_pixel (float): minimum  number of stddev above the mean for all pixels except the
            brightest. Should be equal to or lower than sigma_factor_biggest_pixel.

            sigma_factor_whole_peak (float): minimum  number of stddev above the mean for the accumulated inensity of a
            peak. Should be equal to or lower than sigma_factor_biggest_pixel.

            minimum_sigma (float): minimum number of stddev for a pixel to be a peak candidate.

            minimum_peak_oversize_over_neighbours (float): minimum intensity difference between the brighest pixel in a
            peak and the background pixels, which are the pixels on the border of the background window.

            window_radius (int): radius of the window used to estimate background.

            accumulated_shots (int): the number of accumulated shots before the peak list is returned.

            min_res (int): minimum resolution for a peak to be considered (in pixels).

            max_res (int): minimum resolution for a peak to be considered (in pixels).

            mask_filename (str): filename of the file containing the mask.

            mask_hdf5_path (str): internal hdf5 path of the data block containing the mask.
        """

        self.max_num_peaks = max_num_peaks
        self.asic_nx = asic_nx
        self.asic_ny = asic_ny
        self.nasics_x = nasics_x
        self.nasics_y = nasics_y
        self.sigma_factor_biggest_pixel = sigma_factor_biggest_pixel
        self.sigma_factor_peak_pixel = sigma_factor_peak_pixel
        self.sigma_factor_whole_peak = sigma_factor_whole_peak
        self.minimum_sigma = minimum_sigma
        self.minimum_peak_oversize_over_neighbours = minimum_peak_oversize_over_neighbours
        self.window_radius = window_radius

        if role == 'master':

            self.accumulated_shots = accumulated_shots
            self.accumulator = ([], [], [])
            self.events_in_accumulator = 0

        # Initialized on worker
        if role == 'worker':

            self.mask = load_nparray_from_hdf5_file(mask_filename, mask_hdf5_path)
            self.res_mask = numpy.ones(self.mask.shape, dtype=numpy.int8)
            self.res_mask[numpy.where(pixelmap_radius < min_res)] = 0
            self.res_mask[numpy.where(pixelmap_radius > max_res)] = 0
            self.mask *= self.res_mask

    def find_peaks(self, raw_data):
        """Finds peaks.

        Performs the peak finding.

        Designed to be run on worker nodes.

        Args:

            raw_data (numpy.ndarray): the data on which peak finding is performed, in 'slab' format.

        Returns:

            peak_list (tuple): the peak list, as a tuple of three lists: ([peak_x], [peak_y], [peak_value]). The first
            two contain the coordinates of the peaks in the input data array, the third the intensity of the peaks.
            All are lists of float numbers.
        """

        peak_list = peakfinder_9(self.max_num_peaks,
                                 raw_data.astype(numpy.float32),
                                 self.mask.astype(numpy.int8),
                                 self.asic_nx, self.asic_ny, self.nasics_x,
                                 self.nasics_y,
                                 self.sigma_factor_biggest_pixel,
                                 self.sigma_factor_peak_pixel,
                                 self.sigma_factor_whole_peak,
                                 self.minimum_sigma,
                                 self.minimum_peak_oversize_over_neighbours,
                                 self.window_radius)
        return peak_list

    def accumulate_peaks(self, peak_list):
        """Accumulates peaks.

        Accumulates peaks. The peaks are added to an internal list of peaks. When peaks have been added to the list for
        a numer of times specified by the accumulated_shots algorithm parameter, the function returns the accumulated
        peak list to the user and empties it.

        Designed to be run on the master node.

        Args:

            peak_list (tuple): list of peaks (as returned by the peak_find function) to be added to the internal list.

        Returns:

            peak_list (tuple or None):  the accumulated peak_list if peaks have been added to the list for the number
            of times specified by the accumulated_shots parameter, None otherwise.
        """

        self.accumulator[0].extend(peak_list[0])
        self.accumulator[1].extend(peak_list[1])
        self.accumulator[2].extend(peak_list[2])
        self.events_in_accumulator += 1

        if self.events_in_accumulator == self.accumulated_shots:
            peak_list_to_return = self.accumulator
            self.accumulator = ([], [], [])
            self.events_in_accumulator = 0
            return peak_list_to_return
        return None


####################
# STREAK DETECTION #
####################

class StreakDetection:
    """Strek detection using cheetah's streakfinder algorithm.

    Implements streak finding and masking using the streakfinder algorithm from Cheetah.
    """

    def __init__(self, role, filter_length, min_filter_length, filter_step,
                 sigma_factor, streak_elongation_min_steps_count,
                 streak_elongation_radius_factor,
                 streak_pixel_mask_radius, num_lines_to_check,
                 background_region_preset,
                 background_region_dist_from_edge,
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

            num_lines_to_check (int): maximum distance in pixels from the inner edge of the inner panels to searching
            for the beginning of a streak.

            background_region_preset (int): preset locations of regions to be used to estimate the background level.

            background_region_dist_from_edge (int): distance of background regions in pixels from the edge of the
            inner panels

            asic_nx (int): fs size of a detector's ASIC.

            asic_ny (int): ss size of a detector's ASIC.

            nasics_x (int): number of ASICs in the slab in the fs direction.

            nasics_y (int): number of ASICs in the slab in the ss direction.

            pixel_map_x (numpy.ndarray): pixel_map for x coordinate

            pixel_map_y (numpy.ndarray): pixel_map for y coordinate

            mask_filename (str): filename of the file containing the mask.

            mask_hdf5_path (str): internal hdf5 path of the data block containing the mask.
        """

        # Initialized on worker
        if role == 'worker':

            self.mask = load_nparray_from_hdf5_file(mask_filename,
                                                    mask_hdf5_path)
            self.background_region_mask = numpy.zeros(self.mask.shape)

            self.streak_detection = StreakDetectionClass(
                min_filter_length,
                filter_length, filter_step,
                sigma_factor,
                streak_elongation_min_steps_count,
                streak_elongation_radius_factor,
                streak_pixel_mask_radius, num_lines_to_check,
                0, background_region_preset,
                background_region_dist_from_edge,
                asic_nx, asic_ny, nasics_x, nasics_y,
                pixel_map_x, pixel_map_y, self.mask,
                self.background_region_mask)

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

    def get_background_region_mask(self):
        """Recovers a mask with the background region preset.

        Recovers  a mask with the background region preset used by the streak finder algorithm.

        Returns:

            mask (numpy.ndarray): a mask containing the regions used by the streakfinding algorithm to estimate the
            background level (as masked regions).
        """
        return self.streak_detection.get_background_region_mask()
