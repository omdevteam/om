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
This module implements event handling functions and data extraction
functions used when interacting with the HiDRA framework at the
PetraIII facility.
"""
from onda.data_retrieval_layer.components.event_sources import onda_karabo


########################################
#                                      #
# XFEL-KARABO EVENT HANDLING FUNCTIONS #
#                                      #
########################################

initialize_event_source = (  # pylint: disable=C0103
    onda_karabo.initialize_event_source
)

event_generator = (  # pylint: disable=C0103
    onda_karabo.event_generator
)

EventFilter = (  # pylint: disable=C0103
    onda_karabo.EventFilter
)

open_event = (  # pylint: disable=C0103
    onda_karabo.open_event
)


close_event = (  # pylint: disable=C0103
    onda_karabo.close_event
)

# The function:
#
# - get_num_frames_in_event
#
# is detector-dependent when using the Karabo framework at the
# European XFEL facility. Please import the function from the
# data_source components.


#########################################
#                                       #
# XFEL-KARABO DATA EXTRACTION FUNCTIONS #
#                                       #
#########################################

def timestamp(event):
    """
    Recover the timestamp of the event.

    Return the timestamp of the event (return the file creation time as
    seen by HiDRA).

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
    Recover the distance of the detector from the sample location.

    Return the detector distance information (as found in the
    configuration file).

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
