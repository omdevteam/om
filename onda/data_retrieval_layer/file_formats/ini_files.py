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
This module contains the implementation of several functions used to
manipulate ini files.
"""
from __future__ import absolute_import, division, print_function

import scipy.constants


def beam_energy_from_config(event):
    """
    Retrieve the beam energy from the configuration file.

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
    ) * scipy.constants.electron_volt


def detector_distance_from_config(event):
    """
    Retrieve the beam energy from the configuration file.

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
