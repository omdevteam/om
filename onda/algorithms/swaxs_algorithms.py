"""
    This file is part of OnDA.

    OnDA is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    OnDA is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with OnDA.  If not, see <http://www.gnu.org/licenses/>.
    
    Added July 17, 2017
    Sarah Chamberlain, BS
    Thomas Grant, PhD
    BioXFEL, SUNY at Buffalo
"""


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import numpy as np
import scipy.constants
#import h5py
import os.path
from numpy.fft import fft, ifft
from scipy.signal import argrelmax
from scipy.stats import mode
#import psana

###################################
# PIXEL SPACE / QSPACE CONVERSION #
###################################

class PixelSpaceQSpaceConversion:
    """Pixel space to q-space conversion.

    Implements conversion between pixel space and q-space.
    """
    
    def __init__(self, bins, coffset, dr):
        """ Initializes the QSpace bin calculator algorithm.
            
         Args:

            num_of_bins (int): number of pixel bins
            
            coffset (float) : detector distance's offset (coffset)

            dr (int): size of each bin in pixels
        """

        self.nbins = bins
        self.coffset = coffset
        self.dr = dr



        self.hc = scipy.constants.h * scipy.constants.c
        self.fourpi = 4 * scipy.constants.pi

    def convert_to_q(self, detector_distance, beam_energy, pixel_size):
        """QSpace bin conversion
            
        Calculates bins in QSpace associated with bins in pixel space

        Args:

            detector_distance (float): detector distance

            beam_energy (float): beam_energy

        Returns:

            qbins (numpy.ndarray float): array of q values associated with each radius bin
        """


        lambda_ = self.hc /(scipy.constants.e * beam_energy)

        theta = 0.5 * np.arctan(
            (self.nbins * self.dr * pixel_size) / (detector_distance * 10e-4 + self.coffset)
            )
        
        qbins = self.fourpi * np.sin(theta)/(lambda_/10e-11)


        return qbins


class FilterandMeanProfiles:
    """Standard deviation filters for radial profile averaging
    """

    def __init__(self, num_profiles, n_sigma, min_rbin, max_rbin):
        """Initializes filters

        Filter profiles based on user chosen filter. 
        In monitor.ini file:
            0 - std dev filter based off of average radial intensities
            1 - std dev filter based off of intensity of each bin in scaling region
            2 - No std dev filter, include all profiles

        Args: 
           num_profiles (int): number of profiles for running average and running std dev.

           n_sigma (float): number of std dev to include

           min_rbin (int): lowest bin of scaling region

           max_rbin (int): highest bin of scaling region

        """

        self.num_profiles=num_profiles
        self.n_sigma = n_sigma
        self.min_rbin = min_rbin
        self.max_rbin = max_rbin



    def filter_avg_intensity(self, count_gui, count, count_cumulative, unscaled_radial_profile, sum_, radial, intensity_sum, std_dev_profiles, profiles_to_average):
        """Filters radial profiles based off std dev of average intensities
        include profiles with intensity within N std_dev of average intensity

        Args:
            count_gui (int): counter for gui, indication when gui should calculate cumulative radial profile

            count (int): used while less than number profiles so cumulative average, std dev, and percent do not use zeros

            count_cumulative (ndarray): array of 0's and 1's, 1 indicated profile was used in cumualtive average

            unscaled_radial_profile (ndarray): unscaled radial profile for std dev calculation

            radial (ndarray): scaled radial profile, used in average if unscaled radial profile intensity sum is within std dev range

            intensity_sum (float): sum of radial intensities of unscaled radial profile, used for std dev comparison

            std_dev_profiles (ndarray): profiles to include in cumulative std dev calculation

            profiles_to_average (ndarray):profiles to include in cumulative average

        Returns:
            count_gui (int): +=1 if included in radial stack

            count_cumulative (ndarray): updated array of 0's and 1's, 1 indicated profile was used in cumualtive average

            sum_ (ndarray): updated radial average on profiles_to_average

            std_dev_profiles (ndarray): updated stack of profiles to include in standard deviation calculation

            profiles_to_average (ndarray): updated stack of profiles to be used in average profile

            percent (float): percent of profiles included in radial average out of profiles_to_average
            """

        if count == 0:
            std_dev_profiles[count,:]=unscaled_radial_profile
            profiles_to_average[count,:]=radial
            sum_ = radial
            count_cumulative = np.roll(count_cumulative,1)
            count_cumulative[0] = 1
            count_gui+=1
            percent = 100.0
        elif count < self.num_profiles:
            std_dev_profiles[count,:]=unscaled_radial_profile
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
            count_gui (int): +=1 if included in radial stack

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
            std_dev_profiles[count,:]=radial
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



class OfflineDataAnalysis:
    """Used when run offline
        Will run standard deviation filter on all of data
        saves results to hdf5 file"""

    def __init__(self, num_bins, pump_laser_evr_code, n_sigma, threshold, min_rbin, max_rbin, user_defined_variables):
        """Initializes OffDA
        Args:
            num_bins (int): number of bins in a profile

            pump_laser_evr_code (int): evr code for pump probe experiment, None if mixing experiment

            n_sigma (float): number of std deviations to include for filters

            threshold (float): minimum sum for intensities in unscaled radial profile 

            min_rbin (int): minimum bin in scaling region

            max_rbin (int): maximum bin in scaling region

            user_defined_variables (dict): user defined variables to save to HDF5 file, input in monitor.ini file 
                                           (e.g. 'run':100)
        """

        self.num_bins = num_bins
        self.evr_code = pump_laser_evr_code
        self.n_sigma = n_sigma
        self.threshold = threshold
        self.min_rbin = min_rbin
        self.max_rbin = max_rbin
        self.data_dict = user_defined_variables


    def std_dev_intensity(self, profiles):
        """
        Calculates Standard deviation of sum of intensities on all profiles
        To be used for data filter

        Args:
            profiles (ndarray): Array of all profiles from run to calculate std dev on sum of intensities
                                If pump/probe experiemnt, dark and pumped run seperate

        Returns:
            std_dev_i (float): std deviation of sum of intensities

            intensity_sum_average (float): Average intensity of all profiles
 
        """

        std_dev_i = np.std(np.nansum(profiles, axis = 1))
        intensity_sum_average = np.nanmean(np.nansum(profiles, axis=1))

        return std_dev_i, intensity_sum_average


    def std_dev_bin_value(self, profiles):
        """
        Calculates Standard deviation of intensities in each bin, on all profiles
        To be used for data filter

        Args:
            profiles (ndarray): Array of all profiles from run to calculate std dev on bin intensity value
                                If pump/probe experiemnt, dark and pumped run seperate

        Returns:
            std_dev_bins (ndarray): std dev of intensity value of each bin of profile
        """

        std_dev_bins = np.std(profiles, axis = 0)

        return std_dev_bins

    def filter_avg_intensity(self, unscaled_profiles, std_dev, intensity_sum_average):
        """Filters radial profiles by threshold value (sum of radial intensity below threshold rejected)
        and  std dev of average intensities
        include profiles with intensity within N std_dev of average intensity

        Args:

            unscaled_profiles (ndarray): array of all unscaled profiles from run

            std_dev (float): Std Dev. of sum of intensities

            intensity_sum_average (float): average intensity of all profiles

        Returns:
            accept (ndarray): Boolean array, True indicates profile of that index is to 
                                be included in cumulative radial average
        """

        accept=np.nanmean(profiles, axis = 0)
        intensity_sum = np.nansum(unscaled_profiles, axis = 1)
        for x in range(0,len(unscaled_profiles[:,0])):
            if np.all(
                np.less_equal(
                    (intensity_sum_average - (self.n_sigma * std_dev)),intensity_sum[x]
                    ) & np.less_equal(
                    intensity_sum[x], (intensity_sum_average + (self.n_sigma * std_dev))
                    ) & np.greater_equal(intensity_sum[x], self.threshold)
            ):
                accept[x] = 1
        return accept


    def filter_bin_value(self, profiles, unscaled_profiles, std_dev):
        """Filters radial profiles by threshold (sum of radial intensity below threshold rejected)
        and std dev of each bin in scaling region of radial profile, 
        accepted = True for profiles at that index with all bins in scaling region 
        within N std dev of average bin value

        Args:

            unscaled_profiles (ndarray): array of all unscaled profiles from run

            profiles (ndarray): array of all scaled profiles from run 

            std_dev (ndarray): Std Dev for each bin of profile

         Returns:
            accept (ndarray): Boolean array, True indicates profile of that index is to 
                                be included in cumulative radial average
        """
        accept=np.zeros(len(profiles[:,0]), dtype = bool)

        sum_ = np.nanmean(profiles, axis = 0)
        intensity = np.nansum(unscaled_profiles, axis = 1)
        for x in range(0,len(profiles[:,0])):
            if np.all(
                np.less_equal(
                    sum_[self.min_rbin:self.max_rbin] - (self.n_sigma *
                                               std_dev[self.min_rbin:self.max_rbin]),
                    profiles[x,self.min_rbin:self.max_rbin]
                    ) & np.less_equal(
                    profiles[x,self.min_rbin:self.max_rbin],
                    sum_[self.min_rbin:self.max_rbin] + (self.n_sigma *
                                               std_dev[self.min_rbin:self.max_rbin]))
                    & np.greater_equal(intensity[x], self.threshold)
            ):
                accept[x]=True
        return accept


    def no_filter(self, unscaled_profiles):
        """Only rejects profiles of sum of intensities falls below threshold value

        Args:

            unscaled_profiles (ndarray): All unscaled radial profiles from run

        Returns:

            accept (ndarray): True if profile with cooresponding index passed threshold test

        """
        accept=np.zeros(len(profiles[:,0]), dtype = bool)

        intensity = np.nansum(unscaled_profiles, axis = 1)
        for x in range(0,len(unscaled_profiles[:,0])):
            if np.greater_equal(intensity[x], self.threshold):
                accept[x] = 1

        return accept


    def average_profiles(self, profiles):
        """Averaged radial profiles

        Args:
            profiles (ndarray): All scaled profiles where accepted == True (in processing layer)

        Returns:
            average radial profile

        """
        
        return np.nanmean(profiles, axis = 0)



    def hdf5_write(self, filename, profiles_unscaled, qbins, profiles_scaled, scale_factor, is_pumped, accepted, sum_, num_events_in_run, sub_profile, xtc_time_delay, xtc_data_names, xtc_data, timetool_time_delay, timestamp, timestamp_floats):
        """Function writes raw and analyzed data to hdf5 file
        Args: 
            unscaled_radial_profile (ndarray): all unscaled radial profiles from run

            scaled_profile (ndarray): all scaled radial profiles from run

            scale_factor (ndarray): scale value of each profile (1 for all if scaled=False in monitor.ini)

            pump_laser_on (ndarray): 0 for dark, 1 for pumped, None if not pump-probe experiment

            accepted (ndarray): 0 if not included in average, 1 if included in average

            sum_ (ndarray): Averaged radial profile for mixing experiment, averaged difference profile for pump-probe

            num_events_in_run (int): Number of events found in run

            sub_profile (ndarray or None): None if no profile given in monitor.ini
                                           if not none, qbins and intensities of radial profile subtracted from scaled profiles"""


        if os.path.exists(filename+'.h5'):
            #append stuff here
            f = h5py.File(filename+'.h5', "a")
            data = f["data"]
            length = data["accepted"].shape[0]

            data["qbins"].resize((length+1000, self.num_bins))
            data["qbins"][-1000:, :] = qbins[-1000:, :]
            data["profiles_unscaled"].resize((length+1000, self.num_bins))
            data["profiles_unscaled"][-1000:, :]=profiles_unscaled[-1000:, :]
            data["profiles_scaled"].resize((length+1000, self.num_bins))
            data["profiles_scaled"][-1000:, :]=profiles_scaled[-1000:, :]
            data["scale_factor"].resize((length+1000, 1))
            data["scale_factor"][-1000:,0]=scale_factor[-1000:]
            data["is_pumped"].resize((length+1000, 1))
            data["is_pumped"][-1000:,0]=is_pumped[-1000:]
            data["accepted"].resize((length+1000, 1))
            data["accepted"][-1000:,0]=accepted[-1000:]
            data["timestamp"].resize((length+1000, 1))
            data["timestamp"][-1000:,0]=timestamp[-1000:]
            data["timestamp_floats"].resize((length+1000, 1))
            data["timestamp_floats"][-1000:,0]=timestamp_floats[-1000:]
            if np.count_nonzero(is_pumped) > 0:
                del data["cumulative_average_difference"]
                data.create_dataset("cumulative_average_difference", (1, self.num_bins), maxshape=(1, self.num_bins), data=sum_)
                dark = np.nanmean(profiles_scaled[(is_pumped==False) & (accepted==True)], axis = 0)
                pumped = np.nanmean(profiles_scaled[(is_pumped==True) & (accepted==True)], axis = 0)
                del data["cumulative_average_pumped"]
                data.create_dataset("cumulative_average_pumped", (1, self.num_bins), maxshape=(None, self.num_bins), data=pumped)
                del data["cumulative_average_dark"]
                data.create_dataset("cumulative_average_dark", (1, self.num_bins), maxshape=(None, self.num_bins), data=dark)
                data["xtc_time_delay"].resize((length+1000, 1))
                data["xtc_time_delay"][-1000:,0]=xtc_time_delay[-1000:]
                data["timetool_time_delay"].resize((length+1000, 1))
                data["timetool_time_delay"][-1000:,0]=timetool_time_delay[-1000:]
            else:
                del data["cumulative_average"]
                data.create_dataset("cumulative_average", (1, self.num_bins), maxshape=(1, self.num_bins), data=sum_)
            for keys in self.data_dict.keys():
                data[keys].resize((length+1000, 1))
                user_defined_info = np.full((1000),self.data_dict[keys])
                data[keys][-1000:,0] = user_defined_info
            k=0
            for name in xtc_data_names:
                data[name].resize((length+1000, 1))
                data[name][-1000:,0]=xtc_data[-1000:,k]
                k+=1

            

        else:
            f = h5py.File(filename+'.h5', "w")
    	

            data = f.create_group("data")
            data.create_dataset("qbins",(len(scale_factor), self.num_bins), maxshape=(None, self.num_bins), data=qbins)
            data.create_dataset("profiles_unscaled",(len(scale_factor), self.num_bins), maxshape=(None, self.num_bins), data=profiles_unscaled)
            data.create_dataset("profiles_scaled", (len(scale_factor), self.num_bins), maxshape=(None, self.num_bins), data=profiles_scaled)
            data.create_dataset("scale_factor", (len(scale_factor),1), maxshape=(None, 1), data=scale_factor)
            data.create_dataset("is_pumped", (len(scale_factor),1), maxshape=(None, 1), data=is_pumped)
            data.create_dataset("accepted", (len(scale_factor),1), maxshape=(None, 1), data=accepted)
            data.create_dataset("timestamp", (len(scale_factor),1), maxshape=(None, 1), data=timestamp)
            data.create_dataset("timestamp_floats", (len(scale_factor),1), maxshape=(None, 1), data=timestamp_floats)
            if np.count_nonzero(is_pumped) > 0:
                data.create_dataset("cumulative_average_difference", (1, self.num_bins), maxshape=(1, self.num_bins), data=sum_)
                dark = np.nanmean(profiles_scaled[(is_pumped==False) & (accepted==True)], axis = 0)
                pumped = np.nanmean(profiles_scaled[(is_pumped==True) & (accepted==True)], axis = 0)
                data.create_dataset("cumulative_average_pumped", (1, self.num_bins), maxshape=(None, self.num_bins), data=pumped)
                data.create_dataset("cumulative_average_dark", (1, self.num_bins), maxshape=(None, self.num_bins), data=dark)
                data.create_dataset("xtc_time_delay", (len(scale_factor),1), maxshape=(None, 1), data=xtc_time_delay)
                data.create_dataset("timetool_time_delay", (len(scale_factor),1), maxshape=(None, 1), data=timetool_time_delay)
            else:
                data.create_dataset("cumulative_average", (1, self.num_bins), maxshape=(1, self.num_bins), data=sum_)
            if sub_profile is not None:
                data.create_dataset("profile_subtracted", (2, self.num_bins), maxshape=(2, self.num_bins), data=sub_profile)
            for keys in self.data_dict.keys():
                user_defined_info = np.full((len(is_pumped)),self.data_dict[keys])
                data.create_dataset(keys, (len(scale_factor),1), maxshape=(None, 1), data = user_defined_info)
            k=0
            for name in xtc_data_names:
                data.create_dataset(name, (len(scale_factor),1), maxshape=(None, 1), data = xtc_data[:,k])
                k+=1
        f.close()


        return


class timeToolAnalyzer:

    def __init__(
            self,
            my_fit = np.array([1.16085234e-07, 2.20888594e-03, -1.03396400e+00]),
            referenceCount=0,
            nReferences=100,
            references=None,
            validReferences=None,
            meanReference=None,
            kernel=None,
            kernelWidth=50,
            kernelGap=5,
            N=None):

        self.referenceCount = referenceCount
        self.nReferences = nReferences
        self.validReferences = validReferences
        self.references = references
        self.meanReference = meanReference
        self.kernel = kernel
        self.kernelWidth = kernelWidth
        self.kernelGap = kernelGap
        self.N = N
        if my_fit is not None:
            self.a, self.b, self.c = my_fit
        else:
            self.a = self.b = self.c = None

    def addReference(self, ref):

        if ref is None:
            return True
        i = self.referenceCount % self.nReferences
        if self.references is None:
            self.N = len(ref)
            self.makeKernel()
            self.validReferences = np.zeros([self.nReferences], dtype=np.int)
            self.references = np.zeros([self.nReferences, self.N])
        self.references[i, :] = ref
        self.validReferences[i] = 1
        self.referenceCount += 1
        return False

    def getMeanReference(self):

        if self.referenceCount == 0:
            return None
        return np.mean(self.references, axis=0)

    def getMeanReferencePowerSpectrum(self):

        return np.mean(np.abs(self.referenceFFTs)**2, axis=0)

    def makeKernel(self):

        self.kernel = np.zeros(self.N)
        self.kernel[self.kernelGap:self.kernelWidth] = 1.0 / \
            (self.kernelWidth - self.kernelGap)
        self.kernel += -1 * self.kernel[::-1]
        self.kernelftc = np.conjugate(fft(self.kernel))

    def pixel2seconds(self, pixel):
        assert(self.A is not None)
        return self.a + self.b * pixel + self.c * pixel**2

    def analyze(self, spec):

        s = spec - np.mean(spec)
        b = self.getMeanReference()
        if b is None:
            b = np.zeros(s.shape)
            # Since we couldn't make the kernel from a reference spectrum...
            self.N = len(s)
            self.makeKernel()
        else:
            b = b.copy()
            b -= np.mean(b)
            b *= np.std(s) / np.std(b)
        c = np.real(ifft(fft(s - b) * self.kernelftc))
        c[0:self.kernelWidth] = 0
        c[-self.kernelWidth:] = 0
        cMaxPix = c.argmax()
        cMax = c.flat[cMaxPix]
        cMean = np.mean(c[self.kernelWidth:-self.kernelWidth])
        cStd = np.std(c[self.kernelWidth:-self.kernelWidth])
        result = {"maxPix": cMaxPix, "max": cMax, "mean": cMean, "std": cStd}

        return result, c, s, b

def find_nearest_idx(array,value):
    """Return the index of the array item nearest to specified value"""
    return (np.abs(array-value)).argmin()

def calculate_rbins(pixelmap_radius, nbins):
    """Calculates radius bin pixel map

    Calculates a pixelmap containing radius bin labels for each pixel

        Args:

            pixelmap_radius (numpy.ndarray): pixel map containing absolute radius value for each pixel

            nbins (int): number if bins required by the user

        Returns:

            rpixbins (numpy.ndarray int): array of labels cooresponding to each value in pixelmap_radius
            for radial intensity function

            dr (int): size in pixels of each bin
     """

    rpixbins = np.zeros(pixelmap_radius.shape, dtype=int)

    dr = float(np.max(pixelmap_radius)) / nbins

    for i in range(0, nbins - 1):
        rpixbins[(pixelmap_radius >= i * dr) & (pixelmap_radius < (i + 1) * dr)] = i
        rpixbins[pixelmap_radius >= nbins * dr] = nbins

    return rpixbins, dr


def scale_profile(radial_int, min_rpixbin, max_rpixbin, scale):
    """Scales a radial profile

    Scales a radial profile based on the average intensity value in a region defined by user

    Args:

       radial_int (numpy.ndarray): radial profile of intensities to scale

       min_rpixbin (int): Minimum bin number for scaling region, readi in from monitor params

       max_rpixbin (int): Maximum bin number for scaling region, readi in from monitor params

    Returns:

        self.radial_int_new (numpy.ndarray): array of intensity values scaled using the region specified by the user
    
    self.scale_factor (int): value used to scale array
    """

    region_int = radial_int[min_rpixbin:max_rpixbin]
    if scale is True:
        average = np.average(region_int)
        if average == 0: average = 1.0
    else:
        average = 1.0
    radial_int_new = radial_int / average
    return radial_int_new, average


def calculate_average_radial_intensity(img, rpixbins):
    """Calculates average radial intensities.

    Calculates radial average of input data. Input data is subdivided into radius bins according to a radius bin pixel
    map. An average intensity is then computed for each radius bin.

    Args:

        img (ndarray): raw image

        rpixbins (ndarray): pixel map describing the radius bin each pixels falls into

    Returns:

        radial_average (ndarray): average intensity values for each radius bin
    """

    radial_average = scipy.ndimage.mean(img, labels=rpixbins, index=np.unique(rpixbins))  #arange(0, rpixbins.max()))

    return radial_average


def interpolate_radial_profile(profile, qbins):
    """Loads a radial profile and interpolates to a different number of radius bins.

    Loads a radial profile from a text file and interpolates intensity values if the required number of radius bins
    differs from the one in the file.

    Args:

        fnam (str): name of the file which contains the radial profile.

        num_of_bins (int): required number of radius bins.

    Returns:

        interpolated_profile (array-like): profile to be subtracted from radial average profiles.
    """

    sub_profile = np.interp(qbins, profile[:, 0], profile[:, 1], 0, 0)

    return sub_profile


def std_profile(q,I,scalerange=(2.0,3.0),stdrange=(0.5,3.0)):
    """Calculate the standard deviation of residuals about the mean of a scattering profile

    Args:

        q (ndarray): q-values for each profile

        I (ndarray): averaged radial profile of images

        scalerange (tuple): q-values of scaling range for factor determination

        stdrange (tuple): q-values of region to calculate residuals/noise

    Returns:

        std (float): Average standard deviation of residuals about the average radial profile
    """

    N=5 #window size for running average
    running_mean = np.convolve(I, np.ones((N,))/N, mode='same')
    factor = np.max(running_mean[300:700])
    #factor = np.max(running_mean[(q>scalerange[0])&(q<scalerange[1])])
    #factor = 1
    std = np.std(np.abs(((I[100:900]-running_mean[100:900])/factor)))
    #std = np.std(np.abs(((I[(q>stdrange[0])&(q<stdrange[1])]-running_mean[(q>stdrange[0])&(q<stdrange[1])])/factor)))
    return std


def time_tool_analysis(absorbance_trace_image):
    #time_delay_data_dict is python dictionary of each necessary time tool epics data
    #Currently named by epics variable
    #absorption_trace_image is whole image for laser timing


    my_fit = np.array([1.16085234e-07, 2.20888594e-03, -1.03396400e+00])
    TTA = scalg.timeToolAnalyzer()


    if absorbance_trace_image is None:
        print('Not getting trace')
        return None

    trace = absorbance_trace_image.astype(np.int32).sum(axis=0)
    result = TTA.analyze(trace)[0]


    ana_max, edge_pos, ana_mean, ana_std = result['max'], result['maxPix'], result['mean'], result['std']

    time_delay = np.polyval(my_fit, edge_pos)


    #print(time_delay)
    #Returning zero currently, comment line below out once you would like to test
    #time_delay=0

    return time_delay

