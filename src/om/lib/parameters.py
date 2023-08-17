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

This module contains classes and functions that can be used to manage and validate a
set of OM's configuration parameters from a configuration file.
"""
import pathlib
from typing import Any, Dict, TextIO, Union

import yaml  # type: ignore

from om.lib import exceptions


def get_parameter_from_parameter_group(
    *,
    group: Dict[str, Any],
    parameter: str,
    parameter_type: Any = None,
    required: bool = False,
    default: Any = None,
) -> Any:
    """
    Retrieves the value of an OM's configuration parameter from a parameter group.

    This function retrieves the value of a single configuration parameter from a
    provided group of configuration parameters. Optionally, it validates the type of
    the parameter according to the following rules:

    * If the value of the `required` argument is True and the parameter cannot be
        found in OM's configuration file, this function raises an exception.

    * If the value of the `required` argument is False and the parameter cannot be
        found in OM's configuration file, this function returns None, or the value
        of the `default` argument, if it is provided.

    * If a type is specified for the parameter (the `parameter_type` argument is
        not None) and the type of the retrieved parameter does not match the
        specified one, this function raises an exception.

    Arguments:

        group: The parameter group containing the parameter to retrieve.

        parameter (str): The name of the parameter to retrieve.

        parameter_type: The type of the parameter to retrieve. If a type is
            specified in this argument, the type of the retrieved parameter will be
            validated. Defaults to None.

        required: True if the parameter is strictly required and must be present
            in OM's configuration file, False otherwise. Defaults to False.

        default: The default value that this function should return if the
            requested parameter cannot be found and the parameter is not strictly
            required.


    Returns:

        The value of the requested parameter, or None, if the parameter was not
        found in OM's configuration file, it is not required, and a default value
        has not been provided.

    Raises:


        OmMissingParameterError: Raised if the parameter is required but cannot be
            found in the parameter group.

        OmWrongParameterTypeError: Raised if the requested parameter type does not
            match the type of the retrieved configuration parameter.
    """
    ret: Any = group.get(parameter)
    if ret is None:
        if required is True:
            raise exceptions.OmMissingParameterError(
                f"Parameter {parameter} in group [{group['name']}] was not found, but "
                "is required."
            )
        else:
            return default

    else:
        if parameter_type is not None:
            requested_parameter_type: str = str(parameter_type).split()[1][1:-2]
            real_parameter_type: str = str(type(ret)).split()[1][1:-2]
            if parameter_type is str:
                if not isinstance(ret, str):
                    raise exceptions.OmWrongParameterTypeError(
                        f"Wrong type for parameter {parameter}: should be "
                        f"{requested_parameter_type}, is {real_parameter_type}."
                    )
            elif parameter_type is float:
                if not isinstance(ret, float) and not isinstance(ret, int):
                    raise exceptions.OmWrongParameterTypeError(
                        f"Wrong type for parameter {parameter}: should be "
                        f"{requested_parameter_type}, is {real_parameter_type}."
                    )
            elif not isinstance(ret, parameter_type):
                raise exceptions.OmWrongParameterTypeError(
                    f"Wrong type for parameter {parameter}: should be "
                    f"{requested_parameter_type}, is {real_parameter_type}."
                )

        return ret


class MonitorParameters:
    """
    See documentation for the `__init__` function.
    """

    def __init__(
        self,
        *,
        config: str,
        source: Union[str, None] = None,
        node_pool_size: Union[int, None] = None,
    ) -> None:
        """
        Storage, retrieval and validation of OM's configuration parameters.

        This class stores a set of OM's configuration parameters, subdivided in groups.
        It is initialized with a set of parameters read from a configuration file
        written in YAML format. It then allows single parameters or group of parameters
        to be retrieved, and optionally validated.

        In addition to the set of parameters read from the file, this class stores
        the path to the configuration file itself, in a parameter named
        `configuration_file` within the `om` parameter group.

        Arguments:

            config: The absolute or relative path to a YAML-format configuration file.

        Raises:

            OMConfigurationFileSyntaxError: Raised if there is a syntax error in OM's
                configuration file.
        """

        self._monitor_params: Any = {}

        try:
            open_file: TextIO
            with open(config, "r") as open_file:
                self._monitor_params = yaml.safe_load(open_file)
        except OSError:
            raise exceptions.OmConfigurationFileReadingError(
                f"Cannot open or read the configuration file {config}."
            )
        except (
            yaml.parser.ParserError
        ) as exc:  # pyright: ignore[reportGeneralTypeIssues]  # noqa: E501
            raise exceptions.OmConfigurationFileSyntaxError(
                f"Syntax error in the configuration file: {exc}."
            ) from exc

        # Store group name within the group
        for group in self._monitor_params:
            self._monitor_params[group]["name"] = group

        # Add configuration file path to the om group
        self._monitor_params["om"]["configuration_file"] = str(
            pathlib.Path(config).absolute()
        )

    def get_parameter_group(
        self,
        *,
        group: str,
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
        if group not in self._monitor_params:
            raise exceptions.OmMissingParameterGroupError(
                f"Parameter group '{group}' is not in the configuration file."
            )
        return self._monitor_params[group]

    def get_parameter(
        self,
        *,
        group: str,
        parameter: str,
        parameter_type: Any = None,
        required: bool = False,
        default: Any = None,
    ) -> Any:
        """
        Retrieves an OM's configuration parameter.

        This function retrieves a single parameter from the full set of OM's
        configuration parameters. Optionally, it also validates the type of the
        parameter, according to the following rules:

        * If the value of the `required` argument is True and the parameter cannot be
          found in OM's configuration file, this function raises an exception.

        * If the value of the `required` argument is False and the parameter cannot be
          found in OM's configuration file, this function returns None, or the value
          of the `default` argument, if it is provided.

        * If a type is specified for the parameter (the `parameter_type` argument is
          not None) and the type of the retrieved parameter does not match the
          specified one, this function raises an exception.

        Arguments:

            group: The name of the parameter group from which the parameter must be
                retrieved.

            parameter (str): The name of the parameter to retrieve.

            parameter_type: The type of the parameter to retrieve. If a type is
                specified in this argument, the type of the retrieved parameter will be
                validated. Defaults to None.

            required: True if the parameter is strictly required and must be present
                in OM's configuration file, False otherwise. Defaults to False.

            default: The default value that this function should return if the
                requested parameter cannot be found and the parameter is not strictly
                required.

        Returns:

            The value of the requested parameter, or None, if the parameter was not
            found in OM's configuration file, it is not required, and a default value
            has not been provided.

        Raises:

            OmMissingParameterGroupError: Raised if the requested parameter group is
                not present in the full set of OM's configuration parameters.

            OmMissingParameterError: Raised if the parameter is required but cannot be
                found in the full set of OM's configuration parameters.

            OmWrongParameterTypeError: Raised if the requested parameter type does not
                match the type of the retrieved configuration parameter.
        """
        return get_parameter_from_parameter_group(
            group=self.get_parameter_group(group=group),
            parameter=parameter,
            parameter_type=parameter_type,
            required=required,
            default=default,
        )

    def add_source_and_node_pool_size_information(
        self,
        *,
        source: Union[str, None] = None,
        node_pool_size: Union[int, None] = None,
    ) -> None:
        """
        Adds source and node pool size information to the parameter set.

        If the name of a data source is provided as an input parameter, this function
        adds it to the parameter set stored by this class, and makes it available as a
        parameter with the name `source` within the `om` group. If the total number of
        nodes in OM's node pool is also provided, the information will added to the
        parameter set and made available as a parameter named `node_pool_size` within
        the `om` group.

        Arguments:

            source: A string describing the data event source.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        if source:
            self._monitor_params["om"]["source"] = source
        if node_pool_size:
            self._monitor_params["om"]["node_pool_size"] = node_pool_size
