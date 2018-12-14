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
Retrieval of data from Jungfrau 1M detector files.

Functions and classes used to retrieve data from files written by the
Jungfrau 1M detector.
"""
from __future__ import absolute_import, division, print_function

from onda.data_retrieval_layer.file_formats import hdf5_files
from onda.utils import named_tuples


############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################

open_event = hdf5_files.open_event  # pylint: disable=invalid-name

close_event = hdf5_files.close_event  # pylint: disable=invalid-name


def get_num_frames_in_event(event):
    """
    Number of frames in a Jungfrau 1M file.

    Returns the number of Junfgrau 1M detector frames in an event
    recovered from a file (1 event = 1 file).

    Args:

        event (Dict): a dictionary with the event data.

    Retuns:

        int: the number of frames in the event.
    """
    # The data is stored in a 3-d block. The first axis is the number
    # of frames.
    return event['data']['/entry/instrument/detector/data'].shape[0]


#####################
#                   #
# UTILITY FUNCTIONS #
#                   #
#####################


def get_file_extensions():
    """
    Extensions used for Jungfrau 1M files.

    Returns the extensions used for files written by the Jungfrau 1M
    detector.

    Returns:

        Tuple[str]: the list of file extensions.
    """
    return (".nxs",)


def get_peakfinder8_info():
    """
    Peakfinder8 info for the Jungfrau 1M detector.

    Retrieves the peakfinder8 information matching the data format
    used in files written by the the Jungfrau 1M detector.

    Returns:

        Peakfinder8DetInfo: the peakfinder8-related detector
        information.
    """
    return named_tuples.Peakfinder8DetInfo(
        asic_nx=1024,
        asic_ny=512,
        nasics_x=1,
        nasics_y=1
    )


#############################
#                           #
# DATA EXTRACTION FUNCTIONS #
#                           #
#############################


def detector_data(event):
    """
    One frame of detector data from a Jungfrau 1M file.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        ndarray: one frame of detector data.
    """
    data_block = event['data']['/entry/instrument/detector/data']
    return data_block[event['frame_offset']]


def event_id(event):
    """
    Retrieves a unique event identifier for Jungfrau 1M files.

    Returns a unique label that unambiguosly identifies the current
    event within an experiment. For Jungfrau 1M files, the full path
    to the file storing the event is used as an identifier.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        str: a unique event identifier.
    """
    return event['full_path']


def frame_id(event):
    """
    Retrieves a unique identifier for a Jungfrau 1M frame.

    Returns a unique label that unambiguosly identifies the current
    detector frame within the event. For Jungfrau 1M files, the index
    of the frame within the file is used as an identifier.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        str: a unique frame identifier with the event.
    """
    return str(
        event['data']['/entry/instrument/detector/data'].shape[0] +
        event['frame_offset']
    )
