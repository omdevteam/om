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
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import eiger_hidra as eh


get_file_extensions_filelist = eh.get_file_extensions_hidra

get_peakfinder8_info_filelist = eh.get_peakfinder8_info_hidra

open_event_filelist = eh.open_event_hidra

close_event_filelist = eh.close_event_hidra

get_num_frames_in_event_filelist = eh.get_num_frames_in_event_hidra

detector_data_filelist = eh.detector_data_hidra

timestamp_filelist = eh.timestamp_hidra

beam_energy_filelist = eh.beam_energy_hidra

detector_distance_filelist = eh.detector_distance_hidra

filename_and_frame_index_filelist = eh.filename_and_frame_index_hidra
