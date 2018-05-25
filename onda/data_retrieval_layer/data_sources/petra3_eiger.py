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
Utilities to process Eiger detector data at the Petra III facility.

Exports:

    Namedtuples:

        FilenameAndIndex: information about a frame's location in the
            filesystem.

        Peakfinder8DetInfo: peakfinder8-related information.

    Functions:

        get_file_extensions: get allowed file extensions for this
            detector.

        get_peakfinder8_info: get peakfinder8-related detector info.

        open_event: open an event.

        close_event: close an event.

        get_num_frames_in_event: get number of frames in an event.

        detector_data: recover the raw detector data for the
            event.

        filename_and_frame_index: return the full file path and
            the frame index, within the file, of the frame being
            processed.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import collections

from onda.data_retrieval_layer.data_sources.file_formats import hdf5_files


###############
#             #
# NAMEDTUPLES #
#             #
###############

FilenameAndFrameIndex = collections.namedtuple(  # pylint: disable=C0103
    typename='FilenameAndFrameIndex',
    field_names=['filename', 'frame_index']
)
"""
Information necessary to locate a frame in the filesystem.

A nametuple the storing information necessary to recover a frame from a
filesystem. The two fields, called 'filename' and 'frame_index'
respectively, store the path to the file where the frame can be found,
and the index of the frame in the data block containing the detector
data.
"""


Peakfinder8DetInfo = collections.namedtuple(  # pylint: disable=C0103
    typename='Peakfinder8DetectorInfo',
    field_names=['asic_nx', 'asic_ny', 'nasics_x', 'nasics_y']
)
"""
Peakfinder8-related information.

A namedtuple where the four fields (named respectively 'asics_nx',
'asics_ny', 'nasics_x', and  'nasics_y)' are the four parameters used
by the peakfinder8 algorithm to describe the format of theinput data.
"""


####################################
#                                  #
# PETRAIII-EIGER UTILITY FUNCTIONS #
#                                  #
####################################

def get_file_extensions():
    """
    Return allowed file extensions.

    Return allowed file extensions for the Eiger detector.

    Returns:

        tuple: a tuple containing the list of allowed file extensions.
    """
    return ('.nxs',)


def get_peakfinder8_info():
    """
    Return peakfinder8 detector info.

    Return the peakfinder8 information for the Eiger detector.

    Returns:

       Peakfinder8DetInfo: the peakfinder8-related detector
       information.
    """
    return Peakfinder8DetInfo(1556, 516, 1, 1)


##########################################
#                                         #
# PETRAIII-EIGER EVENT HANDLING FUNCTIONS #
#                                         #
###########################################

open_event = hdf5_files.open_event  # pylint: disable=C0103


close_event = hdf5_files.close_event  # pylint: disable=C0103


def get_num_frames_in_event(event):
    """
    The number of frames in the file.

    Return the number of frames in a file (the length of the first axis
    of the 3d data block where the detector data is stored).

    Args:

        event (Dict): a dictionary with the event data.

        data_hdf5_path: internal HDF5 path of the data block containing
            the detector data.

    Retuns:

        int: the number of frames in an event (usually corresponding to
        a file).
    """
    return event['data']['/entry/data/data'].shape[0]


############################################
#                                          #
# PETRAIII-EIGER DATA EXTRACTION FUNCTIONS #
#                                          #
############################################

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
    return event['/data']['/entry/data/data'].shape[0]


def filename_and_frame_index(event):
    """
    The filename and frame index for the frame being processed.

    Return the name of the file where the frame being processed is
    stored, and the index of the frame within the file.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        FilenameAndFrameIndex: the path to the file which stores the
        current frame, and the index of the frame in the data block
        containing the detector data.
    """
    return FilenameAndFrameIndex(
        event['metadata']['full_path'],
        (
            event['/data']['/entry/data/data'].shape[0] +
            event['metadata']['frame_offset']
        )
    )