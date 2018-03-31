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
Functions and classes to recover and process data from HiDRA.

Exports:

    Functions:

        initialize_event_source: connect to the event source and
            configure it.

        event_generator: event recovery from HiDRA.

    Classes:

        EventFilter (class): filter and reject events.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import collections
import os.path
import socket
import sys
from builtins import str  # pylint: disable=W0622

from future.utils import raise_from

from onda.data_recovery_layer import hidra_api
from onda.utils import dynamic_import, exceptions


def _get_hidra_info(source,
                    mpi_pool_size,
                    monitor_params):
    # Compute the HiDRA connection parameters.

    # Read the requested transfer type from the configuration file.
    # If it is not specified there, import the suggested transfer type
    # from the detector layer and use that. If the transfer type is
    # unknown, raise an exception.
    transfer_type = monitor_params.get_param(
        section='HidraDataRecoveryLayer',
        parameter='transfer_type',
        type_=str,
    )
    if transfer_type is None:
        detector_layer = dynamic_import.import_detector_layer(
            monitor_params
        )
        transfer_type = detector_layer.get_hidra_transfer_type()

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
        raise RuntimeError(
            "Unrecognized transfer type for HiDRA data recoverylayer."
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
        detector_layer = dynamic_import.import_detector_layer(
            monitor_params
        )
        hidra_selection_string = detector_layer.get_file_extensions()

    # Create the target list for HiDRA. Add an empty target at the
    # beginning to cover the master node. In this way, the index of the
    # a node in the target list will match its rank. With the full
    # list, create the HiDRA query object, as requested by the API.
    targets = [['', '', 1, '']]
    for rank in range(1, mpi_pool_size):
        target_entry = [
            socket.gethostname(),
            str(base_port + rank),
            str(1),
            b''
            # hidra_selection_string
        ]
        targets.append(target_entry)

    query = hidra_api.Transfer(
        connection_type=query_text,
        signal_host=source,
        use_log=False
    )

    HiDRAInfo = collections.namedtuple(  # pylint: disable=C0103
        typename='HiDRAInfo',
        field_names=['query', 'targets', 'data_base_path']
    )
    return HiDRAInfo(query, targets, data_base_path)


def initialize_event_source(source,
                            node_rank,  # pylint: disable=W0613
                            mpi_pool_size,
                            monitor_params):
    """
    Initialize event generator.

    Connect to the event generator and configure it. Connect to HiDRA
    and request the correct connection_type. Provide HiDRA with the
    information about all the worker nodes that will connect to it.

    Args:

        source (str): the IP or hostname of the machine where hidra is
            running.

        node_rank (int): rank of the node where the function is called

        mpi_pool_size (int): size of the node pool that includes the
            node where the function is called.

        monitor_params (MonitorParams): a MonitorParams object
            containing the monitor parameters from the
            configuration file.
    """
    print("Announcing OnDA to sender.")
    sys.stdout.flush()

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

    Initialize the connection with HiDRA. When called on the master
    node, deal with the initialization of the connection and with
    authentication. When called on a worker node, return an iterator
    which will recover an event from HiDRA at each step (This function
    is a python generator). In order for the retrieval to work
    correctly, this function must be called initially on the master
    node, and subsequently on each worker node that receovers
    events from HiDRA.

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
        # Recover the data from HiDRA. Create the event dictionary
        # and store the recovered data there. Add two custom
        # entries that are needed by the data extraction functions:
        # the full path to the file, and the file creation date (a
        # first approximation of the timestamp). Then yield the
        # event.

        print('Asking')
        sys.stdout.flush()

        recovered_metadata, recovered_data = hidra_info.query.get()

        print('Got it')
        sys.stdout.flush()

        event = {
            'data': recovered_data,
        }

        event['full_path'] = os.path.join(
            hidra_info.data_base_path,
            recovered_metadata['relative_path'],
            recovered_metadata['filename']
        )

        event['file_creation_time'] = (
            recovered_metadata['file_create_time']
        )

        yield event


class EventFilter(object):
    """
    Filter events.

    Reject files whose extensions does not match the one of the
    extensions allowed for the detector being used.
    """

    def __init__(self,
                 monitor_params):
        """
        Initialize the EventFilter class.

        Args:

        monitor_params (MonitorParams): a MonitorParams object
            containing the monitor parameters from the
            configuration file.
        """
        # Import the function that recovers the list of allowed file
        # extensions from the detector layer, call it and store
        # the list of file extensions in an attribute.
        get_file_extensions = dynamic_import.import_func_from_detector_layer(
            'get_file_extensions',
            monitor_params
        )
        self._file_extensions = get_file_extensions()

    def should_reject(self,
                      event):
        """
        Decide on event rejection.

        Decide if the event should be rejected based on the list of
        extensions allowed for the detector in use.

        Args:

            event (Dict): a dictionary with the event data.

        Returns:

            bool: True if the event should be rejected. False if the
            event should be processed.
        """
        if os.path.basename(
                event['full_path'].endswith(
                    self._file_extensions
                )
        ):
            return False
        else:
            return True
