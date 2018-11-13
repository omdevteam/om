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
Retrieval of data from the Eiger detector at Petra III.

Functions and classes used to retrieve data from the Eiger detector as
used at the Petra III facility.
"""
from __future__ import absolute_import, division, print_function

from onda.data_retrieval_layer.file_formats import hdf5_files
from onda.utils import named_tuples


#####################
#                   #
# UTILITY FUNCTIONS #
#                   #
#####################


def get_file_extensions():
    """
    Extensions used for Eiger files at Petra III.

    Returns the extensions used for files written by the Eiger detector
    at the Petra III facility.

    Returns:

        Tuple[str]: the list of file extensions.
    """
    return (".nxs", ".h5")


def get_peakfinder8_info():
    """
    Peakfinder8 info for the Eiger detector at Petra III.

    Retrieves the peakfinder8 information matching the data format used
    by the Eiger detector at the Petra III facility.

    Returns:

        Peakfinder8DetInfo: the peakfinder8-related detector
        information.
    """
    return named_tuples.Peakfinder8DetInfo(
        asic_nx=1556,
        asic_ny=516,
        nasics_x=1,
        nasics_y=1
    )


############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################


open_event = hdf5_files.open_event  # pylint: disable=invalid-name

close_event = hdf5_files.close_event  # pylint: disable=invalid-name


def get_num_frames_in_event(event):
    """
    Number of Eiger frames in  Petra III event.

    Returns the number of Eiger detector frames in an event retrieved
    at the Petra III facility (1 event = 1 file).

    Args:

        event (Dict): a dictionary with the event data.

    Retuns:

        int: the number of frames in the event.
    """
    # The data is stored in a 3-d block. The first axis is the nunmber
    # of frames.
    return event['data']['/entry/data/data'].shape[0]


#############################
#                           #
# DATA EXTRACTION FUNCTIONS #
#                           #
#############################


def detector_data(event):
    """
    One frame of Eiger detector data at Petra III.

    Extracts one frame of Eiger detector data from an event retrieved
    at the Petra III facility.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        ndarray: one frame of detector data.
    """
    return event['data']['/entry/data/data'][event['frame_offset']]


def filename_and_frame_index(event):
    """
    Filename and frame index of the current frame.

    For Eiger events retrieved at the Petra III facility, returns the
    name of the file where the current frame can be found, together
    with the index of the frame in the file.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        FilenameAndFrameIndex: a
        :obj:`~onda.utils.named_tuples.FilenameAndFrameIndex` object
        with the path to the file which stores the current frame, and
        the index of the frame in the data block containing the
        detector data.
    """
    return named_tuples.FilenameAndFrameIndex(
        filename=event['full_path'],
        frame_index=(
            event['data']['/entry/data/data'].shape[0] + event['frame_offset']
        )
    )
