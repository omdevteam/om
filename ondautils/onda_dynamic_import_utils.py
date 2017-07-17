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
from future.utils import raise_from

import importlib
import inspect

from ondautils.onda_exception_utils import MissingParameterFileSection, MissingParameter, DynamicImportError


def import_correct_layer_module(layer, monitor_params):
    layer_paths = {
        'processing_layer': 'processing_layer.',
        'facility_layer': 'facility_layer.',
        'data_extraction_layer': 'data_extraction_layer.',
        'detector_layer': 'detector_layer.',
    }

    if 'Onda' not in monitor_params:
        raise MissingParameterFileSection('[Onda] section is not present in the configuration file.')

    if layer not in monitor_params['Onda']:
        raise MissingParameter('Module for {0} not specified in the configuration file.'.format(layer))

    try:
        m = importlib.import_module(
            '{0}{1}'.format(
                layer_paths.get(layer, ''),
                (monitor_params['Onda'][layer]))
        )
    except ImportError as e:
        raise_from(DynamicImportError('Error when importing the {0}: {1}'.format(layer, e)), None)
    else:
        return m


def import_function_from_layer(function_, layer):
    try:
        ret = getattr(layer, function_)
    except AttributeError:
        raise_from(DynamicImportError('Error importing function {0} from layer {1}, the function does not '
                                      'exist.'.format(function_, layer.__name__)), None)
    else:
        if not inspect.isfunction(ret):
            raise_from(DynamicImportError('Error importing function {0} from layer {1}, {0} is not a function'.format(
                function_, layer.__name__)), None)
        else:
            return ret


def import_class_from_layer(cls, layer):
    try:
        ret = getattr(layer, cls)
    except AttributeError:
        raise_from(DynamicImportError('Error importing class {0} from layer {1}, {0} does not exist.'.format(
            cls, layer.__name__)), None)
    else:
        if not inspect.isclass(ret):
            raise_from(DynamicImportError('Error importing class {0} from layer {1}, {0} is not a class.'.format(
                cls, layer.__name__)), None)
        else:
            return ret


def import_list_from_layer(lst, layer):
    try:
        ret = getattr(layer, lst)
    except AttributeError:
        raise_from(DynamicImportError('Error importing list {0} from layer {1}, {0} does not exist.'.format(
            lst, layer.__name__)), None)
    else:
        if not isinstance(ret, list):
            raise_from(DynamicImportError('Error importing list {0} from layer {1}, {0} is not a list.'.format(
                lst, layer.__name__)), None)
        else:
            return ret


def import_str_from_layer(string, layer):
    try:
        ret = getattr(layer, string)
    except AttributeError:
        raise_from(DynamicImportError('Error importing string {0} from layer {1}, {0} does not exist.'.format(
            string, layer.__name__)), None)
    else:
        if not isinstance(ret, str):
            raise_from(DynamicImportError('Error importing string {0} from layer {1}, {0} is not a list.'.format(
                string, layer.__name__)), None)
        else:
            return ret


def import_class_from_module(cls, module_):
    try:
        ret = getattr(module_, cls)
    except AttributeError:
        raise_from(DynamicImportError('Error importing class {0} from layer {1}, {0} does not exist.'.format(
            cls, module_.__name__)), None)
    else:
        if not inspect.isclass(ret):
            raise_from(DynamicImportError('Error importing class {0} from layer {1}, {0} is not a class.'.format(
                cls, module_.__name__)), None)
        else:
            return ret
