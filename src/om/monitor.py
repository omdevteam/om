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

This module contains the main function that tarts an OnDA Monitor.
"""

import importlib
import signal
import sys
from types import ModuleType
from typing import Type, TypeVar, Union, cast

import click

from om.data_retrieval_layer import base as drl_base
from om.parallelization_layer import base as pa_base
from om.processing_layer import base as pr_base
from om.utils import exceptions, parameters

T = TypeVar("T")


def _import_class(*, layer: str, class_name: str) -> Type[T]:
    try:
        imported_layer: ModuleType = importlib.import_module(name=layer)
    except ImportError:
        try:
            imported_layer = importlib.import_module(f"om.{layer}")
        except ImportError as exc:
            exc_type, exc_value = sys.exc_info()[:2]
            # TODO: Fix types
            if exc_type is not None:
                raise exceptions.OmInvalidDataBroadcastUrl(
                    f"The python module file {layer}.py cannot be found or loaded due "
                    f"to the following error: {exc_type.__name__}: {exc_value}"
                ) from exc
    try:
        imported_class: Type[T] = getattr(imported_layer, class_name)
    except AttributeError:
        raise exceptions.OmMissingDataRetrievalClassError(
            f"The {class_name} class cannot be found in the {layer} file."
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
def main(*, source: str, config: str, debug: bool) -> None:
    """
    OnDA Monitor. This script starts an OnDA Monitor whose behavior is defined by the
    configuration parameters read from a provided file. The monitor retrieves data
    events from the source specified by the SOURCE argument, and starts processing
    them. The exact format of SOURCE depends on the specific Data Extraction Layer used
    by the monitor (see the relevant documentation). When OM uses the `mpi`
    Parallelization Layer, this script should be launched via the `mpirun` or `mpiexec`
    commands.
    """
    # This function is turned into a script by the Click library. The docstring
    # above becomes the help string for the script.
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Sets a custom exception handler to deal with OM-specific exceptions.
    if not debug:
        sys.excepthook = exceptions.om_exception_handler

    monitor_parameters: parameters.MonitorParams = parameters.MonitorParams(
        config, source=source
    )

    data_retrieval_layer_class_name: str = monitor_parameters.get_parameter(
        group="om",
        parameter="data_retrieval_layer",
        parameter_type=str,
        required=True,
    )

    parallelization_layer_class_name: str = monitor_parameters.get_parameter(
        group="om",
        parameter="parallelization_layer",
        parameter_type=str,
        required=True,
    )

    processing_layer_class_name: str = monitor_parameters.get_parameter(
        group="om",
        parameter="processing_layer",
        parameter_type=str,
        required=True,
    )

    parallelization_layer_class: Type[pa_base.OmParallelization] = _import_class(
        layer="parallelization_layer",
        class_name=parallelization_layer_class_name,
    )
    data_retrieval_layer_class: Type[drl_base.OmDataRetrieval] = _import_class(
        layer="data_retrieval_layer",
        class_name=data_retrieval_layer_class_name,
    )
    processing_layer_class: Type[pr_base.OmProcessing] = _import_class(
        layer="processing_layer",
        class_name=processing_layer_class_name,
    )

    processing_layer: pr_base.OmProcessing = processing_layer_class(
        monitor_parameters=monitor_parameters
    )
    data_retrieval_layer: drl_base.OmDataRetrieval = data_retrieval_layer_class(
        monitor_parameters=monitor_parameters,
        source=source,
    )
    parallelization_layer: pa_base.OmParallelization = parallelization_layer_class(
        data_retrieval_layer=data_retrieval_layer,
        processing_layer=processing_layer,
        monitor_parameters=monitor_parameters,
    )

    parallelization_layer.start()
