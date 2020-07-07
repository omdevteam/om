# This file is part of OM.
#
# OM is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# OM is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with OM.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2020 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Retrieval of events from Karabo at the European XFEL.

This module contains functions and classes that retrieve data events from the Karabo
framework at the European XFEL facility.
"""
from __future__ import absolute_import, division, print_function

import sys
import time
from typing import Generator

import numpy
from future.utils import raise_from

from onda.utils import (
    data_event,
    dynamic_import,
    exceptions,
    parameters,
)
from .karabo_api import client


############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################


def initialize_event_source(source, node_pool_size, monitor_params):
    # type: (str, int, parameters.MonitorParams) -> None
    """
    Initializes the Karabo event source at XFEL.

    This function must be called on the master node before the :func:`event_generator`
    function is called on the worker nodes. There is no need to initialize the Karabo
    event source, so this function actually does nothing.

    Arguments:

        source (str): the hostname (or IP address) and the port where the Karabo Bridge
            is running, separated by a colon.

        node_pool_size (int): the total number of nodes in the OnDA pool, including all
            the worker nodes and the master node.

        monitor_params (:class:`~onda.utils.parameters.MonitorParams`): an object
            storing the OnDA monitor parameters from the configuration file.
    """
    del source
    del node_pool_size
    del monitor_params


def event_generator(
    source,  # type: str
    node_rank,  # type: int
    node_pool_size,  # type: int
    monitor_params,  # type: parameters.MonitorParams
):
    # type: (...) -> Generator[data_event.DataEvent, None, None]
    """
    Retrieves events to process from Karabo at XFEL .

    This function must be called on each worker node after the
    :func:`initialize_event_source` function has been called on the master node.
    The function is a generator and it returns an iterator over the events that the
    calling worker must process.

    Arguments:

        source (str): the hostname (or IP address) and the port where the Karabo Bridge
            is running, separated by a colon.

        node_rank (int): the rank, in the OnDA pool, of the worker node calling the
            function.

        node_pool_size (int): the total number of nodes in the OnDA pool, including all
            the worker nodes and the master node.

        monitor_params (:class:`~onda.utils.parameters.MonitorParams`): an object
            storing the OnDA monitor parameters from the configuration file.

    Yields:

        :class:`~onda.utils.data_event.DataEvent`: an object storing the event data.

    Raises:

        :class:`~onda.utils.exceptions.OndaInvalidSourceError`: if the format of the
            'source' argument is wrong.
    """
    del node_pool_size
    data_retrieval_layer_filename = monitor_params.get_param(
        group="Onda",
        parameter="data_retrieval_layer",
        parameter_type=str,
        required=True,
    )
    data_retrieval_layer = dynamic_import.import_data_retrieval_layer(
        data_retrieval_layer_filename=data_retrieval_layer_filename
    )
    required_data = monitor_params.get_param(
        group="Onda", parameter="required_data", parameter_type=list, required=True
    )
    event_handling_functions = dynamic_import.get_event_handling_funcs(
        data_retrieval_layer=data_retrieval_layer
    )
    data_extraction_functions = dynamic_import.get_data_extraction_funcs(
        required_data=required_data, data_retrieval_layer=data_retrieval_layer
    )
    event = data_event.DataEvent(
        event_handling_funcs=event_handling_functions,
        data_extraction_funcs=data_extraction_functions,
    )

    # Fills the framework info with static data that will be retrieved later.
    event.framework_info["detector_label"] = monitor_params.get_param(
        group="DataRetrievalLayer",
        parameter="karabo_detector_label",
        parameter_type=str,
        required=True,
    )
    if "detector2_label" in data_extraction_functions:
        event.framework_info["detector2_label"] = monitor_params.get_param(
            group="DataRetrievalLayer",
            parameter="karabo_detector2_label",
            parameter_type=str,
            required=True,
        )
    if "detector3_label" in data_extraction_functions:
        event.framework_info["detector3_label"] = monitor_params.get_param(
            group="DataRetrievalLayer",
            parameter="karabo_detector3_label",
            parameter_type=str,
            required=True,
        )
    if "beam_energy" in data_extraction_functions:
        event.framework_info["beam_energy"] = monitor_params.get_param(
            group="DataRetrievalLayer",
            parameter="fallback_beam_energy_in_eV",
            parameter_type=float,
            required=True,
        )
    if "detector_distance" in data_extraction_functions:
        event.framework_info["detector_distance"] = monitor_params.get_param(
            group="DataRetrievalLayer",
            parameter="fallback_detector_distance_in_mm",
            parameter_type=float,
            required=True,
        )
    if "optical_laser_active" in data_extraction_functions:
        event.framework_info["frames_with_optical_laser"] = monitor_params.get_param(
            group="DataRetrievalLayer",
            parameter="karabo_frame_ids_with_optical_laser_active",
            parameter_type=list,
            required=True,
        )
    if "xrays_active" in data_extraction_functions:
        event.framework_info["frames_with_xrays"] = monitor_params.get_param(
            group="DataRetrievalLayer",
            parameter="karabo_frame_ids_with_xrays_active",
            parameter_type=list,
            required=True,
        )

    # Connects to the Karabo Bridge using the Karabo API.
    max_event_age = monitor_params.get_param(
        group="DataRetrievalLayer",
        parameter="karabo_max_event_age",
        parameter_type=float,
    )
    if max_event_age is None:
        max_event_age = 10000000000

    source_parts = source.split(":")
    try:
        hostname = source_parts[0]
        port = source_parts[1]
    except IndexError as exc:
        raise_from(
            exc=exceptions.OndaInvalidSourceError(
                "Invalid source format: {0}.".format(source)
            ),
            cause=exc,
        )
    print("Worker {0} listening to {1} at port {2}".format(node_rank, hostname, port))
    sys.stdout.flush()
    krb_client = client.Client("tcp://{0}".format(source))

    while True:
        event.data, event.metadata = krb_client.next()
        event.timestamp = numpy.float64(
            "{0}.{1}".format(
                event.metadata[event.framework_info["detector_label"]]["timestamp.sec"],
                event.metadata[event.framework_info["detector_label"]][
                    "timestamp.frac"
                ],
            )
        )
        time_now = numpy.float64(time.time())
        if (time_now - event.timestamp) > max_event_age:
            continue

        yield event


def open_event(event):
    # type: (data_event.DataEvent) -> None
    """
    Opens an event retrieved from Karabo at XFEL.

    Karabo events do not need to be opened. As soon as an event is retrieved, its
    content is made available in the 'data' field of the 'event' object. This function
    actually does nothing.

    NOTE: This function is designed to be injected as a member function into an
    :class:`~onda.utils.data_event.DataEvent` object.

    Arguments:

        event (:class:`~onda.utils.data_event.DataEvent`): an object storing the event
            data.
    """
    del event


def close_event(event):
    # type: (data_event.DataEvent) -> None
    """
    Closes an event retrieved from Karabo at XFEL.

    Karabo events do not need to be closed, so this function actually does nothing.

    NOTE: This function is designed to be injected as a member function into an
    :class:`~onda.utils.data_event.DataEvent` object.

    Arguments:

        event (:class:`~onda.utils.data_event.DataEvent`): an object storing the event
            data.
    """
    del event


#############################
#                           #
# DATA EXTRACTION FUNCTIONS #
#                           #
#############################


def timestamp(event):
    # type: (data_event.DataEvent) -> numpy.float64
    """
    Gets the timestamp of an event retrieved from Karabo at XFEL.

    Arguments:

        event (:class:`~onda.utils.data_event.DataEvent`): an object storing the event
            data.

    Returns:

        numpy.float64: the timestamp of the event  in seconds from the Epoch.
    """
    # Returns the timestamp previously stored in the event.
    return event.timestamp


def optical_laser_active(event):
    # type: (data_event.DataEvent) -> bool
    """
    Retrieves from Karabo the status of the optical laser at XFEL.

    Returns whether, in pump probe experiments, the optical laser is active for the
    current frame. Currently Karabo provides no information about the status of
    optical lasers at XFEL. Hence, this function determines the status of the laser
    according to information provided in the OnDA configuration file.

    * The file must include a entry called 'karabo_frame_ids_with_optical_laser_active'
      in the 'DataRetrievalLayer' parameter group.

    * The entry must contain a list of frame indexes for which the optical laser is
      supposed to be active.

    * If the index of the current frame within the event is included in the list, the
      optical laser is considered to be active.

    Arguments:

        event (:class:`~onda.utils.data_event.DataEvent`): an object storing the event
            data.

    Returns:

        bool: True if the optical laser is active, False otherwise.
    """
    frame_cell_id = event.data[event.framework_info["data_label"]]["image.pulseId"][
        event.current_frame
    ]
    return frame_cell_id in event.framework_info["frames_with_optical_laser"]


def xrays_active(event):
    # type: (data_event.DataEvent) -> bool
    """
    Retrieves from Karabo the status of the x-ray beam at XFEL.

    Returns whether the x-ray beam is active for the current frame. Currently Karabo
    provides no information about the status of the x-ray beam at XFEL. Hence, this
    function determines the status of the beam according to information provided in the
    OnDA configuration file.

    * The file must include a entry called 'karabo_frame_ids_with_xrays_active'
      in the 'DataRetrievalLayer' parameter group.

    * The entry must contain a list of frame indexes for which the x-ray beam is
      supposed to be active.

    * If the index of the current frame within the event is included in the list, the
      x-ray beam is considered to be active.

    Arguments:

        event (:class:`~onda.utils.data_event.DataEvent`): an object storing the event
            data.

    Returns:

        bool: True if the x-ray beam is active, False otherwise.
    """
    frame_cell_id = event.data[event.framework_info["data_label"]]["image.pulseId"][
        event.current_frame
    ]
    return frame_cell_id in event.framework_info["frames_with_xrays"]


def event_id(event):
    # type: (data_event.DataEvent) -> str
    """
    Retrieves a unique identifier for an event retrieved from Karabo at XFEL.

    Returns a label that unambiguously identifies, within an experiment, the event
    currently being processed. At the European XFEL facility, an event corresponds to a
    pulse train and the train id is used as identifier.

    Arguments:

        event (:class:`~onda.utils.data_event.DataEvent`): an object storing the event
            data.

    Returns:

        str: a unique event identifier.
    """
    return str(event.metadata[event.framework_info["detector_label"]]["timestamp.tid"])


def frame_id(event):
    # type: (data_event.DataEvent) -> str
    """
    Gets a unique identifier for a data frame retrieved from Karabo at XFEL.

    Returns a label that unambiguously identifies, within an event, the frame currently
    being processed. At the European XFEL facility, the cellId property of the frame
    within its train is used as identifier.

    Arguments:

         event (:class:`~onda.utils.data_event.DataEvent`): an object storing the event
            data.

    Returns:

        str: a unique frame identifier (within an event).
    """
    return str(
        event.data[event.framework_info["detector_label"]]["image.cellId"][
            event.current_frame
        ]
    )


def beam_energy(event):
    # type: (data_event.DataEvent) -> float
    """
    Gets the beam energy for an event retrieved from Karabo at XFEL.

    Karabo events do not currently contain beam energy information. This function takes
    it from the configuration file, specifically from the
    'fallback_beam_energy_in_eV' entry in the 'DataRetrievalLayer' parameter
    group.

    Arguments:

        event (:class:`~onda.utils.data_event.DataEvent`): an object storing the event
            data.

    Returns:

        float: the energy of the beam in eV.
    """
    # Returns the value previously stored in the event.
    return event.framework_info["beam_energy"]


def detector_distance(event):
    # type: (data_event.DataEvent) -> float
    """
    Gets the detector distance for an event retrieved from Karabo at XFEL.

    Karabo events don't currently contain detector distance information. This function
    takes it from the configuration file, specifically from the
    'fallback_detector_distance_in_mm' entry in the 'DataRetrievalLayer'
    parameter group.

    Arguments:

        event (:class:`~onda.utils.data_event.DataEvent`): an object storing the event
            data.

    Returns:

        float: the detector distance in mm.
    """
    # Returns the value previously stored in the event.
    return event.framework_info["detector_distance"]
