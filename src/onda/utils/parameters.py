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
OnDA configuration parameter object.

This module contains a class that stores a set of configuration parameters read from a
file. Configuration parameters can be retrieved from this class and optionally
validated.
"""
from __future__ import absolute_import, division, print_function

from typing import Any, List, MutableMapping, Union  # pylint: disable=unused-import

import toml
from future.utils import raise_from
from past.builtins import basestring

from onda.utils import exceptions


class MonitorParams(object):
    """
    See documentation for the '__init__' function.
    """

    def __init__(self, config):
        # type: (str) -> None
        """
        Storage, retrieval and validation of OnDA monitor parameters.

        This class stores a set of OnDA configuration parameters read from a file in
        TOML format. The parameters are grouped together in groups ('Tables' in TOML
        parlance) and can be retrieved and optionally validated.

        Arguments:

            config (str): the absolute or relative path to a TOML-format configuration
                file.

        Raises:

            :class:`~onda.utils.exceptions.OndaConfigurationFileSyntaxError`: if there
                is a syntax error in theconfiguration file.
        """
        try:
            self._monitor_params = toml.load("".join(config))
        except OSError:
            raise exceptions.OndaConfigurationFileReadingError(
                "Cannot open or read the configuration file {0}".format(config)
            )
        except toml.TomlDecodeError as exc:
            raise_from(
                exc=exceptions.OndaConfigurationFileSyntaxError(
                    "Syntax error in the configuration file: {0}".format(exc)
                ),
                cause=exc,
            )

    def get_param(self, group, parameter, type_=None, required=False):
        # type: (str, str, type, bool) -> Union[Any, None]
        """
        Retrieves an OnDA monitor configuration parameter.

        This function retrives a configuration parameter belonging to a parameter
        group. Optionally, it validates the type of the parameter. The function behaves
        according to the following rules:

        * If the 'required' argument is True and the parameter cannot be found in the
          configuration file, this function will raise an exception.

        * If the 'required' argument is False and the parameter cannot be found in the
          configuration file, this function will return None.

        * If a type is specified in the function call (the 'type_' argument is not
          None), this function will raise an exception if the type of the retrieved
          parameter does not match the specified one.

        Arguments:

            group (str): the name of the parameter group in which the parameter to
                retrieve is located.

            parameter (str): the name of the parameter to retrieve.

            type_ (Optional[type]): the type of the parameter. If a type is specified
                here, the type of the retrieved parameter will be validated. Defaults
                to None.

            required (bool): True if the parameter is strictly required and must be
                present in the configuration file, False otherwise. Defaults to False.

        Returns:

            Union[Any, None]: the value of the requested parameter, or None, if the
            parameter was not found in the configuration file (and it is not
            required).

        Raises:

            :class:`~onda.utils.exceptions.OndaMissingParameterGroupError`: if the
                requested parameter group is not present in the configuration file.

            :class:`~onda.utils.exceptions.OndaMissingParameterError`: if the parameter
                is required but cannot be found in the configuration file.

            :class:`~onda.utils.exceptions.OndaWrongParameterTypeError`: if the
                requested parameter type does not match the type of the parameter in
                the configuration file.
        """
        if group not in self._monitor_params:
            raise exceptions.OndaMissingParameterGroupError(
                "Parameter group [{0}] is not in the configuration file".format(group)
            )
        else:
            ret = self._monitor_params[group].get(parameter)
            if ret is None and required is True:
                raise exceptions.OndaMissingParameterError(
                    "Parameter {0} in group [{1}] was not found, but is "
                    "required.".format(parameter, group)
                )
            if ret is not None and type_ is not None:
                if type_ is str:
                    if not isinstance(ret, basestring):
                        raise exceptions.OndaWrongParameterTypeError(
                            "Wrong type for parameter {0}: should be {1}, is "
                            "{2}.".format(
                                parameter,
                                str(type_).split()[1][1:-2],
                                str(type(ret)).split()[1][1:-2],
                            )
                        )
                elif type_ is float:
                    if not isinstance(ret, float) and not isinstance(ret, int):
                        raise exceptions.OndaWrongParameterTypeError(
                            "Wrong type for parameter {0}: should be {1}, is "
                            "{2}.".format(
                                parameter,
                                str(type_).split()[1][1:-2],
                                str(type(ret)).split()[1][1:-2],
                            )
                        )
                elif not isinstance(ret, type_):
                    raise exceptions.OndaWrongParameterTypeError(
                        "Wrong type for parameter {0}: should be {1}, is {2}.".format(
                            parameter,
                            str(type_).split()[1][1:-2],
                            str(type(ret)).split()[1][1:-2],
                        )
                    )

                return ret
            else:

                return ret

    def get_all_parameters(self):
        # type: () -> MutableMapping[str, Any]
        """
        Returns the whole set of parameters read from the configuration file.

        Returns:

            MutableMapping[str, Any]: a dictionary containing the parameters read from
            the configuration file.
        """
        return self._monitor_params
