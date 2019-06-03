# This file is part of OnDA.
#
# OnDA is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# OnDA is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with OnDA.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Retrieval of events from files.

Functions and classes used to retrieve data events from files.
"""
from __future__ import absolute_import, division, print_function

import os.path

import numpy
from future.utils import raise_from

from onda.utils import data_event, dynamic_import


############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################


def initialize_event_source(source, mpi_pool_size, monitor_params):
    """
    Initializes the file event source.

    This function must be called on the master node before the :obj:`event_generator`
    function is called on the worker nodes.

    Args:

        source (str): full path to a file containing the list of files to process
            (one per line, with their full path).

        mpi_pool_size (int): size of the node pool that includes the node where the
            function is called.

        monitor_params (MonitorParams): a :obj:`~onda.utils.parameters.MonitorParams`
            object containing the monitor parameters from the configuration file.
    """
    del source
    del mpi_pool_size
    del monitor_params
    # There is no event source to initialize when recovering events from files, so
    # does nothing.


def event_generator(source, node_rank, mpi_pool_size, monitor_params):
    """
    Initializes the recovery of events from files.

    Returns an iterator over the events that should be processed by the worker that
    calls the function. This function must be called on each worker node after the
    :obj:`initialize_event_source` function has been called on the master node.

    Args:

        source (str): the full path to a file containing the list of files to be
            processed (their full path).

        node_rank (int): rank of the node where the function is called.

        mpi_pool_size (int): size of the node pool that includes the node where the
            function is called.

        monitor_params (MonitorParams): a :obj:`~onda.utils.parameters.MonitorParams`
            object containing the monitor parameters from the configuration file.

    Yields:

        Dict: A dictionary containing the metadata and data of an event
        (1 event = 1file).
    """
    event_handling_functions = dynamic_import.get_event_handling_funcs(monitor_params)
    data_extraction_functions = dynamic_import.get_data_extraction_funcs(monitor_params)

    event = data_event.DataEvent(
        event_handling_funcs=event_handling_functions,
        data_extraction_funcs=data_extraction_functions,
    )

    # Fills required frameworks info.
    if "beam_energy" in data_extraction_functions:
        event.framework_info["beam_energy"] = monitor_params.get_param(
            section="DataRetrievalLayer",
            parameter="files_fallback_beam_energy_in_eV",
            type_=float,
            required=True,
        )

    if "detector_distance" in data_extraction_functions:
        event.framework_info["detector_distance"] = monitor_params.get_param(
            section="DataRetrievalLayer",
            parameter="files_fallback_detector_distance_in_mm",
            type_=float,
            required=True,
        )

    try:
        with open(source, "r") as fhandle:
            filelist = fhandle.readlines()
    except (IOError, OSError) as exc:
        raise_from(
            exc=RuntimeError("Error reading the {} source file.".format(source)),
            cause=exc,
        )

    # Computes how many files the current worker node should process. Splits the files
    # as equally as possible amongst the workers with the last worker getting a
    # smaller number of files if the number of files to be processed cannot be exactly
    # divided by the number of workers.
    num_files_curr_node = int(numpy.ceil(len(filelist) / float(mpi_pool_size - 1)))

    files_curr_node = filelist[
        ((node_rank - 1) * num_files_curr_node) : (node_rank * num_files_curr_node)
    ]

    for entry in files_curr_node:
        stripped_entry = entry.strip()
        event.framework_info["full_path"] = stripped_entry

        # File modification time is used as a first approximation of the timestamp
        # when the timestamp is not available.
        event.framework_info["file_creation_time"] = (
            os.stat(stripped_entry).st_mtime
        )
        yield event


#############################
#                           #
# DATA EXTRACTION FUNCTIONS #
#                           #
#############################


def timestamp(event):
    """
    Timestamp for detector file data.

    Files written by the detectors don't usually contain timestamp information.
    The creation date and time of the file is taken as timestamp of the event.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        numpy.float64: the timestamp of the event.
    """
    # Returns the file creation time previously stored in the event.
    return event.framework_info["file_creation_time"]


def beam_energy(event):
    """
    Retrieves the beam energy for detector file data.

    Files written by the detectors don't usually contain beam energy information.
    The value is taken from the configuration file, specifically from the
    'files_fallback_beam_energy_in_eV' entry in the 'DataRetrievalLayer' section.

    Args:

        event (DataEvent): :obj:`onda.utils.data_event.DataEvent` object storing the
            data event.

    Returns:

        float: the energy of the beam in eV.
    """
    # Returns the value previously stored in the event.
    return event.framework_info["beam_energy"]


def detector_distance(event):
    """
    Retrieves the detector distance for detector file data.

    Files written by the detectors don't usually contain detector distance information.
    The value is taken from the configuration file, specifically from the
    'files_fallback_detector_distance_in_mm' entry in the 'DataRetrievalLayer' section.

    Args:

        event (DataEvent): :obj:`onda.utils.data_event.DataEvent` object storing the
            data event.

    Returns:

        float: the distance between the detector and the sample in mm.
    """
    # Returns the value previously stored in the event.
    return event.framework_info["detector_distance"]
