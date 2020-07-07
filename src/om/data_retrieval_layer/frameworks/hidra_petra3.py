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
Retrieval of events from HiDRA at Petra III.

This module contains functions and classes that retrieve data events from the HiDRA
framework at the PETRA III facility.
"""
from __future__ import absolute_import, division, print_function

import os.path
import socket
import sys
from typing import Any, Dict, Generator

import numpy
from future.utils import raise_from

from onda.utils import (
    data_event,
    dynamic_import,
    exceptions,
    parameters,
)
from .hidra_api import Transfer, transfer


def _create_hidra_info(source, node_pool_size, monitor_params):
    # type: (str, int, parameters.MonitorParams) -> Dict[str, Any]

    # Creates the HidraInfo object needed to initialize the HiDRA event source.

    # Reads the requested transfer type from the configuration file. If it is not
    # specified there, imports the suggested transfer type from the data extraction
    # layer and use that.
    transfer_type = monitor_params.get_param(
        group="DataRetrievalLayer", parameter="hidra_transfer_type", parameter_type=str
    )
    if transfer_type is None:
        transfer_type = dynamic_import.get_hidra_transfer_type(monitor_params)

    if transfer_type == "data":
        # If the transfer type is data-based, requests the latest event with full
        # data, and sets the data base path to an empty path, because HiDRA will
        # provide the data directly, and there will be no need to look for the file.
        query_text = "QUERY_NEXT"
        data_base_path = ""
    elif transfer_type == "metadata":
        # If the transfer type is metadata-based, requests the latest event with
        # metadata only and reads the data base path from the configuration file:
        # HiDRA will only provide the path to the file relative to the base data path.
        query_text = "QUERY_METADATA"
        data_base_path = os.path.join(
            monitor_params.get_param(
                group="DataRetrievalLayer",
                parameter="hidra_data_base_path",
                parameter_type=str,
                required=True,
            )
        )
    else:
        raise RuntimeError("Unrecognized HiDRA transfer type.")

    base_port = monitor_params.get_param(
        group="DataRetrievalLayer",
        parameter="hidra_base_port",
        parameter_type=int,
        required=True,
    )

    # Search the configuration file for a HiDRA selection string. If the selection
    # string is not found, use the file extensions from the detector layer as
    # selection string.
    hidra_selection_string = monitor_params.get_param(
        group="DataRetrievalLayer",
        parameter="hidra_selection_string",
        parameter_type=str,
    )
    if hidra_selection_string is None:
        hidra_selection_string = dynamic_import.get_file_extensions(monitor_params)

    # Add an empty target at the beginning to cover the master node. In this way, the
    # index of a node in the target list will match its rank.
    targets = [["", "", 1, ""]]

    # Create the HiDRA query object, as requested by the HiDRA API.
    for rank in range(1, node_pool_size):
        target_entry = [
            socket.gethostname(),
            str(base_port + rank),
            str(1),
            hidra_selection_string,
        ]
        targets.append(target_entry)

    query = Transfer(connection_type=query_text, signal_host=source, use_log=False)

    return {
        "query": query,
        "targets": targets,
        "data_base_path": data_base_path,
    }


############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################


def initialize_event_source(source, node_pool_size, monitor_params):
    # type: (str, int, parameters.MonitorParams) -> Dict[str, Any]
    """
    Initializes the HiDRA event source at Petra III.

    This function must be called on the master node before the :func:`event_generator`
    function is called on the worker nodes.

    Arguments:

        source (str): the hostname or ip address of the machine where HiDRA is running.

        node_pool_size (int): the total number of nodes in the OnDA pool, including all
            the worker nodes and the master node.

        monitor_params (:class:`~onda.utils.parameters.MonitorParams`): an object
            storing the OnDA monitor parameters from the configuration file.

    Returns:

        Dict[str, Any] a dictionary storing the HiDRA initialization information.

    Raises:

        :class:`~onda.utils.exceptions.OndaHidraAPIError`: if the initial connection to
            HiDRA fails.
    """
    print("Announcing OnDA to HiDRA.")
    sys.stdout.flush()
    hidra_info = _create_hidra_info(
        source=source, node_pool_size=node_pool_size, monitor_params=monitor_params
    )

    try:
        hidra_info["query"].initiate(hidra_info["targets"][1:])
    except transfer.CommunicationFailed as exc:
        raise_from(
            exc=exceptions.OndaHidraAPIError(
                "Failed to contact HiDRA: {0}".format(exc)
            ),
            cause=exc,
        )

    return hidra_info


def event_generator(
    source,  # type: str
    node_rank,  # type: int
    node_pool_size,  # type: int
    monitor_params,  # type: parameters.MonitorParams
):
    # type: (...) -> Generator[data_event.DataEvent, None, None]
    """
    Retrieves events to process from HiDRA at Petra III.

    This function must be called on each worker node after the
    :func:`initialize_event_source` function has been called on the master node.
    The function is a generator and it returns an iterator over the events that the
    calling worker must process.


    Arguments:

        source (str): the hostname or ip address of the machine where HiDRA is running.

        node_rank (int): the rank, in the OnDA pool, of the worker node calling the
            function.

        node_pool_size (int): the total number of nodes in the OnDA pool, including all
            the worker nodes and the master node.

        monitor_params (:class:`~onda.utils.parameters.MonitorParams`): an object
            storing the OnDA monitor parameters from the configuration file.

    Yields:

        :class:`~onda.utils.data_event.DataEvent`: an object storing the event data.

    Raises:

        :class:`~onda.utils.exceptions.OndaHidraAPIError`: if the initial connection to
            HiDRA fails.
    """
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

    # Creates the hidra_info object and connect to HiDRA.
    hidra_info = _create_hidra_info(
        source=source, node_pool_size=node_pool_size, monitor_params=monitor_params
    )
    print(
        "Worker {0} listening at port {1}".format(
            node_rank, hidra_info["targets"][node_rank][1]
        )
    )
    sys.stdout.flush()
    try:
        hidra_info["query"].start(hidra_info["targets"][node_rank][1])
    except transfer.CommunicationFailed as exc:
        raise_from(
            exc=exceptions.OndaHidraAPIError(
                "Failed to contact HiDRA: {0}".format(exc)
            ),
            cause=exc,
        )

    while True:
        recovered_metadata, recovered_data = hidra_info["query"].get()
        event.data = recovered_data
        event.metadata = recovered_metadata
        event.framework_info["full_path"] = os.path.join(
            hidra_info["data_base_path"],
            recovered_metadata["relative_path"],
            recovered_metadata["filename"],
        )
        event.framework_info["file_creation_time"] = recovered_metadata[
            "file_create_time"
        ]

        yield event


#############################
#                           #
# DATA EXTRACTION FUNCTIONS #
#                           #
#############################


def timestamp(event):
    # type: (data_event.DataEvent) -> numpy.float64
    """
    Gets the timestamp of an event retrieved from HiDRA at Petra III

    A HiDRA event usually corresponds to a single data file written by a detector. The
    creation date and time of the file is used as timestamp for the event.

    Arguments:

        event (:class:`~onda.utils.data_event.DataEvent`): an object storing the event
            data.

    Returns:

        numpy.float64: the timestamp of the event in seconds from the Epoch.
    """
    # Returns the file creation time previously stored in the event.
    return event.framework_info["file_creation_time"]


def beam_energy(event):
    # type: (data_event.DataEvent) -> float
    """
    Gets the beam energy for an event retrieved from HiDRA at Petra III.

    HiDRA events do not usually contain beam energy information. This function takes
    the beam energy value from the configuration file, specifically from the
    'fallback_beam_energy_in_eV' entry in the 'DataRetrievalLayer' parameter group.

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
    Gets the detector distance for an event retrieved from HiDRA at Petra III.

    HiDRA events don't usually contain detector distance information. This function
    takes it from the configuration file, specifically from the
    'fallback_detector_distance_in_mm' entry in the 'DataRetrievalLayer' parameter
    group.

    Arguments:

        event (:class:`~onda.utils.data_event.DataEvent`): an object storing the event
            data.

    Returns:

        float: the detector distance in mm.
    """
    # Returns the value previously stored in the event.
    return event.framework_info["detector_distance"]
