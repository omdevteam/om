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
Retrieval of data from the Pilatus detector at Petra III.

Functions and classes used to retrieve data from the Pilatus detector
as used at the Petra III facility.
"""
from __future__ import absolute_import, division, print_function

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
        cause=None,
    )

#####################
#                   #
# UTILITY FUNCTIONS #
#                   #
#####################


def get_file_extensions():
    """
    Extensions used for Lambda files at Petra III.

    Returns the extensions used for files written by the Lambda
    detector at the Petra III facility.

    Returns:

        Tuple[str]: the list of file extensions.
    """
    return (".cbf",)


def get_peakfinder8_info():
    """
    Peakfinder8 info for the Pilatus detector at LCLS.

    Retrieves the peakfinder8 information matching the data format used
    by the Pilatus detector at the Petra III facility.

    Returns:

        Peakfinder8DetInfo: the peakfinder8-related detector
        information.
    """
    return named_tuples.Peakfinder8DetInfo(
        asic_nx=2463, asic_ny=2527, nasics_x=1, nasics_y=1
    )


############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################


def open_event(event):
    """
    Opens a Pilatus event retrieved at Petra III.

    Makes the content of a Pilatus event retrieved at the petra III
    facility available in the 'data' entry of the event dictionary.

    Args:

        event (Dict): a dictionary with the event data.
    """
    # Wraps the binary data that HiDRA sends to OnDA in a BytesIO
    # object.
    byio_data = io.BytesIO(event["data"])

    # Reads the data using the fabio library and stores the content as
    # a cbf_obj object in the 'data' entry of the event dictionary.
    cbf_image = fabio.cbfimage.CbfImage()
    event["data"] = cbf_image.read(byio_data)


def close_event(event):
    """
    Closes a Pilatus event retrieved at Petra III.

    Args:

        event (Dict): a dictionary with the event data.
    """
    del event
    # Does nothing: cbf_obj objects don't need to be closed.


def get_num_frames_in_event(event):
    """
    Number of Pilatus frames in  Petra III event.

    Returns the number of Lambda detector frames in an event retrieved
    at the Petra III facility (1 event = 1 file).

    Args:

        event (Dict): a dictionary with the event data.

    Retuns:

        int: the number of frames in the event.
    """
    del event
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
    One frame of Pilatus detector data at Petra III.

    Extracts one frame of Pilatus detector data from an event retrieved
    at the Petra III facility.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        ndarray: one frame of detector data.
    """
    # Extracts frame information from the data stored in the event
    # dictionary.
    return event["data"].data


def event_id(event):
    """
    Retrieves a Pilatus unique event identifier at Petra III.

    Returns a unique label that unambiguosly identifies the current
    event within an experiment. When using the Pilatus detector at the
    Petra III facility, the full path of the file where the current
    event has been saved is used as an identifier.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        str: a unique event identifier.
    """
    return event["full_path"]


def frame_id(event):
    """
    Retrieves a Pilatus unique frame identifier at Petra III.

    Returns a unique label that unambiguosly identifies the current
    detector frame within the event. When using the Pilatus detector
    at the Petra III facility, the index of the current frame within
    the file where the event has been saved is used as an identifier.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        str: a unique frame identifier with the event.
    """
    del event

    # Pilatus events only contains one frame, so returns 0.
    return str(0)
