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


import numpy


def pixel_maps_from_geometry_file(fnam):
    """Extracts pixel maps from a CrystFEL-style geometry file.

    Args:

        fnam (str): geometry filename.

    Returns:

        x,y,r (numpy.ndarray float, numpy.ndarray float, numpy.ndarray float):
        slab-like pixel maps with respectively x, y coordinates of the pixel
        and distance of the pixel from the center of the reference system
        (usually the beam position).
    """

    f = open(fnam, 'r')
    f_lines = f.readlines()
    f.close()

    keyword_list = ['min_fs', 'min_ss', 'max_fs', 'max_ss', 'fs', 'ss', 'corner_x', 'corner_y']

    detector_dict = {}

    panel_lines = [x for x in f_lines if '/' in x and len(x.split('/')) == 2 and x.split('/')[1].split('=')[0].strip() in keyword_list]

    for pline in panel_lines:
        items = pline.split('=')[0].split('/')
        panel = items[0].strip()
        prop = items[1].strip()
        if prop in keyword_list:
            if panel not in detector_dict.keys():
                detector_dict[panel] = {}
            detector_dict[panel][prop] = pline.split('=')[1].split(';')[0]

    parsed_detector_dict = {}

    for p in detector_dict.keys():

        parsed_detector_dict[p] = {}

        parsed_detector_dict[p]['min_fs'] = int(detector_dict[p]['min_fs'])
        parsed_detector_dict[p]['max_fs'] = int(detector_dict[p]['max_fs'])
        parsed_detector_dict[p]['min_ss'] = int(detector_dict[p]['min_ss'])
        parsed_detector_dict[p]['max_ss'] = int(detector_dict[p]['max_ss'])
        parsed_detector_dict[p]['fs'] = []
        parsed_detector_dict[p]['fs'].append(float(detector_dict[p]['fs'].split('x')[0]))
        parsed_detector_dict[p]['fs'].append(float(detector_dict[p]['fs'].split('x')[1].split('y')[0]))
        parsed_detector_dict[p]['ss'] = []
        parsed_detector_dict[p]['ss'].append(float(detector_dict[p]['ss'].split('x')[0]))
        parsed_detector_dict[p]['ss'].append(float(detector_dict[p]['ss'].split('x')[1].split('y')[0] ) )
        parsed_detector_dict[p]['corner_x'] = float(detector_dict[p]['corner_x'])
        parsed_detector_dict[p]['corner_y'] = float(detector_dict[p]['corner_y'])

    max_slab_fs = numpy.array([parsed_detector_dict[k]['max_fs'] for k in parsed_detector_dict.keys()]).max()
    max_slab_ss = numpy.array([parsed_detector_dict[k]['max_ss'] for k in parsed_detector_dict.keys()]).max()

    x = numpy.zeros((max_slab_ss+1, max_slab_fs+1), dtype=numpy.float32)
    y = numpy.zeros((max_slab_ss+1, max_slab_fs+1), dtype=numpy.float32)

    for p in parsed_detector_dict.keys():
        # get the pixel coords for this asic
        i, j = numpy.meshgrid(numpy.arange(parsed_detector_dict[p]['max_ss'] - parsed_detector_dict[p]['min_ss'] + 1),
                              numpy.arange(parsed_detector_dict[p]['max_fs'] - parsed_detector_dict[p]['min_fs'] + 1), indexing='ij')

        #
        # make the y-x ( ss, fs ) vectors, using complex notation
        dx = parsed_detector_dict[p]['fs'][1] + 1J * parsed_detector_dict[p]['fs'][0]
        dy = parsed_detector_dict[p]['ss'][1] + 1J * parsed_detector_dict[p]['ss'][0]
        r_0 = parsed_detector_dict[p]['corner_y'] + 1J * parsed_detector_dict[p]['corner_x']
        #
        r = i * dy + j * dx + r_0
        #
        y[parsed_detector_dict[p]['min_ss']: parsed_detector_dict[p]['max_ss'] + 1, parsed_detector_dict[p]['min_fs']: parsed_detector_dict[p]['max_fs'] + 1] = r.real
        x[parsed_detector_dict[p]['min_ss']: parsed_detector_dict[p]['max_ss'] + 1, parsed_detector_dict[p]['min_fs']: parsed_detector_dict[p]['max_fs'] + 1] = r.imag

    r = numpy.sqrt(numpy.square(x) + numpy.square(y))

    return x, y, r


def coffset_from_geometry_file(fnam):
    """Extracts detector distance offset information from a CrystFEL-style
       geometry file.

    Args:

        fnam (str): geometry filename.

    Returns:

        coffset (float): the detector distance offset
    """
    f = open(fnam, 'r')
    f_lines = f.readlines()
    f.close()

    coffset = 0.0

    for line in f_lines:
        if line.startswith('coffset'):
            coffset = float(line.split('=')[1].split('#')[0])

    return coffset


def res_from_geometry_file(fnam):
    """Extracts pixel resolution information from a CrystFEL-style
       geometry file.

    Args:

        fnam (str): geometry filename.

    Returns:

        res (float): the pixel resolution
    """
    f = open(fnam, 'r')
    f_lines = f.readlines()
    f.close()

    res = None

    for line in f_lines:
        if line.startswith('res'):
            res = float(line.split('=')[1].split('#')[0])

    return res
