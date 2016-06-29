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


import importlib as il


def import_layer_module(layer, monitor_params):

    layer_paths = {
        'processing_layer': 'processing_layer.',
        'parallelization_layer': 'parallelization_layer.',
        'data_extraction_layer':
            'data_extraction_layer.',
        'instrument_layer':
            'data_extraction_layer.instrument_layer.',
    }

    return il.import_module(
        '{0}{1}'.format(
            layer_paths.get(layer, ''),
            monitor_params['Backend'][layer])
        )
