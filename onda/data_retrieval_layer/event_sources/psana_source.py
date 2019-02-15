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

Functions and classes used to retrieve data events from psana.
"""
from __future__ import absolute_import, division, print_function

import numpy
from future.utils import iteritems, raise_from

from onda.utils import dynamic_import, exceptions

try:
    import psana  # pylint: disable=import-error
except ImportError:
    raise_from(
        exc=exceptions.MissingDependency(
            "The psana module could not be loaded. The following "
            "dependency does not appear to be available on the "
            "system: psana."
        ),
        cause=None,
    )


############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################


def _psana_offline_event_generator(psana_source, node_rank, mpi_pool_size):

    # Computes how many events the current worker node should process
    # Split the events as equally as possible amongst the workers with
    # the last worker getting a smaller number of events if the number
    # of files to be processed cannot be exactly divided by the number
    # of workers.
    for run in psana_source.runs():
        times = run.times()

        num_events_curr_node = int(
            numpy.ceil(len(times) / float(mpi_pool_size - 1))
        )

        events_curr_node = times[
            (node_rank - 1)
            * num_events_curr_node : node_rank
            * num_events_curr_node
        ]

        for evt in events_curr_node:
            yield run.event(evt)


def initialize_event_source(source, mpi_pool_size, monitor_params):
    """
    Initializes the psana event source.

    This function must be called on the master node before the
    :obj:`event_generator` function is called on the worker nodes.

    Args:

        source (str): a psana experiment string.

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
    # Psana needs no initialization, so thid function does nothing.


def event_generator(source, node_rank, mpi_pool_size, monitor_params):
    """
    Initializes the recovery of events from psana.

    Returns an iterator over the events that should be processed by the
    worker that calls the function. This function must be called on
    each worker node after the :obj:`initialize_event_source` function
    has been called on the master node.

    Args:

        source (str): a psana experiment string.

        node_rank (int): rank of the node where the function is called.

        mpi_pool_size (int): size of the node pool that includes the
            node where the function is called.

        monitor_params (MonitorParams): a
            :obj:`~onda.utils.parameters.MonitorParams` object
            containing the monitor parameters from the configuration
            file.

    Yields:

        Dict: A dictionary containing the metadata and data of an event
    """
    # Detects if data is being read from an online or offline source.
    if "shmem" in source:
        offline = False
    else:
        offline = True
    if offline and not source[-4:] == ":idx":
        source += ":idx"

    # If the psana calibration directory is provided in the
    # configuration file, adds it as an option to psana.
    psana_calib_dir = monitor_params.get_param(
        section="DataRetrievalLayer",
        parameter="psana_calibration_directory",
        type_=str,
    )
    if psana_calib_dir:
        psana.setOption(
            "psana.calib-dir".encode("ascii"), psana_calib_dir.encode("ascii")
        )
    else:
        print("Calibration directory not provided or not found.")

    psana_source = psana.DataSource(source)
    psana_interface_funcs = dynamic_import.get_psana_det_interface_funcs(
        monitor_params
    )

    # Calls all the required psana detector interface initialization
    # functions and stores the returned handlers in a dictionary.
    psana_det_interface = {}
    for f_name, func in iteritems(psana_interface_funcs):
        psana_det_interface[f_name.split("_init")[0]] = func(monitor_params)

    if offline:
        psana_events = _psana_offline_event_generator(
            psana_source=psana_source,
            node_rank=node_rank,
            mpi_pool_size=mpi_pool_size,
        )
    else:
        psana_events = psana_source.events()

    for psana_event in psana_events:
        event = {
            "psana_detector_interface": psana_det_interface,
            "psana_event": psana_event,
        }

        # Recovers the timestamp from the psana event
        # (in epoch format) and stores it in the event dictionary.
        timestamp_epoch_format = psana_event.get(
            psana.EventId  # pylint: disable=no-member
        ).time()

        event["timestamp"] = numpy.float64(
            str(timestamp_epoch_format[0])
            + "."
            + str(timestamp_epoch_format[1])
        )

        yield event


def open_event(event):
    """
    Opens an event retrieved from psana.

    Makes the content of a retrieved psana event available in the
    'data' entry of the event dictionary.

    Args:

        event (Dict): a dictionary with the event data.
    """
    # Psana events do not need to be opened. This function does
    # nothing.
    del event


def close_event(event):
    """
    Closes an event retrieved from psana.

    Args:

        event (Dict): a dictionary with the event data.
    """
    # Psana events do not need to be closed. This function does
    # nothing.
    del event


def get_num_frames_in_event(event):
    """
    Number of frames in an psana event.

    Returns the number of frames in an event retrieved from psana.

    Args:

        event (Dict): a dictionary with the event data.

    Retuns:

        int: the number of frames in the event.
    """
    del event

    # Psana events usually contain just one frame.
    return 1
