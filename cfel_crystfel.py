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
Utilities for interoperability with the CrystFEL software package.

This module contains reimplementation of Crystfel functions and utilities.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import OrderedDict
from math import inf, sqrt
import re


def load_crystfel_geometry(filename):

    def assplode_algebraic(v):
        items = [item for item in re.split('([+-])', v.strip()) if item != '']

        if len(items) != 0 and items[0] not in ('+', '-'):
            items.insert(0, '+')

        return [''.join((items[x], items[x + 1])) for x in range(0, len(items), 2)]

    def dir_conv(direction_x, direction_y, direction_z):

        direction = [direction_x, direction_y, direction_z]

        items = assplode_algebraic(value)

        if len(items) == 0:
            raise RuntimeError('Invalid direction: {}.'.format(value))

        for item in items:
            axis = item[-1]

            if axis != 'x' and axis != 'y' and axis != 'z':
                raise RuntimeError('Invalid Symbol: {} (must be x, y or z).'.format(axis))

            if item[:-1] == '+':
                v = '1.0'
            elif item[:-1] == '-':
                v = '-1.0'
            else:
                v = item[-1]

            if axis == 'x':
                direction[0] = float(v)
            elif axis == 'y':
                direction[1] = float(v)
            elif axis == 'z':
                direction[2] = float(v)

        return direction

    def set_dim_structure_entry(k, v, pan):

        if pan['dim_structure'] is not None:
            dim = pan['dim_structure']
        else:
            dim = []

        dim_index = int(k[3])

        if dim_index > len(dim)-1:
            for index in range(len(dim), dim_index + 1):
                dim.append(None)

        if v == 'ss' or v == 'fs' or v == '%':
            dim[dim_index] = v
        elif v.isdigit():
            dim[dim_index] = int(v)
        else:
            raise RuntimeError('Invalid dim entry: {}.'.format(v))

    def parse_field_for_panel(k, v, pan):

        if k == 'min_fs':
            pan['origin_min_fs'] = int(v)
            pan['min_fs'] = int(v)

        elif k == 'max_fs':
            pan['origin_max_fs'] = int(v)
            pan['max_fs'] = int(v)

        elif k == 'min_ss':
            pan['origin_min_ss'] = int(v)
            pan['min_ss'] = int(v)

        elif k == 'max_ss':
            pan['origin_max_ss'] = int(v)
            pan['max_ss'] = int(v)

        elif k == 'corner_x':
            pan['cnx'] = float(v)

        elif k == 'corner_y':
            pan['cny'] = float(v)

        elif k == 'rail_direction':
            try:
                pan['rail_x'], pan['rail_y'], pan['rail_z'] = dir_conv(pan['rail_x'],
                                                                       pan['rail_y'],
                                                                       pan['rail_z'])
            except RuntimeError as e:
                raise RuntimeError('Invalid rail direction. ', e)

        elif k == 'clen_for_centering':
            pan['clen_for_centering'] = float(v)

        elif k == 'adu_per_eV':
            pan['adu_per_eV'] = float(v)

        elif k == 'adu_per_photon':
            pan['adu_per_photon'] = float(v)

        elif k == 'rigid_group':
            pan['rigid_group'] = v

        elif k == 'clen':
            try:
                pan['clen'] = float(v)
                pan['clen_from'] = None
            except ValueError:
                pan['clen'] = -1
                pan['clen_from'] = v

        elif k == 'data':
            if not v.startswith('/'):
                raise RuntimeError('Invalid data location: {}'.format(v))
            pan['data'] = v

        elif k == 'mask':
            if not v.startswith('/'):
                raise RuntimeError('Invalid data location: {}'.format(v))
            pan['mask'] = v

        elif k == 'mask_file':
            pan['mask_file'] = v

        elif k == 'saturation_map':
            pan['saturation_map'] = v

        elif k == 'saturation_map_file':
            pan['saturation_map_file'] = v

        elif k == 'coffset':
            pan['coffset'] = float(v)

        elif k == 'res':
            pan['res'] = float(v)

        elif k == 'max_adu':
            pan['max_adu'] = v

        elif k == 'badrow_direction':
            if v == 'x':
                pan['badrow'] = 'f'
            elif v == 'y':
                pan['badrow'] = 's'
            elif v == 'f':
                pan['badrow'] = 'f'
            elif v == 's':
                pan['badrow'] = 's'
            elif v == '-':
                pan['badrow'] = '-'
            else:
                print('badrow_direction must be x, t, f, s, or \'-\'')
                print('Assuming \'-\'.')
                pan['badrow'] = '-'

        elif k == 'no_index':
            pan['no_index'] = bool(v)

        elif k == 'fs':
            try:
                pan['fsx'], pan['fsy'], pan['fsz'] = dir_conv(pan['fsx'], pan['fsy'],
                                                              pan['fsz'])

            except RuntimeError as e:
                raise RuntimeError('Invalid fast scan direction. ', e)

        elif k == 'ss':
            try:
                pan['ssx'], pan['ssy'], pan['ssz'] = dir_conv(pan['ssx'], pan['ssy'],
                                                              pan['ssz'])

            except RuntimeError as e:
                raise RuntimeError('Invalid slow scan direction. ', e)

        elif k.startswith('dim'):
            set_dim_structure_entry(k, v, pan)

        else:
            raise RuntimeError('Unrecognised field: {}'.format(k))

    def parse_top_level(k, v, det, b, pan):

        if k == 'mask_bad':
            try:
                det['mask_bad'] = int(v)
            except ValueError:
                det['mask_bad'] = int(v, 16)

        elif k == 'mask_good':
            try:
                det['mask_good'] = int(v)
            except ValueError:
                det['mask_good'] = int(v, 16)

        elif k == 'coffset':
            pan['coffset'] = float(v)

        elif k == 'photon_energy':
            if v.startswith('/'):
                b['photon_energy'] = 0.0
                b['photon_energy_from'] = v
            else:
                b['photon_energy'] = float(v)
                b['photon_energy_from'] = None

        elif k == 'photon_energy_scale':
            b['photon_energy_scale'] = float(v)

        elif k == 'peak_info_location':
            det['peak_info_location'] = v

        elif k.startswith('rigid_group') and not k.startswith('rigid_group_collection'):
            det['rigid_groups'][k[12:]] = v.split(',')

        elif k.startswith('rigid_group_collection'):
            det['rigid_group_collections'][k[23:]] = v.split(',')

        else:
            parse_field_for_panel(k, v, pan)

    def check_bad_fsss(bad, is_fsss):

        if bad['is_fsss'] == 99:
            bad['is_fsss'] = is_fsss
            return

        if is_fsss != bad['is_fsss']:
            raise RuntimeError("You can't mix x/y and fs/ss in a bad region")

        return

    def parse_field_bad(k, v, bad):

        if k == 'min_x':
            bad['min_x'] = float(v)
            check_bad_fsss(bad, False)
        elif k == 'max_x':
            bad['max_x'] = float(v)
            check_bad_fsss(bad, False)
        elif k == 'min_y':
            bad['min_y'] = float(v)
            check_bad_fsss(bad, False)
        elif k == 'max_y':
            bad['max_y'] = float(v)
            check_bad_fsss(bad, False)
        elif k == 'min_fs':
            bad['min_fs'] = int(v)
            check_bad_fsss(bad, True)
        elif k == 'max_fs':
            bad['max_fs'] = int(v)
            check_bad_fsss(bad, True)
        elif k == 'min_ss':
            bad['min_ss'] = int(v)
            check_bad_fsss(bad, True)
        elif k == 'max_ss':
            bad['max_ss'] = int(v)
            check_bad_fsss(bad, True)
        elif k == 'panel':
            bad['panel'] = v
        else:
            raise RuntimeError('Unrecognised field: {}'.format(k))

        return

    def check_point(n, pan, fs, ss, min_d, max_d, det):

        xs = fs * pan['fsx'] + ss * pan['ssx']
        ys = fs * pan['fsy'] + ss * pan['ssy']

        rx = (xs + pan['cnx']) / pan['res']
        ry = (ys + pan['cny']) / pan['res']

        dist = sqrt(rx * rx + ry * ry)

        if dist > max_d:
            det['furthest_out_panel'] = n
            det['furthest_out_fs'] = fs
            det['furthest_out_ss'] = ss
            max_d = dist
        elif dist < min_d:
            det['furthest_in_panel'] = n
            det['furthest_in_fs'] = fs
            det['furthest_in_ss'] = ss
            min_d = dist

        return min_d, max_d

    def find_min_max_d(det):

        min_d = inf
        max_d = 0.0

        for n, pan in det['panels'].items():
            min_d, max_d = check_point(n, pan, 0, 0, min_d, max_d, det)
            min_d, max_d = check_point(n, pan, pan['w'], 0, min_d, max_d, det)
            min_d, max_d = check_point(n, pan, 0, pan['h'], min_d, max_d, det)
            min_d, max_d = check_point(n, pan, pan['w'], pan['h'], min_d, max_d, det)

    fh = open(filename, 'r')

    beam = {
        'photon_energy': 0.0,
        'photon_energy_from': None,
        'photon_energy_scale': 1
    }

    detector = {
        'panels': OrderedDict(),
        'bad': OrderedDict(),
        'mask_good': 0,
        'mask_bad': 0,
        'rigid_groups': {},
        'rigid_group_collections': {}
    }

    default_panel = {
        'cnx': None,
        'cny': None,
        'clen': None,
        'coffset': 0.0,
        'res': -1.0,
        'badrow': '-',
        'no_index': False,
        'fsx': 1.0,
        'fsy': 0.0,
        'fsz': 0.0,
        'ssx': 0.0,
        'ssy': 1.0,
        'ssz': 0.0,
        'rail_x': None,
        'rail_y': None,
        'rail_z': None,
        'clen_for_centering': None,
        'adu_per_eV': None,
        'adu_per_photon': None,
        'max_adu': inf,
        'mask': None,
        'mask_file': None,
        'satmap': None,
        'satmap_file': None,
        'data': None,
        'dim_structure': None,
        'name': ''
    }

    default_bad_region = {
        'min_x': None,
        'max_x': None,
        'min_y': None,
        'max_y': None,
        'min_fs': 0,
        'max_fs': 0,
        'min_ss': 0,
        'max_ss': 0,
        'is_fsss': 99,
        'name': ''
    }

    default_dim = ['ss', 'fs']

    fhlines = fh.readlines()

    for line in fhlines:

        if line.startswith(';'):
            continue

        line_without_comments = line.strip().split(';')[0]
        line_items = re.split('([ \t])', line_without_comments)
        line_items = [item for item in line_items if item not in ('', ' ', '\t')]

        if len(line_items) < 3:
            continue

        value = ''.join(line_items[2:])

        if line_items[1] != '=':
            continue

        path = re.split('(/)', line_items[0])
        path = [item for item in path if item not in '/']

        if len(path) < 2:
            parse_top_level(line_items[0], value, detector, beam, default_panel)
            continue

        curr_bad = None
        curr_panel = None

        if path[0].startswith('bad'):

            if path[0] in detector['bad']:
                curr_bad = detector['bad'][path[0]]
            else:
                curr_bad = default_bad_region.copy()
                detector['bad'][path[0]] = curr_bad

        else:

            if path[0] in detector['panels']:
                curr_panel = detector['panels'][path[0]]
            else:
                curr_panel = default_panel.copy()
                detector['panels'][path[0]] = curr_panel

        if curr_panel is not None:
            parse_field_for_panel(path[1], value, curr_panel)
        else:
            parse_field_bad(path[1], value, curr_bad)

    if len(detector['panels']) == 0:
        raise RuntimeError("No panel descriptions in geometry file.")

    num_placeholders_in_panels = None

    for panel in detector['panels'].values():

        if panel['dim_structure'] is not None:
            curr_num_placeholders = panel['dim_structure'].values().count('%')
        else:
            curr_num_placeholders = 0

        if num_placeholders_in_panels is None:
            num_placeholders_in_panels = curr_num_placeholders
        else:
            if curr_num_placeholders != num_placeholders_in_panels:
                raise RuntimeError('All panels\' data and mask entries must have the same number of placeholders.')

    num_placeholders_in_masks = None

    for panel in detector['panels'].values():

        if panel['mask'] is not None:
            curr_num_placeholders = panel['mask'].count('%')
        else:
            curr_num_placeholders = 0

        if num_placeholders_in_masks is None:
            num_placeholders_in_masks = curr_num_placeholders
        else:
            if curr_num_placeholders != num_placeholders_in_masks:
                raise RuntimeError('All panels\' data and mask entries must have the same number of placeholders.')

    if num_placeholders_in_masks > num_placeholders_in_panels:
        raise RuntimeError('Number of placeholders in mask cannot be larget than for data.')

    dim_length = None

    for panel in detector['panels'].values():

        if panel['dim_structure'] is None:
            panel['dim_structure'] = default_dim.copy()

        found_ss = False
        found_fs = False
        found_placeholder = False

        for entry in panel['dim_structure']:
            if entry is None:
                raise RuntimeError('Not all dim entries are defined for all panels.')
            elif entry == 'ss':
                if found_ss is True:
                    raise RuntimeError('Only one slow scan dim coordinate is allowed.')
                else:
                    found_ss = True
            elif entry == 'fs':
                if found_fs is True:
                    raise RuntimeError('Only one fast scan dim coordinate is allowed.')
                else:
                    found_fs = True
            elif entry == '%':
                if found_placeholder is True:
                    raise RuntimeError('Only one placeholder dim coordinate is allowed.')
                else:
                    found_placeholder = True

    for panel in detector['panels'].values():

        if panel['origin_min_fs'] < 0:
            raise RuntimeError('Please specify the minimum fs coordinate for panel {}.'.format(panel['name']))

        if panel['origin_max_fs'] < 0:
            raise RuntimeError('Please specify the maximum fs coordinate for panel {}.'.format(panel['name']))

        if panel['origin_min_ss'] < 0:
            raise RuntimeError('Please specify the minimum ss coordinate for panel {}.'.format(panel['name']))

        if panel['origin_max_ss'] < 0:
            raise RuntimeError('Please specify the maximum ss coordinate for panel {}.'.format(panel['name']))

        if panel['cnx'] is None:
            raise RuntimeError('Please specify the corner X coordinate for panel {}.'.format(panel['name']))

        if panel['clen'] is None and panel['clen_from'] is None:
            raise RuntimeError('Please specify the camera length for panel {}.'.format(panel['name']))

        if panel['res'] < 0:
            raise RuntimeError('Please specify the resolution or panel {}.'.format(panel['name']))

        if panel['adu_per_eV'] is None and panel['adu_per_photon'] is None:
            raise RuntimeError('Please specify either adu_per_eV or adu_per_photon for '
                               'panel {}.'.format(panel['name']))

        if panel['clen_for_centering'] is None and panel['rail_x'] is not None:
            raise RuntimeError('You must specify clen_for_centering if you specify the rail direction '
                               '(panel {})'.format(panel['name']))

        if panel['rail_x'] is None:
            panel['rail_x'] = 0.0
            panel['rail_y'] = 0.0
            panel['rail_z'] = 1.0

        if panel['clen_for_centering'] is None:
            panel['clen_for_centering'] = 0.0

        panel['w'] = panel['origin_max_fs'] - panel['origin_min_fs'] + 1
        panel['h'] = panel['origin_max_ss'] - panel['origin_min_ss'] + 1

    for bad_region in detector['bad']:
        if bad_region['is_fsss'] == 99:
            raise RuntimeError('Please specify the coordinate ranges for bad region {}.'.format(bad_region['name']))

    for group in detector['rigid_groups'].keys():
        for name in detector['rigid_groups'][group]:
            if name not in detector['panels']:
                raise RuntimeError('Cannot add panel to rigid_group. Panel not found: {}'.format(name))

    for group_collection in detector['rigid_group_collections'].keys():
        for name in detector['rigid_group_collections'][group_collection]:
            if name not in detector['rigid_groups']:
                raise RuntimeError('Cannot add rigid_group to collection. Rigid group not found: {}'.format(name))

    for panel in detector['panels'].values():

        d = panel['fsx'] * panel['ssy'] - panel['ssx'] * panel['fsy']

        if d == 0.0:
            raise RuntimeError('Panel {} transformation is singluar.')

        panel['xfs'] = panel['ssy'] / d
        panel['yfs'] = panel['ssx'] / d
        panel['xss'] = panel['fsy'] / d
        panel['yss'] = panel['fsx'] / d

    find_min_max_d(detector)
    fh.close()

    return detector
