# This file is part of OnDA.
#
# OnDA is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# OnDA is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with OnDA.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Retrieval of AGIPD 1M detector data from Karabo.
"""
from __future__ import absolute_import, division, print_function

import numpy  # pylint: disable=unused-import

from onda.utils import data_event, named_tuples  # pylint: disable=unused-import

#####################
#                   #
# UTILITY FUNCTIONS #
#                   #
#####################


def get_peakfinder8_info():
    # type () -> named_tuples.Peakfinder8Info
    """
    Retrieves the peakfinder8 information for the AGIPD 1M detector.

    Returns:

        :class:`~onda.utils.named_tuples.Peakfinder8Info`: a named tuple storing the
        peakfinder8 information.
    """
    return named_tuples.Peakfinder8Info(
        asic_nx=128, asic_ny=512, nasics_x=1, nasics_y=16
    )


############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################


def get_num_frames_in_event(event):
    # type: (data_event.DataEvent) -> int
    """
    Gets the number of frames in an AGIPD 1M event retrieved from Karabo.

    This function retrieves the number of frames for the detector identified by the
    'karabo_detector_label' entry in the 'DataRetrievalLayer' section of the
    configuration file.

    Note:

        This function is designed to be injected as a member function into an
        :class:`~onda.utils.data_event.DataEvent` object.

    Arguments:

        event (:class:`~onda.utils.data_event.DataEvent`): an object storing the event
            data.

    Returns:

        int: the number of frames in the event.
    """
    # return event.data[event.framework_info["detector_label"]]["image.data"].shape[0]
    return (
        event.data[event.framework_info["detector_label"]]["image.data"]
        .transpose(3, 0, 2, 1)
        .shape[0]
    )


#############################
#                           #
# DATA EXTRACTION FUNCTIONS #
#                           #
#############################


def detector_data(event):
    # type: (data_event.DataEvent) -> numpy.ndarray
    """
    Retrieves from Karabo one frame of AGIPD 1M detector data.

    This function retrieves a data frame from the detector identified by the
    'karabo_detector_label' entry in the 'DataRetrievalLayer' section of the
    configuration file.

    Arguments:

        event (:class:`~onda.utils.data_event.DataEvent`): an object storing
            the event data.

    Returns:

        numpy.ndarray: one frame of detector data.
    """
    # Rearranges the data into 'slab' format.
    return (
        event.data[event.framework_info["detector_label"]]["image.data"]
        .transpose(3, 0, 2, 1)[
            # return event.data[event.framework_info["detector_label"]]["image.data"][
            event.current_frame,
            ...,
        ]
        .reshape(16 * 512, 128)
    )
