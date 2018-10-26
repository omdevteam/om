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
import scipy.constants

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
        radius bin.
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

    return q_in_meters * 1.0e-10


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
    average = numpy.average(scaling_region)
    if average == 0:
        average = 1.0
    scaled_radial_profile = radial_profile / average
    return scaled_radial_profile


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
