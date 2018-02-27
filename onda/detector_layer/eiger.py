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
Functions and classes for the processing of data from the Eiger detector.

Exports:

    Functions:

        get_file_extensions_hidra: get allowed file extensions for this
        detector (HiDRA-specific version).

        get_peakfinder8_detector_info_hidra: get peakfinder8-related detector
        info (HiDRA-specific version).

        open_event_hidra: open an event (HiDRA-specific version).

        close_event_hidra: close an event (HiDRA-specific version).

        get_num_frames_in_event_hidra: get number of frames in an event
        (HiDRA-specific version).

        detector_data_hidra: recover the raw detector data for the event
        (HiDRA-specific version).

        timestamp_hidra: recover the timestamp information of the event
        (HiDRA-specific version).

        beam_energy_hidra: recover the beam energy during the current event
        (HiDRA-specific version).

        detector_distance_hidra: recover the distance between the sample and
        the detector for the current event (HiDRA-specific version).

        filename_and_frame_index_hidra: return the full file path and the frame
        index, within the file, of the frame being processed  (HiDRA-specific
        version).

        get_file_extensions_filelist: get allowed file extensions for this
        detector (filelist-specific version).

        get_peakfinder8_detector_info_filelist: get peakfinder8-related
        detector info (filelist-specific version).

        open_event_filelist: open an event (filelist-specific version).

        close_event_filelist: close an event (filelist-specific version).

        get_num_frames_in_event_filelist: get number of frames in an event
        (filelist-specific version).

        detector_data_filelist: recover the raw detector data for the event
        (filelist-specific version).

        timestamp_filelist: recover the timestamp information of the event
        (filelist-specific version).

        beam_energy_filelist: recover the beam energy during the current event
        (filelist-specific version).

        detector_distance_filelist: recover the distance between the sample and
        the detector for the current event (filelist-specific version).

        filename_and_frame_index_filelist: return the full file path and the
        frame index, within the file, of the frame being processed
        (filelist-specific version).
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import collections

import h5py


##############
#    HiDRA   #
##############

def get_file_extensions_hidra():
    """
    Return allowed file extensions.

    Returns:

        tuple: a tuple containing the list of allowed file extensions.
    """
    return ('.nxs',)


def get_peakfinder8_info_hidra():
    """
    Return peakfinder8 detector info.

    Returns:

        Tuple[int, int, int, int]: A tuple where the four fields (named
        respectively 'asics_nx', 'asics_ny', 'nasics_x', and 'nasics_y)'are
        the four parameters used by the peakfinder8 algorithm to describe the
        format of the input data.
    """
    # A namedtuple used for peakfinder8-related detector information.
    Peakfinder8DetInfo = collections.namedtuple(
        typename='Peakfinder8DetectorInfo',
        field_names=['asics_nx', 'asics_ny', 'nasics_x', 'nasics_y']
    )

    return Peakfinder8DetInfo(1556, 516, 1, 1)


def open_event_hidra(event):
    """
    Open event.

    Open the file using the h5py and save the open file filehandle
    in the 'data' entry of the event dictionary.

    Args:

        event (Dict): a dictionary with the event data.
    """
    event['data'] = h5py.File(
        name=event['metadata']['full_path'],
        mode='r'
    )


def close_event_hidra(event):
    """
    Close event.

    Close the h5py file.

    Args:

        event (Dict): a dictionary with the event data.
    """
    event['data'].close()


def get_num_frames_in_event_hidra(event):
    """
    The number of frames in the file.

    Return the length of the first axis of the 3d data block where the detector
    data is stored.

    Args:

        event (Dict): a dictionary with the event data.
    """
    return event['data']['/entry/data/data'].shape[0]


def detector_data_hidra(event):
    """
    Recover raw detector data for one frame.

    Return a 'slice' of the 3d data block where the detector data is stored.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        ndarray: the raw detector data for one frame.
    """
    return event['/data']['/entry/data/data'].shape[0]


def timestamp_hidra(event):
    """
    Recover the timestamp of the event.

    Extract and return the event timestamp from the event dictionary.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        timestamp: the creation time of the file containing the detector data.
    """
    return event['metadata']['file_creation_time']


def beam_energy_hidra(event):
    """
    Recover the energy of the beam.

    Return the information found in the configuration file.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        float: the energy of the beam in eV.
    """
    return float(
        event['monitor_params'].get_param(
            section='General',
            parameter='fallback_beam_energy',
            type_=float,
            required=True
        )
    )


def detector_distance_hidra(event):
    """
    Recover the distance of the detector from the sample location.

    Return the information found in the configuration file.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        float: the distance between the detector and the sample in mm.
    """
    return float(
        event['monitor_params'].get_param(
            section='General',
            parameter='fallback_detector_distance',
            type_=float,
            required=True
        )
    )


def filename_and_frame_index_hidra(event):
    """
    Recover the distance of the detector from the sample location.

    Return the information found in the configuration file.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        float: the distance between the detector and the sample in mm.
    """
    # A namedtuple used to store filename and index information.
    FilenameAndFrameIndex = collections.namedtuple(
        typename='FilenameAndFrameIndex',
        field_names=['filename', 'frame_index']
    )

    # Recover the file path from the opened_event dictionary. Compute the
    # current frame and return the tuple.
    return FilenameAndFrameIndex(
        event['metadata']['full_path'],
        (
            event['/data']['/entry/data/data'].shape[0] +
            event['metadata']['frame_offset']
        )
    )


#################
#    Filelist   #
#################

get_file_extensions_filelist = get_file_extensions_hidra

get_peakfinder8_info_filelist = get_peakfinder8_info_hidra

open_event_filelist = open_event_hidra

close_event_filelist = close_event_hidra

get_num_frames_in_event_filelist = get_num_frames_in_event_hidra

detector_data_filelist = detector_data_hidra

timestamp_filelist = timestamp_hidra

beam_energy_filelist = beam_energy_hidra

detector_distance_filelist = detector_distance_hidra

filename_and_frame_index_filelist = filename_and_frame_index_hidra
