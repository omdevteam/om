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

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from cfelpyutils.cfel_fabio import read_cbf_from_stream
from parallelization_layer.utils import onda_params as gp
from parallelization_layer.utils.onda_dynamic_import import import_correct_layer_module, import_function_from_layer


in_layer = import_correct_layer_module('instrument_layer', gp.monitor_params)
num_events_in_file = import_function_from_layer('num_events_in_file', in_layer)

file_extensions = ['.cbf']

avail_data_sources = ['raw_data', 'detector_distance', 'beam_energy', 'pulse_energy', 'timestamp', 'filename_and_event']

for data_source in avail_data_sources:
    locals()[data_source] = lambda x: None

required_data = gp.monitor_params['Backend']['required_data'].split(',')
for data_source in required_data:
    data_source = data_source.strip()
    if data_source not in avail_data_sources:
        raise RuntimeError('Unknown data type: {0}'.format(data_source))
    try:
        locals()[data_source] = getattr(in_layer, data_source)
    except AttributeError:
        try:
            locals()[data_source] = locals()[data_source + '_dataext']
        except KeyError:
            raise RuntimeError('Undefined data type: {0}'.format(data_source))


def open_file(data):
    data_stringio = StringIO(data)
    f = read_cbf_from_stream(data_stringio)
    data_stringio.close()
    return f


def close_file(_):
    pass


def num_events(filehandle):
    return num_events_in_file(filehandle)


def extract(evt, monitor):
    # Extract timestamp
    try:
        monitor.event_timestamp = timestamp(evt)

    except Exception as e:
        print('Error while extracting timestamp:', e)
        monitor.event_timestamp = None

    # Extract detector data in slab format
    try:
        monitor.raw_data = raw_data(evt)

    except Exception as e:
        print('Error while extracting raw_data:', e)
        monitor.raw_data = None

    # Extract beam energy in eV
    try:
        monitor.beam_energy = beam_energy(evt)

    except Exception as e:
        print('Error while extracting beam_energy:', e)
        monitor.beam_energy = None

    # Extract detector distance in mm
    try:
        monitor.detector_distance = detector_distance(evt)

    except Exception as e:
        print('Error while extracting detector_distance:', e)
        monitor.detector_distance = None

    # Extract filename and event
    try:
        monitor.filename, monitor.event = filename_and_event(evt)

    except Exception as e:
        print('Error while extracting filename and event:', e)
        monitor.filename_and_event = None
