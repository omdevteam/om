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
Retrieval of data from Jungfrau 1M detector files.

Functions and classes used to retrieve data from files written by the
Pilatus detector.
"""
from __future__ import absolute_import, division, print_function

from onda.data_retrieval_layer.file_formats import cbf_files
from onda.utils import named_tuples


#####################
#                   #
# UTILITY FUNCTIONS #
#                   #
#####################


def get_file_extensions():
    """
    Extensions used for Pilatus files.

    Returns the extensions used for files written by the Pilatus
    detector.

    Returns:

        Tuple[str]: the list of file extensions.
    """
    return (".cbf",)


def get_peakfinder8_info():
    """
    Peakfinder8 info for the Pilatus detector.

    Retrieves the peakfinder8 information matching the data format
    used in files written by the the Pilatus detector.

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


open_event = cbf_files.open_event  # pylint: disable=invalid-name

close_event = cbf_files.close_event  # pylint: disable=invalid-name


def get_num_frames_in_event(event):
    """
    Number of frames in a Pilatus file.

    Returns the number of Pilatus detector frames in an event recovered
    from a file (1 event = 1 file).

    Args:

        event (Dict): a dictionary with the event data.

    Retuns:

        int:
    """
    del event
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
    One frame of detector data from a Pilatus file.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        ndarray: one frame of detector data.
    """
    # Returns the data from the fabio cbf_obj object previously stored
    # in the input dictionary.
    return event['data'].data


def event_id(event):
    """
    Retrieves a unique event identifier for Pilatus files.

    Returns a unique label that unambiguosly identifies the current
    event within an experiment. For Pilatus files, the full path to the
    file storing the event is used as an identifier.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        str: a unique event identifier.
    """
    return event['full_path']


def frame_id(event):
    """
    Retrieves a unique identifier for a Pilaltus frame.

    Returns a unique label that unambiguosly identifies the current
    detector frame within the event. For Pilatus files, the index of
    the frame within the file is used as an identifier.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        str: a unique frame identifier with the event.
    """
    # The frame index is always 0, as Pilatus files usually contain
    # just one frame.
    del event
    return str(0)
