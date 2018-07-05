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
Processing of data from the Lambda detector at Petra III.

This module contains the implementation of several functions used
to process data from the Lambda detector as used at the Petra III
facility.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from onda.data_retrieval_layer.components.file_formats import hdf5_files
from onda.utils import named_tuples


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
    return (".nxs", ".h5")


def get_peakfinder8_info():
    """
    Retrieve the peakfinder8 detector information.

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

open_event = hdf5_files.open_event  # pylint: disable=C0103


close_event = hdf5_files.close_event  # pylint: disable=C0103


def get_num_frames_in_event(event):
    """
    Retrieve the number of frames in the event.

    Args:

        event (Dict): a dictionary with the event data.

    Retuns:

        int: the number of frames in an event.
    """
    # The number of frames in an event is the length of the first axis
    # in the data block where the data is stored.
    return event['data']['/entry/instrument/detector/data'].shape[0]


#############################################
#                                           #
# PETRAIII-LAMBDA DATA EXTRACTION FUNCTIONS #
#                                           #
#############################################

def detector_data(event):
    """
    Retrieve one frame of detector data.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        numpy.ndarray: one frame of detector data.
    """
    data_block = event['/data']['/entry/instrument/detector/data']
    return data_block[data_block.shape[0] + event['metadata']['frame_offset']]


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
        filename=event['metadata']['full_path'],
        frame_index=(
            event['/data']['/entry/instrument/detector/data'].shape[0] +
            event['metadata']['frame_offset']
        )
    )
