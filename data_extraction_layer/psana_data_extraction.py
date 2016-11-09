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

from psana import Detector

from parallelization_layer.utils import onda_params as gp
from parallelization_layer.utils.onda_dynamic_import import import_correct_layer_module


def raw_data_init(det):
    det['detect'] = Detector(gp.monitor_params['PsanaParallelizationLayer']['detector_name'].encode('ascii'))


def timestamp_init(_):
    pass


def detector_distance_init(det):
    det['detect_dist'] = Detector(gp.monitor_params['PsanaParallelizationLayer'][
                                                    'detector_dist_epics_name'].encode('ascii'))

def beam_energy_init(det):
    det['beam_energy'] = Detector('EBeam'.encode('ascii'))


def timetool_data_init(det):
    det['timetool'] = Detector(gp.monitor_params['PsanaParallelizationLayer']['timetool_epics_name'].encode('ascii'))


def digitizer_data_init(det):
    det['digitizer'] = Detector(gp.monitor_params['PsanaParallelizationLayer']['digitizer_name'].encode('ascii'))


def digitizer2_data_init(det):
    det['digitizer2'] = Detector(gp.monitor_params['PsanaParallelizationLayer']['digitizer2_name'].encode('ascii'))


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


in_layer = import_correct_layer_module('instrument_layer', gp.monitor_params)

avail_data_sources = ['raw_data', 'detector_distance', 'beam_energy', 'timestamp', 'timetool_data', 'digitizer_data',
                      'digitizer2_data']

for data_source in avail_data_sources:
    globals()[(data_source + '_initialize').encode('ascii')] = lambda x: None

for data_source in avail_data_sources:
    print('Source:', data_source)
    globals()[data_source.encode('ascii')] = lambda x: None

required_data = gp.monitor_params['Backend']['required_data'].split(',')
for data_source in required_data:
    data_source = data_source.strip()
    if data_source not in avail_data_sources:
        raise RuntimeError('Unknown data type: {0}'.format(data_source))
    try:
        globals()[(data_source + '_initialize').encode('ascii')] = getattr(in_layer, (data_source + '_init').encode('ascii'))
    except AttributeError:
        try:
            globals()[(data_source + '_initialize').encode('ascii')] = globals()[(data_source + '_init').encode('ascii')]
        except KeyError:
            raise RuntimeError('Initialization function not defined for the following '
                               'data type: {0}'.format(data_source))

for data_source in required_data:
    data_source = data_source.strip()
    if data_source not in avail_data_sources:
        raise RuntimeError('Unknown data type: {0}'.format(data_source))
    try:
        globals()[data_source.encode('ascii')] = getattr(in_layer, (data_source + '_dataext').encode('ascii'))
    except AttributeError:
        try:
            globals()[data_source.encode('ascii')] = globals()[(data_source + '_dataext').encode('ascii')]
        except KeyError:
            raise RuntimeError('Data extraction function not defined for the following '
                               'data type: {0}'.format(data_source))


def initialize(det):
    for init_data_source in avail_data_sources:
        if init_data_source in required_data:
            globals()[(init_data_source + '_initialize').encode('ascii')](det)


def extract(event, monitor):

    # Extract time stamp data
    #try:
    monitor.timestamp = timestamp(event)

    #except Exception as e:
    #    print('Error when extracting raw data:', e)
    #    monitor.timestamp = None

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
