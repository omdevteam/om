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
Retrieval of data from the Eiger detector at Petra III.

This module contains the implementation of several functions used to
retrieve data from the Eiger detector as used at the Petra III
facility.
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
    Retrieve allowed files extensions.

    Returns:

        Tuple[str]: the list of allowed file extensions.
    """
    return (".h5",)


def get_peakfinder8_info():
    """
    Retrieve the peakfinder8 detector information.

    Returns:

        Peakfinder8DetInfo: the peakfinder8-related detector
        information.
    """
    return named_tuples.Peakfinder8DetInfo(
        asic_nx=512,
        asic_ny=128,
        nasics_x=1,
        nasics_y=16
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
    # The data is stored in a 4-d block. The last axis is the nunmber
    # of frames.
    return (
        event[
            'data'
        ][
            'SPB_DET_AGIPD1M-1/CAL/APPEND_CORRECTED'
        ][
            'image.data'
        ].shape[-1]
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
    return (
        event[
            'data'
        ][
            'SPB_DET_AGIPD1M-1/CAL/APPEND_CORRECTED'
        ][
            'image.data'
        ][..., event['frame_offset']].reshape(16*128, 512)
    )
