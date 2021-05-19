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
# Copyright 2020 -2021 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
OM's main function.

This module contains the main function that instantiates an OnDA Monitor when called.
"""

import importlib
import signal
import sys
from types import ModuleType
from typing import Type, TypeVar

import click

from om.data_retrieval_layer import base as data_ret_layer_base
from om.parallelization_layer import base as parallel_layer_base
from om.processing_layer import base as process_layer_base
from om.utils import exceptions, parameters

T = TypeVar("T")


def _import_class(layer: str, layer_filename: str, class_name: str) -> Type[T]:
    try:
        imported_layer: ModuleType = importlib.import_module(name=layer_filename)
    except ImportError:
        try:
            imported_layer = importlib.import_module(
                "om.{0}.{1}".format(layer, layer_filename)
            )
        except ImportError as exc:
            exc_type, exc_value = sys.exc_info()[:2]
            # TODO: Fix types
            if exc_type is not None:
                raise exceptions.OmInvalidDataBroadcastUrl(
                    "The python module file {0}.py with the implementation of the "
                    "{1} cannot be found or loaded due to the following error: "
                    "{2}: {3}.".format(
                        layer_filename, layer, exc_type.__name__, exc_value
                    )
                ) from exc
    try:
        imported_class: Type[T] = getattr(imported_layer, class_name)
    except AttributeError:
        raise exceptions.OmMissingDataEventHandlerError(
            "The {0} class cannot be found in the {1} file.".format(
                class_name, layer_filename
            )
        )

    return imported_class


@click.command()
@click.option(
    "--config",
    "-c",
    default="monitor.yaml",
    type=click.Path(),
    help="The path to a configuration file (default: monitor.yaml file in the current "
    "working directory)",
)
@click.option(
    "--debug",
    "-d",
    default=False,
    type=bool,
    is_flag=True,
    help=(
        "Disable the custom OM error handler for OM-related exceptions. Useful for "
        "debugging."
    ),
)
@click.argument("source", type=str)
def main(source: str, config: str, debug: bool) -> None:
    """
    OnDA Monitor. This script starts a online data analysis monitor that behaves
    according to the parameters defined in the provided configuration file. The monitor
    retrieves data from the source specified by SOURCE_STRING. The exact format of
    SOURCE_STRING depends on the specific Data Extraction Layer currently used by the
    monitor (see the relevant documentation). When the 'mpi' Parallelization Layer is
    used, this script should be launched via the 'mpirun' or 'mpiexec' commands.
    """
    # This function is turned into a script by the Click library. The docstring
    # above becomes the help string for the script.
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Sets a custom exception handler to deal with OM-specific exceptions.
    if not debug:
        sys.excepthook = exceptions.om_exception_handler

    monitor_parameters: parameters.MonitorParams = parameters.MonitorParams(config)

    data_retrieval_layer_filename: str = monitor_parameters.get_param(
        group="om", parameter="data_retrieval_layer", parameter_type=str, required=True
    )
    data_event_handler_name: str = monitor_parameters.get_param(
        group="om", parameter="data_event_handler", parameter_type=str, required=True
    )
    parallelization_layer_filename: str = monitor_parameters.get_param(
        group="om", parameter="parallelization_layer", parameter_type=str, required=True
    )
    processing_layer_filename: str = monitor_parameters.get_param(
        group="om", parameter="processing_layer", parameter_type=str, required=True
    )
    monitor_name = monitor_parameters.get_param(
        group="om", parameter="monitor", parameter_type=str, required=True
    )

    parallelization_engine_name: str = monitor_parameters.get_param(
        group="om",
        parameter="parallelization_engine",
        parameter_type=str,
        required=True,
    )

    parallelization_engine_class: Type[
        parallel_layer_base.OmParallelizationEngine
    ] = _import_class(
        layer="parallelization_layer",
        layer_filename=parallelization_layer_filename,
        class_name=parallelization_engine_name,
    )
    data_event_handler_class: Type[
        data_ret_layer_base.OmDataEventHandler
    ] = _import_class(
        layer="data_retrieval_layer",
        layer_filename=data_retrieval_layer_filename,
        class_name=data_event_handler_name,
    )
    monitor_class: Type[process_layer_base.OmMonitor] = _import_class(
        layer="processing_layer",
        layer_filename=processing_layer_filename,
        class_name=monitor_name,
    )

    monitor: process_layer_base.OmMonitor = monitor_class(
        monitor_parameters=monitor_parameters
    )
    data_event_handler: data_ret_layer_base.OmDataEventHandler = (
        data_event_handler_class(
            monitor_parameters=monitor_parameters,
            source=source,
        )
    )
    parallelization_engine: parallel_layer_base.OmParallelizationEngine = (
        parallelization_engine_class(
            data_event_handler=data_event_handler,
            monitor=monitor,
            monitor_parameters=monitor_parameters,
        )
    )

    parallelization_engine.start()
