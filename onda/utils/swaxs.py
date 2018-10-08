from __future__ import absolute_import, division, print_function

import numpy
import scipy.constants
#import h5py
import os.path
from numpy.fft import fft, ifft
from scipy.signal import argrelmax
from scipy.stats import mode
#import psana

def find_nearest_idx(array,value):
    """Return the index of the array item nearest to specified value"""
    return (numpy.abs(array-value)).argmin()

def calculate_radial_bin_pixel_map(radius_pixel_map, num_bins):
    """
    Calculates a radial bin pixel map.

    Calculates a pixel map containing radial bin information for each
    pixel.

       Args:

           pixelmap_radius (ndarray): radial pixel map.

           num_radial_bins (int): number of radial bins required by the
              user.

       Returns:

           Tuple[ndarray, int]: a tuple where the first entry is a
           pixel map storing, for each pixel, the radial bin to
           corresponding to the pixe, while second entry is the
           size (in pixels) of each radial bin.
    """
    radial_bin_pixel_map = numpy.zeros(radius_pixel_map.shape, dtype=int)

    deltar = float(numpy.max(radius_pixel_map)) / num_bins

    for i in range(0, num_bins - 1):
        radial_bin_pixel_map[
            (radius_pixel_map >= i * deltar) &
            (radius_pixel_map < (i + 1) * deltar)
        ] = i

        radial_bin_pixel_map[
            radius_pixel_map >= num_bins * deltar
        ] = num_bins

    return radial_bin_pixel_map, deltar


def scale_profile(radial_profile, min_radial_bin, max_radial_bin):
    """
    Scales a radial profile.

    The scaling is based on the average intensity value in the
    radial bin region specified by the user.

    Args:

        radial (ndarray): radial profile to scale

        min_radial_bin (int): Start bin number for the scaling region.

        max_radial_bin (int): End bin bumber for the scaling region.

    Returns:

        Tuple[ndarray, int]: a tuple where the first entry is the
        array with the  scaled radial intensity values, while the
        second entry in the factor that was used for the scaling.
    """
    scaling_region = radial_profile[min_radial_bin:max_radial_bin]
    average = numpy.average(scaling_region)
    if average == 0:
        average = 1.0
    scaled_radial_profile = radial_profile/ average
    return scaled_radial_profile, average


def calculate_avg_radial_intensity(data, radial_bin_pixel_map):
    """
    Calculates average radial intensities.

    The input data is split into radial bins according to the provided
    radius bin pixel map. An average intensity is then computed for
    each bin.

    Args:

        data (ndarray): frame data.

        radial_bin_pixel_map (ndarray): pixel map describing the radius
            bin each pixels falls into.

    Returns:

        ndarray: average intensity values for each radial bin.
    """
    radial_average = scipy.ndimage.mean(
        data,
        labels=radial_bin_pixel_map,
        index=numpy.unique(radial_bin_pixel_map)
    )

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

    sub_profile = numpy.interp(qbins, profile[:, 0], profile[:, 1], 0, 0)

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
    running_mean = numpy.convolve(I, numpy.ones((N,))/N, mode='same')
    factor = numpy.max(running_mean[300:700])
    #factor = numpy.max(running_mean[(q>scalerange[0])&(q<scalerange[1])])
    #factor = 1
    std = numpy.std(numpy.abs(((I[100:900]-running_mean[100:900])/factor)))
    #std = numpy.std(numpy.abs(((I[(q>stdrange[0])&(q<stdrange[1])]-running_mean[(q>stdrange[0])&(q<stdrange[1])])/factor)))
    return std


def time_tool_analysis(absorbance_trace_image):
    #time_delay_data_dict is python dictionary of each necessary time tool epics data
    #Currently named by epics variable
    #absorption_trace_image is whole image for laser timing


    my_fit = numpy.array([1.16085234e-07, 2.20888594e-03, -1.03396400e+00])
    TTA = scalg.timeToolAnalyzer()


    if absorbance_trace_image is None:
        print('Not getting trace')
        return None

    trace = absorbance_trace_image.astype(numpy.int32).sum(axis=0)
    result = TTA.analyze(trace)[0]


    ana_max, edge_pos, ana_mean, ana_std = result['max'], result['maxPix'], result['mean'], result['std']

    time_delay = numpy.polyval(my_fit, edge_pos)


    #print(time_delay)
    #Returning zero currently, comment line below out once you would like to test
    #time_delay=0

    return time_delay

