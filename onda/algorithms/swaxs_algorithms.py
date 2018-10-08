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
#    @ 2017-2018 Thomas Grant, PhD and Sarah Chamberlain, BS
#                BioXFEL, SUNY at Buffalo
"""
Algorithms for small and wide angle x-ray scattering.

Algorithms for the processing of detector solution scattering data for
small and wide angle x-ray scattering experiments (SWAXS).
"""
from __future__ import absolute_import, division, print_function

import numpy as np
import scipy.constants
import os.path
from numpy.fft import fft, ifft
from scipy.signal import argrelmax
from scipy.stats import mode

###################################
# PIXEL SPACE / QSPACE CONVERSION #
###################################

class PixelSpaceQSpaceConversion:
    """
    Pixel space to q-space conversion.

    Converts coordinates on a pixel grid to coordinate in real space.
    """

    def __init__(self, num_of_bins, coffset, bin_size):
        """
        Initializes PixelSpaceQSpaceCoversion.

        Args:

            num_of_bins (int): number of pixel bins.

            coffset (float) : detector distance's offset in meters
                (adjustment to the detector distance reported by the
                facility).

            bin_size (int): size of each bin in pixels
        """
        self._num_of_bins = bins
        self._coffset = coffset
        self._bin_size = bin_size

    def convert_to_q(self, detector_distance, beam_energy, pixel_size):
        """
        Converts pixel-space radial bins to q-space radial_bins.

        Given a fixed number of radial bins, and a fixed size of each
        bin, computes the bin edges for specific detector distance
        and energy values.

        Args:

            detector_distance (float): detector distance in m.

            beam_energy (float): beam_energy in J.

            # TODO: Is this right?
            pixel_size (float): size of the pixel in m.

        Returns:

            ndarray: array of q values associated with each
            radius bin.
        """
        # TODO: Check the calculation. The units are now SI.
        lambda_ = (
            (scipy.constants.h * scipy.constants.c) /
            beam_energy
        )

        theta = 0.5 * np.arctan(
            (self._num_of_bins * self.dr * pixel_size) /
            (detector_distance + self._coffset)
        )

        return (
            4.0 * scipy.constants.pi *np.sin(theta) /
            lambda_
        )


class ProfileAveragingWithFilters:
    """
    Cumulative statisticse on radial profiles, with optional filtering.

    Algorithm to compute cumulative average and standard deviation for
    radial profiles. Optionally, several filtering criteria can be
    apply to the radial profiles being added to the calculation.
    """

    def __init__(
            self,
            num_profiles,
            sigma_threshold,
            min_radial_bin,
            max_radial_bin
    ):
        """
        Initializes ProfileAveragingWithFilters.

        TODO: Is this the place to put this information?
        Filter profiles based on user chosen filter. 
        In monitor.ini file:
            0 - std dev filter based off of average radial intensities
            1 - std dev filter based off of intensity of each bin in scaling region
            2 - No std dev filter, include all profiles

        Args: 

            num_profiles (int): number of profiles to use for the
                calculation of the cumulative statistics.

            sigma_threshold (float): standard deviation threshold for
                inclusion in the calculation.

            min_radial_bin (int): lowest bin of scaling region in the
                radial average.

            max_radial_bin (int): highest bin of scaling region in the
                radial average.
        """
        self._num_profiles = num_profiles
        self._sigma_threshold = sigma_threshold
        self._min_radial_bin = min_radial_bin
        self._max_radital_bin = max_radial_bin

        self._count = 0
        self._profiles_for_std_dev = None
        self._profiles_to_average = None
        self._profile_usage_map = numpy.zero(num_profiles, dtype=bool)


    def add_profile_with_avg_filtering(
            self,
            count_gui,
            count,
            count_cumulative,
            unscaled_radial_profile,
            sum_,
            radial,
            intensity_sum,
            std_dev_profiles,
            profiles_to_average
        ):
        """
        Add radial profile to average if it passes an avg-based filter.

        The radial profile is added to the average if its intensity
        falls within the prefefined number of standard devations from
        the average intensity.

        Args:

            TODO: Fix this comment.
            count_cumulative (ndarray): array of 0's and 1's, 1 indicated profile was used in cumualtive average

            unscaled_radial_profile (ndarray): unscaled radial profile
                (used for the standard deviation calculation).

            scaled_radial_profile (ndarray): added to the average if 
                the correspodning unscaled radial profile intensity sum
                is within the required standard deviation range.

            intensity_sum (float): sum of the radial intensities of the
                unscaled radial profile (used for standard deviation
                comparison).

            st_dev_profiles (ndarray): profiles to include in the
                calculation of the cumulative deviation calculation.

            profiles_to_average (ndarray): profiles to include in the
                calculation of the cumulative average.

            TODO: Fix this comment.

        Returns:

            count_cumulative (ndarray): updated array of 0's and 1's, 1 indicated profile was used in cumualtive average

            sum_ (ndarray): updated radial average on profiles_to_average

            std_dev_profiles (ndarray): updated stack of profiles to include in standard deviation calculation

            profiles_to_average (ndarray): updated stack of profiles to be used in average profile

            percent (float): percent of profiles included in radial average out of profiles_to_average
        """
        if self._count == 0:

            self._profiles_for_std_dev = numpy.zeros(
                (num_profiles,) + unscaled_radial_profile.shape()
            )
            self._profiles_for_std_dev[count, ...] = unscaled_radial_profile

            self._profiles_to_average = numpy.zeros(
                (num_profiles,) + unscaled_radial_profile.shape()
            )
            self._profiles_to_average[count, ...] = scaled_radial_profile
            sum_ = radial
            self._usage_map[0] = 1
            percent = 100.0
        elif self._count < self._num_profiles:
            std_dev_profiles[self._count, ...] = unscaled_radial_profile
            std_dev = np.std(np.nansum(std_dev_profiles[0:count,:], axis=1))
            intensity_sum_average = np.nanmean(np.nansum(std_dev_profiles[0:count,:], axis=1))
            if np.all(
                np.less_equal(
                    (intensity_sum_average - (self.n_sigma * std_dev)),intensity_sum
                    ) & np.less_equal(
                    intensity_sum, (intensity_sum_average + (self.n_sigma * std_dev))
                )
            ):
                profiles_to_average[count,:]=radial
                sum_ = np.mean(profiles_to_average[0:count,:], axis=0)
                count_cumulative = np.roll(count_cumulative,1)
                count_cumulative[0] = 1
                count_gui+=1
            else:
                count_cumulative = np.roll(count_cumulative,1)
                count_cumulative[0] = 0
            percent = np.count_nonzero(count_cumulative[0:count]) / (count+1) * 100.0
        else:
            std_dev_profiles = np.roll(std_dev_profiles, 1, axis=0)
            std_dev_profiles[0,:]=unscaled_radial_profile
            std_dev = np.std(np.nansum(std_dev_profiles, axis=1))
            intensity_sum_average = np.nanmean(np.nansum(std_dev_profiles, axis=1))
            if np.all(
                np.less_equal(
                    (intensity_sum_average - (self.n_sigma * std_dev)),intensity_sum
                    ) & np.less_equal(
                    intensity_sum, (intensity_sum_average + (self.n_sigma * std_dev))
                )
            ):
                profiles_to_average= np.roll(profiles_to_average, 1, axis=0)
                profiles_to_average[0]=radial
                sum_ = np.mean(profiles_to_average, axis=0)
                count_cumulative = np.roll(count_cumulative,1)
                count_cumulative[0] = 1
                count_gui+=1
            else:
                count_cumulative = np.roll(count_cumulative,1)
                count_cumulative[0] = 0
            percent = np.count_nonzero(count_cumulative) / self.num_profiles * 100.0

        return count_gui, count_cumulative, sum_, std_dev_profiles, profiles_to_average, percent



    def filter_by_bin_value(self, count_gui, count, count_cumulative, sum_, radial, std_dev_profiles, profiles_to_average):
        """Filters radial profiles based off std dev of bins defined in scale region
        include profiles which have all values within std dev
        inputs:
            count_gui (int) counter for gui, indication when gui should calculate cumulative radial profile

            count (int) used while less than number profiles so cumulative average, std dev, and percent do not use zeros

            count_cumulative (ndarray, int): array of 0's and 1's, 1 indicated profile was used in cumualtive average

            sum_ (ndarray[num_bins], float): current averaged profile, used for std dev comparison

            radial (ndarray, float): scaled radial profile, used in average if unscaled radial profile intensity sum is within std dev range

            std_dev_profiles (ndarray[num_profiles, num_bins], float): profiles to include in cumulative std dev calculation

            profiles_to_average	(ndarray[num_profiles, num_bins], float):profiles to include in	cumulative average

        Returns:

            TODO: Fix this comment.
            Tuple[ndarray, ndarray, ndarray, ndarray. float]: Tuple
            where the first element:

            count_cumulative (ndarray): updated array of 0's and 1's, 1 indicated profile was used in cumualtive average

            sum_ (ndarray): updated radial average on profiles_to_average

            std_dev_profiles (ndarray): updated stack of profiles to include in standard deviation calculation

            profiles_to_average (ndarray): updated stack of profiles to be used in average profile

            percent (float): percent of profiles included in radial average out of profiles_to_average
        """

        if count == 0:
            std_dev_profiles[count,:] = radial
            profiles_to_average[count,:] = radial
            sum_ = radial
            count_cumulative = np.roll(count_cumulative,1)
            count_cumulative[0] = 1
            count_gui+=1
            percent = 100.0
        elif count < self.num_profiles:
            std_dev_profiles[count, ...]=radial
            std_dev = np.std(std_dev_profiles[0:count,:], axis=0)
            average = np.mean(std_dev_profiles[0:count,:], axis = 0)
            if np.all(
                np.less_equal(
                    average[self.min_rbin:self.max_rbin] - (self.n_sigma *
                                                           std_dev[self.min_rbin:self.max_rbin]),
                    radial[self.min_rbin:self.max_rbin]
                    ) & np.less_equal(
                    radial[self.min_rbin:self.max_rbin],
                    average[self.min_rbin:self.max_rbin] + (self.n_sigma *
                                                           std_dev[self.min_rbin:self.max_rbin])
                )
            ):
                profiles_to_average[count,:]=radial
                sum_ = np.mean(profiles_to_average[0:count,:], axis=0)
                count_cumulative = np.roll(count_cumulative,1)
                count_cumulative[0] = 1
                count_gui+=1
            else:
                count_cumulative=np.roll(count_cumulative,1)
                count_cumulative[0] = 0
            percent = np.count_nonzero(count_cumulative[0:count]) / (count+1) * 100.0

        else:
            std_dev_profiles = np.roll(std_dev_profiles, 1, axis=0)
            std_dev_profiles[0,:]=radial
            std_dev = np.std(std_dev_profiles, axis=0)
            average = np.mean(std_dev_profiles, axis=0)
            if np.all(
                np.less_equal(
                    average[self.min_rbin:self.max_rbin] - (self.n_sigma *
                                                           std_dev[self.min_rbin:self.max_rbin]),
                    radial[self.min_rbin:self.max_rbin]
                    ) & np.less_equal(
                    radial[self.min_rbin:self.max_rbin],
                    average[self.min_rbin:self.max_rbin] + (self.n_sigma *
                                                           std_dev[self.min_rbin:self.max_rbin])
                )
            ):
                profiles_to_average= np.roll(profiles_to_average, 1, axis=0)
                profiles_to_average[0]=radial
                sum_ = np.mean(profiles_to_average, axis=0)
                count_cumulative=np.roll(count_cumulative,1)
                count_cumulative[0] = 1
                count_gui+=1
            else:
                count_cumulative=np.roll(count_cumulative,1)
                count_cumulative[0] = 0
            percent = np.count_nonzero(count_cumulative) / self.num_profiles * 100.0 

        return count_gui, count_cumulative, sum_, std_dev_profiles, profiles_to_average, percent


    def no_filter(self, count, count_cumulative, radial, profiles_to_average):
        """If user does not want filter, just averages profiles above intensity threshold
        Args:
            count (int) used while less than number profiles so cumulative average, std dev, and percent do not use zeros

            count_cumulative (ndarray, int): array of 0's and 1's, 1 indicated profile was used in cumulative average

            radial (ndarray, float): scaled radial profile, used in average if unscaled radial profile intensity sum is within std dev range

            profiles_to_average (ndarray[num_profiles, num_bins], float):profiles to include in cumulative average

        Returns:
            count_cumulative (ndarray): updated array of 0's and 1's, 1 indicated profile was used in cumualtive average

            sum_ (ndarray): updated radial average on profiles_to_average

            profiles_to_average (ndarray): updated stack of profiles to be used in average profile

            percent (float): percent of profiles included in radial average out of profiles_to_average
        """

        if count < self.num_profiles:
            profiles_to_average[count,:]=radial
            sum_ = np.mean(profiles_to_average[0:count,:], axis=0)
            count_cumulative = np.roll(count_cumulative,1)
            count_cumulative[0] = 1
            percent = np.count_nonzero(count_cumulative[0:count]) / (count+1) * 100.0
        else:
            profiles_to_average=np.roll(profiles_to_average, 1, axis=0)
            profiles_to_average[0,:]=radial
            sum_ = np.mean(profiles_to_average, axis=0)
            count_cumulative = np.roll(count_cumulative,1)
            count_cumulative[0] = 1
            percent = np.count_nonzero(count_cumulative) / self.num_profiles * 100.0

        return count_cumulative, sum_, profiles_to_average, percent

