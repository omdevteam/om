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


import fabio

from parallelization_layer.utils import (
    global_params as gp,
    dynamic_import as dyn_imp
)

in_layer = dyn_imp.import_layer_module('instrument_layer', gp.monitor_params)
num_events_in_file = getattr(in_layer, 'num_events_in_file')

file_extensions = ['.cbf']

data_ext_funcs = ['raw_data', 'detector_distance', 'beam_energy', 'pulse_energy', 'timestamp', 'filename_and_event']

for data_entry in data_ext_funcs:
    locals()[data_entry] = lambda x: None

required_data = gp.monitor_params['Backend']['required_data'].split(',')
for data_entry in required_data:
    data_entry = data_entry.strip()
    if data_entry not in data_ext_funcs:
        raise RuntimeError('Unknown data type: {0}'.format(data_entry))
    try:
        locals()[data_entry] = getattr(in_layer, data_entry)
    except AttributeError:
        try:
            locals()[data_entry] = locals()[data_entry+'_dataext']
        except KeyError:
            raise RuntimeError('Undefined data type: {0}'.format(data_entry))


def open_file(data):
    f = fabio.open(data, 'r')
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
        print ('Error while extracting timestamp: {0}'.format(e))
        monitor.event_timestamp = None

    # Extract detector data in slab format
    try:
        monitor.raw_data = raw_data(evt)

    except Exception as e:
        print ('Error while extracting raw_data: {0}'.format(e))
        monitor.raw_data = None

    # Extract beam energy in eV
    try:
        monitor.beam_energy = beam_energy(evt)

    except Exception as e:
        print ('Error while extracting beam_energy: {0}'.format(e))
        monitor.beam_energy = None

    # Extract detector distance in mm
    try:
        monitor.detector_distance = detector_distance(evt)

    except Exception as e:
        print ('Error while extracting detector_distance: {0}'.format(e))
        monitor.detector_distance = None

    # Extract filename and event
    try:
        monitor.filename, monitor.event = filename_and_event(evt)

    except Exception as e:
        print ('Error while extracting filename and event: {0}'.format(e))
        monitor.filename = None
        monitor.event = None
