#    This file is part of OnDA.
#
#    OnDA is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    OnDA is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with OnDA.  If not, see <http://www.gnu.org/licenses/>.
"""
Configuration parameter retrieval and validation.

This module contains the implementation of a class used to store,
retrieve and validate configuration options for OnDA monitors.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import str  # pylint: disable=W0622

from onda.cfelpyutils import parameter_utils
from onda.utils import exceptions


class MonitorParams(object):
    """
    Storage and retrieval of OnDA monitor parameters.

    A class that allows the storage, retrieval and validatio of OnDA
    monitor parameters.
    """

    def __init__(self, param_dictionary):
        """
        Initialize the MonitorParams class.

        Args:

            param_dictionary (Dict): a dictionary containing the
                parameters, as return by the configparse python module.

        Raises:

            MissingParameterFileSection: if the requested section is
                not present in the parameter dictionary.

            MissingParameter: if the requested parameter is required
                (i.e.: it must be present in the configuration
                dictionary) but cannot be found.

            WrongParameterType: if the required parameter type does not
                match the type of the parameter in the configuration
                dictionary.
        """
        # Convert the entries of the configuration dictionary to the
        # corresponding data types and store the dictionary in an
        # attribute.
        self._monitor_params = parameter_utils.convert_parameters(
            config_dict=param_dictionary
        )

    def get_param(self, section, parameter, type_=None, required=False):
        """
        Retrieve the requested OnDA monitor parameter.

        Retrieve the configuration parameter as found in the
        configuration file. Optionally, check that the type of the
        retrieved parameter matches the type required by the user.

        Args:

            section (str): name of configuration file section where the
                requested is located.

            parameter (str): name of the requested parameter.

            type_ (type): type of the requested parameter. If this
                argument is not None, the function will make sure that
                the type of the recovered parameter matches the type
                provided here. Otherwise, an exception will be raised.
                If the type of the recovered parameter is None, or if
                the parameter is not present in the configuration
                dictionary, the check will not be performed. Defaults
                to None.

            required (bool): if this argument is True, the function
                will raise an exception if the parameter is not present
                in the configuration dictionary (Normally the function
                returns None for parameters that were not found).

        Returns:

            Any: the value of the requested parameter. If the parameter
            is not found, the value None is returned, unless the
            'required' input argument is True, in which case an
            exception will be raised.
        """
        # Look for the relevant section in the configuration
        # dictionary, and raise an Exception if it is not found.
        if section not in self._monitor_params:
            raise exceptions.MissingParameterFileSection(
                "Section {} is not in the configuration file".format(section)
            )
        else:

            # If the section exists, look for the parameter. If the
            # parameter is not found, raise an exception or return None
            # depending on the value of the 'required' parameter.
            ret = self._monitor_params[section].get(parameter)
            if ret is None and required is True:
                raise exceptions.MissingParameter(
                    "Parameter {} in section [{}] was not found, but is "
                    "required.".format(parameter, section)
                )

            # If required, check the type of the retrieved parameter,
            # and raise an exception if a mismatch is detected.
            if ret is not None and type_ is not None:
                if not isinstance(ret, type_):
                    raise exceptions.WrongParameterType(
                        "Wrong type for parameter {}: should be {}, "
                        "is {}.".format(
                            parameter,
                            str(type_).split()[1][1:-2],
                            str(type(ret)).split()[1][1:-2]
                        )
                    )
                else:
                    return ret
            else:
                return ret
