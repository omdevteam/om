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

import parallelization_layer.utils.onda_dynamic_import as di
import parallelization_layer.utils.onda_params as op
import psana


def raw_data_init(det):
    det['detect'] = psana.Detector(op.monitor_params['PsanaParallelizationLayer']['detector_name'])


def timestamp_init(_):
    pass


def detector_distance_init(det):
    det['detect_dist'] = psana.Detector(op.monitor_params['PsanaParallelizationLayer']['detector_dist_epics_name'])


def beam_energy_init(det):
    det['beam_energy'] = psana.Detector('EBeam'.encode('ascii'))


def timetool_data_init(det):
    det['timetool'] = psana.Detector(op.monitor_params['PsanaParallelizationLayer']['timetool_epics_name'])


def digitizer_data_init(det):
    det['digitizer'] = psana.Detector(op.monitor_params['PsanaParallelizationLayer']['digitizer_name'])


def digitizer2_data_init(det):
    det['digitizer2'] = psana.Detector(op.monitor_params['PsanaParallelizationLayer']['digitizer2_name'])


def event_codes_init(det):
    det['EVR'] = psana.Detector('evr0')


def timestamp_dataext(event):
    return event['det']['timestamp']


def detector_distance_dataext(event):
    return event['det']['detect_dist']()


def beam_energy_dataext(event):
    return event['det']['beam_energy'].get(event['evt']).ebeamPhotonEnergy()


def timetool_data_dataext(event):
    return event['det']['time_tool']()


def digitizer_data_dataext(event):
    return event['det']['digitizer'].waveform(event['evt'])


def digitizer2_data_dataext(event):
    return event['det']['digitizer2'].waveform(event['evt'])


def event_codes_dataext(event):
    return event['det']['evr'].eventCodes(event['evt'])


in_layer = di.import_correct_layer_module('instrument_layer', op.monitor_params)

raw_data_initialize = lambda x: None
detector_distance_initialize = lambda x: None
beam_energy_initialize = lambda x: None
timestamp_initialize = lambda x: None
timetool_data_initialize = lambda x: None
digitizer_data_initialize = lambda x: None
digitizer2_data_initialize = lambda x: None
event_codes_initialize = lambda x: None

raw_data = lambda x: None
detector_distance = lambda x: None
beam_energy = lambda x: None
timestamp = lambda x: None
timetool_data = lambda x: None
digitizer_data = lambda x: None
digitizer2_data = lambda x: None
event_codes = lambda x: None

avail_data_sources = ['raw_data', 'detector_distance', 'beam_energy', 'timestamp', 'timetool_data', 'digitizer_data',
                      'digitizer2_data', 'event_codes']

required_data = op.monitor_params['Onda']['required_data'].split(',')
for data_source in required_data:
    data_source = data_source.strip()
    if data_source not in avail_data_sources:
        raise RuntimeError('Unknown data type: {0}'.format(data_source))
    try:
        globals()[data_source + '_initialize'] = getattr(in_layer, data_source + '_init')
    except AttributeError:
        try:
            globals()[data_source + '_initialize'] = globals()[data_source + '_init']
        except KeyError:
            raise RuntimeError('Initialization function not defined for the following '
                               'data type: {0}'.format(data_source))

for data_source in required_data:
    data_source = data_source.strip()
    if data_source not in avail_data_sources:
        raise RuntimeError('Unknown data type: {0}'.format(data_source))
    try:
        if data_source == 'raw_data' and op.param('PsanaParallelizationLayer', 'pedestals_only', bool):
            globals()[data_source] = getattr(in_layer, data_source + '_dataext_pedestals_only')
        else:
            globals()[data_source] = getattr(in_layer, data_source + '_dataext')
    except AttributeError:
        try:
            if data_source == 'raw_data' and op.param('PsanaParallelizationLayer', 'pedestals_only', bool):
                globals()[data_source] = globals()[data_source + '_dataext_pedestals_only']
            else:
                globals()[data_source] = globals()[data_source + '_dataext']
        except KeyError:
            raise RuntimeError('Data extraction function not defined for the following '
                               'data type: {0}'.format(data_source))


def initialize(det):
    for init_data_source in avail_data_sources:
        if init_data_source in required_data:
            globals()[init_data_source + '_initialize'](det)


def extract(event, monitor):

    # Extract time stamp data
    try:
        monitor.timestamp = timestamp(event)

    except Exception as e:
        print('Error when extracting raw data:', e)
        monitor.timestamp = None

    # Extract detector data in slab format
    try:
        monitor.raw_data = raw_data(event)

    except Exception as e:
        print('Error when extracting raw data:', e)
        monitor.raw_data = None

    # Extract detector distance in mm
    try:
        monitor.detector_distance = detector_distance(event)

    except Exception as e:
        print('Error when extracting detector distance:', e)
        monitor.detector_distance = None

    # Extract beam energy in eV
    try:
        monitor.beam_energy = beam_energy(event)

    except Exception as e:
        print('Error when extracting beam energy:', e)
        monitor.beam_energy = None

    # Extract timetool data
    try:
        monitor.timetool_data = timetool_data(event)

    except Exception as e:
        print('Error when extracting timetool data:', e)
        monitor.timetool_data = None

    # Extract Acquiris data
    try:
        monitor.digitizer_data = digitizer_data(event)

    except Exception as e:
        print('Error when extracting digitizer data:', e)
        monitor.digitizer_data = None

    # Extract Acquiris data
    try:
        monitor.digitizer2_data = digitizer2_data(event)

    except Exception as e:
        print('Error when extracting digitizer2 data:', e)
        monitor.digitizer2_data = None

    # Extract Acquiris data
    try:
        monitor.event_codes = event_codes(event)

    except Exception as e:
        print('Error when extracting event_codes:', e)
        monitor.event_codes = None
