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
# Copyright 2020 -2023 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
OM's main function.

This module contains the main function that tarts an OnDA Monitor.
"""

import signal
import sys
from typing import Any, Dict, Type

import click
from pydantic import BaseModel

from om.lib.layer_management import import_class_from_layer
from om.lib.logging import log
from om.lib.parameters import (
    get_parameter_group,
    load_configuration_parameters,
    validate_parameters,
)
from om.typing import (
    OmDataRetrievalProtocol,
    OmParallelizationProtocol,
    OmProcessingProtocol,
)


class _MonitorParameters(BaseModel):
    parallelization_layer: str
    data_retrieval_layer: str
    processing_layer: str


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
    "--node-pool-size",
    "-n",
    default=0,
    type=int,
    help=(
        "The total number of nodes in the OM pool, including all the processing nodes "
        "and the collecting node."
    ),
)
@click.argument("source", type=str)
def main(*, source: str, node_pool_size: int, config: str) -> None:
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

    configuration_parameters: Dict[str, Dict[str, Any]] = load_configuration_parameters(
        config=config
    )

    om_parameter_group: Dict[str, Any] = get_parameter_group(
        configuration_parameters=configuration_parameters, group_name="om"
    )

    data_retrieval_layer_parameter_group: Dict[str, Any] = get_parameter_group(
        configuration_parameters=configuration_parameters,
        group_name="data_retrieval_layer",
    )

    monitor_parameters: _MonitorParameters = validate_parameters(
        model=_MonitorParameters,
        parameter_group=om_parameter_group,
    )

    if monitor_parameters.parallelization_layer == "MpiParallelization":
        try:
            from mpi4py import MPI

            mpi_size: int = MPI.COMM_WORLD.Get_size()
            mpi_rank: int = MPI.COMM_WORLD.Get_rank()

            if node_pool_size != 0:
                if mpi_rank == 0:
                    log.warning(
                        "OM Warning: ignoring --node-pool-size or -n option to this "
                        "script and using the number of nodes defined by MPI "
                        f"({mpi_size}).",
                    )

            node_pool_size = mpi_size

        except ImportError:
            log.error(
                "OM ERROR: mpi parallelization selected, but mpi4py failed to import.",
            )
            sys.exit(1)
    else:
        if node_pool_size == 0:
            log.error(
                "OM ERROR: When not using the mpi parallelization layer, the "
                "number of nodes must be specified using the --node-pool-size or "
                "-n option to this script.",
            )
            sys.exit(1)

    configuration_parameters["om"]["source"] = source
    configuration_parameters["om"]["node_pool_size"] = node_pool_size

    parallelization_layer_class: Type[
        OmParallelizationProtocol
    ] = import_class_from_layer(
        layer_name="parallelization_layer",
        class_name=monitor_parameters.parallelization_layer,
    )
    data_retrieval_layer_class: Type[OmDataRetrievalProtocol] = import_class_from_layer(
        layer_name="data_retrieval_layer",
        class_name=monitor_parameters.data_retrieval_layer,
    )
    processing_layer_class: Type[OmProcessingProtocol] = import_class_from_layer(
        layer_name="processing_layer", class_name=monitor_parameters.processing_layer
    )

    processing_layer: OmProcessingProtocol = processing_layer_class(
        monitor_parameters=configuration_parameters
    )
    data_retrieval_layer: OmDataRetrievalProtocol = data_retrieval_layer_class(
        parameters=data_retrieval_layer_parameter_group,
        source=source,
    )
    parallelization_layer: OmParallelizationProtocol = parallelization_layer_class(
        data_retrieval_layer=data_retrieval_layer,
        processing_layer=processing_layer,
        monitor_parameters=configuration_parameters,
    )

    parallelization_layer.start()
