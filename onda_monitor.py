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

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import importlib as il
import sys
from configparser import ConfigParser

import onda.cfelpyutils.cfel_optarg as coa
import onda.utils.argument_parsing as ap
import onda.utils.parameters as op
from onda.utils.exceptions import onda_exception_handler


if __name__ == "__main__":

    sys.excepthook = onda_exception_handler

    processing_layer = il.import_module(
        'onda.processing_layer.{0}'.format(
            op.param('Onda', 'processing_layer', str, required=True)
        )
    )

    args = ap.parse_onda_cmdline_args()
    config = ConfigParser()
    config.read(args.ini)

    op.monitor_params = coa.parse_parameters(config)

    OndaMonitor = getattr(processing_layer, 'OndaMonitor')

    mon = OndaMonitor(args.source)
    mon.start(verbose=False)
