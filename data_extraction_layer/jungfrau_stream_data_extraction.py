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

from io import BytesIO
import ondautils.onda_dynamic_import_utils as di
import ondautils.onda_param_utils as op

in_layer = di.import_correct_layer_module('instrument_layer', op.monitor_params)
num_events_in_file = di.import_function_from_layer('num_events_in_file', in_layer)

file_extensions = ['.cbf']

data_extraction_funcs = [x.strip() for x in op.param('Onda', 'required_data', list, required=True)]
for func in data_extraction_funcs:
    try:
        globals()[func] = getattr(in_layer, func)
    except AttributeError:
        if func not in globals():
            raise RuntimeError('Data extraction function not defined for the following '
                               'data type: {0}'.format(func))


def open_file(data):
    data_stringio = BytesIO(data)
    return data_stringio


def close_file(data):
    data.close()


def num_events(evt):
    return num_events_in_file(evt)


def extract(evt, monitor):
    for entry in data_extraction_funcs:
        try:
            setattr(monitor, entry, globals()[entry](evt))
        except:
            print('Error extracting {}'.format(entry))
            setattr(monitor, entry, None)
