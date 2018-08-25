
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
from onda.data_retrieval_layer.data_sources import files_jungfrau1module
from onda.data_retrieval_layer.event_sources import file_source
from onda.data_retrieval_layer.file_formats import ini_files


############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################

initialize_event_source = (  # pylint: disable=C0103
    file_source.initialize_event_source
)


event_generator = (  # pylint: disable=C0103
    file_source.event_generator
)


EventFilter = (  # pylint: disable=C0103
    file_source.EventFilter
)


open_event = (  # pylint: disable=C0103
    files_jungfrau1module.open_event
)


close_event = (  # pylint: disable=C0103
    files_jungfrau1module.close_event
)


get_num_frames_in_event = (  # pylint: disable=C0103
    files_jungfrau1module.get_num_frames_in_event
)


#############################
#                           #
# DATA EXTRACTION FUNCTIONS #
#                           #
#############################

detector_data = (  # pylint: disable=C0103
    files_jungfrau1module.detector_data
)


detector_distance = (  # pylint: disable=C0103
    ini_files.detector_distance_from_config
)


beam_energy = (  # pylint: disable=C0103
    ini_files.beam_energy_from_config
)


filename_and_frame_index = (  # pylint: disable=C0103
    files_jungfrau1module.filename_and_frame_index
)

############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################

get_file_extensions = (  # pylint: disable=C0103
    files_jungfrau1module.get_file_extensions
)


get_peakfinder8_info_detector_data = (  # pylint: disable=C0103
    files_jungfrau1module.get_peakfinder8_info
)
