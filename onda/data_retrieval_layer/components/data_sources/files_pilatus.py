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
Utilities to process data from the Pilatus detector stored in files.

This module implements several functions used to process data from the
Pilatus detector stored in files.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from onda.data_retrieval_layer.components.file_formats import cbf_files
from onda.utils import named_tuples


#####################
#                   #
# UTILITY FUNCTIONS #
#                   #
#####################

def get_file_extensions():
    """
    Files extensions for the Pilatus detector.

    Return allowed file extensions for the Pilatus detector.

    Returns:

        tuple: a tuple containing the list of allowed file extensions.
    """
    return (".cbf",)


def get_peakfinder8_info():
    """
    Peakfinder8 detector info for the Pilatus detector.

    Return peakfinder8 information for the Pilatus detector.

    Returns:

        :obj:`onda.utils.name_tuples.Peakfinder8DetInfo`: the
        peakfinder8-related detector information.
    """
    return named_tuples.Peakfinder8DetInfo(
        asic_nx=2463,
        asic_ny=2527,
        nasics_x=1,
        nasics_y=1
    )


############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################

open_event = cbf_files.open_event  # pylint: disable=C0103


close_event = cbf_files.close_event  # pylint: disable=C0103


def get_num_frames_in_event(_):
    """
    The number of frames in the file.

    Return the number of frames in a file.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        int: the number of frames in an event.
    """
    # CBF files from the Pilatus detector usually contain only one
    # frame.
    return 1


#############################
#                           #
# DATA EXTRACTION FUNCTIONS #
#                           #
#############################

def detector_data(event):
    """
    Recover detector data for one frame.

    Return the detector data for one single frame.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        ndarray: the raw detector data for one frame.
    """
    # Return the data from the fabio cbf_obj object, previously stored
    # in the input dictionary.
    return event['data'].data


def filename_and_frame_index(event):
    """
    The filename and frame index for the frame being processed.

    Return the name of the file where the frame being processed is
    stored, and the index of the frame within the file.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        :obj:`onda.utils.named_tuples.FilenameAndFrameIndex`: the path
        to the file which stores the current frame, and the index of
        the frame in the data block containing the detector data.
    """
    # The frame index is always 0, as Pilatus files usually contain
    # just one frame.
    return named_tuples.FilenameAndFrameIndex(
        filename=event['metadata']['full_path'],
        frame_index=0
    )
