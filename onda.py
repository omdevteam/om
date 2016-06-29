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


try:
    import configparser
except ImportError:
    import ConfigParser as configparser

import cfelpyutils.cfeloptarg as cfel_oa
from parallelization_layer.utils import (
    onda_optargs as onda_oa,
    global_params as gp,
    dynamic_import as dyn_imp
)

if __name__ == "__main__":
    args = onda_oa.parse_onda_cmdline_args()

    config = configparser.ConfigParser()
    config.read(args.ini)

    monitor_params = cfel_oa.parse_parameters(config)
    gp.monitor_params = monitor_params

    processing_layer = dyn_imp.import_layer_module('processing_layer', monitor_params)
    Onda = getattr(processing_layer, 'Onda')

    mon = Onda(args.source, monitor_params)
    mon.start(verbose=False)
