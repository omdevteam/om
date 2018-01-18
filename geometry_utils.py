#    This file is part of cfelpyutils.
#
#    cfelpyutils is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    cfelpyutils is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with cfelpyutils.  If not, see <http://www.gnu.org/licenses/>.
"""
Utilities for CrystFEL-style geometry files.

This module contains utilities for the processing of CrystFEL-style geometry
files.
"""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import collections

import numpy


PixelMaps = collections.namedtuple('PixelMaps', ['x', 'y', 'r'])
ImageShape = collections.namedtuple('ImageShape', ['ss', 'fs'])


def compute_pixel_maps(geometry):
    """Create pixel maps from a CrystFEL geometry object.

    Compute pixel maps from a CrystFEL-style geometry object (A dictionary
    returned by the load_crystfel_geometry function from the crystfel_utils
    module). The pixel maps can be used to create a representation of
    the physical layout of the geometry, keeping the origin of the reference
    system at the beam interaction point.

    Args:

        geometry (dict): A CrystFEL geometry object (A dictionary returned by
            the load_crystfel_geometry function from the crystfel_utils
            module).

    Returns:

        tuple: a tuple containing three float32 numpy arrays ('slab'-like pixel
            maps) with respectively x, y coordinates of the data pixels and
            distance of each pixel from the center of the reference system.
    """

    # Determine the max fs and ss in the geometry object.
    max_slab_fs = numpy.array(
        [geometry['panels'][k]['max_fs'] for k in geometry['panels']]
    ).max()

    max_slab_ss = numpy.array(
        [geometry['panels'][k]['max_ss'] for k in geometry['panels']]
    ).max()

    # Create the empty arrays that will contain the pixel maps.
    x_map = numpy.zeros(
        shape=(max_slab_ss + 1, max_slab_fs + 1),
        dtype=numpy.float32
    )
    y_map = numpy.zeros(
        shape=(max_slab_ss + 1, max_slab_fs + 1),
        dtype=numpy.float32
    )

    # Iterate over the panels.
    for pan in geometry['panels']:

        # Determine the pixel coordinates for the current panel.
        i, j = numpy.meshgrid(
            numpy.arange(
                geometry['panels'][pan]['max_ss'] -
                geometry['panels'][pan]['min_ss'] +
                1
            ),
            numpy.arange(
                geometry['panels'][pan]['max_fs'] -
                geometry['panels'][pan]['min_fs'] +
                1
            ),
            indexing='ij'
        )

        # Compute the x,y vectors, using complex notation.
        d_x = (
            geometry['panels'][pan]['fsy'] +
            1J * geometry['panels'][pan]['fsx']
        )
        d_y = (
            geometry['panels'][pan]['ssy'] +
            1J * geometry['panels'][pan]['ssx']
        )
        r_0 = (
            geometry['panels'][pan]['cny'] +
            1J * geometry['panels'][pan]['cnx']
        )

        cmplx = i * d_y + j * d_x + r_0

        # Fill maps that will be returned with the computed
        # values (x and y maps).
        y_map[
            geometry['panels'][pan]['min_ss']:
            geometry['panels'][pan]['max_ss'] + 1,
            geometry['panels'][pan]['min_fs']:
            geometry['panels'][pan]['max_fs'] + 1
        ] = cmplx.real

        x_map[
            geometry['panels'][pan]['min_ss']:
            geometry['panels'][pan]['max_ss'] + 1,
            geometry['panels'][pan]['min_fs']:
            geometry['panels'][pan]['max_fs'] + 1
        ] = cmplx.imag

    # Compute the values for the radius pixel maps that will be returned.
    r_map = numpy.sqrt(numpy.square(x_map) + numpy.square(y_map))

    # Return the pixel maps as a tuple.
    return PixelMaps(x_map, y_map, r_map)


def apply_pixel_maps(data_as_slab, pixel_maps, output_array=None):
    """Apply geometry in pixel map format to the input data.

    Applies geometry, described by pixel maps, to input data in 'slab' format.
    Turns a 2d array of pixel values into an array containing a representation
    of the physical layout of the geometry, keeping the origin of the reference
    system at the beam interaction point.

    Args:

        data_as_slab (ndarray): the pixel values on which to apply the
            geometry, in 'slab' format.

        pixel_maps (tuple): pixel maps, as returned by the
            compute_pixel_maps function in this module.

        output_array (Optional[numpy.ndarray]): array to hold the output.
            If the array is not provided, one will be generated automatically.
            Defaults to None (No array provided).

    Returns:

        ndarray: Array with the same dtype as the input data containing a
            representation of the physical layout of the geometry (i.e.: the
            geometry information applied to the input data).
    """

    # If no array was provided, generate one.
    if output_array is None:
        output_array = numpy.zeros(
            shape=data_as_slab.shape,
            dtype=data_as_slab.dtype
        )

    # Apply the pixel map geometry to the data.
    output_array[pixel_maps.y, pixel_maps.x] = data_as_slab.ravel()

    # Return the output array.
    return output_array


def compute_minimum_image_size(pixel_maps):
    """
    Compute the minimum size of an image that can represent the geometry.

    Compute the minimum size of an image that can contain a
    representation of the geometry described by the pixel maps, assuming
    that the image is center at the center of the reference system.

    Args:

        pixel_maps (tuple): pixel maps, as returned by the
        compute_pixel_maps function in this module.

    Returns:

        tuple: numpy shape object describing the minimum image size.
    """

    # Recover the x and y pixel maps.
    x_map, y_map = pixel_maps.x, pixel_maps.x.y

    # Find the largest absolute values of x and y in the maps.
    y_largest = 2 * int(max(abs(y_map.max()), abs(y_map.min()))) + 2
    x_largest = 2 * int(max(abs(x_map.max()), abs(x_map.min()))) + 2

    # Return a tuple with the computed shape.
    return ImageShape(y_largest, x_largest)


def adjust_pixel_maps_for_pyqtgraph(pixel_maps):
    """
    Adjust pixel maps for visualization of the data in a pyqtgraph widget.

    Adjust the pixel maps for use in a Pyqtgraph's ImageView widget.
    Essentially, the origin of the reference system is moved to the
    top-left of the image.

    Args:

        pixel_maps (tuple): pixel maps, as returned by the
            compute_pixel_maps function in this module.

    Returns:

        tuple: a three-element tuple containing two float32 numpy arrays
            ('slab'-like pixel maps) with respectively x, y coordinates of the
            data pixels as the first two elements, and None as the third.
    """

    # Compute the minimum image shape needed to represent the coordinates
    min_ss, min_fs = compute_minimum_image_size(pixel_maps)

    # convert y x values to i j values
    i = numpy.array(pixel_maps.y, dtype=numpy.int) + min_ss // 2 - 1
    j = numpy.array(pixel_maps.x, dtype=numpy.int) + min_fs // 2 - 1

    y_map = i.flatten()
    x_map = j.flatten()

    return PixelMaps(x_map, y_map, None)
