# This file is part of OM.
#
# OM is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# OM is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with OM.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2020 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
OM main function.

This module contains the main function that instantiates an OM monitor.
"""
from __future__ import absolute_import, division, print_function

import sys
from types import ModuleType

import click

from om.utils import dynamic_import, exceptions, parameters


@click.command()
@click.option(
    "--config",
    "-c",
    default="monitor.yaml",
    type=click.Path(),
    help="configuration file (default: monitor.yaml file in the current working "
    "directory",
)
@click.option(
    "--debug",
    "-d",
    default=False,
    type=bool,
    is_flag=True,
    help="Disable custom OM error handler",
)
@click.argument("source", type=str)
def main(source, config, debug):
    # type: (str, str, bool) -> None
    """
    OM monitor. This script starts a monitor that runs according to the provided
    configuration file and retrieves data from the specified source. When the 'mpi'
    Parallelization Layer is used, this script should be launched via the 'mpirun' or
    'mpiexec' commands.

    SOURCE: the source of data for the OM monitor. The exact format of this string
    depends on the specific Data Extraction Layer currently used (see documentation).
    """
    # Sets a custom exception handler to deal with OM-specific exceptions.
    if not debug:
        sys.excepthook = exceptions.om_exception_handler

    monitor_parameters = parameters.MonitorParams(
        config
    )  # type: parameters.MonitorParams
    processing_layer_filename = monitor_parameters.get_param(
        group="om", parameter="processing_layer", parameter_type=str, required=True
    )  # type: str
    processing_layer = dynamic_import.import_processing_layer(
        processing_layer_filename
    )  # type: ModuleType
    monitor = processing_layer.OmMonitor(  # type: ignore
        source=source, monitor_parameters=monitor_parameters
    )
    # TODO: Fix types.
    monitor.start()
