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
Event and data retrieval from HiDRA at Petra III.

Non detector-specific functions and classes used for event and data
retrieval from HiDRA at the Petra III facility.
"""
from __future__ import absolute_import, division, print_function

from onda.data_retrieval_layer.event_sources import hidra_source
from onda.data_retrieval_layer.filters import event_filters, frame_filters
from onda.utils import parameters


############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################


initialize_event_source = (  # pylint: disable=invalid-name
    hidra_source.initialize_event_source
)


event_generator = hidra_source.event_generator  # pylint: disable=invalid-name


EventFilter = event_filters.NullEventFilter  # pylint: disable=invalid-name


FrameFilter = frame_filters.NullFrameFilter  # pylint: disable=invalid-name


#############################
#                           #
# DATA EXTRACTION FUNCTIONS #
#                           #
#############################


def timestamp(event):
    """
    Timestamp of an event retrieved from HiDRA at Petra III.

    Extracts the timestamp of an event retrieved from HiDRA at the
    Petra III facility (1 event = 1 file, and when the timestamp
    is not otherwise available, the creation data of the file is taken
    as timestamp of the event).

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        numpy.float64: the timestamp of the event.
    """
    return event["file_creation_time"]


beam_energy = (  # pylint: disable=invalid-name
    parameters.beam_energy_from_monitor_params
)


detector_distance = (  # pylint: disable=invalid-name
    parameters.detector_distance_from_monitor_params
)
