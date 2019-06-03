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
Retrieval of events from HiDRA.

Functions and classes used to retrieve data events from Karabo.
"""
from __future__ import absolute_import, division, print_function

import sys
import time

import numpy
from future.utils import raise_from

from onda.data_retrieval_layer.frameworks.karabo_api import client
from onda.utils import data_event, dynamic_import, exceptions


############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################


def initialize_event_source(source, mpi_pool_size, monitor_params):
    """
    Initializes the Karabo event source.

    This function must be called on the master node before the :obj:`event_generator`
    function is called on the worker nodes.

    Args:

        source (str): a string containing the IP address (or the hostname) and the
            port of the machine where the Karabo Bridge is running, separated by a
            colon (i.e:'ip:port').

        mpi_pool_size (int): size of the node pool that includes the node where the
            function is called.

        monitor_params (MonitorParams): a :obj:`~onda.utils.parameters.MonitorParams`
            object containing the monitor parameters from the configuration file.
    """
    del source
    del mpi_pool_size
    del monitor_params
    # Karabo needs no initialization, so the function does nothing.


def event_generator(source, node_rank, mpi_pool_size, monitor_params):
    """
    Initializes the recovery of events from Karabo.

    Returns an iterator over the events that should be processed by the worker that
    calls the function. This function must be called on each worker node after the
    :obj:`initialize_event_source` function has been called on the master node.

    Args:

        source (str): a string containing the IP address (or the hostname) and the
            port of the machine where the Karabo Bridge is running, separated by a
            colon (i.e:'ip:port').

        node_rank (int): rank of the node where the function is called.

        mpi_pool_size (int): size of the node pool that includes the node where the
            function is called.

        monitor_params (MonitorParams): a :obj:`~onda.utils.parameters.MonitorParams`
            object containing the monitor parameters from the configuration file.

    Yields:

        Dict: A dictionary containing the metadata and data of an event (at XFEL: 1
        event = 1 train).
    """
    del mpi_pool_size
    source_parts = source.split(":")
    try:
        hostname = source_parts[0]
        port = source_parts[1]
    except IndexError as exc:
        raise_from(
            exc=exceptions.InvalidSource("Invalid source format: {}.".format(source)),
            cause=exc,
        )

    data_label = monitor_params.get_param(
        section="DataRetrievalLayer",
        parameter="karabo_data_label",
        type_=str,
        required=True,
    )

    max_event_age = monitor_params.get_param(
        section="DataRetrievalLayer", parameter="karabo_max_event_age", type_=float
    )
    if not max_event_age:
        max_event_age = 10000000000

    event_handling_functions = dynamic_import.get_event_handling_funcs(monitor_params)
    data_extraction_functions = dynamic_import.get_data_extraction_funcs(monitor_params)
    event = data_event.DataEvent(
        event_handling_funcs=event_handling_functions,
        data_extraction_funcs=data_extraction_functions,
    )

    # Fills required frameworks info.
    event.framework_info["data_label"] = data_label
    if "beam_energy" in data_extraction_functions:
        event.framework_info["beam_energy"] = monitor_params.get_param(
            section="DataRetrievalLayer",
            parameter="karabo_fallback_beam_energy_in_eV",
            type_=float,
            required=True,
        )

    if "detector_distance" in data_extraction_functions:
        event.framework_info["detector_distance"] = monitor_params.get_param(
            section="DataRetrievalLayer",
            parameter="karabo_fallback_detector_distance_in_mm",
            type_=float,
            required=True,
        )

    if "optical_laser_active" in data_extraction_functions:
        event.framework_info["frames_with_optical_laser"] = monitor_params.get_param(
            section="DataRetrievalLayer",
            parameter="karabo_frame_ids_with_optical_laser_active",
            type_=list,
            required=True,
        )

    if "xrays_active" in data_extraction_functions:
        event.framework_info["frames_with_xrays"] = monitor_params.get_param(
            section="DataRetrievalLayer",
            parameter="karabo_frame_ids_with_xrays_active",
            type_=list,
            required=True,
        )

    print("Worker {} listening to {} at port {}".format(node_rank, hostname, port))
    sys.stdout.flush()

    # Connects to the Karabo Bridge using the Karabo API.
    krb_client = client.Client("tcp://{}".format(source))
    while True:
        event.data, event.metadata = krb_client.next()
        event.timestamp = numpy.float64(
            "{0}.{1}".format(
                event.metadata[data_label]["timestamp.sec"],
                event.metadata[data_label]["timestamp.frac"],
            )
        )
        time_now = numpy.float64(time.time())  # pylint: disable=no-member
        if (time_now - event.timestamp) > max_event_age:
            continue

        yield event


def open_event(event):
    """
    Opens an event retrieved from Karabo.

    Makes the content of a retrieved Karabo event available in the 'data' entry of the
    event dictionary.

    Args:

        event (DataEvent): :obj:`onda.utils.data_event.DataEvent` object storing the
            data event.
    """
    # Karabo events do not need to be opened. this function does nothing.
    del event


def close_event(event):
    """
    Closes an event retrieved from Karabo.

    Args:

        event (DataEvent): :obj:`onda.utils.data_event.DataEvent` object storing the
            data event.
    """
    # Karabo events do not need to be closed. This function does nothing.
    del event


#############################
#                           #
# DATA EXTRACTION FUNCTIONS #
#                           #
#############################


def timestamp(event):
    """
    Timestamp of an event retrieved from Karabo at XFEL.

    Extracts the timestamp of an event retrieved from Karabo at the European XFEL
    facility.

    Args:

        event (DataEvent): :obj:`onda.utils.data_event.DataEvent` object storing the
            data event.

    Returns:

        numpy.float64: the timestamp of the event.
    """
    # Returns the timestamp previously stored in the event.
    return event.timestamp


def optical_laser_active(event):
    """
    Retrieves from Karabo the optical laser status at XFEL.

    Returns whether the optical laser is active or not. In order to determine this, it
    needs information about the optical laser activation pattern to be provided in the
    configuration file. The configuration file should contain a list of cellIds for
    which the optical laser is supposed to be active.

    Args:

        event (DataEvent): :obj:`onda.utils.data_event.DataEvent` object storing the
            data event.

    Returns:

        bool: True if the optical laser is active. False otherwise.
    """
    frame_cell_id = event.data[event.framework_info["data_label"]]["image.pulseId"][
        event.current_frame
    ]
    return frame_cell_id in event.framework_info["frames_with_optical_laser"]


def xrays_active(event):
    """
    Retrieves from Karabo the X-ray status at XFEL.

    Returns whether the X-rays are active or not. In order to determine this, it needs
    information about the X-ray activation pattern to be provided in the configuration
    file. The configuration file should contain a list of cellIds for which the X-rays
    are active.

    Args:

        event (DataEvent): :obj:`onda.utils.data_event.DataEvent` object storing the
            data event.

    Returns:

        bool: True if the X-rays are active. False otherwise.
    """
    frame_cell_id = event.data[event.framework_info["data_label"]]["image.pulseId"][
        event.current_frame
    ]
    return frame_cell_id in event.framework_info["frames_with_xrays"]


def event_id(event):
    """
    Retrieves from Karabo a unique event idenitfier at XFEL.

    Returns a unique label that unambiguosly identifies the current event within an
    experiment. When using Karabo at the European XFEL facility, the train id of the
    current event is used as an identifier.

    Args:

        event (DataEvent): :obj:`onda.utils.data_event.DataEvent` object storing the
            data event.

    Returns:

        str: a unique event identifier.
    """
    return str(event.data[event.framework_info["data_label"]]["timestamp.trainId"])


def frame_id(event):
    """
    Retrieves from Karabo a unique frame identifier at XFEL.

    Returns a unique label that unambiguosly identifies the current detector frame
    within the event. When using Karabo at the European XFEL facility, the cell id of
    the current frame is used as an idenitifer.

    Args:

        event (DataEvent): :obj:`onda.utils.data_event.DataEvent` object storing the
            data event.

    Returns:

        str: a unique frame identifier with the event.
    """
    return str(event.current_frame)


def beam_energy(event):
    """
    Retrieves the beam energy from Karabo.

    Karabo does not currently provide information about the beam energy. The value is
    taken from the configuration file, specifically fromt the
    'karabo_fallback_beam_energy_in_eV' entry in the 'DataRetrievalLayer' section.

    Args:

        event (DataEvent): :obj:`onda.utils.data_event.DataEvent` object storing the
            data event.

    Returns:

        float: the energy of the beam in eV.
    """
    # Returns the value previously stored in the event.
    return event.framework_info["beam_energy"]


def detector_distance(event):
    """
    Retrieves the detector distance from Karabo.

    Karabo does not currently provide information about the detector distance. The
    value is taken from the configuration file, specifically fromt the
    'karabo_fallback_detector_distance_in_mm' entry in the 'DataRetrievalLayer'
    section.

    Args:

        event (DataEvent): :obj:`onda.utils.data_event.DataEvent` object storing the
            data event.

    Returns:

        float: the distance between the detector and the sample in m.
    """
    # Returns the value previously stored in the event.
    return event.framework_info["detector_distance"]
