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
Data retrieval at the CXI beamline of LCLS.

Classes and functions used to retrieve and extract data at the CXI
beamline of the LCLS facility.
"""
from __future__ import absolute_import, division, print_function

import functools

from onda.data_retrieval_layer.data_sources import lcls_cspad
from onda.data_retrieval_layer.facility_profiles import lcls_psana


#####################
#                   #
# UTILITY FUNCTIONS #
#                   #
#####################


get_peakfinder8_info_detector_data = (  # pylint: disable=invalid-name
    lcls_cspad.get_peakfinder8_info
)


############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################


initialize_event_source = (  # pylint: disable=invalid-name
    lcls_psana.initialize_event_source
)


event_generator = lcls_psana.event_generator  # pylint: disable=invalid-name


EventFilter = lcls_psana.EventFilter  # pylint: disable=invalid-name


FrameFilter = lcls_psana.FrameFilter  # pylint: disable=invalid-name


open_event = lcls_psana.open_event  # pylint: disable=invalid-name


close_event = lcls_psana.close_event  # pylint: disable=invalid-name


get_num_frames_in_event = (  # pylint: disable=invalid-name
    lcls_psana.get_num_frames_in_event
)


#####################################################
#                                                   #
# PSANA DETECTOR INTERFACE INITIALIZATION FUNCTIONS #
#                                                   #
#####################################################


detector_data_init = functools.partial(  # pylint: disable=invalid-name
    lcls_psana.detector_data_init, data_extraction_func_name="detector_data"
)
functools.update_wrapper(detector_data_init, lcls_psana.detector_data_init)


timestamp_init = lcls_psana.timestamp_init  # pylint: disable=invalid-name


detector_distance_init = (  # pylint: disable=invalid-name
    lcls_psana.detector_distance_init
)


beam_energy_init = lcls_psana.beam_energy_init  # pylint: disable=invalid-name

optical_laser_active_init = (  # pylint: disable=invalid-name
    lcls_psana.optical_laser_active_init
)

xrays_active_init = lcls_psana.xrays_active_init  # pylint: disable=invalid-name

target_time_delay_init = (  # pylint: disable=invalid-name
    lcls_psana.target_time_delay_init
)

#############################
#                           #
# DATA EXTRACTION FUNCTIONS #
#                           #
#############################

detector_data = functools.partial(  # pylint: disable=invalid-name
    lcls_cspad.detector_data, data_extraction_func_name="detector_data"
)
functools.update_wrapper(detector_data, lcls_cspad.detector_data)


timestamp = lcls_psana.timestamp  # pylint: disable=invalid-name


detector_distance = lcls_psana.detector_distance  # pylint: disable=invalid-name


beam_energy = lcls_psana.beam_energy  # pylint: disable=invalid-name


optical_laser_active = (  # pylint: disable=invalid-name
    lcls_psana.optical_laser_active
)


xrays_active = lcls_psana.xrays_active  # pylint: disable=invalid-name

target_time_delay = lcls_psana.target_time_delay  # pylint: disable=invalid-name
