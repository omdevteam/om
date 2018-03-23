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

        open_event_hidra: open an event. HiDRA-specific version.

        open_event_filelist: open an event. filelist-specific version.

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

import scipy.constants

from .data_recovery_specific.pilatus_filelist import (  # pylint: disable=W0611
    open_event as open_event_filelist
)
from .data_recovery_specific.pilatus_hidra import(  # pylint: disable=W0611
    open_event as open_event_hidra
)


def get_file_extensions():
    """
    Return allowed file extensions.

    Return allowed file extensions for the Lmabda detector.

    Returns:

        tuple: a tuple containing the list of allowed file extensions.
    """
    return (".cbf",)


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
    return Peakfinder8DetInfo(2463, 2527, 1, 1)


def close_event(_):
    """
    Close event.

    Close event by doing nothing: fabio module cbf_obj objects don't
    need to be closed.

    Args:

        event (Dict): a dictionary with the event data.
    """
    pass


def get_num_frames_in_event(_):
    """
    The number of frames in the file.

    Return the number of frames in a file (cbf files usually contain
    one frame per file.

    Args:

        event (Dict): a dictionary with the event data.
    """
    return 1


def detector_data(event):
    """
    Recover raw detector data for one frame.

    Return the detector data for one single frame (the data from the
    fabio cbf_obj object contained in the input dictionary).

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        ndarray: the raw detector data for one frame.
    """
    return event['data'].data


def timestamp(event):
    """
    Recover the timestamp of the event.

    Return the timestamp of the event (return the event timestamp from
    the event dictionary.

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

    Return the beam energy information for the event. Return the
    information from the header of the CBF file if the information is
    there, otherwise fall back to the value found in the configuration
    file.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        float: the energy of the beam in eV.
    """
    try:
        header_data_list = event['data']['cbf_obj'].header[
            u'_array_data.header_contents'
        ].split('\r\n')
        wavelength = float(header_data_list[15].split()[2])
        return float(
            scipy.constants.h * scipy.constants.c /
            (wavelength * scipy.constants.electron_volt)
        )
    except (AttributeError, IndexError, ValueError):
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

    Return the detector distance information for the event. Return the
    information from the header of the CBF file if the information is
    there, otherwise fall back to the value found in the configuration
    file.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        float: the distance between the detector and the sample in mm.
    """

    try:
        header_data_list = event['data']['cbf_obj'].header[
            u'_array_data.header_contents'
        ].split('\r\n')
        return float(header_data_list[16].split()[2])
    except (AttributeError, IndexError, ValueError):
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
    stored, and the index of the frame within the file (which is
    always 0, as Pilatus files usually contain just one file).

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
    return FnameAndFrameIndex(event['metadata']['full_path'], 0)
