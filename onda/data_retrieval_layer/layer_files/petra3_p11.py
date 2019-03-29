# This file is part of OnDA.
#
# OnDA is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# OnDA is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with OnDA.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2014-2018 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Data retrieval at the P11 beamline of Petra III.

Classes and functions used to retrieve and extract data at the P11 beamline of the
Petra III facility.
"""
from __future__ import absolute_import, division, print_function

from onda.data_retrieval_layer.data_sources import pilatus_hidra
from onda.data_retrieval_layer.frameworks import hidra_petra3


#####################
#                   #
# UTILITY FUNCTIONS #
#                   #
#####################


globals()["get_peakfinder8_info"] = pilatus_hidra.get_peakfinder8_info
globals()["get_file_extensions"] = pilatus_hidra.get_file_extensions


############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################


globals()["initialize_event_source"] = hidra_petra3.initialize_event_source
globals()["event_generator"] = hidra_petra3.event_generator
globals()["open_event"] = pilatus_hidra.open_event
globals()["close_event"] = pilatus_hidra.close_event
globals()["get_num_frames_in_event"] = pilatus_hidra.get_num_frames_in_event


#############################
#                           #
# DATA EXTRACTION FUNCTIONS #
#                           #
#############################


globals()["detector_data"] = pilatus_hidra.detector_data
globals()["timestamp"] = hidra_petra3.timestamp
globals()["detector_distance"] = hidra_petra3.detector_distance
globals()["beam_energy"] = hidra_petra3.beam_energy
globals()["event_id"] = pilatus_hidra.frame_id
globals()["frame_id"] = pilatus_hidra.frame_id
