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
Retrieval of events from HiDRA.

Functions and classes used to retrieve data events from HidDRA.
"""
from __future__ import absolute_import, division, print_function

import os.path
import socket
import sys

from future.utils import raise_from

from onda.data_retrieval_layer.event_sources import hidra_api
from onda.utils import dynamic_import, exceptions, named_tuples


############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################


def _get_hidra_info(
        source,
        mpi_pool_size,
        monitor_params
):
    # Reads the requested transfer type from the configuration file.
    # If it is not specified there, imports the suggested transfer type
    # from the data extraction layer and use that.
    transfer_type = monitor_params.get_param(
        section='DataRetrievalLayer',
        parameter='transfer_type',
        type_=str,
    )
    if transfer_type is None:
        transfer_type = dynamic_import.get_hidra_transfer_type(monitor_params)

    if transfer_type == 'data':
        # If the transfer type is data-based, requests the latest event
        # with full data, and sets the data base path to an empty path,
        # because HiDRA will provide the data directly, and there will
        # be no need to look for the file.
        query_text = 'QUERY_NEXT'
        data_base_path = ''
    elif transfer_type == 'metadata':

        # If the transfer type is metadata-based, requests the latest
        # event with metadata only and reads the data base path from the
        # configuration file: HiDRA will only provide the path to the
        # file relative to the base data path.
        query_text = 'QUERY_METADATA'
        data_base_path = os.path.join(
            monitor_params.getparam(
                section='DataRetrievalLayer',
                parameter='data_base_path',
                type_=str,
                required=True
            )
        )
    else:
        raise RuntimeError("Unrecognized HiDRA transfer type.")

    base_port = monitor_params.get_param(
        section='DataRetrievalLayer',
        parameter='base_port',
        type_=int,
        required=True
    )

    # Search the configuration file for a HiDRA selection string.
    # If the selection string is not found, use the file extensions
    # from the detector layer as selection string.
    hidra_selection_string = monitor_params.get_param(
        section='DataRetrievalLayer',
        parameter='hidra_selection_string',
        type_=str
    )
    if hidra_selection_string is None:
        hidra_selection_string = dynamic_import.get_file_extensions(
            monitor_params
        )

    # Add an empty target at the beginning to cover the master node. In
    # this way, the index of a node in the target list will match its
    # rank.
    targets = [['', '', 1, '']]

    # Create the HiDRA query object, as requested by the HiDRA API.
    for rank in range(1, mpi_pool_size):
        target_entry = [
            socket.gethostname(),
            str(base_port + rank),
            str(1),
            hidra_selection_string
        ]
        targets.append(target_entry)

    query = hidra_api.Transfer(
        connection_type=query_text,
        signal_host=source,
        use_log=False
    )

    return named_tuples.HidraInfo(
        query=query,
        targets=targets,
        data_base_path=data_base_path
    )


def initialize_event_source(
        source,
        mpi_pool_size,
        monitor_params
):
    """
    Initializes the HiDRA event source.

    This function must be called on the master node before the
    :obj:`event_generator` function is called on the worker nodes.

    Args:

        source (str): the IP address or hostname of the machine where
            HiDRA is running.

        mpi_pool_size (int): size of the node pool that includes the
            node where the function is called.

        monitor_params (MonitorParams): a
            :obj:`~onda.utils.parameters.MonitorParams` object
            containing the monitor parameters from the configuration
            file.
    """
    print("Announcing OnDA to HiDRA.")
    sys.stdout.flush()

    hidra_info = _get_hidra_info(
        source=source,
        mpi_pool_size=mpi_pool_size,
        monitor_params=monitor_params
    )

    try:
        hidra_info.query.initiate(hidra_info.targets[1:])
    except hidra_api.transfer.CommunicationFailed as exc:
        raise_from(
            exc=exceptions.HidraAPIError(
                "Failed to contact HiDRA: {0}".format(exc)
            ),
            cause=None
        )


def event_generator(
        source,
        node_rank,
        mpi_pool_size,
        monitor_params
):
    """
    Initializes the recovery of events from HiDRA.

    Returns an iterator over the events that should be processed by the
    worker that calls the function. This function must be called on
    each worker node after the :obj:`initialize_event_source` function
    has been called on the master node.

    Args:

        source (str): ip address or hostname of the machine where HiDRA
            is running.

        node_rank (int): rank of the node where the function is called.

        mpi_pool_size (int): size of the node pool that includes the
            node where the function is called.

        monitor_params (MonitorParams): a
            :obj:`~onda.utils.parameters.MonitorParams` object
            containing the monitor parameters from the configuration
            file.

    Yields:

        Dict: A dictionary containing the metadata and data of an event
        (1 event = 1file).
    """
    hidra_info = _get_hidra_info(
        source=source,
        mpi_pool_size=mpi_pool_size,
        monitor_params=monitor_params
    )

    print(
        "Worker {0} listening at port {1}".format(
            node_rank,
            hidra_info.targets[node_rank][1]
        )
    )
    sys.stdout.flush()

    hidra_info.query.start(hidra_info.targets[node_rank][1])
    while True:
        recovered_metadata, recovered_data = hidra_info.query.get()

        event = {'data': recovered_data, 'metadata': recovered_metadata}
        event['full_path'] = os.path.join(
            hidra_info.data_base_path,
            recovered_metadata['relative_path'],
            recovered_metadata['filename']
        )

        # File creation date is used as a first approximation of the
        # timestamp when the timestamp is not available.
        event['file_creation_time'] = (recovered_metadata['file_create_time'])

        yield event
