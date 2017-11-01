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


from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from collections import namedtuple

import h5py
import numpy


SlabShape = namedtuple('SlabShape', ['ss', 'fs'])
NativeShape = namedtuple('NativeShape', ['ss', 'fs'])

slab_shape = SlabShape(128, 4096)
native_shape = NativeShape(128, 4096)

file_extensions = ['.nxs']


def open_file(filename):
    return h5py.File(filename, 'r')


def close_file(filehandle):
    filehandle.close()


def num_events_in_file(filehandle):
    return filehandle['/entry/instrument/detector/data'].shape[0]


def raw_data(event):
    raw = event.filehandle['/entry/instrument/detector/data'][event.shot_offset, :, :].reshape(512, 1024)
    adu_data = numpy.bitwise_and(raw, 0x3fff)
    gain_data = numpy.bitwise_and(numpy.right_shift(raw, 14), 0x3)
    adu_data[gain_data != 0] = -999.0
    return adu_data


def timestamp(event):
    return event.filectime


def detector_distance(event):
    return float(event.monitor_params['General']['fallback_detector_distance'])


def beam_energy(event):
    return float(event.monitor_params['General']['fallback_beam_energy'])


def filename_and_event(event):
    return (event.filename, event.filehandle['/entry/instrument/detector/data'].shape[0] + event.shot_offset)
