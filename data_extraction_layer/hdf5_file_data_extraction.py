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

import h5py

from ondautils.onda_exception_utils import MissingDataExtractionFunction
import ondautils.onda_dynamic_import_utils as di
import ondautils.onda_param_utils as op


in_layer = di.import_correct_layer_module('instrument_layer', op.monitor_params)
num_events_in_file = di.import_function_from_layer('num_events_in_file', in_layer)

data_extraction_funcs = [x.strip() for x in op.param('Onda', 'required_data', list, required=True)]
for func in data_extraction_funcs:
    try:
        globals()[func] = getattr(in_layer, func)
    except AttributeError:
        if func not in globals():
            raise MissingDataExtractionFunction('Data extraction function not defined for the following '
                                                'data type: {0}'.format(func)) from None


def open_file(filename):
    f = h5py.File(filename, 'r')
    return f


def close_file(filehandle):
    filehandle.close()


def num_events(filehandle):
    return num_events_in_file(filehandle)


def extract(event, monitor):
    for entry in data_extraction_funcs:
        try:
            setattr(monitor, entry, globals()[entry](event))
        except:
            print('OnDA Warning: Error extracting {}'.format(entry))
            setattr(monitor, entry, None)
