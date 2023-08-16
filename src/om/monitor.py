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
from typing import Dict, Type, Union, cast

import click

from om.lib.layer_management import import_class_from_layer
from om.lib.parameters import MonitorParameters
from om.lib.rich_console import console, set_custom_theme, set_null_theme
from om.protocols.data_retrieval_layer import OmDataRetrievalProtocol
from om.protocols.parallelization_layer import OmParallelizationProtocol
from om.protocols.processing_layer import OmProcessingProtocol


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

    monitor_parameters: MonitorParameters = MonitorParameters(config=config)

    colors_in_rich_console: Union[bool, None] = monitor_parameters.get_parameter(
        group="om",
        parameter="colors_in_rich_console",
        parameter_type=bool,
    )

    if colors_in_rich_console is False:
        set_null_theme()
    else:
        custom_rich_console_colors: Union[
            Dict[str, str], None
        ] = monitor_parameters.get_parameter(
            group="om",
            parameter="custom_rich_console_colors",
            parameter_type=dict,
        )

        if custom_rich_console_colors is not None:
            set_custom_theme(theme_dict=custom_rich_console_colors)

    parallelization_layer_class_name: str = monitor_parameters.get_parameter(
        group="om",
        parameter="parallelization_layer",
        parameter_type=str,
        required=True,
    )

    if parallelization_layer_class_name == "MpiParallelization":
        try:
            from mpi4py import MPI

            mpi_size: int = MPI.COMM_WORLD.Get_size()
            mpi_rank: int = MPI.COMM_WORLD.Get_rank()

            if node_pool_size != 0:
                if mpi_rank == 0:
                    console.print(
                        "OM Warning: ignoring --node-pool-size or -n option to this "
                        "script and using the number of nodes defined by MPI "
                        f"({mpi_size}).",
                        style="warning",
                    )

            node_pool_size = mpi_size

        except ImportError:
            console.print(
                "OM ERROR: mpi parallelization selected, but mpi4py failed to import.",
                style="error",
            )
            sys.exit(1)
    else:
        if node_pool_size == 0:
            console.print(
                "OM ERROR: When not using the mpi parallelization layer, the "
                "number of nodes must be specified using the --node-pool-size or "
                "-n option to this script.",
                style="error",
            )
            sys.exit(1)

    monitor_parameters.add_source_and_node_pool_size_information(
        source=source,
        node_pool_size=node_pool_size,
    )

    data_retrieval_layer_class_name: str = monitor_parameters.get_parameter(
        group="om",
        parameter="data_retrieval_layer",
        parameter_type=str,
        required=True,
    )

    processing_layer_class_name: str = monitor_parameters.get_parameter(
        group="om",
        parameter="processing_layer",
        parameter_type=str,
        required=True,
    )

    parallelization_layer_class: Type[OmParallelizationProtocol] = cast(
        Type[OmParallelizationProtocol],
        import_class_from_layer(
            layer_name="parallelization_layer",
            class_name=parallelization_layer_class_name,
        ),
    )
    data_retrieval_layer_class: Type[OmDataRetrievalProtocol] = cast(
        Type[OmDataRetrievalProtocol],
        import_class_from_layer(
            layer_name="data_retrieval_layer",
            class_name=data_retrieval_layer_class_name,
        ),
    )
    processing_layer_class: Type[OmProcessingProtocol] = cast(
        Type[OmProcessingProtocol],
        import_class_from_layer(
            layer_name="processing_layer",
            class_name=processing_layer_class_name,
        ),
    )

    processing_layer: OmProcessingProtocol = processing_layer_class(
        monitor_parameters=monitor_parameters
    )
    data_retrieval_layer: OmDataRetrievalProtocol = data_retrieval_layer_class(
        monitor_parameters=monitor_parameters,
        source=source,
    )
    parallelization_layer: OmParallelizationProtocol = parallelization_layer_class(
        data_retrieval_layer=data_retrieval_layer,
        processing_layer=processing_layer,
        monitor_parameters=monitor_parameters,
    )

    parallelization_layer.start()
