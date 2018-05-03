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
Utilities to load, manipulate and apply geometry information to
detector pixel data.

Exports:

    Functions:

        compute_pix_maps: turn a CrystFEL geometry object into pixel
            maps.

        compute_min_array_size: compute the minimum array size that
            is required to store data to which a geometry has been
            applied.

        compute_visualization_pix_maps: ajust pixel maps to be used in
            a PyQtGraph's ImageView widget.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import collections

import numpy


PixelMaps = collections.namedtuple(  # pylint: disable=C0103
    typename='PixelMaps',
    field_names=['x', 'y', 'r']
)
"""
Pixel maps storing data geometry.

A namedtuple that stores the pixel maps describing the geometry of a
dataset. The first two fields, named "x" and "y" respectively, store
the pixel maps for the x coordinate and the y coordinate. The third
field, named "r", is instead a pixel map storing the distance of each
pixel in the data array from the center of the reference system.
"""


def compute_pix_maps(geometry):
    """
    Compute pixel maps from a CrystFEL geometry object.

    Take as input a CrystFEL-style geometry object (A dictionary
    returned by the function load_crystfel_geometry function in the
    crystfel_utils module) and return a PixelMap tuple . The origin the
    reference system used by the pixel maps is set at the beam
    interaction point.

    Args:

        geometry (dict): A CrystFEL geometry object (A dictionary
            returned by the
            :obj:`cfelpyutils.crystfel_utils.load_crystfel_geometry`
            function).

    Returns:

        PixelMaps: A PixelMaps tuple storing the pixel maps (ndarrays
        of type float).
    """
    # Determine the max fs and ss in the geometry object.
    max_slab_fs = numpy.array([
        geometry['panels'][k]['max_fs']
        for k in geometry['panels']
    ]).max()

    max_slab_ss = numpy.array([
        geometry['panels'][k]['max_ss']
        for k in geometry['panels']
    ]).max()

    # Create empty arrays, of the same size of the input data, that
    # will store the x and y pixel maps.
    x_map = numpy.zeros(
        shape=(max_slab_ss + 1, max_slab_fs + 1),
        dtype=numpy.float32  # pylint: disable=E1101
    )

    y_map = numpy.zeros(
        shape=(max_slab_ss + 1, max_slab_fs + 1),
        dtype=numpy.float32  # pylint: disable=E1101
    )

    # Iterate over the panels. For each panel, determine the pixel
    # indices, then compute the x,y vectors. Finally, copy the
    # panel pixel maps into the detector-wide pixel maps.
    # At the end, compute the values for the radius pixel map.
    for pan in geometry['panels']:
        ss_grid, fs_grid = numpy.meshgrid(
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

        y_panel = (
            ss_grid * geometry['panels'][pan]['ssy'] +
            fs_grid * geometry['panels'][pan]['fsy'] +
            geometry['panels'][pan]['cny']
        )

        x_panel = (
            ss_grid * geometry['panels'][pan]['ssx'] +
            fs_grid * geometry['panels'][pan]['fsx'] +
            geometry['panels'][pan]['cnx']
        )

        x_map[
            geometry['panels'][pan]['min_ss']:
            geometry['panels'][pan]['max_ss'] + 1,
            geometry['panels'][pan]['min_fs']:
            geometry['panels'][pan]['max_fs'] + 1
        ] = x_panel

        y_map[
            geometry['panels'][pan]['min_ss']:
            geometry['panels'][pan]['max_ss'] + 1,
            geometry['panels'][pan]['min_fs']:
            geometry['panels'][pan]['max_fs'] + 1
        ] = y_panel

    r_map = numpy.sqrt(numpy.square(x_map) + numpy.square(y_map))

    return PixelMaps(x_map, y_map, r_map)


def compute_min_array_size(pixel_maps):
    """
    Compute the minimum array size storing data with applied geometry.

    Return the minimum size of an array that can store data on which
    the geometry information described by the pixel maps has been
    applied.

    The returned array shape is big enough to display all the input
    pixel values in the reference system of the physical detector. The
    array is also supposed to be centered at the center of the
    reference system of the detector (i.e: the beam interaction point).

    Args:

        pixel_maps [PixelMaps]: a PixelMaps tuple.

    Returns:

        Tuple[int, int]: a numpy-style shape tuple storing the minimum
        array size.
    """
    # Find the largest absolute values of x and y in the maps. Since
    # the returned array is centered on the origin, the minimum array
    # size along a certain axis must be at least twice the maximum
    # value for that axis. 2 pixels are added for good measure.
    x_map, y_map = pixel_maps.x, pixel_maps.y
    y_minimum = 2 * int(max(abs(y_map.max()), abs(y_map.min()))) + 2
    x_minimum = 2 * int(max(abs(x_map.max()), abs(x_map.min()))) + 2

    # Return a numpy-style tuple with the computed shape.
    return (y_minimum, x_minimum)


def compute_visualization_pix_maps(geometry):
    """
    Compute pixel maps for visualization of the data.

    The pixel maps can be used for to display the data in a Pyqtgraph
    ImageView widget.

    Args:

        geometry (dict): A CrystFEL geometry object (A dictionary
            returned by the
            :obj:`cfelpyutils.crystfel_utils.load_crystfel_geometry`
            function).

    Returns:

        PixelMaps: A PixelMaps tuple containing the adjusted pixel
            maps. The first two fields, named "x" and "y" respectively,
            store the pixel maps for the x coordinate and the y
            coordinates (as ndarrays of type int). The third field
            ("r") is just set to None.
    """
    # Essentially, the origin of the reference system needs to be
    # moved from the beam position to the top-left of the image that
    # will be displayed. First, compute the normal pixel maps, then
    # compute the size of the array used to display the data, finally
    # use this information to estimate the magnitude of the shift that
    # needs to be applied to the origin of the system.
    pixel_maps = compute_pix_maps(geometry)
    min_shape = compute_min_array_size(pixel_maps)
    new_x_map = numpy.array(
        object=pixel_maps.x,
        dtype=numpy.int
    ) + min_shape[1] // 2 - 1

    new_y_map = numpy.array(
        object=pixel_maps.y,
        dtype=numpy.int
    ) + min_shape[0] // 2 - 1

    return PixelMaps(new_x_map, new_y_map, None)
