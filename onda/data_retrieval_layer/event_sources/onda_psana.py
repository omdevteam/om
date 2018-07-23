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
Retrieval of events from psana.

This module contains the implementation of event handling functions
used retrieve data from psana.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import time
from builtins import str  # pylint: disable=W0622

import numpy
from future.utils import iteritems, raise_from

from onda.utils import dynamic_import, exceptions

try:
    import psana  # pylint: disable=E0401
except ImportError:
    raise_from(
        exc=exceptions.MissingDependency(
            "The onda_psana module could not be loaded. The following "
            "dependency does not appear to be available on the system: psana."
        ),
        source=None
    )


def _psana_offline_event_generator(psana_source,
                                   node_rank,
                                   mpi_pool_size):

    # Compute how many events the current worker node should process
    # Split the events as equally as possible amongst the workers with
    # the last worker getting a smaller number of events if the number
    # of files to be processed cannot be exactly divided by the number
    # of workers.
    for run in psana_source.runs():
        times = run.times()

        num_events_curr_node = int(
            numpy.ceil(
                len(times) / float(mpi_pool_size - 1)
            )
        )

        events_curr_node = times[
            (node_rank - 1) * num_events_curr_node:
            node_rank * num_events_curr_node
        ]

        for evt in events_curr_node:
            yield run.event(evt)


def initialize_event_source(source,  # pylint: disable=W0613
                            node_rank,  # pylint: disable=W0613
                            mpi_pool_size,  # pylint: disable=W0613
                            monitor_params):  # pylint: disable=W0613
    """
    Initialize the event source.

    This function must be called on the master node before the
    :obj:`event_generator` function is called on the worker nodes..

    Args:

        source (str): a psana experiment string.

        node_rank (int): rank of the node where the function is called.

        mpi_pool_size (int): size of the node pool that includes the
            node where the function is called.

        monitor_params (:obj:`~onda.utils.parameters.MonitorParams`):
            a MonitorParams object containing the monitor parameters
            from the configuration file.

     Yields:

        dict: A dictionary containing the data and metadata of a
        psana event.
    """
    # Psana needs no initialization, so do nothing.
    pass


def event_generator(source,
                    node_rank,
                    mpi_pool_size,  # pylint: disable=W0613
                    monitor_params):
    """
    Return an iterator over the events that should be processed by the
    worker that calls the function. This function must be called on
    each worker node after the :obj:`initialize_event_source` function
    has been called on the master node.

    Args:

        source (str): the IP or hostname of the machine where HiDRA is
            running.

        node_rank (int): rank of the node where the function is called.

        mpi_pool_size (int): size of the node pool that includes the
            node where the function is called.

        monitor_params (MonitorParams): a
            :obj:`~onda.utils.parameters.MonitorParams` object
            containing the monitor parameters from the configuration
            file.

    Yields:

        Dict: A dictionary containing the data and metadata of an
        event.
    """
    # Detect if data is being read from an online or offline source.
    if 'shmem' in source:
        offline = False
    else:
        offline = True

    if offline and not source[-4:] == ':idx':
        source += ':idx'

    # If the psana calibration directory is provided in the
    # configuration file, add it as an option to psana.
    psana_calib_dir = monitor_params.get_param(
        section='PsanaDataRecoveryLayer',
        parameter='psana_calibration_directory',
        type_=str
    )
    if psana_calib_dir:
        psana.setOption(
            'psana.calib-dir'.encode('ascii'),
            psana_calib_dir.encode('ascii')
        )
    else:
        print('Calibration directory not provided or not found.')

    psana_source = psana.DataSource(source.encode('ascii'))
    psana_interface_funcs = (
        dynamic_import.get_psana_det_interface_funcs(monitor_params)
    )

    # Call all the required psana detector interface initialization
    # functions and store the returned handlers in a dictionary.
    psana_det_interface = {}
    for f_name, func in iteritems(psana_interface_funcs):
        psana_det_interface[
            f_name.split("_init")[0]
        ] = func(monitor_params)

    if offline:
        psana_events = _psana_offline_event_generator(
            psana_source=psana_source,
            node_rank=node_rank,
            mpi_pool_size=mpi_pool_size
        )
    else:
        psana_events = psana_source.events()

    for psana_event in psana_events:
        event = {
            'psana_det_interface': psana_det_interface,
            'psana_event': psana_event
        }

        yield event


class EventFilter(object):
    """
    See __init__ for documentation.
    """

    def __init__(self,
                 monitor_params):
        """
        Filter events based on their 'age'.

        Reject files whose 'age' (the time between the data collection
        and the moment OnDA receives the data) is higher than a
        predefined threshold.

        Args:

            monitor_params (MonitorParams): a
                :obj:`~onda.utils.parameters.MonitorParams` object
                containing the monitor parameters from the
                configuration file.
        """
        # Read the rejection threshold from the configuration file
        # and store it in an attribute.
        rejection_threshold = monitor_params.get_param(
            section='PsanaDataRecoveryLayer',
            parameter='event_rejection_threshold',
            type_=float
        )
        if rejection_threshold:
            self._event_rejection_threshold = rejection_threshold
        else:
            self._event_rejection_threshold = 10000000000

    def should_reject(self,
                      event):
        """
        Decide if the event should be rejected.

        Args:

            event (Dict): a dictionary with the event data.

        Returns:

            bool: True if the event should be rejected. False if the
            event should be processed.
        """
        # Recover the timestamp from the psana event
        timestamp_epoch_format = event['psana_event'].get(
            psana.EventId  # pylint: disable=E1101
        ).time()

        event_timestamp = numpy.float64(  # pylint: disable=E1101
            str(timestamp_epoch_format[0]) + '.' +
            str(timestamp_epoch_format[1])
        )

        time_now = numpy.float64(time.time())  # pylint: disable=E1101
        if (time_now - event_timestamp) > self._event_rejection_threshold:

            # Store the timestamp in the event dictionary so it does
            # not have to be extracted again if the timestamp is one
            # of the requested data sources.
            return True
        else:
            event['timestamp'] = event_timestamp
            return False


def open_event(event):  # pylint: disable=W0613
    """
    Open the event.

    Make the content of the event available in the 'data' entry of the
    event dictionary.

    Args:

        event (Dict): a dictionary with the event data.
    """
    # Psana events do not need to be opened. Do nothing.
    pass


def close_event(event):  # pylint: disable=W0613
    """
    Close the event.

    Args:

        event (Dict): a dictionary with the event data.
    """
    # Events do not need to be closed. Do nothing.
    pass


def get_num_frames_in_event(event):  # pylint: disable=W0613
    """
    Retrieve the number of frames in the event.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        int: the number of frames in an event.
    """
    # Psana events usually contain just one frame.
    return 1
