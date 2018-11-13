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
#
#    Copyright 2014-2018 Deutsches Elektronen-Synchrotron DESY,
#    a research centre of the Helmholtz Association.
"""
Configuration parameter retrieval and validation.

Functions and classes used to retrieve and validate configuration
options from OnDA monitor configuration files.
"""
from __future__ import absolute_import, division, print_function

from past.builtins import basestring
from scipy import constants

from onda.utils import exceptions


class MonitorParams(object):
    """
    Storage, retrieval and validation of OnDA monitor parameters.

    A class that stores a set of configuration parameters for an OnDA
    monitor read from a configuration file. The class has members that
    allow the retrieval of data options from different sections of the
    configuration files. Optionally, the parameter type can also be
    checkes and validated.

    Raises:

        MissingParameterFileSection: if the requested section is
            not present in the configuration file.

        MissingParameter: if the parameter is strictly required
            (i.e. the 'required' argument is set to True) but
            cannot be found in the configuration file.

        WrongParameterType: if the requested parameter type does
            not match the type of the parameter in the
            configuration file.
    """
    def __init__(self, param_dictionary):
        """
        Initializes the MonitorParams class.

        Args:

            param_dictionary (Dict): a dictionary containing the
                parameters from a configuration file, as returned by
                the :obj:`toml` python module.
        """
        self._monitor_params = param_dictionary

    def get_param(self, section, parameter, type_=None, required=False):
        """
        Retrieves an OnDA monitor parameter.

        Optionally, checks that the type of the retrieved parameter
        matches the type needed by the user.

        Args:

            section (str): name of configuration file section where the
                parameter is located.

            parameter (str): name of the parameter.

            type_ (type): required type of the parameter. If this
                argument is not None, the function will make sure that
                the type of the recovered parameter matches the type
                requested here. If the type does not match, an
                exception will be raised. If the type of the recovered
                parameter is None, or if the parameter is not present
                in the configuration file, the check will not be
                performed. Defaults to None.

            required (bool): if this argument is True, the function
                will raise an exception if the parameter is not present
                in the configuration file (Normally the function
                returns None for parameters that are not found in the
                configuration file).

        Returns:

            Union[Any, None]: the value of the requested parameter. If
            the parameter is not found, the value None is returned,
            unless the 'required' input argument is True, in which case
            an exception is raised.
        """
        if section not in self._monitor_params:
            raise exceptions.MissingParameterFileSection(
                "Section {} is not in the configuration file".format(section)
            )
        else:
            ret = self._monitor_params[section].get(parameter)
            if ret is None and required is True:
                raise exceptions.MissingParameter(
                    "Parameter {} in section [{}] was not found, but is "
                    "required.".format(parameter, section)
                )
            if ret is not None and type_ is not None:
                if type_ is str:
                    if not isinstance(ret, basestring):
                        raise exceptions.WrongParameterType(
                            "Wrong type for parameter {}: should be {}, "
                            "is {}.".format(
                                parameter,
                                str(type_).split()[1][1:-2],
                                str(type(ret)).split()[1][1:-2]
                            )
                        )
                elif type_ is float:
                    if (
                            not isinstance(ret, float) or
                            not isinstance(ret, int)
                    ):
                        raise exceptions.WrongParameterType(
                            "Wrong type for parameter {}: should be {}, "
                            "is {}.".format(
                                parameter,
                                str(type_).split()[1][1:-2],
                                str(type(ret)).split()[1][1:-2]
                            )
                        )
                elif not isinstance(ret, type_):
                    raise exceptions.WrongParameterType(
                        "Wrong type for parameter {}: should be {}, "
                        "is {}.".format(
                            parameter,
                            str(type_).split()[1][1:-2],
                            str(type(ret)).split()[1][1:-2]
                        )
                    )
                return ret
            else:
                return ret


def beam_energy_from_monitor_params(event):
    """
    Retrieves the beam energy from the configuration file.

    The beam energy should be stored in the 'General' section under the
    'fallback_beam_energy' entry.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        float: the energy of the beam in J.
    """
    return float(
        event['monitor_params'].get_param(
            section='General',
            parameter='fallback_beam_energy',
            type_=float,
            required=True
        )
    ) * constants.electron_volt


def detector_distance_from_monitor_params(event):
    """
    Retrieves the beam energy from the configuration file.

    The beam energy should be stored in the 'General' section under the
    'fallback_detector_distance' entry.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        float: the distance between the detector and the sample in m.
    """
    return float(
        event['monitor_params'].get_param(
            section='General',
            parameter='fallback_detector_distance',
            type_=float,
            required=True
        )
    )
