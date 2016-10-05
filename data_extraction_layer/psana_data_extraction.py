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


def detector_distance_init(det):
    det['det_dist'] = Detector(gp.monitor_params['PsanaParallelizationLayer']['detector_dist_epics_pv'])


def timetool_data_init(det):
    det['time_tools'] = Detector(gp.monitor_params['PsanaParallelizationLayer']['timetool_epics_pv'])


def acqiris1_data_init(det):
    det['acqiris1'] = Detector(gp.monitor_params['PsanaParallelizationLayer']['digitizer1_psana_source'])


def acqiris2_data_init(det):
    det['acqiris2'] = Detector(gp.monitor_params['PsanaParallelizationLayer']['digitizer2_psana_source'])


def pulse_energy_init(det):
    det['pulse_energy'] = Detector('FEEGasDetEnergy')


def beam_energy_init(det):
    det['beam_energy'] = Detector('EBeam')


def detector_distance_dataext(event):
    return event['det']['det_dist']()


def timetool_data_dataext(event):
    return event['det']['timetool']()


def acqiris1_data_dataext(event):
    return event['det']['acqiris1'].waveform(event['evt'])


def acqiris2_data_dataext(event):
    return event['det']['acqiris2'].waveform(event['evt'])


in_layer = import_correct_layer_module('instrument_layer', gp.monitor_params)

avail_data_sources = ['raw_data', 'opal_data', 'detector_distance', 'beam_energy', 'pulse_energy', 'timestamp',
                      'timetool_data', 'acqiris1_data', 'acqiris2_data']

for data_source in avail_data_sources:
    locals()[data_source] = lambda x: None

for data_source in avail_data_sources:
    locals()[data_source + '_initialize'] = lambda x: None

required_data = gp.monitor_params['Backend']['required_data'].split(',')
for data_source in required_data:
    data_source = data_source.strip()
    if data_source not in avail_data_sources:
        raise RuntimeError('Unknown data type: {0}'.format(data_source))
    try:
        locals()[data_source + '_initialize'] = getattr(in_layer, data_source + '_init')
        locals()[data_source] = getattr(in_layer, data_source)
    except AttributeError:
        try:
            locals()[data_source + '_initialize'] = locals()[data_source + '_init']
            locals()[data_source] = locals()[data_source + '_dataext']
        except KeyError:
            raise RuntimeError('Undefined data type: {0}'.format(data_source))


def initialize(det):
    for init_data_source in avail_data_sources:
        locals()[init_data_source + '_initialize'](det)


def extract(event, monitor):
    # Extract detector data in slab format
    try:
        monitor.raw_data = raw_data(event)

    except Exception as e:
        print('Error when extracting raw_data:', e)
        monitor.raw_data = None

    # Extract pulse energy in mJ
    try:
        monitor.pulse_energy = pulse_energy(event)

    except Exception as e:
        print('Error when extracting pulse_energy:', e)
        monitor.pulse_energy = None

    # Extract beam energy in eV
    try:
        monitor.beam_energy = beam_energy(event)

    except Exception as e:
        print('Error when extracting beam_energy:', e)
        monitor.beam_energy = None

    # Extract detector distance in mm
    try:
        monitor.detector_distance = detector_distance(event)

    except Exception as e:
        print('Error when extracting detector_distance:', e)
        monitor.detector_distance = None

    # Extract Opal camera data
    try:
        monitor.opal_data = opal_data(event)

    except Exception as e:
        print('Error when extracting opal_data:', e)
        monitor.opal_data = None

    # Extract timetool data
    try:
        monitor.timetool_data = timetool_data(event)

    except Exception as e:
        print('Error when extracting timetool_data:', e)
        monitor.timetool_data = None

    # Extract Acquiris data
    try:
        monitor.acqiris1_data = acqiris1_data(event)

    except Exception as e:
        print('Error when extracting tof_data:', e)
        monitor.tof_data = None

    # Extract Acquiris data
    try:
        monitor.acqiris2_data = acqiris2_data(event)

    except Exception as e:
        print('Error when extracting tof_data:', e)
        monitor.tof_data = None
