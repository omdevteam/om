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
Data retrieval at from Jungfrau 1M files.

Classes and functions used to retrieve and extract data at from
files written by a Jungfrau 1M detector.
"""
from __future__ import absolute_import, division, print_function

from onda.data_retrieval_layer.data_sources import files_jungfrau1module
from onda.data_retrieval_layer.event_sources import file_source
from onda.data_retrieval_layer.filters import event_filters, frame_filters
from onda.utils import parameters


#####################
#                   #
# UTILITY FUNCTIONS #
#                   #
#####################


get_file_extensions = (  # pylint: disable=invalid-name
    files_jungfrau1module.get_file_extensions
)


get_peakfinder8_info_detector_data = (  # pylint: disable=invalid-name
    files_jungfrau1module.get_peakfinder8_info
)


############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################


initialize_event_source = (  # pylint: disable=invalid-name
    file_source.initialize_event_source
)


event_generator = (  # pylint: disable=invalid-name
    file_source.event_generator
)


EventFilter = (  # pylint: disable=invalid-name
    event_filters.NullEventFilter
)


FrameFilter = (  # pylint: disable=invalid-name
    frame_filters.NullFrameFilter
)


open_event = (  # pylint: disable=invalid-name
    files_jungfrau1module.open_event
)


close_event = (  # pylint: disable=invalid-name
    files_jungfrau1module.close_event
)


get_num_frames_in_event = (  # pylint: disable=invalid-name
    files_jungfrau1module.get_num_frames_in_event
)


#############################
#                           #
# DATA EXTRACTION FUNCTIONS #
#                           #
#############################


def timestamp(event):
    """
    Retrieves the timestamp of a Junfgrau 1M file event.

    Since the Jungfrau 1M does not provide timestamp information, the
    modification time of the source file is used as a first
    approximation of the timestamp when the timestamp is not available.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        numpy.float64: the time at which the event was collected.
    """
    return event['timestamp']


detector_data = (  # pylint: disable=invalid-name
    files_jungfrau1module.detector_data
)


detector_distance = (  # pylint: disable=invalid-name
    parameters.detector_distance_from_monitor_params
)


beam_energy = (  # pylint: disable=invalid-name
    parameters.beam_energy_from_monitor_params
)


filename_and_frame_index = (  # pylint: disable=invalid-name
    files_jungfrau1module.filename_and_frame_index
)
