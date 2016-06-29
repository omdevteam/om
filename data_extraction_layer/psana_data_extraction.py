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


import psana

from parallelization_layer.utils import (
    global_params as gp,
    dynamic_import as dyn_imp
)


def pulse_energy_dataext(event):
    gas = event['evt'].get(psana.Bld.BldDataFEEGasDetEnergyV1, psana.Source('BldInfo(FEEGasDetEnergy)'))

    return (gas.f_11_ENRC() + gas.f_12_ENRC() + gas.f_21_ENRC() + gas.f_22_ENRC()) / 4.


def beam_energy_dataext(event):
    return event['evt'].get(psana.Bld.BldDataEBeamV7, psana.Source('BldInfo(EBeam)')).ebeamPhotonEnergy()


def detector_distance_dataext(event):
    return event['det_dist']()


def acqiris_data_dataext(event):
    return event['evt'].get(psana.Acqiris.DataDescV1,
                            psana.Source(gp.monitor_params['PsanaParallelizationLayer']['digitizer_psana_source'])
                            ).data(gp.monitor_params['PsanaParallelizationLayer'][
                                                     'digitizer_psana_channel']).waveforms()


in_layer = dyn_imp.import_layer_module('instrument_layer', gp.monitor_params)

data_ext_funcs = ['raw_data', 'opal_data', 'detector_distance', 'beam_energy', 'pulse_energy', 'timestamp',
                  'acqiris_data']

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


def extract(event, monitor):

    # Extract detector data in slab format
    try:
        monitor.raw_data = raw_data(event)

    except Exception as e:
        print ('Error when extracting raw_data: {0}'.format(e))
        monitor.raw_data = None

    # Extract pulse energy in mJ
    try:
        monitor.pulse_energy = pulse_energy(event)

    except Exception as e:
        print ('Error when extracting pulse_energy: {0}'.format(e))
        monitor.pulse_energy = None

    # Extract beam energy in eV
    try:
        monitor.beam_energy = beam_energy(event)

    except Exception as e:
        print ('Error when extracting beam_energy: {0}'.format(e))
        monitor.beam_energy = None

    # Extract detector distance in mm
    try:
        monitor.detector_distance = detector_distance(event)

    except Exception as e:
        print ('Error when extracting detector_distance: {0}'.format(e))
        monitor.detector_distance = None

    # Extract Opal camera data
    try:
        monitor.opal_data = opal_data(event)

    except Exception as e:
        print ('Error when extracting opal_data: {0}'.format(e))
        monitor.opal_data = None

    # Extract Acquiris data
    try:
        monitor.acqiris_data = acqiris_data(event)

    except Exception as e:
        print ('Error when extracting tof_data: {0}'.format(e))
        monitor.tof_data = None
