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
Retrieval of data from the Pilatus detector at Petra III.

This module contains the implementation of several functions used to
retrieve data from the Pilatus detector as used at the Petra III
facility.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import io

from future.utils import raise_from

from onda.utils import exceptions, named_tuples

try:
    import fabio
except ImportError:
    raise_from(
        exc=exceptions.MissingDependency(
            "The petra3_pilatus module could not be loaded. The following "
            "dependency does not appear to be available on the system: fabio."
        ),
        cause=None
    )


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

def open_event(event):
    """
    Open the event.

    Make the content of the event available in the 'data' entry of the
    event dictionary.

    Args:

        event (Dict): a dictionary with the event data.
    """
    # Wrap the binary data that HiDRA streams to OnDA in a BytesIO
    # object.
    byio_data = io.BytesIO(event['data'])

    # Read the data that using the fabio library and store the content
    # as a cbf_obj object in the 'data' entry of the event dictionary.
    cbf_image = fabio.cbfimage.CbfImage()
    event['data'] = cbf_image.read(byio_data)


def close_event(_):
    """
    Close the event.

    Args:

        event (Dict): a dictionary with the event data.
    """
    # Do nothing: cbf_obj objects don't need to be closed.
    pass


def get_num_frames_in_event(_):
    """
    Retrieve the number of frames in the event.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        int: the number of frames in an event.
    """
    # Each event from a Pilatus detector usually contains only a single
    # frame.
    return 1


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
    # Extract frame information from the data stored in the event
    # dictionary.
    return event['data'].data


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
    # The frame index is always 0, as Pilatus files usually contain
    # just one frame.
    return named_tuples.FilenameAndFrameIndex(
        filename=event['full_path'],
        frame_index=0
    )
