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
Data retrieval at the AMO beamline of LCLS.

Classes and functions used to retrieve and extract data at the AMO beamline of the
LCLS facility.
"""
from __future__ import absolute_import, division, print_function

import functools

from onda.data_retrieval_layer.frameworks import psana_lcls
from onda.data_retrieval_layer.data_sources import pnccd_psana


#####################
#                   #
# UTILITY FUNCTIONS #
#                   #
#####################


globals()["get_peakfinder8_info"] = pnccd_psana.get_peakfinder8_info


############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################


globals()["initialize_event_source"] = psana_lcls.initialize_event_source
globals()["event_generator"] = psana_lcls.event_generator
globals()["open_event"] = psana_lcls.open_event
globals()["close_event"] = psana_lcls.close_event
globals()["get_num_frames_in_event"] = psana_lcls.get_num_frames_in_event


#####################################################
#                                                   #
# PSANA DETECTOR INTERFACE INITIALIZATION FUNCTIONS #
#                                                   #
#####################################################


globals()["detector_data_init"] = functools.partial(
    psana_lcls.detector_data_init, data_extraction_func_name="detector_data"
)
globals()["timestamp_init"] = psana_lcls.timestamp_init
globals()["detector_distance_init"] = psana_lcls.detector_distance_init
globals()["beam_energy_init"] = psana_lcls.beam_energy_init
globals()["optical_laser_active_init"] = psana_lcls.optical_laser_active_init
globals()["xrays_active_init"] = psana_lcls.xrays_active_init


#############################
#                           #
# DATA EXTRACTION FUNCTIONS #
#                           #
#############################


globals()["detector_data"] = functools.partial(
    pnccd_psana.detector_data, data_extraction_func_name="detector_data"
)
globals()["timestamp"] = psana_lcls.timestamp
globals()["detector_distance"] = psana_lcls.detector_distance
globals()["beam_energy"] = psana_lcls.beam_energy
globals()["optical_laser_active"] = psana_lcls.optical_laser_active
globals()["xrays_active"] = psana_lcls.xrays_active
