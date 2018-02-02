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
Geometry utilities.

Functions that load, manipulate and apply geometry information to detector
pixel data.
"""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import collections

import numpy


PixelMaps = collections.namedtuple('PixelMaps', ['x', 'y', 'r'])
'''
A namedtuple used for pixel maps objects.

Pixel maps are arrays of the same shape of the data whose geometry they
describe. Each cell in the array holds the coordinate, in the reference system
of the physical detector, of the corresponding pixel in the data array.

The first two fields store the pixel maps for the x coordinate
and the y coordinate respectively. The third field is instead a pixel map
storing the distance of each pixel in the data array from the center of the
reference system.
'''


def compute_pixel_maps(geometry):
    """Compute pixel maps from a CrystFEL geometry object.

    Take as input a CrystFEL-style geometry object (A dictionary
    returned by the function load_crystfel_geometry function in the
    crystfel_utils module) and return a PixelMap tuple . The origin
    the reference system used by the pixel maps is set at the beam interaction
    point.

    Args:

        geometry (dict): A CrystFEL geometry object (A dictionary returned by
            the :obj:`cfelpyutils.crystfel_utils.load_crystfel_geometry`
            function).

    Returns:

        PixelMaps: a PixelMaps tuple.
    """

    # Determine the max fs and ss in the geometry object.
    max_slab_fs = numpy.array(
        [geometry['panels'][k]['max_fs'] for k in geometry['panels']]
    ).max()

    max_slab_ss = numpy.array(
        [geometry['panels'][k]['max_ss'] for k in geometry['panels']]
    ).max()

    # Create the empty arrays that will store the pixel maps.
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

        # Determine the pixel indexes for the current panel.
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

        # Compute the x,y vectors, using the complex notation.
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

        # Compute values for the x and y maps.
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

    # Compute the values for the radius pixel map.
    r_map = numpy.sqrt(numpy.square(x_map) + numpy.square(y_map))

    # Return the pixel maps as a tuple.
    return PixelMaps(x_map, y_map, r_map)


def apply_pixel_maps(data, pixel_maps, output_array=None):
    """Apply geometry in pixel map format to the input data.

    Turn an array of detector pixel values into an array
    containing a representation of the physical layout of the detector.

    Args:

        data (ndarray): array containing the data on which the geometry
            will be applied.

        pixel_maps (PixelMaps): a pixelmap tuple, as returned by the
            :obj:`compute_pixel_maps` function in this module.

        output_array (Optional[ndarray]): a preallocated array (of dtype
            numpy.float32) to store the function output. If provided, this
            array will be filled by the function and returned to the user.
            If not provided, the function will create a new array
            automatically and return it to the user. Defaults to None
            (No array provided).

    Returns:

        ndarray: a numpy.float32 array containing the geometry information
        applied to the input data (i.e.: a physical representation of the
        layout of the detector).
    """

    # If no output array was provided, create one.
    if output_array is None:
        output_array = numpy.zeros(
            shape=data.shape,
            dtype=numpy.float32
        )

    # Apply the pixel map geometry information the data.
    output_array[pixel_maps.y, pixel_maps.x] = data.ravel()

    # Return the output array.
    return output_array


def compute_minimum_array_size(pixel_maps):
    """
    Compute the minimum size of an array that can store the applied geometry.

    Return the minimum size of an array that can store data on which the
    geometry information described by the pixel maps has been applied.

    The returned array shape is big enough to display all the input pixel
    values in the reference system of the physical detector. The array is
    supposed to be centered at the center of the reference system of the
    detector (i.e: the beam interaction point).

    Args:

        pixel_maps (PixelMaps): a PixelMaps tuple, as returned by the
            :obj:`compute_pixel_maps` function in this module.

    Returns:

        tuple: numpy shape-like tuple storing the minimum array size.
    """

    # Recover the x and y pixel maps.
    x_map, y_map = pixel_maps.x, pixel_maps.x.y

    # Find the largest absolute values of x and y in the maps.
    y_largest = 2 * int(max(abs(y_map.max()), abs(y_map.min()))) + 2
    x_largest = 2 * int(max(abs(x_map.max()), abs(x_map.min()))) + 2

    # Return a tuple with the computed shape.
    return (y_largest, x_largest)


def adjust_pixel_maps_for_pyqtgraph(pixel_maps):
    """
    Adjust pixel maps for visualization of the data in a pyqtgraph widget.

    The adjusted maps can be used for a Pyqtgraph ImageView widget.
    Essentially, the origin of the reference system is moved to the
    top-left of the image.

    Args:

        pixel_maps (PixelMaps): pixel maps, as returned by the
            :obj:`compute_pixel_maps` function in this module.

    Returns:

        PixelMaps: a PixelMaps tuple containing the ajusted pixel maps for
        the x and y coordinates in the first two fields, and the
        value None in the third.
    """

    # Compute the minimum image shape needed to represent the coordinates.
    min_shape = compute_minimum_array_size(pixel_maps)

    # Convert the old pixemap values to the new pixelmap values.
    new_x_map = numpy.array(
        object=pixel_maps.x,
        dtype=numpy.int
    ) + min_shape[1] // 2 - 1

    new_y_map = numpy.array(
        object=pixel_maps.y,
        dtype=numpy.int
    ) + min_shape[0] // 2 - 1

    return PixelMaps(new_x_map, new_y_map, None)
