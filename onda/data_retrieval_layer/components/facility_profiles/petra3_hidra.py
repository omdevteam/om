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
HiDRA at the Petra III facility.

This module contains the implementation of event handling functions and
data extraction functions used when interacting with the HiDRA
framework at the PetraIII facility.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from onda.data_retrieval_layer.components.event_sources import onda_hidra


###########################################
#                                         #
# PETRAIII-HIDRA EVENT HANDLING FUNCTIONS #
#                                         #
###########################################

initialize_event_source = (  # pylint: disable=C0103
    onda_hidra.initialize_event_source
)

event_generator = (  # pylint: disable=C0103
    onda_hidra.event_generator
)

EventFilter = (  # pylint: disable=C0103
    onda_hidra.EventFilter
)

# The functions:
#
# - open_event
# - close_event
# - get_num_frames_in_event
#
# are detector-dependent when using the HiDRA framework at the PetraIII
# facility. Please import them from the data_source components.


############################################
#                                          #
# PETRAIII-HIDRA DATA EXTRACTION FUNCTIONS #
#                                          #
############################################

def timestamp(event):
    """
    Retrieve the timestamp of the event.

    As approximated by the file creation time provided by HiDRA.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        timestamp: the time at which the event was collected.
    """
    return event['metadata']['file_creation_time']


def beam_energy(event):
    """
    Retrieve the beam energy.

    As provided in the configuration file.

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
    )


def detector_distance(event):
    """
    Retrieve the distance of the detector from the sample location.

    As provided in the configuration file.

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

# Import other data extraction functions from the data_source
# components.
