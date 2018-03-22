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
Classes and functions for storing and recovering monitor parameters.

Exports:

    Classes:

        MonitorParams: storage and retrieval of OnDA monitor
            parameters.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import str

from onda.cfelpyutils import parameter_utils
from onda.utils import exceptions


class MonitorParams(object):
    """
    Store the parameters for an OnDA monitor.

    Store OnDA monitor parameters from a configuration file.
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

            WrongParameterType: if the type with which the parameter
                has been requested does not match the typ of the
                parameter in the configuration dictionary.
        """

        # Convert the entries of the configuration dictionary to the
        # corresponding data types and store the dictionary in an
        # attribute.
        self._monitor_params = parameter_utils.convert_parameters(
            config_dict=param_dictionary
        )

    def get_param(self, section, parameter, type_=None, required=False):
        '''
        Recover the requested monitor parameter.

        Optionally, check that the type of the recovered parameter
        matches the a type specified by the caller. If the parameter is
        not found return None, unless the callers flags it as
        'required', in which case raise an exception. Please notice
        that even when a parameter does not exist in the configuration
        dictionary, the requested section must be present in the file.

        Args:

            section (str): name of the section where the requested
                parameter should be searched,

            parameter (str): name of the requested parameter.

            type_ (type): type of the requested parameter. If this
                argument is not None, the function will make sure that
                the type of the recovered parameter matches the type
                provided here. Otherwise, an exception will be raised.
                If the type of the recovered parameter is None (or if
                the parameter is not present in the configuration
                dictionary, the check will not be performed). Defaults
                to None.

            required (bool): if this argument is True, the function
                will raise an exception if the parameter is not present
                in the configuration dictionary.

        Returns:

        Any: the value of the requested parameter in the configuration
        dictionary. If the parameter it is not in the dictionary, the
        value None is returned.
        '''
        if section not in self._monitor_params:
            raise exceptions.MissingParameterFileSection(
                "Section {0} is not in the configuration file".format(section)
            )
        else:
            ret = self._monitor_params[section].get(parameter)
            if ret is None and required is True:
                raise exceptions.MissingParameter(
                    "Parameter {0} in section [{1}] was not found, but is "
                    "required.".format(parameter, section)
                )

            if ret is not None and type_ is not None:
                if not isinstance(ret, type_):
                    raise exceptions.WrongParameterType(
                        "Wrong type for parameter {0}: should be {1}, "
                        "is {2}.".format(
                            parameter,
                            str(type_).split()[1][1:-2],
                            str(type(ret)).split()[1][1:-2]
                        )
                    )
                else:
                    return ret
            else:
                return ret
