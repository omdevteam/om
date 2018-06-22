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
Karabo event handling.

This module implements event handling functions used to process data
received from Karabo.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import sys

from future.utils import raise_from

from onda.data_retrieval_layer.components.event_sources import karabo_api
from onda.utils import exceptions


def initialize_event_source(source,  # pylint: disable=W0613
                            node_rank,  # pylint: disable=W0613
                            mpi_pool_size,  # pylint: disable=W0613
                            monitor_params):  # pylint: disable=W0613
    """
    Initialize the event recovery from Karabo.

    Initialize the psana event source. This function must be called on
    the master node before the 'event_generator' function is
    called on the worker nodes.

    Args:

        source (str): the hostname (or IP) of the machine where the
            Karabo Bridge software is running, and the port on which it
            is running (separated by a semicolon).

        node_rank (int): rank of the node where the function is called.

        mpi_pool_size (int): size of the node pool that includes the
            node where the function is called.

        monitor_params (:obj:`onda.utils.parameters.MonitorParams`):
            a MonitorParams object containing the monitor parameters
            from the configuration file.

     Yields:

        Dict: A dictionary containing the data and metadata of a
        Karabo event.
    """
    # Karabo needs no initialization, so do nothing.
    pass


def event_generator(source,
                    node_rank,
                    mpi_pool_size,  # pylint: disable=W0613
                    monitor_params):  # pylint: disable=W0613
    """
    Initialize HiDRA event recovery.

    Initialize the recovery of events from Karabo. Return an iterator
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

        monitor_params (:obj:`onda.utils.parameters.MonitorParams`):
            a MonitorParams object containing the monitor parameters
            from the configuration file.

     Yields:

        Dict: A dictionary containing the data and metadata of an
        event.
    """
    # Extract from the source string the IP address and the port to
    # which OnDA should connect.
    source_parts = source.split(':')

    try:
        hostname = source_parts[0]
        port = source_parts[1]
    except IndexError:
        raise_from(
            exc=exceptions.InvalidSource(
                "Invalid source format: {}.".format(source)
            ),
            source=None
        )

    # Notify the user that the worker node is starting.
    print(
        "Worker {} listening to {} at port {}".format(
            node_rank,
            hostname,
            port
        )
    )
    sys.stdout.flush()

    # Connect to the Karabo Bridge using the Karabo API.
    krb_client = karabo_api.Client('tcp://{}'.format(source))

    while True:

        # Create the event dictionary, recover an event from the Karabo
        # Bridge and store the recovered data in the dictionary.
        event = {}
        event['data'], event['metadata'] = krb_client.next()

        yield event


class EventFilter(object):
    """
    Null filter.

    Do not filter events.
    """

    def __init__(self,
                 monitor_params):   # pylint: disable=W0613
        """
        Initialize the EventFilter class.

        Args:

            monitor_params (:obj:`onda.utils.parameters.MonitorParams`):
                a MonitorParams object containing the monitor
                parameters from the configuration file.
        """
        # Do nothing.
        pass

    def should_reject(self,
                      event):     # pylint: disable=W0613
        """
        Decide on event rejection.

        Decide if the event should be rejected.

        Args:

            event (Dict): a dictionary with the event data.

        Returns:

            bool: True if the event should be rejected. False if the
            event should be processed.
        """
        # Do nothing.
        pass


def open_event(event):  # pylint: disable=W0613
    """
    Open event.

    Open the event and make the content of the event available in the
    'data' entry of the event dictionary.

    Args:

        event (Dict): a dictionary with the event data.
    """
    # Karabo events do not need to be opened. Do nothing.
    pass


def close_event(event):  # pylint: disable=W0613
    """
    Close event.

    Close the event.

    Args:

        event (Dict): a dictionary with the event data.
    """
    # Karabo events do not need to be closed. Do nothing.
    pass
