# This file is part of OnDA.
#
# OnDA is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# OnDA is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with OnDA.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2014-2018 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Retrieval of 1 module Jungfrau detector data from HiDRA.

Functions used to retrieve data from the 1 module Jungfrau detector using HiDRA.
"""
from __future__ import absolute_import, division, print_function

import h5py

from onda.utils import named_tuples


#####################
#                   #
# UTILITY FUNCTIONS #
#                   #
#####################


def get_file_extensions():
    """
    Extensions used for Jungfrau 1M files.

    Returns the extensions used for files written by the Jungfrau 1M detector.

    Returns:

        Tuple[str]: the list of file extensions.
    """
    return (".nxs",)


def get_peakfinder8_info():
    """
    Peakfinder8 info for the Jungfrau 1M detector.

    Retrieves the peakfinder8 information matching the data format used in files
    written by the the Jungfrau 1M detector.

    Returns:

        Peakfinder8DetInfo: the peakfinder8-related detector information.
    """
    return named_tuples.Peakfinder8DetInfo(
        asic_nx=1024, asic_ny=512, nasics_x=1, nasics_y=1
    )


############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################


def open_event(event):
    """
    Opens a Jungfrau event retrieved from HiDRA.

    Makes the content of a retrieved Jungfrau event available in the 'data' entry of
    the event dictionary.

    Args:

        event (Dict): a dictionary with the event data.
    """
    # The event is an HDF5 file. The h5py File function is used to open it.
    event.data = h5py.File(name=event.framework_info["full_path"], mode="r")


def close_event(event):
    """
    Closes a Jungfrau event retrieved from HiDRA.

    Args:

        event (Dict): a dictionary with the event data.
    """
    # The event is an HDF5 file. The h5py Close function is used to close it.
    event.data.close()


def get_num_frames_in_event(event):
    """
    Number of frames in a Jungfrau 1M event retrieved from HiDRA.

    Returns the number of Junfgrau 1M detector frames in an event recovered from HiDRA.
    (Currently 1 event = 1 file).

    Args:

        event (Dict): a dictionary with the event data.

    Retuns:

        int: the number of frames in the event.
    """
    # The data is stored in a 3-d block. The first axis is the number
    # of frames.
    return event.data["/entry/instrument/detector/data"].shape[0]


#############################
#                           #
# DATA EXTRACTION FUNCTIONS #
#                           #
#############################


def detector_data(event):
    """
    One frame of detector data from a Jungfrau 1M event retrieved from HiDRA.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        ndarray: one frame of detector data.
    """
    return event.data["/entry/instrument/detector/data"][event.current_frame]


def event_id(event):
    """
    Retrieves a unique event identifier for a Jungfrau 1M events from HiDRA.

    Returns a unique label that unambiguosly identifies the current event within an
    experiment. For Jungfrau 1M events retrieved from HiDRA, the full path to the file
    storing the event is used as identifier.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        str: a unique event identifier.
    """
    return event.framework_info["full_path"]


def frame_id(event):
    """
    Retrieves a unique identifier for a Jungfrau 1M frame from HiDRA.

    Returns a unique label that unambiguosly identifies the current detector frame
    within the event. For Jungfrau 1M events retrieved from HiDRA, the index of the
    frame within the file storing the event is used as identifier.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        str: a unique frame identifier with the event.
    """
    return str(event.current_frame)
