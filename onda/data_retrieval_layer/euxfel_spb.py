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
Data retrieval at the SPB beamline of XFEL.

Classes and functions used to retrieve and extract data at the SPB
beamline of the European XFEL facility.
"""
from __future__ import absolute_import, division, print_function

from onda.data_retrieval_layer.data_sources import euxfel_agipd
from onda.data_retrieval_layer.facility_profiles import euxfel_karabo


#####################
#                   #
# UTILITY FUNCTIONS #
#                   #
#####################


get_peakfinder8_info_detector_data = (  # pylint: disable=invalid-name
    euxfel_agipd.get_peakfinder8_info
)


############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################


initialize_event_source = (  # pylint: disable=invalid-name
    euxfel_karabo.initialize_event_source
)


event_generator = (  # pylint: disable=invalid-name
    euxfel_karabo.event_generator
)


EventFilter = (  # pylint: disable=invalid-name
    euxfel_karabo.EventFilter
)


FrameFilter = (  # pylint: disable=invalid-name
    euxfel_karabo.FrameFilter
)


open_event = (  # pylint: disable=invalid-name
    euxfel_karabo.open_event
)


close_event = (  # pylint: disable=invalid-name
    euxfel_karabo.close_event
)


get_num_frames_in_event = (  # pylint: disable=invalid-name
    euxfel_agipd.get_num_frames_in_event
)


#############################
#                           #
# DATA EXTRACTION FUNCTIONS #
#                           #
#############################


detector_data = (  # pylint: disable=invalid-name
    euxfel_agipd.detector_data
)


timestamp = (  # pylint: disable=invalid-name
    euxfel_karabo.timestamp
)


detector_distance = (  # pylint: disable=invalid-name
    euxfel_karabo.detector_distance
)


beam_energy = (  # pylint: disable=invalid-name
    euxfel_karabo.beam_energy
)


frame_id = (  # pylint: disable=invalid-name
    euxfel_karabo.frame_id
)


event_id = (  # pylint: disable=invalid-name
    euxfel_karabo.frame_id
)


optical_laser_active = (  # pylint: disable=invalid-name
    euxfel_karabo.optical_laser_active
)


xrays_active = (  # pylint: disable=invalid-name
    euxfel_karabo.xrays_active
)
