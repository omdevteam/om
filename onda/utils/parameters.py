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
OnDA configuration parameter storage, retrieval and validation.
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

        This object stores a set of OnDA configuration parameters read from a
        configuration file. The parameters, which are grouped together in 'Parameter
        Groups', must come from a TOML-formatted file. They can be retrieved from
        this object via the 'get_param' member function. Optionally, the parameters
        can also be validated at the time of retrieval.

        Arguments:

            config (List[str]): the absolute or relative path to a TOML-format
                configuration file.

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

    def get_param(self, section, parameter, type_=None, required=False):
        # type (str, str, type, bool) -> Union[Any, None]
        """
        Retrieves an OnDA monitor configuration parameter.

        This functions returns the retrived configuration parameter.

        * If the 'required'  arguments is True and the parameter cannot be found in the
          configuration file, this function will raise an exception.

        * If the 'required'  arguments is False and the parameter cannot be found in the
          configuration file, this function will return None.

        * If a required type is specified (the 'type_' argument is not None), this
          function will raise an exception if the type of the retrieved parameter does
          not match the requested one.

        Arguments:

            section (str): the name of the parameter group in which the parameter to
                to retrieve is located.

            parameter (str): the name of the parameter to retrieve.

            type_ (type): the required type of the parameter. If a type is specified
                and the argument is not None, the type of the retrieved parameter will
                be validated. Defaults to None.

            required (bool): True if the parameter is required (must be present in the
                configuration file), False otherwise. Defaults to False.

        Returns:

            Union[Any, None]: the value of the requested parameter, or None, if the
            parameter was not found in the configuration file.

        Raises:

            :class:`onda.utils.exceptions.OndaMissingParameterGroupError`: if the
                requested parameter group is not present in the configuration file.

            :class:`onda.utils.exceptions.OndaMissingParameterError`: if the parameter
                is required but cannot be found in the configuration file.

            :class:`onda.utils.exceptions.OndaWrongParameterTypeError`: if the
                requested parameter type does not match the type of the parameter in
                the configuration file.
        """
        if section not in self._monitor_params:
            raise exceptions.OndaMissingParameterGroupError(
                "Parameter group [{}] is not in the configuration file".format(section)
            )
        else:
            ret = self._monitor_params[section].get(parameter)
            if ret is None and required is True:
                raise exceptions.OndaMissingParameterError(
                    "Parameter {} in section [{}] was not found, but is "
                    "required.".format(parameter, section)
                )
            if ret is not None and type_ is not None:
                if type_ is str:
                    if not isinstance(ret, basestring):
                        raise exceptions.OndaWrongParameterTypeError(
                            "Wrong type for parameter {}: should be {}, is "
                            "{}.".format(
                                parameter,
                                str(type_).split()[1][1:-2],
                                str(type(ret)).split()[1][1:-2],
                            )
                        )
                elif type_ is float:
                    if not isinstance(ret, float) and not isinstance(ret, int):
                        raise exceptions.OndaWrongParameterTypeError(
                            "Wrong type for parameter {}: should be {}, is "
                            "{}.".format(
                                parameter,
                                str(type_).split()[1][1:-2],
                                str(type(ret)).split()[1][1:-2],
                            )
                        )
                elif not isinstance(ret, type_):
                    raise exceptions.OndaWrongParameterTypeError(
                        "Wrong type for parameter {}: should be {}, is {}.".format(
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
