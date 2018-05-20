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
Utilities to retrieve data from HiDRA at the PetraIII facility.

Exports:

    Functions:

        initialize_event_source: connect to the event source and
            configure it.

        event_generator: event recovery from HiDRA.

        timestamp: recover the timestamp information of the
            event.

        beam_energy: recover the beam energy during the current
            event.

        detector_distance: recover the distance between the
            sample and the detector for the current event.

    Classes:

        EventFilter (class): filter and reject events.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from onda.data_retrieval_layer.components.frameworks import hidra


###########################################
#                                         #
# PETRAIII-HIDRA EVENT HANDLING FUNCTIONS #
#                                         #
###########################################

initialize_event_source = (  # pylint: disable=C0103
    hidra.initialize_event_source
)

event_generator = (  # pylint: disable=C0103
    hidra.event_generator
)

EventFilter = (  # pylint: disable=C0103
    hidra.EventFilter
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
    Recover the timestamp of the event.

    Return the timestamp of the event (return the file creation time as
    seen by HiDRA)

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        timestamp: the creation time of the file containing the
        detector data.
    """
    return event['metadata']['file_creation_time']


def beam_energy(event):
    """
    Recover the energy of the beam.

    Return the beam energy information (as found in the configuration
    file).

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        float: the energy of the beam in eV.
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
    Recover the distance of the detector from the sample location.

    Return the detector distance information (as found in the
    configuration file).

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        float: the distance between the detector and the sample in mm.
    """
    return float(
        event['monitor_params'].get_param(
            section='General',
            parameter='fallback_detector_distance',
            type_=float,
            required=True
        )
    )
