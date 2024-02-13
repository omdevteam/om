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
OM's configuration parameter management.

This module contains classes and functions that can be used to manage a set of OM's
configuration parameters read from a configuration file.
"""
import pathlib
import sys
from typing import Any, Dict, TextIO, TypeVar

# TODO: Unify yaml library
import yaml  # type: ignore
from pydantic import BaseModel, ValidationError

from om.lib import exceptions

T = TypeVar("T", bound=BaseModel)


def load_configuration_parameters(
    *,
    config: str,
) -> Dict[str, Dict[str, Any]]:
    """
    #TODO: Documentation
    """

    try:
        open_file: TextIO
        with open(config, "r") as open_file:
            monitor_params: Dict[str, Dict[str, Any]] = yaml.safe_load(open_file)
    except OSError:
        raise exceptions.OmConfigurationFileReadingError(
            f"Cannot open or read the configuration file {config}."
        )
    except yaml.parser.ParserError as exc:
        raise exceptions.OmConfigurationFileSyntaxError(
            f"Syntax error in the configuration file: {exc}."
        ) from exc

    # Store group name within the group
    for group in monitor_params:
        monitor_params[group]["name"] = group

    # Add configuration file path to the om group
    monitor_params["om"]["configuration_file"] = str(pathlib.Path(config).absolute())

    return monitor_params


def validate_parameters(
    *,
    model: type[T],
    parameter_group: Dict[str, Any],
) -> T:
    """
    #TODO: Documentation
    """
    try:
        parameters: T = model.model_validate(parameter_group)
        return parameters
    except ValidationError:
        _, value, _ = sys.exc_info()
        if "name" in parameter_group:
            parameter_group_name: str = f"[{parameter_group['name']}]"
        else:
            parameter_group_name = "provided"
        raise RuntimeError(
            f"The following errors occurred while parsing the {parameter_group_name} "
            f"parameter group:\n{value}"
        ) from None


def get_parameter_group(
    *,
    configuration_parameters: Dict[str, Dict[str, Any]],
    group_name: str,
) -> Any:
    """
    Retrieves an OM's configuration parameter group.

    This function retrieves a configuration parameter group from the full set of
    OM's configuration parameters.

    Arguments:

        group: The name of the parameter group to retrieve.

    Returns:

        The parameter group.

    Raises:

        OmMissingParameterGroupError: Raised if the requested parameter group is
            not present in the full set of OM's configuration parameters.
    """
    if group_name not in configuration_parameters:
        raise exceptions.OmMissingParameterGroupError(
            f"Parameter group '[{group_name}]' is not in the configuration file."
        )
