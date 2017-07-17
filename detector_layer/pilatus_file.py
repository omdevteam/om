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


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import namedtuple
from scipy.constants import h, c, electron_volt

import fabio

SlabShape = namedtuple('SlabShape', ['ss', 'fs'])
NativeShape = namedtuple('NativeShape', ['ss', 'fs'])

slab_shape = (2527, 2463)
native_shape = (2527, 2463)

file_extensions = ['.cbf']


def open_file(data):
    f = fabio.open(data, 'r')
    return f


def close_file(_):
    pass


def num_events_in_file(_):
    return 1


def raw_data(event):
    return event.filehandle.data


def timestamp(event):
    return event.filectime


def beam_energy(event):
    try:
        header_data_list = event.filehandle.header[u'_array_data.header_contents'].split('\r\n')
        wavelength = float(header_data_list[15].split()[2])
        return float(h * c / (wavelength * electron_volt))
    except (AttributeError, IndexError, ValueError):
        return float(event.monitor_params['General']['fallback_beam_energy'])


def detector_distance(event):
    try:
        header_data_list = event.filehandle.header[u'_array_data.header_contents'].split('\r\n')
        return float(header_data_list[16].split()[2])
    except (AttributeError, IndexError, ValueError):
        return float(event.monitor_params['General']['fallback_detector_distance'])


def filename_and_event(event):
    return (event.filename, 0)
