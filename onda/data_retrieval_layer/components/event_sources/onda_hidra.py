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
HiDRA event handling.

This module implements event handling functions used to process data
received from HiDRA.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os.path
import socket
import sys
from builtins import str  # pylint: disable=W0622

from future.utils import raise_from

from onda.data_retrieval_layer.components.event_sources import hidra_api
from onda.utils import dynamic_import, exceptions, named_tuples


def _get_hidra_info(source,
                    mpi_pool_size,
                    monitor_params):
    # Compute the HiDRA connection parameters.

    # Read the requested transfer type from the configuration file.
    transfer_type = monitor_params.get_param(
        section='HidraDataRecoveryLayer',
        parameter='transfer_type',
        type_=str,
    )
    # If it is not specified there, import the suggested transfer type
    # from the deta extraction layer and use that.
    if transfer_type is None:
        transfer_type = dynamic_import.get_hidra_transfer_type(
            monitor_params
        )

    if transfer_type == 'data':

        # If the transfer type is data-based, request the latest event
        # with full data, and set the data base path to an empty path,
        # because HiDRA will provide the data directly, and there will
        # be no need to look fot the file.
        query_text = 'QUERY_NEXT'
        data_base_path = ''
    elif transfer_type == 'metadata':

        # If the transfer type is metadata-based, request the latest
        # event with metadata only and read the data base path from the
        # configuration file: HiDRA will only provide the path to the
        # file relative to the base data path.
        query_text = 'QUERY_METADATA'
        data_base_path = os.path.join(
            monitor_params.getparam(
                section='HidraDataRecoveryLayer',
                parameter='data_base_path',
                type_=str,
                required=True
            )
        )
    else:

        # If the transfer type is unknown, raise an exception.
        raise RuntimeError(
            "Unrecognized HiDRA transfer type."
        )

    # Read the base port for communication with HiDRA from the
    # configuration file.
    base_port = monitor_params.get_param(
        section='HidraDataRecoveryLayer',
        parameter='base_port',
        type_=int,
        required=True
    )

    # Search the configuration file for a HiDRA selection string.
    # If the selection string is not found, use the file extensions
    # from the detector layer as selection string.
    hidra_selection_string = monitor_params.get_param(
        section='HidraDataRecoveryLayer',
        parameter='hidra_selection_string',
        type_=str
    )
    if hidra_selection_string is None:
        hidra_selection_string = dynamic_import.get_file_extensions(
            monitor_params
        )

    # Create the target list for HiDRA.

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
            b''
            # hidra_selection_string
        ]
        targets.append(target_entry)

    # Prepare the transfer request to be sent to HiDRA
    query = hidra_api.Transfer(
        connection_type=query_text,
        signal_host=source,
        use_log=False
    )

    # Return a HiDRAInfo tuple with all the information.
    return named_tuples.HidraInfo(
        query=query,
        targets=targets,
        data_base_path=data_base_path
    )


def initialize_event_source(source,
                            node_rank,  # pylint: disable=W0613
                            mpi_pool_size,
                            monitor_params):
    """
    Initialize the event recovery from HiDRA.

    Initialize the HiDRA event source. This function must be called on
    the master node before the 'event_generator' function is
    called on the worker nodes.

    Args:

        source (str): the IP or hostname of the machine where HiDRA is
            running.

        node_rank (int): rank of the node where the function is called.

        mpi_pool_size (int): size of the node pool that includes the
            node where the function is called.

        monitor_params (:obj:`onda.utils.parameters.MonitorParams`):
            a MonitorParams object containing the monitor parameters
            from the configuration file.

     Yields:

        Dict: A dictionary containing the data and metadata of an
        event.
    """
    print("Announcing OnDA to HiDRA.")
    sys.stdout.flush()

    # Create the HidraInfo object needed to initialize Hidra.
    hidra_info = _get_hidra_info(
        source=source,
        mpi_pool_size=mpi_pool_size,
        monitor_params=monitor_params
    )

    # Initiate the connection to HiDRA (as dictated by the API) and
    # raise an exception if the connection fails.
    try:
        hidra_info.query.initiate(hidra_info.targets[1:])
    except hidra_api.transfer.CommunicationFailed as exc:
        raise_from(
            exc=exceptions.HidraAPIError(
                "Failed to contact HiDRA: {0}".format(exc)
            ),
            cause=None
        )


def event_generator(source,
                    node_rank,
                    mpi_pool_size,
                    monitor_params):
    """
    Initialize HiDRA event recovery.

    Initialize the recovery of events from files. Return an iterator
    over the events that should be processed by the worker that calls
    the function. This function must be called on each worker node
    after the 'initialize_event_source' function is called on the
    master node.

    Args:

        source (str): the IP or hostname of the machine where hidra is
            running.

        node_rank (int): rank of the node where the function is called

        mpi_pool_size (int): size of the node pool that includes the
            node where the function is called.

        monitor_params (MonitorParams): a MonitorParams object
            containing the monitor parameters from the
            configuration file.

     Yields:

        Dict: A dictionary containing the data and the metadata of an
        event recovered from HiDRA (usually corresponding to a file).
    """
    # Create the HidraInfo object needed to event recovery form Hidra.
    hidra_info = _get_hidra_info(
        source=source,
        mpi_pool_size=mpi_pool_size,
        monitor_params=monitor_params
    )

    # Notify the user that the worker node is starting.
    print(
        "Worker {0} listening at port {1}".format(
            node_rank,
            hidra_info.targets[node_rank][1]
        )
    )
    sys.stdout.flush()

    # Connect to HiDRA.
    hidra_info.query.start(hidra_info.targets[node_rank][1])
    while True:
        # Recover the data from HiDRA. Add two custom entries that are
        # needed by the data extraction functions.
        recovered_metadata, recovered_data = hidra_info.query.get()

        # Create the event dictionary and store the recovered data
        # there.
        event = {
            'data': recovered_data,
        }

        # Also store the full path to the file,
        event['full_path'] = os.path.join(
            hidra_info.data_base_path,
            recovered_metadata['relative_path'],
            recovered_metadata['filename']
        )

        # Store additionally the file creation date (a first
        # approximation of the timestamp).
        event['file_creation_time'] = (
            recovered_metadata['file_create_time']
        )

        yield event


class EventFilter(object):
    """
    Filter events based on file extension.

    Reject files whose extensions are not amongst the extensions
    allowed for the detector(s) being used.
    """

    def __init__(self,
                 monitor_params):
        """
        Initialize the EventFilter class.

        Args:

            monitor_params (:obj:`onda.utils.parameters.MonitorParams`):
                a MonitorParams object containing the monitor
                parameters from the configuration file.
        """
        # Recover the list of allowed file extensions and store it in
        # an attribute.
        self._file_extensions = dynamic_import.get_file_extensions(
            monitor_params
        )

    def should_reject(self,
                      event):
        """
        Decide on event rejection.

        Decide if the event should be rejected.

        Args:

            event (Dict): a dictionary with the event data.

        Returns:

            bool: True if the event should be rejected. False if the
            event should be processed.
        """
        # Check if the filename ends with one of the allowed file
        # extensions. If it doesn't, reject the file.
        if os.path.basename(event).endswith(self._file_extensions):
            return False
        return True
