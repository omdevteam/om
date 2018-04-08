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
Functions and classes to recover and process data from Karabo

Exports:

    Functions:

        initialize_event_source: connect to the event source and
            configure it. For Karabo, no initialization is
            needed, so do nothing.

        event_generator: connect to Karabo recover events.

    Classes:

        EventFilter (class): filter and reject events. No rejection
            policy is currently implemented for Karabo, so do
            nothing.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import sys

from onda.data_recovery_layer.karabo_api import client


def initialize_event_source(source,  # pylint: disable=W0613
                            node_rank,  # pylint: disable=W0613
                            mpi_pool_size,  # pylint: disable=W0613
                            monitor_params):  # pylint: disable=W0613
    """
    Initialize event generator.

    Connect to the event generator and configure it. Karabo does not
    need to be configured, so do nothing.

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
    pass


def event_generator(source,
                    node_rank,
                    mpi_pool_size,  # pylint: disable=W0613
                    monitor_params):  # pylint: disable=W0613
    """
    Initialize Karabo event recovery.

    Initialize the connection with Karabo. Return an iterator which
    will recover an event from Karabo at each step (This function
    is a python generator).

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
        event recovered from Karabo (usually corresponding to a train).
    """
    hostname = source.split(':')[0]
    port = source.split(':')[1]
    print(
        "Worker {} listening to {} at port {}".format(
            node_rank,
            hostname,
            port
        )
    )
    sys.stdout.flush()

    krb_client = client.Client('tcp://{}'.format(source))

    while True:
        # Recover the data from Karabo. Create the event dictionary
        # and store the recovered data there. Then yield the
        # event.

        event = {
            'data': krb_client.next(),
        }

        yield event


class EventFilter(object):
    """
    Filter events.

    Filter events according to certain criteria. Currently no filtering
    capabilities are implemented for Karabo, so do nothing
    """

    def __init__(self,
                 monitor_params):   # pylint: disable=W0613
        """
        Initialize the EventFilter class.

        Args:

        monitor_params (MonitorParams): a MonitorParams object
            containing the monitor parameters from the
            configuration file.
        """
        pass

    def should_reject(self,
                      event):     # pylint: disable=W0613
        """
        Decide on event rejection.

        Decide if the event should be rejected. Currently no rejection
        is implemented, so do nothing.

        Args:

            event (Dict): a dictionary with the event data.

        Returns:

            bool: True if the event should be rejected. False if the
            event should be processed.
        """
        pass
