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
Retrieval of data from the AGIPD detector at XFEL.

Functions and classes used to retrieve data from the AGIPD detector as
used at the European XFEL facility.
"""
from __future__ import absolute_import, division, print_function

from onda.data_retrieval_layer.file_formats import hdf5_files
from onda.utils import named_tuples


#####################
#                   #
# UTILITY FUNCTIONS #
#                   #
#####################


def get_peakfinder8_info():
    """
    Peakfinder8 info for the AGIPD detector at XFEL.

    Retrieves the peakfinder8 information matching the data format used
    by the AGIPD detector at the European XFEL facility.

    Returns:

        Peakfinder8DetInfo: a named tuple for which the four fields,
        'asic_nx', 'asic_ny', 'nasics_x' and 'nasics_y' store the
        four peakfinder8 parameters.
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


open_event = hdf5_files.open_event  # pylint: disable=invalid-name


close_event = hdf5_files.close_event  # pylint: disable=invalid-name


def get_num_frames_in_event(event):
    """
    Number of AGIPD frames in an XFEL event.

    Returns the number of AGIPD detector frames in an event retrieved
    at the European XFEL facility.

    Args:

        event (Dict): a dictionary with the event data.

    Retuns:

        int: the number of frames in the event.
    """
    # The data is stored in a 4-d block. The last axis is the nunmber
    # of frames.
    return (
        event['data']['SPB_DET_AGIPD1M-1/CAL/APPEND_CORRECTED']['image.data'].
        shape[-1]
    )


#############################
#                           #
# DATA EXTRACTION FUNCTIONS #
#                           #
#############################


def detector_data(event):
    """
    One frame of AGIPD detector data (at XFEL).

    Extracts one frame of AGIPD detector data from an event retrieved
    at the European XFEL facility.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        ndarray: one frame of detector data.
    """
    return (
        event['data']['SPB_DET_AGIPD1M-1/CAL/APPEND_CORRECTED']['image.data'][
            ..., event['frame_offset']
        ].reshape(16 * 128, 512)
    )
