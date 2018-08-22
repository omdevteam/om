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
Retrieval of events from files.

This module contains the implementation of event handling functions
used to retrieve data stored in files.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os.path

import numpy
from future.utils import raise_from

from onda.utils import dynamic_import


def initialize_event_source(source,  # pylint: disable=W0613
                            node_rank,  # pylint: disable=W0613
                            mpi_pool_size,  # pylint: disable=W0613
                            monitor_params):  # pylint: disable=W0613
    """
    Initialize the event source.

    This function must be called on the master node before the
    :obj:`event_generator` function is called on the worker nodes.

    Args:

        source (str): full path to a file containing the list of
            files to process (one per line, with their full path).

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
    # There is no event source to initialize when recovering events
    # from files, so do nothing.
    pass


def event_generator(source,
                    node_rank,
                    mpi_pool_size,
                    monitor_params):  # pylint: disable=W0613
    """
    Initialize the event recovery from files.

    Return an iterator over the events that should be processed by the
    worker that calls the function. This function must be called on
    each worker node after the :obj:`initialize_event_source` function
    has been called on the master node.

    Args:

        source (str): the full path to a file containing the list of
            files to be processed (their full path).

        node_role (str): a string describing the role of the node
            where the function is called ('worker' or 'master').

        node_rank (int): rank of the node where the function is called.

        mpi_pool_size (int): size of the node pool that includes the
            node where the function is called.

        monitor_params (MonitorParams): a
            :obj:`~onda.utils.parameters.MonitorParams` object
            containing the monitor parameters from the configuration
            file.

    Yields:

        Dict: A dictionary containing the metadata (full path, etc. )
        of a file from thelist.
    """
    try:
        with open(source, 'r') as fhandle:
            filelist = fhandle.readlines()
    except (IOError, OSError):
        raise_from(
            exc=RuntimeError(
                "Error reading the {} source file.".format(
                    source
                )
            ),
            source=None
        )

    # Compute how many files the current worker node should
    # process. Split the files as equally as possible amongst the
    # workers with the last worker getting a smaller number of
    # files if the number of files to be processed cannot be
    # exactly divided by the number of workers.
    num_files_curr_node = int(
        numpy.ceil(
            len(filelist) / float(mpi_pool_size - 1)
        )
    )

    files_curr_node = filelist[
        ((node_rank - 1) * num_files_curr_node):
        (node_rank * num_files_curr_node)
    ]

    for entry in files_curr_node:
        stripped_entry = entry.strip()
        event = {'full_path': stripped_entry}

        # File creation date is used as a first approximation of the
        # timestamp when the timestamp is not available.
        event['file_creation_time'] = os.stat(stripped_entry).st_mtime

        yield event


class EventFilter(object):
    """
    See __init__ for documentation.
    """

    def __init__(self,
                 monitor_params):
        """
        Filter events based on file extensions.

        Reject files whose extensions are not allowed for the
        detector(s) being used.

        Args:

            monitor_params (MonitorParams): a
                :obj:`~onda.utils.parameters.MonitorParams` object
                containing the monitor parameters from the
                configuration file.
        """
        self._file_extensions = dynamic_import.get_file_extensions(
            monitor_params
        )

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
        if os.path.basename(
                event['full_path']
        ).endswith(self._file_extensions):
            return False
        else:
            return True
