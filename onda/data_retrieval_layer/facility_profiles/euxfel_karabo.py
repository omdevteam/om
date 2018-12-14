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
Event and data retrieval from Karabo at XFEL.

Non detector-specific functions and classes used for event and data
retrieval from Karabo at the European XFEL facility.
"""
from __future__ import absolute_import, division, print_function

from onda.data_retrieval_layer.event_sources import karabo_source
from onda.data_retrieval_layer.filters import event_filters, frame_filters
from onda.utils import parameters


############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################


initialize_event_source = (  # pylint: disable=invalid-name
    karabo_source.initialize_event_source
)


event_generator = (  # pylint: disable=invalid-name
    karabo_source.event_generator
)


open_event = (  # pylint: disable=invalid-name
    karabo_source.open_event
)


close_event = (  # pylint: disable=invalid-name
    karabo_source.close_event
)


EventFilter = (  # pylint: disable=invalid-name
    event_filters.AgeEventFilter
)


FrameFilter = (  # pylint: disable=invalid-name
    frame_filters.IndexBasedFrameFilter
)


#############################
#                           #
# DATA EXTRACTION FUNCTIONS #
#                           #
#############################


def timestamp(event):
    """
    Timestamp of an event retrieved from Karabo at XFEL.

    Extracts the timestamp of an event retrieved from Karabo at the
    European XFEL facility.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        numpy.float64: the timestamp of the event.
    """
    return event['timestamp']


def optical_laser_active(event):
    """
    Retrieves from Karabo the optical laser status at XFEL.

    Returns whether the optical laser is active or not. In order to
    determine this, it needs information about the optical laser
    activation pattern to be provided in the configuration file.
    The configuration file should contain a list of cellIds for which
    the optical laser is supposed to be active.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        bool: True if the optical laser is active. False otherwise.
    """
    frame_cell_id = (
        event[
            'data'
        ][
            'SPB_DET_AGIPD1M-1/CAL/APPEND_CORRECTED'
        ][
            'image.pulseId'
        ][
            event['frame_offset']
        ]
    )

    return frame_cell_id in event['monitor_params'].get_param(
        section='DataRetrievalLayer',
        parameter='frame_ids_with_optical_laser_active',
        type_=list,
        required=True
    )


def xrays_active(event):
    """
    Retrieves from Karabo the X-ray status at XFEL.

    Returns whether the X-rays are active or not. In order to
    determine this, it needs information about the X-ray
    activation pattern to be provided in the configuration file.
    The configuration file should contain a list of cellIds for which
    the X-rays are supposed to be active.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        bool: True if the X-rays are active. False otherwise.
    """
    frame_cell_id = (
        event[
            'data'
        ][
            'SPB_DET_AGIPD1M-1/CAL/APPEND_CORRECTED'
        ][
            'image.pulseId'
        ][
            event['frame_offset']
        ]
    )

    return frame_cell_id in event['monitor_params'].get_param(
        section='DataRetrievalLayer',
        parameter='frame_ids_with_xrays_active',
        type_=list,
        required=True
    )


def event_id(event):
    """
    Retrieves from Karabo a unique event idenitfier at XFEL.

    Returns a unique label that unambiguosly identifies the current
    event within an experiment. When using Karabo at the
    European XFEL facility, the train id of the current event is used
    as an identifier.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        str: a unique event identifier.
    """
    frame_cell_id = (
        event[
            'data'
        ][
            'SPB_DET_AGIPD1M-1/CAL/APPEND_CORRECTED'
        ][
            'timestamp.trainId'
        ]
    )

    return str(frame_cell_id)


def frame_id(event):
    """
    Retrieves from Karabo a unique frame identifier at XFEL.

    Returns a unique label that unambiguosly identifies the current
    detector frame within the event. When using Karabo at the
    European XFEL facility, the cell id of the current frame is used as
    an idenitifer.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        str: a unique frame identifier with the event.
    """
    frame_cell_id = (
        event[
            'data'
        ][
            'SPB_DET_AGIPD1M-1/CAL/APPEND_CORRECTED'
        ][
            'image.pulseId'
        ][
            event['frame_offset']
        ]
    )

    return str(frame_cell_id)


beam_energy = (  # pylint: disable=invalid-name
    parameters.beam_energy_from_monitor_params
)


detector_distance = (  # pylint: disable=invalid-name
    parameters.detector_distance_from_monitor_params
)
