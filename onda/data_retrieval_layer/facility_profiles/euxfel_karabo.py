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
Karabo at the European XFEL facility.

This module contains the implementation of event handling functions
and data extraction functions used to interact with Karabo at the
European XFEL facility.
"""
from __future__ import absolute_import, division, print_function

from onda.data_retrieval_layer.event_sources import karabo_source
from onda.data_retrieval_layer.file_formats import ini_files
from onda.data_retrieval_layer.filters import event_filters, frame_filters

########################################
#                                      #
# XFEL-KARABO EVENT HANDLING FUNCTIONS #
#                                      #
########################################

initialize_event_source = (  # pylint: disable=C0103
    karabo_source.initialize_event_source
)

event_generator = (  # pylint: disable=C0103
    karabo_source.event_generator
)


open_event = (  # pylint: disable=C0103
    karabo_source.open_event
)


close_event = (  # pylint: disable=C0103
    karabo_source.close_event
)


EventFilter = (  # pylint: disable=C0103
    event_filters.AgeEventFilter
)


FrameFilter = (  # pylint: disable=C0103
    frame_filters.IndexBasedFrameFilter
)


# The function:
#
# - get_num_frames_in_event
#
# is detector-dependent when using the Karabo framework at the
# European XFEL facility. Please import the function from the
# 'data_source' submodules.


#########################################
#                                       #
# XFEL-KARABO DATA EXTRACTION FUNCTIONS #
#                                       #
#########################################

def timestamp(event):
    """
    Retrieve the timestamp of the event.

    As extracted previously and stored in the event structure.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        numpy.float64: the time at which the event was collected.
    """
    return event['timestamp']

beam_energy = (  # pylint: disable=C0103
    ini_files.beam_energy_from_config
)


detector_distance = (  # pylint: disable=C0103
    ini_files.detector_distance_from_config
)


# Import other data extraction functions from the 'data_sources'
# submodules.
