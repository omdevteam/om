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
Data retrieval at the P11 beamline of Petra III.

Classes and functions used to retrieve and extract data at the P11
beamline of the Petra III facility.
"""
from __future__ import absolute_import, division, print_function

from onda.data_retrieval_layer.data_sources import petra3_pilatus
from onda.data_retrieval_layer.facility_profiles import petra3_hidra


#####################
#                   #
# UTILITY FUNCTIONS #
#                   #
#####################


get_peakfinder8_info_detector_data = (  # pylint: disable=invalid-name
    petra3_pilatus.get_peakfinder8_info
)


get_file_extensions = (  # pylint: disable=invalid-name
    petra3_pilatus.get_file_extensions
)


############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################


initialize_event_source = (  # pylint: disable=invalid-name
    petra3_hidra.initialize_event_source
)


event_generator = petra3_hidra.event_generator  # pylint: disable=invalid-name


EventFilter = petra3_hidra.EventFilter  # pylint: disable=invalid-name


FrameFilter = petra3_hidra.FrameFilter  # pylint: disable=invalid-name


open_event = petra3_pilatus.open_event  # pylint: disable=invalid-name


close_event = petra3_pilatus.close_event  # pylint: disable=invalid-name


get_num_frames_in_event = (  # pylint: disable=invalid-name
    petra3_pilatus.get_num_frames_in_event
)


#############################
#                           #
# DATA EXTRACTION FUNCTIONS #
#                           #
#############################


detector_data = petra3_pilatus.detector_data  # pylint: disable=invalid-name


timestamp = petra3_hidra.timestamp  # pylint: disable=invalid-name


detector_distance = (  # pylint: disable=invalid-name
    petra3_hidra.detector_distance
)


beam_energy = petra3_hidra.beam_energy  # pylint: disable=invalid-name


event_id = petra3_pilatus.event_id  # pylint: disable=invalid-name


frame_id = petra3_pilatus.frame_id  # pylint: disable=invalid-name
