# This file is part of OnDA.
#
# OnDA is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# OnDA is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with OnDA.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
OnDA entry point function.
"""
from __future__ import absolute_import, division, print_function

import sys

import click

from onda.utils import dynamic_import, exceptions, parameters


@click.command()
@click.option(
    "--config",
    "-c",
    default="monitor.ini",
    type=click.Path(),
    help="configuration file (default: monitor.ini file in the current working "
    "directory",
)
@click.option(
    "--debug",
    "-d",
    default=False,
    type=bool,
    is_flag=True,
    help="Disable custom OnDA error handler",
)
@click.argument("source", type=str)
def main(source, config, debug):
    # type: (str, str, bool) -> None
    """
    OnDA monitor. This script starts a monitor that is based on the provided
    configuration file and retrieves data from the specified source. When the 'mpi'
    Parallelization Layer is used, this script should be launched via the 'mpirun' or
    'mpiexec' commands.

    SOURCE: the source of data for the OnDA monitor. The exact format of this string
    depends on the specific Data Extraction Layer currently used by the OnDA monitor
    (see documentation).
    """
    # Sets a custom exception handler to deal with OnDA-specific exceptions.
    if not debug:
        sys.excepthook = exceptions.onda_exception_handler

    monitor_parameters = parameters.MonitorParams(config)
    processing_layer_filename = monitor_parameters.get_param(
        section="Onda", parameter="processing_layer", type_=str, required=True
    )
    processing_layer = dynamic_import.import_processing_layer(processing_layer_filename)
    monitor = processing_layer.OndaMonitor(
        source=source, monitor_parameters=monitor_parameters
    )
    monitor.start()
