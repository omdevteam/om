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
File event handling.

This module implements event handling functions used to process data
stored in files.
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
    Initialize the event recovery from files.

    Initialize the event recovery from files. This function must be
    called on the master node before the 'event_generator' function is
    called on the worker nodes.

    Args:

        source (str): full path to a file containing the list of
            files to process (one per line, with their full path).

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
    # There is no event source to initialize when recovering events
    # from files, so do nothing.
    pass


def event_generator(source,
                    node_rank,
                    mpi_pool_size,
                    monitor_params):  # pylint: disable=W0613
    """
    Initialize the event recovery from files.

    Initialize the recovery of events from files. Return an iterator
    over the events that should be processed by the worker that calls
    the function. This function must be called on each worker node
    after the 'initialize_event_source' function is called on the
    master node.

    Args:

        source (str): the full path to a file containing the list of
            files to be processed (their full path).

        node_role (str): a string describing the role of the node
            where the function is called ('worker' or 'master').

        node_rank (int): rank of the node where the function is called.

        mpi_pool_size (int): size of the node pool that includes the
            node where the function is called.

        monitor_params (:obj:`onda.utils.parameters.MonitorParams`):
            a MonitorParams object containing the monitor parameters
            from the configuration file.

     Yields:

        Dict: A dictionary containing the metadata (full path, etc. )
        of a file from thelist.
    """
    # Open the file with the list of files to process. Raise an
    # exception in case of failure.
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
    mylength = int(
        numpy.ceil(
            len(filelist) / float(mpi_pool_size - 1)
        )
    )

    # Extract the portion of the list that should be processed by
    # the current worker.
    myfiles = filelist[
        ((node_rank - 1) * mylength):(node_rank * mylength)
    ]

    for entry in myfiles:
        
        # Create the event dictionary object. Add two custom
        # entries that are needed by the data extraction functions:
        # the full path to the file, and the file creation date (a
        # first approximation of the timestamp).
        event = {'full_path': entry}
        event['file_creation_time'] = os.stat(entry).st_crtime

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
