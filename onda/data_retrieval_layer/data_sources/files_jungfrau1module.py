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
Retrieval of data from the Jungfrau 1M detector at LCLS.

This module contains the implementation of several functions used to
retrieve data from the Jungfrau 1M detector as used at the LCLS
facility.
"""
from __future__ import absolute_import, division, print_function

from onda.data_retrieval_layer.file_formats import hdf5_files
from onda.utils import named_tuples


############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################

open_event = hdf5_files.open_event  # pylint: disable=C0103


close_event = hdf5_files.close_event  # pylint: disable=C0103


def get_num_frames_in_event(event):  # pylint: disable=W0613
    """
    The number of frames in the file.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        int: the number of frames in an event.
    """
    # The data is stored in a 3-d block. The first axis is the nunmber
    # of frames.
    return event['data']['/entry/instrument/detector/data'].shape[0]


#####################
#                   #
# UTILITY FUNCTIONS #
#                   #
#####################

def get_file_extensions():
    """
    Retrieve allowed files extensions.

    Returns:

        Tuple[str]: the list of allowed file extensions.
    """
    return (".nxs",)


def get_peakfinder8_info():
    """
    Retrieve the peakfinder8 detector information.

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
    Retrieve one frame of detector data.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        numpy.ndarray: one frame of detector data.
    """
    data_block = event['data']['/entry/instrument/detector/data']
    return data_block[event['frame_offset']]


def filename_and_frame_index(event):
    """
    Retrieve the filename and frame index of the frame being processed.

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
            event['data']['/entry/instrument/detector/data'].shape[0] +
            event['frame_offset']
        )
    )
