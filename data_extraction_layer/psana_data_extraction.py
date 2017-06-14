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

from collections import namedtuple
import ondautils.onda_dynamic_import_utils as di
import ondautils.onda_param_utils as op
import psana


EventData = namedtuple('EventData', ['filehandle', 'filename', 'filectime', 'num_events_per_file', 'shot_offset',
                                     'monitor_params'])


def raw_data_init(detector):
    return psana.Detector(op.monitor_params['PsanaParallelizationLayer']['detector_name'])


def timestamp_init(_):
    return None


def detector_distance_init():
    return psana.Detector(op.monitor_params['PsanaParallelizationLayer']['detector_dist_epics_name'])


def beam_energy_init():
    return psana.Detector('EBeam'.encode('ascii'))


def timetool_data_init():
    return psana.Detector(op.monitor_params['PsanaParallelizationLayer']['timetool_epics_name'])


def digitizer_data_init():
    return psana.Detector(op.monitor_params['PsanaParallelizationLayer']['digitizer_name'])


def digitizer2_data_init():
    return psana.Detector(op.monitor_params['PsanaParallelizationLayer']['digitizer2_name'])


def event_codes_init():
    return psana.Detector('evr0')


def timestamp(event):
    return event.detector['timestamp']


def detector_distance(event):
    return event.detector['raw_data']['detect_dist']()


def beam_energy(event):
    return event.detector['beam_energy'].get(event.evt).ebeamPhotonEnergy()


def timetool_data(event):
    return event.det['timetool_data']()


def digitizer_data(event):
    return event.det['digitizer_data'].waveform(event.evt)


def digitizer2_data(event):
    return event.det['digitizer2_data'].waveform(event.evt)


def event_codes_dataext(event):
    return event.det['event_codes'].eventCodes(event.evt)


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
    detector = {}
    for init_data_source in data_extraction_funcs:
        detector[init_data_source] = globals().init_data_source + '_init'()


def extract(event, monitor):
    for entry in data_extraction_funcs:
        try:
            setattr(monitor, entry, globals()[entry](event))
        except:
            print('Error extracting {}'.format(entry))
            setattr(monitor, entry, None)
