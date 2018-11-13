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

Functions and classes used to retrieve data events from Karabo.
"""
from __future__ import absolute_import, division, print_function

import sys

import numpy
from future.utils import raise_from

from onda.data_retrieval_layer.event_sources.karabo_api import client
from onda.utils import exceptions


############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################


def initialize_event_source(
        source,
        mpi_pool_size,
        monitor_params
):
    """
    Initializes the Karabo event source.

    This function must be called on the master node before the
    :obj:`event_generator` function is called on the worker nodes.

    Args:

        source (str): a string containing the IP address (or the
            hostname) and the port of the machine where the Karabo
            Bridge is running, separated by a colon (i.e:
            'ip:port').

        mpi_pool_size (int): size of the node pool that includes the
            node where the function is called.

        monitor_params (MonitorParams): a
            :obj:`~onda.utils.parameters.MonitorParams` object
            containing the monitor parameters from the configuration
            file.
    """
    del source
    del mpi_pool_size
    del monitor_params
    # Karabo needs no initialization, so the function does nothing.


def event_generator(
        source,
        node_rank,
        mpi_pool_size,
        monitor_params
):
    """
    Initializes the recovery of events from Karabo.

    Returns an iterator over the events that should be processed by the
    worker that calls the function. This function must be called on
    each worker node after the :obj:`initialize_event_source` function
    has been called on the master node.

    Args:

        source (str): a string containing the IP address (or the
            hostname) and the port of the machine where the Karabo
            Bridge is running, separated by a colon (i.e:
            'ip:port').

        node_rank (int): rank of the node where the function is called.

        mpi_pool_size (int): size of the node pool that includes the
            node where the function is called.

        monitor_params (MonitorParams): a
            :obj:`~onda.utils.parameters.MonitorParams` object
            containing the monitor parameters from the configuration
            file.

    Yields:

        Dict: A dictionary containing the metadata and data of an event
        (at XFEL: 1 event = 1 train).
    """
    del mpi_pool_size
    del monitor_params
    source_parts = source.split(':')
    try:
        hostname = source_parts[0]
        port = source_parts[1]
    except IndexError:
        raise_from(
            exc=exceptions.InvalidSource(
                "Invalid source format: {}.".format(source)
            ),
            cause=None
        )

    print(
        "Worker {} listening to {} at port {}".format(
            node_rank,
            hostname,
            port
        )
    )
    sys.stdout.flush()

    # Connects to the Karabo Bridge using the Karabo API.
    krb_client = client.Client('tcp://{}'.format(source))
    while True:
        event = {}
        event['data'], event['metadata'] = krb_client.next()

        event['timestamp'] = numpy.float64(
            str(
                event['metadata']['SPB_DET_AGIPD1M-1/CAL/APPEND_CORRECTED']
                ['timestamp.sec']
            ) + '.' + str(
                event['metadata']['SPB_DET_AGIPD1M-1/CAL/APPEND_CORRECTED']
                ['timestamp.frac']
            )
        )

        yield event


def open_event(event):
    """
    Opens an event retrieved from Karabo.

    Makes the content of a retrieved Karabo event available in the
    'data' entry of the event dictionary.

    Args:

        event (Dict): a dictionary with the event data.
    """
    del event
    # Karabo events do not need to be opened. this function does
    # nothing.


def close_event(event):
    """
    Closes an event retrieved from Karabo.

    Args:

        event (Dict): a dictionary with the event data.
    """
    del event
    # Karabo events do not need to be closed. This function does
    # nothing.
