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

import subprocess

import click
from rich import console

from om.utils import parameters


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
@click.option(
    "--node_pool_size",
    "-n",
    default=False,
    type=int,
    required=True,
    help=(
        "The total number of nodes in the OM pool, including all the processing nodes "
        "and the collecting node."
    ),
)
@click.argument("source", type=str)
def main(*, source: str, node_pool_size: int, config: str, debug: bool) -> None:
    """ """
    monitor_parameters: parameters.MonitorParams = parameters.MonitorParams(
        config=config
    )

    parallelization_layer: str = monitor_parameters.get_parameter(
        group="om",
        parameter="parallelization_layer",
        parameter_type=str,
        required=True,
    )

    if parallelization_layer == "MpiParallelization":
        om_process: subprocess.Popen[str] = subprocess.Popen(
            f"mpirun --np "
            f"{node_pool_size} "
            "om_monitor.py "
            f"{source} "
            f"{node_pool_size}",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True,
            encoding="utf-8",
        )
    else:
        om_process = subprocess.Popen(
            [
                "om_monitor.py",
                f"{source}",
                f"{node_pool_size}",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            encoding="utf-8",
        )
