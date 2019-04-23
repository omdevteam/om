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
Data retrieval at the SPB beamline of XFEL.

Classes and functions used to retrieve and extract data at the SPB beamline of the
European XFEL facility.
"""
from __future__ import absolute_import, division, print_function

from onda.data_retrieval_layer.frameworks import karabo_euxfel
from onda.data_retrieval_layer.data_sources import agipd_karabo


#####################
#                   #
# UTILITY FUNCTIONS #
#                   #
#####################


globals()["get_peakfinder8_info_detector_data"] = agipd_karabo.get_peakfinder8_info


############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################


globals()["initialize_event_source"] = karabo_euxfel.initialize_event_source
globals()["event_generator"] = karabo_euxfel.event_generator
globals()["open_event"] = karabo_euxfel.open_event
globals()["close_event"] = karabo_euxfel.close_event
globals()["get_num_frames_in_event"] = agipd_karabo.get_num_frames_in_event


#############################
#                           #
# DATA EXTRACTION FUNCTIONS #
#                           #
#############################


globals()["detector_data"] = agipd_karabo.detector_data
globals()["timestamp"] = karabo_euxfel.timestamp
globals()["detector_distance"] = karabo_euxfel.detector_distance
globals()["beam_energy"] = karabo_euxfel.beam_energy
globals()["frame_id"] = karabo_euxfel.frame_id
globals()["event_id"] = karabo_euxfel.frame_id
globals()["optical_laser_active"] = karabo_euxfel.optical_laser_active
globals()["xrays_active"] = karabo_euxfel.xrays_active
