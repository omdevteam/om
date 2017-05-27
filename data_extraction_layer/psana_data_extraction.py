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

import ondautils.onda_dynamic_import_utils as di
import ondautils.onda_param_utils as op
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


def timestamp(event):
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

data_extraction_funcs = [x.strip() for x in op.param('Onda', 'required_data', list, required=True)]

for func in data_extraction_funcs:
    try:
        globals()[func + '_init'] = getattr(in_layer, func + '_init')
    except AttributeError:
        if func + '_init' not in globals():
            raise RuntimeError('Initialization function not defined for the following '
                               'data type: {0}'.format(func))

for func in data_extraction_funcs:
    try:
        if func == 'raw_data' and op.param('PsanaParallelizationLayer', 'pedestals_only', bool):
            globals()[func] = getattr(in_layer, func + '_pedestals_only')
        else:
            globals()[func] = getattr(in_layer, func)
    except AttributeError:
            if func == 'raw_data' and op.param('PsanaParallelizationLayer', 'pedestals_only', bool):
                if func + '_pedestals_only' not in globals():
                    raise RuntimeError('Data extraction function not defined for the following '
                                       'data type: {0} (pedestals_only)'.format(func))
            else:
                if func not in globals():
                    raise RuntimeError('Data extraction function not defined for the following '
                                       'data type: {0}'.format(func))


def initialize(det):
    for init_data_source in data_extraction_funcs:
        globals()[init_data_source + '_init'](det)


def extract(evt, monitor):
    for entry in data_extraction_funcs:
        try:
            setattr(monitor, entry, globals()[entry](evt))
        except:
            print('Error extracting {}'.format(entry))
            setattr(monitor, entry, None)
