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
Data retrieval from files using the Jungfrau 1M detector.

This module collects several functions and classes used to manage
events and retrieve data when reading Jungfrau 1M data from files.
"""
from onda.data_retrieval_layer.data_sources import euxfel_agipd
from onda.data_retrieval_layer.facility_profiles import euxfel_karabo


############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################

initialize_event_source = (  # pylint: disable=C0103
    euxfel_karabo.initialize_event_source
)


event_generator = (  # pylint: disable=C0103
    euxfel_karabo.event_generator
)


EventFilter = (  # pylint: disable=C0103
    euxfel_karabo.EventFilter
)


FrameFilter = (  # pylint: disable=C0103
    euxfel_karabo.FrameFilter
)


open_event = (  # pylint: disable=C0103
    euxfel_karabo.open_event
)


close_event = (  # pylint: disable=C0103
    euxfel_karabo.close_event
)


get_num_frames_in_event = (  # pylint: disable=C0103
    euxfel_agipd.get_num_frames_in_event
)


#############################
#                           #
# DATA EXTRACTION FUNCTIONS #
#                           #
#############################

detector_data = (  # pylint: disable=C0103
    euxfel_agipd.detector_data
)


timestamp = (  # pylint: disable=C0103
    euxfel_karabo.timestamp
)


detector_distance = (  # pylint: disable=C0103
    euxfel_karabo.detector_distance)


beam_energy = (  # pylint: disable=C0103
    euxfel_karabo.beam_energy
)


############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################


get_peakfinder8_info_detector_data = (  # pylint: disable=C0103
    euxfel_agipd.get_peakfinder8_info
)
