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
Functions and classes for the processing of data from the Lambda
detector.

Exports:

    Functions:

        get_file_extensions_hidra: get allowed file extensions for this
            detector (HiDRA-specific version).

        get_peakfinder8_detector_info_hidra: get peakfinder8-related
            detector info (HiDRA-specific version).

        open_event_hidra: open an event (HiDRA-specific version).

        close_event_hidra: close an event (HiDRA-specific version).

        get_num_frames_in_event_hidra: get number of frames in an event
            (HiDRA-specific version).

        detector_data_hidra: recover the raw detector data for the
            event (HiDRA-specific version).

        timestamp_hidra: recover the timestamp information of the event
            (HiDRA-specific version).

        beam_energy_hidra: recover the beam energy during the current
            event (HiDRA-specific version).

        detector_distance_hidra: recover the distance between the
            sample and the detector for the current event
            (HiDRA-specific version).

        filename_and_frame_index_hidra: return the full file path and
            the frame index, within the file, of the frame being
            processed  (HiDRA-specific version).

        get_file_extensions_filelist: get allowed file extensions for
            this detector (filelist-specific version).

        get_peakfinder8_detector_info_filelist: get peakfinder8-related
        d   etector info (filelist-specific version).

        get_file_extensions_filelist: get allowed file extensions for
            this detector (filelist-specific version).

        get_peakfinder8_detector_info_filelist: get peakfinder8-related
            detector info (filelist-specific version).

        open_event_filelist: open an event (filelist-specific version).

        close_event_filelist: close an event (filelist-specific
            version).

        get_num_frames_in_event_filelist: get number of frames in an
            event (filelist-specific version).

        detector_data_filelist: recover the raw detector data for the
            event (filelist-specific version).

        timestamp_filelist: recover the timestamp information of the
            event (filelist-specific version).

        beam_energy_filelist: recover the beam energy during the
            current event (filelist-specific version).

        detector_distance_filelist: recover the distance between the
            sample and the detector for the current event
            (filelist-specific version).

        filename_and_frame_index_filelist: return the full file path
            and the frame index, within the file, of the frame being
            processed  (filelist-specific version).
"""
from .lambda_hidra import (
    get_file_extensions_hidra,
    get_peakfinder8_info_hidra,
    open_event_hidra,
    close_event_hidra,
    get_num_frames_in_event_hidra,
    detector_data_hidra,
    timestamp_hidra,
    beam_energy_hidra,
    detector_distance_hidra,
    filename_and_frame_index_hidra
)

from .lambda_filelist import (
    get_file_extensions_filelist,
    get_peakfinder8_info_filelist,
    open_event_filelist,
    close_event_filelist,
    get_num_frames_in_event_filelist,
    detector_data_filelist,
    timestamp_filelist,
    beam_energy_filelist,
    detector_distance_filelist,
    filename_and_frame_index_filelist
)
