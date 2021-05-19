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
OM's configuration parameter management.

This module contains a class that can be used to manage and validate a set of
configuration parameters read from a file.
"""
from typing import Any, TextIO

import yaml

from om.utils import exceptions


class MonitorParams:
    """
    See documentation for the `__init__` function.
    """

    def __init__(self, config: str) -> None:
        """
        Storage, retrieval and validation of OM monitor parameters.

        This class stores a set of parameters, subdivided in groups, read from an OM
        configuration file written in YAML format. This class has methods to retrieve,
        and optionally validate, configuration parameters.

        Arguments:

            config: The absolute or relative path to a YAML-format configuration file.

        Raises:

            OMConfigurationFileSyntaxError: A [OmConfigurationFileSyntaxError]
                [om.utils.exceptions.OmConfigurationFileSyntaxError] is raised if there
                is a syntax error in the configuration file.
        """

        self._monitor_params: Any = {}

        try:
            open_file: TextIO
            with open(config, "r") as open_file:
                self._monitor_params = yaml.safe_load(open_file)
        except OSError:
            raise exceptions.OmConfigurationFileReadingError(
                "Cannot open or read the configuration file {0}".format(config)
            )
        except yaml.parser.ParserError as exc:
            raise exceptions.OmConfigurationFileSyntaxError(
                "Syntax error in the configuration file: {0}".format(exc)
            ) from exc

    def get_param(
        self,
        group: str,
        parameter: str,
        parameter_type: Any = None,
        required: bool = False,
    ) -> Any:
        """
        Retrieves an OM monitor configuration parameter.

        This function retrives a configuration parameter belonging to a parameter
        group. Optionally, it validates the type of the parameter. The function behaves
        according to the following rules:

        * If the 'required' argument is True and the parameter cannot be found in the
          configuration file, this function will raise an exception.

        * If the 'required' argument is False and the parameter cannot be found in the
          configuration file, this function will return None.

        * If a type is specified in the function call (the 'parameter_type' argument
          is not None), this function will raise an exception if the type of the
          retrieved parameter does not match the specified one.

        Arguments:

            group: The name of the parameter group in which the parameter to retrieve
                is located.

            parameter (str): The name of the parameter to retrieve.

            parameter_type: The type of the parameter. If a type is specified here, the
                type of the retrieved parameter will be validated. Defaults to None.

            required: True if the parameter is strictly required and must be present
                in the configuration file, False otherwise. Defaults to False.

        Returns:

            The value of the requested parameter, or None, if the parameter was not
            found in the configuration file (and it is not required).

        Raises:

            OmMissingParameterGroupError: A [OmMissingParameterGroupError]
                [om.utils.exceptions.OmMissingParameterGroupError] exception is raised
                if the requested parameter group is not present in the configuration
                file.

            OmMissingParameterError: A [OmMissingParameterError]
                [om.utils.exceptions.OmMissingParameterError] exception is raised if
                the parameter is required but cannot be found in the configuration
                file.

            OmWrongParameterTypeError: A [OmWrongParameterTypeError]
                [om.utils.exceptions.OmWrongParameterTypeError] exception is raised if
                the requested parameter type does not match the type of the parameter
                in the configuration file.
        """
        # TODO: check types
        if group not in self._monitor_params:
            raise exceptions.OmMissingParameterGroupError(
                "Parameter group [{0}] is not in the configuration file".format(group)
            )
        else:
            ret: Any = self._monitor_params[group].get(parameter)
            if ret is None and required is True:
                raise exceptions.OmMissingParameterError(
                    "Parameter {0} in group [{1}] was not found, but is "
                    "required.".format(parameter, group)
                )
            if ret is not None and parameter_type is not None:
                if parameter_type is str:
                    if not isinstance(ret, str):
                        raise exceptions.OmWrongParameterTypeError(
                            "Wrong type for parameter {0}: should be {1}, is "
                            "{2}.".format(
                                parameter,
                                str(parameter_type).split()[1][1:-2],
                                str(type(ret)).split()[1][1:-2],
                            )
                        )
                elif parameter_type is float:
                    if not isinstance(ret, float) and not isinstance(ret, int):
                        raise exceptions.OmWrongParameterTypeError(
                            "Wrong type for parameter {0}: should be {1}, is "
                            "{2}.".format(
                                parameter,
                                str(parameter_type).split()[1][1:-2],
                                str(type(ret)).split()[1][1:-2],
                            )
                        )
                elif not isinstance(ret, parameter_type):
                    raise exceptions.OmWrongParameterTypeError(
                        "Wrong type for parameter {0}: should be {1}, is {2}.".format(
                            parameter,
                            str(parameter_type).split()[1][1:-2],
                            str(type(ret)).split()[1][1:-2],
                        )
                    )

                return ret
            else:

                return ret

    def get_all_parameters(self) -> Any:
        """
        Returns the whole set of parameters read from the configuration file.

        Returns:

            A dictionary containing the parameters read from the configuration file.
        """
        # TODO: check types
        return self._monitor_params
