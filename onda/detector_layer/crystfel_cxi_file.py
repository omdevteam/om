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
from time import strptime

import h5py


SlabShape = namedtuple('SlabShape', ['ss', 'fs'])
NativeShape = namedtuple('NativeShape', ['ss', 'fs'])

slab_shape = SlabShape(1480, 1552)
native_shape = NativeShape(1480, 1552)

file_extensions = ['.cxi']


def open_file(filename):
    return h5py.File(filename, 'r')


def close_file(filehandle):
    filehandle.close()


def num_events_in_file(filehandle):
    return filehandle['/entry_1/instrument_1/detector_1/detector_corrected/data'].shape[0]


def timestamp(event):
    return strptime(event.filehandle['/LCLS/eventTimeString'][event['shot_offset']].decode(
        'ascii').strip(), '%a %b  %d %H:%M:%S %Y')


def raw_data(event):
    return event.filehandle['/entry_1/instrument_1/detector_1/detector_corrected/data'][event.shot_offset, :, :]


def detector_distance(event):
    return float(event.filehandle['LCLS/detector_1/EncoderValue'][event.shot_offset])


def beam_energy(event):
    return float(event.filehandle['/LCLS/photon_energy_eV'][event.shot_offset])


def filename_and_event(event):
    return (event.filename,
            event.filehandle['/entry_1/instrument_1/detector_1/detector_corrected/data'].shape[0]+event.shot_offset)
