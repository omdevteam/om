#!/usr/bin/env python
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

import sys
try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser
from traceback import extract_tb, print_exception

import parallelization_layer.utils.onda_params as op
from cfelpyutils.cfel_optarg import parse_parameters
from parallelization_layer.utils.onda_dynamic_import import import_correct_layer_module, import_class_from_layer
from parallelization_layer.utils.onda_optargs import parse_onda_cmdline_args


def exception_handler(exception_type, exception, traceback):

    if exception_type == SyntaxError:
        print_exception(exception_type, exception, traceback)
    else:
        print('OnDA Error:', exception)
        print('           ', 'Error Type:', exception_type.__name__)
        print('           ', 'File:', extract_tb(traceback)[-1][0])
        print('           ', 'Line:', extract_tb(traceback)[-1][1])


if __name__ == "__main__":
    args = parse_onda_cmdline_args()

    config = ConfigParser()
    config.read(args.ini)

    if not args.debug:
        sys.excepthook = exception_handler

    op.monitor_params = parse_parameters(config)

    processing_layer = import_correct_layer_module('processing_layer', op.monitor_params)
    Onda = import_class_from_layer('Onda', processing_layer)

    mon = Onda(args.source)
    mon.start(verbose=False)
