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

from psana import Detector, EventID

from parallelization_layer.utils import onda_params as gp
from parallelization_layer.utils.onda_dynamic_import import import_correct_layer_module


def raw_data_init(det):
    det['detect'] = Detector(gp.monitor_params['PsanaParallelizationLayer']['detector_name'])


def detector_distance_init(det):
    det['detect_dist'] = Detector(gp.monitor_params['PsanaParallelizationLayer']['detector_dist_epics_name'])


def beam_energy_init(det):
    det['beam_energy'] = Detector('EBeam')


def timetool_data_init(det):
    det['timetool'] = Detector(gp.monitor_params['PsanaParallelizationLayer']['timetool_epics_name'])


def acqiris_data_init(det):
    det['digitizer'] = Detector(gp.monitor_params['PsanaParallelizationLayer']['digitizer_name'])


def acqiris2_data_init(det):
    det['digitizer2'] = Detector(gp.monitor_params['PsanaParallelizationLayer']['digitizer2_name'])


def lcls_extra_init(det):
    det['LCLS_FEE_gas_enery_detect'] = Detector('FEEGasDetEnergy')
    det['LCLS_EncoderValue'] = Detector(gp.monitor_params['PsanaParallelizationLayer']['detector_dist_epics_name'])
    det['LCLS_photon_energy_eV'] = Detector('EBeam')



def raw_data_dataext(event):
    return event['det']['detect']()


def detector_distance_dataext(event):
    return event['det']['detect_dist']()


def beam_energy_dataext(event):
    return event['det']['beam_energy'].ebeamPhotonEnergy()


def timetool_data_dataext(event):
    return event['det']['time_tool']()


def acqiris_data_dataext(event):
    return event['det']['digitizer'].waveform(event['evt'])


def acqiris2_data_dataext(event):
    return event['det']['digitizer2'].waveform(event['evt'])




def lcls_extra_dataext(event):


    gas_energy_det = event['det']['LCLS_FEE_gas_enery_detect'].get()
    enc_value = event['det']['LCLS_EncoderValue']()
    evt_id = event['evt'].get(EventID)
    phot_en = event['det']['beam_energy'].ebeamPhotonEnergy()





    ret_dict = {}

    ret_dict['LCLS_EncoderValue'] = enc_value
    ret_dict['LCLS_f_11_ENRC'] = gas_energy_det.f11_ENRC
    ret_dict['LCLS_f_12_ENRC'] = gas_energy_det.f12_ENRC
    ret_dict['LCLS_f_21_ENRC'] = gas_energy_det.f21_ENRC
    ret_dict['LCLS_f_22_ENRC'] = gas_energy_det.f22_ENRC
    ret_dict['LCLS_machineTime'] = evt_id.time()[0]
    ret_dict['LCLS_machineTimeNanoSeconds'] = evt_id.time()[1]
    ret_dict['LCLS_photon_energy_eV'] = phot_en





in_layer = import_correct_layer_module('instrument_layer', gp.monitor_params)

avail_data_sources = ['raw_data', 'opal_data', 'detector_distance', 'beam_energy', 'pulse_energy', 'time_stamp',
                      'timetool_data', 'digitizer_data', 'digitizer2_data', 'lcls_extra']

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

    # Extract Opal camera data
    try:
        monitor.opal_data = opal_data(event)

    except Exception as e:
        print('Error when extracting opal data:', e)
        monitor.opal_data = None

    # Extract timetool data
    try:
        monitor.timetool_data = timetool_data(event)

    except Exception as e:
        print('Error when extracting timetool data:', e)
        monitor.timetool_data = None

    # Extract Acquiris data
    try:
        monitor.acqiris_data = acqiris_data(event)

    except Exception as e:
        print('Error when extracting aquiris data:', e)
        monitor.acqiris_data = None

    # Extract Acquiris data
    try:
        monitor.acqiris2_data = acqiris2_data(event)

    except Exception as e:
        print('Error when extracting aquiris2 data:', e)
        monitor.acqiris2_data = None
