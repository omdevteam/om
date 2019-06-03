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
# Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Data retrieval at the from single-module Jungfrau files.

Classes and functions used to retrieve and extract data from files written by a single
module Jungfrau detector.
"""
from __future__ import absolute_import, division, print_function

from onda.data_retrieval_layer.frameworks import files_filesystem
from onda.data_retrieval_layer.data_sources import jungfrau_1module_files


#####################
#                   #
# UTILITY FUNCTIONS #
#                   #
#####################


globals()["get_peakfinder8_info_detector_data"] = (
    jungfrau_1module_files.get_peakfinder8_info
)

############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################


globals()["initialize_event_source"] = files_filesystem.initialize_event_source
globals()["event_generator"] = files_filesystem.event_generator
globals()["open_event"] = jungfrau_1module_files.open_event
globals()["close_event"] = jungfrau_1module_files.close_event
globals()["get_num_frames_in_event"] = jungfrau_1module_files.get_num_frames_in_event


#############################
#                           #
# DATA EXTRACTION FUNCTIONS #
#                           #
#############################


globals()["detector_data"] = jungfrau_1module_files.detector_data
globals()["timestamp"] = files_filesystem.timestamp
globals()["detector_distance"] = files_filesystem.detector_distance
globals()["beam_energy"] = files_filesystem.beam_energy
globals()["frame_id"] = jungfrau_1module_files.frame_id
globals()["event_id"] = jungfrau_1module_files.frame_id
