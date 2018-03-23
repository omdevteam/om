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

        get_file_extensions: get allowed file extensions for this
            detector.

        get_peakfinder8_info: get peakfinder8-related detector info.

        open_event: open an event.

        close_event: close an event.

        get_num_frames_in_event: get number of frames in an event.

        detector_data: recover the raw detector data for the event.

        timestamp: recover the timestamp information of the event.

        beam_energy: recover the beam energy during the current event.

        detector_distance: recover the distance between the sample
            and the detector for the current event.

        filename_and_frame_index: return the full file path and the
            frame index, within the file, of the frame being processed.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import collections

import h5py


def get_file_extensions():
    """
    Return allowed file extensions.

    Return allowed file extensions for the Lambda detector.

    Returns:

        tuple: a tuple containing the list of allowed file extensions.
    """
    return (".h5", ".nxs")


def get_peakfinder8_info():
    """
    Return peakfinder8 detector info.

    Return the peakfinder8 information for the Lambda detector.

    Returns:

        Tuple[int, int, int, int]: A tuple where the four fields (named
        respectively 'asics_nx', 'asics_ny', 'nasics_x', and
        'nasics_y)' are the four parameters used by the peakfinder8
        algorithm to describe the format of the input data.
    """
    Peakfinder8DetInfo = collections.namedtuple(  # pylint: disable=C0103
        typename='Peakfinder8DetectorInfo',
        field_names=['asic_nx', 'asic_ny', 'nasics_x', 'nasics_y']
    )
    return Peakfinder8DetInfo(1556, 516, 1, 1)


def open_event(event):
    """
    Open event.

    Open the event by opening the file using the h5py library. Save
    the open file filehandle in the 'data' entry of the event
    dictionary.

    Args:

        event (Dict): a dictionary with the event data.
    """
    event['data'] = h5py.File(
        name=event['metadata']['full_path'],
        mode='r'
    )


def close_event(event):
    """
    Close event.

    Close event by closing the h5py file.

    Args:

        event (Dict): a dictionary with the event data.
    """
    event['data'].close()


def get_num_frames_in_event(event):
    """
    The number of frames in the file.

    Return the number of frames in a file (the length of the first axis
    of the 3d data block where the detector data is stored).

    Args:

        event (Dict): a dictionary with the event data.
    """
    return event['data']['/entry/instrument/detector/data'].shape[0]


def detector_data(event):
    """
    Recover raw detector data for one frame.

    Return the detector data for one single frame (a 'slice' of the 3d
    data block where the detector data is stored).

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        ndarray: the raw detector data for one frame.
    """
    data_block = event['/data']['/entry/instrument/detector/data']
    return data_block[data_block.shape[0] + event['metadata']['frame_offset']]


def timestamp(event):
    """
    Recover the timestamp of the event.

    Return the timestamp of the event (return the event timestamp from
    the event dictionary).

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        timestamp: the creation time of the file containing the
        detector data.
    """
    return event['metadata']['file_creation_time']


def beam_energy(event):
    """
    Recover the energy of the beam.

    Return the beam energy information (as found in the configuration
    file).

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


def detector_distance(event):
    """
    Recover the distance of the detector from the sample location.

    Return the detector distance information (as found in the
    configuration file).

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


def filename_and_frame_index(event):
    """
    The filename and frame index for the frame being processed.

    Return the name of the file where the frame being processed is
    stored, and the index of the frame within the file.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        Tuple[str, int]: a tuple with two fields. The first, named
        'filename', stores the name of the file containing the current
        frame. The second, named 'frame_index', contains the index of
        the current frame within the file.
    """
    FnameAndFrameIndex = collections.namedtuple(  # pylint: disable=C0103
        typename='FilenameAndFrameIndex',
        field_names=['filename', 'frame_index']
    )
    return FnameAndFrameIndex(
        event['metadata']['full_path'],
        (
            event['/data']['/entry/instrument/detector/data'].shape[0] +
            event['metadata']['frame_offset']
        )
    )
