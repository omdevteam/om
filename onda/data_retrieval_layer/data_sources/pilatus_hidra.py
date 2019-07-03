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
Retrieval of Pilatus detector data from HiDRA.
"""
from __future__ import absolute_import, division, print_function

import io

import fabio

from .pilatus_files import (  # pylint: disable=unused-import
    # Utility functions.
    get_file_extensions,
    get_peakfinder8_info,

    # Event_handing_functions.
    get_num_frames_in_event,

    # Data extraction functions.
    detector_data,  
    event_id,
    frame_id,
)


############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################


def open_event(event):
    # type: (data_event.DataEvent) -> None
    """
    Opens a Pilatus event retrieved from HiDRA.

    For the Pilatus detector, a HiDRA event corresponds to the full content of a single
    Pilatus CBF data file. This function makes the content of the file available in
    the 'data' field of the 'event' object.

    Note:

        This function is designed to be injected as a member function into an
        :class:`~onda.utils.data_event.DataEvent` object.

    Arguments:

        event (:class:`~onda.utils.data_event.DataEvent`): an object storing the event
            data.
    """
    # Wraps the binary data that HiDRA sends to OnDA in a BytesIO object.
    byio_data = io.BytesIO(event["data"])

    # Reads the data using the fabio library and stores the content as a cbf_obj
    # object.
    cbf_image = fabio.cbfimage.CbfImage()
    event["data"] = cbf_image.read(byio_data)


def close_event(event):
    # type: (data_event.DataEvent) -> None
    """
    Closes a Pilatus event retrieved from HiDRA.

    The HiDRA event does not need to be closed, so this function actually does nothing.

    Note:

        This function is designed to be injected as a member function into an
        :class:`~onda.utils.data_event.DataEvent` object.

    Arguments:

        event (:class:`~onda.utils.data_event.DataEvent`): an object storing the event
            data.
    """
    del event
