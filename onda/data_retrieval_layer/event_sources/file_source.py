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
Retrieval of events from files.

Functions and classes used to retrieve data events from files.
"""
from __future__ import absolute_import, division, print_function

import os.path

import numpy
from future.utils import raise_from


############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################


def initialize_event_source(source, mpi_pool_size, monitor_params):
    """
    Initializes the file event source.

    This function must be called on the master node before the
    :obj:`event_generator` function is called on the worker nodes.

    Args:

        source (str): full path to a file containing the list of
            files to process (one per line, with their full path).

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
    # There is no event source to initialize when recovering events
    # from files, so does nothing.


def event_generator(source, node_rank, mpi_pool_size, monitor_params):
    """
    Initializes the recovery of events from files.

    Returns an iterator over the events that should be processed by the
    worker that calls the function. This function must be called on
    each worker node after the :obj:`initialize_event_source` function
    has been called on the master node.

    Args:

        source (str): the full path to a file containing the list of
            files to be processed (their full path).

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
    del monitor_params
    try:
        with open(source, "r") as fhandle:
            filelist = fhandle.readlines()
    except (IOError, OSError):
        raise_from(
            exc=RuntimeError(
                "Error reading the {} source file.".format(source)
            ),
            cause=None,
        )

    # Computes how many files the current worker node should
    # process. Splits the files as equally as possible amongst the
    # workers with the last worker getting a smaller number of
    # files if the number of files to be processed cannot be
    # exactly divided by the number of workers.
    num_files_curr_node = int(
        numpy.ceil(len(filelist) / float(mpi_pool_size - 1))
    )

    files_curr_node = filelist[
        ((node_rank - 1) * num_files_curr_node) : (
            node_rank * num_files_curr_node
        )
    ]

    for entry in files_curr_node:
        stripped_entry = entry.strip()
        event = {"full_path": stripped_entry}

        # File modification time is used as a first approximation of
        # the timestamp when the timestamp is not available.
        event["timestamp"] = os.stat(stripped_entry).st_mtime

        yield event
