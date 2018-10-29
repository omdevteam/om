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
#    Copyright ©
#
"""
Processing of SWAXS data.

Utilities for the processing of Small And Wide Angle X-Ray Scattering
data (radial pixel map calculation, radial profile scaling, etc.).
"""
from __future__ import absolute_import, division, print_function

import numpy
import scipy.constants, scipy.stats

from onda.utils import named_tuples


def pixel_bins_to_q_bins(
        detector_distance,
        beam_energy,
        pixel_size,
        pixel_radial_bins,
        coffset,
        radial_bin_size
):
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

        pixel_bins (array): array of pixel bins (e.g. np.arange(1000)).

        coffset (float) : detector distance's offset in meters
            (adjustment to the detector distance reported by the
            facility).

        radial_bin_size (float): size of each bin in pixels

    Returns:

        ndarray: array of q values associated with each
        radius bin in inverse angstroms.
    """

    # TODO: Check the calculation. The units are now SI.
    lambda_ = (
        (scipy.constants.h * scipy.constants.c) /
        beam_energy
    )

    theta = 0.5 * numpy.arctan(
        (pixel_radial_bins * radial_bin_size * pixel_size) /
        (detector_distance + coffset)
    )

    q_in_meters = (
        4.0 * scipy.constants.pi * numpy.sin(theta) /
        lambda_
    )
    
    q_in_angstroms = q_in_meters * 1.0e-10

    return q_in_angstroms


def calculate_radial_bin_info(radius_pixel_map, num_bins):
    """
    Calculates a radial bin pixel map.

    Calculates a pixel map containing radial bin information for each
    pixel.

       Args:

           pixelmap_radius (ndarray): radial pixel map.

           num_radial_bins (int): number of radial bins required by the
              user.

       Returns:

           RadialBinInfo: a named tuple with the radial bin info.
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

    return named_tuples.RadialBinInfo(
        radial_bin_pixel_map=radial_bin_pixel_map,
        radial_bin_size=deltar
    )


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

        ndarray: array with the  scaled radial intensity values.
    """
    scaling_region = radial_profile[min_radial_bin:max_radial_bin]
    average = numpy.abs(numpy.average(scaling_region))
    if average == 0:
        average = 1.0
    scaled_radial_profile = radial_profile / numpy.sum(radial_profile[min_radial_bin:max_radial_bin])
    return scaled_radial_profile


def calculate_avg_radial_intensity(data, radial_bin_pixel_map, mask):
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
    idx, counts = numpy.unique(radial_bin_pixel_map,return_counts=True)
    radial_average = scipy.ndimage.sum(
        data,
        labels=radial_bin_pixel_map,
        index=idx
    )
    #mask = numpy.ones(data.shape)
    #mask[data==0] = 0
    mask_radial = scipy.ndimage.sum(
        mask,
        labels=radial_bin_pixel_map,
        index=idx
    )
    radial_average /= mask_radial

    return numpy.nan_to_num(radial_average)

np = numpy

def mask_panel( panel, sub_sh=(32,32), thresh=7):
    """
    Make a mask for an AGIPD panel
    
    panel, np.array (128x512)
        an AGIPD panel whose slow-scan, fast-scan is 128, 512
    sub_sh, tuple, 
        divides the panel into chunks of this size
    thresh, float
        outlier threshold in units of pixel median
        (see is_outlier below)

    returns a mask array, 0 is bad, 1 is good 
    """

    subs = panel.reshape( (-1,32,32) )
    masks = np.zeros( subs.shape, np.bool)
    for i,s in enumerate(subs):
        m = ~is_outlier( s.ravel(), thresh).reshape(s.shape)
        masks[i] = m 
    return masks.reshape( panel.shape)


def is_outlier(points, thresh=3.5):
    """
    http://stackoverflow.com/a/22357811/2077270
    
    Returns a boolean array with True if points are outliers and False 
    otherwise.
    Parameters:
    -----------
        points : An numobservations by numdimensions array of observations
        thresh : The modified z-score to use as a threshold. Observations with
            a modified z-score (based on the median absolute deviation) greater
            than this value will be classified as outliers.
    Returns:
    --------
        mask : A numobservations-length boolean array.
    References:
    ----------
        Boris Iglewicz and David Hoaglin (1993), "Volume 16: How to Detect and
        Handle Outliers", The ASQC Basic References in Quality Control:
        Statistical Techniques, Edward F. Mykytka, Ph.D., Editor. 
    """
    if len(points.shape) == 1:
        points = points[:,None]
    median = np.median(points, axis=0)
    diff = np.sum((points-median)**2, axis=-1)
    diff = np.sqrt(diff)
    med_abs_deviation = np.median(diff)

    modified_z_score = 0.6745*diff / med_abs_deviation

    return modified_z_score > thresh
