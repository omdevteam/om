# This file is part of OM.
#
# OM is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# OM is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with OnDA.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2020 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Retrieval of file events from the filesystem.

This module contains functions and classes that retrieve data events from files written
on disk.
"""
from __future__ import absolute_import, division, print_function

import os.path
from typing import Generator

import numpy
from future.utils import raise_from

from onda.utils import (
    data_event,
    dynamic_import,
    parameters,
)


############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################


def initialize_event_source(source, node_pool_size, monitor_params):
    # type: (str, int, parameters.MonitorParams) -> None
    """
    Initializes the file event source when reading files from the filesystem.

    This function must be called on the master node before the :func:`event_generator`
    function is called on the worker nodes. There is no need to initialize the event
    source when reading from files, so this function actually does nothing.

    Arguments:

        source (str): the relative or absolute path to a file containing a list of
            files to process (one per line, with their full path).

        node_pool_size (int): the total number of nodes in the OnDA pool, including all
            the worker nodes and the master node.

        monitor_params (:class:`~onda.utils.parameters.MonitorParams`): an object
            storing the OnDA monitor parameters from the configuration file.
    """
    del source
    del node_pool_size
    del monitor_params


def event_generator(
    source,  # type: str
    node_rank,  # type: int
    node_pool_size,  # type: int
    monitor_params,  # type: parameters.MonitorParams
):
    # type: (...) -> Generator[data_event.DataEvent, None, None]
    """
    Retrieves data events to process from the filesystem.

    This function must be called on each worker node only after the
    :func:`initialize_event_source` function has been called on the master node. The
    function is a generator and it returns an iterator over the events that the calling
    worker must process.

    Arguments:

        source (str): the relative or absolute path to a file containing a list of
            files to process (one per line, with their full path).

        node_rank (int): the rank, in the OnDA pool, of the worker node calling the
            function.

        node_pool_size (int): the total number of nodes in the OnDA pool, including all
            the worker nodes and the master node.

        monitor_params (:class:`~onda.utils.parameters.MonitorParams`): an object
            storing the OnDA monitor parameters from the configuration file.

    Yields:

        :class:`~onda.utils.data_event.DataEvent`: an object storing the event data.
    """
    data_retrieval_layer_filename = monitor_params.get_param(
        group="Onda",
        parameter="data_retrieval_layer",
        parameter_type=str,
        required=True,
    )
    data_retrieval_layer = dynamic_import.import_data_retrieval_layer(
        data_retrieval_layer_filename=data_retrieval_layer_filename
    )
    required_data = monitor_params.get_param(
        group="Onda", parameter="required_data", parameter_type=list, required=True
    )
    event_handling_functions = dynamic_import.get_event_handling_funcs(
        data_retrieval_layer=data_retrieval_layer
    )
    data_extraction_functions = dynamic_import.get_data_extraction_funcs(
        required_data=required_data, data_retrieval_layer=data_retrieval_layer
    )
    event = data_event.DataEvent(
        event_handling_funcs=event_handling_functions,
        data_extraction_funcs=data_extraction_functions,
    )

    # Fills the framework info with static data that will be retrieved later.
    if "beam_energy" in data_extraction_functions:
        event.framework_info["beam_energy"] = monitor_params.get_param(
            group="DataRetrievalLayer",
            parameter="fallback_beam_energy_in_eV",
            type_=float,
            required=True,
        )
    if "detector_distance" in data_extraction_functions:
        event.framework_info["detector_distance"] = monitor_params.get_param(
            group="DataRetrievalLayer",
            parameter="fallback_detector_distance_in_mm",
            type_=float,
            required=True,
        )

    # Computes how many files the current worker node should process. Splits the files
    # as equally as possible amongst the workers with the last worker getting a
    # smaller number of files if the number of files to be processed cannot be exactly
    # divided by the number of workers.
    try:
        with open(source, "r") as fhandle:
            filelist = fhandle.readlines()
    except (IOError, OSError) as exc:
        raise_from(
            exc=RuntimeError("Error reading the {0} source file.".format(source)),
            cause=exc,
        )
    num_files_curr_node = int(numpy.ceil(len(filelist) / float(node_pool_size - 1)))
    files_curr_node = filelist[
        ((node_rank - 1) * num_files_curr_node) : (node_rank * num_files_curr_node)
    ]

    for entry in files_curr_node:
        stripped_entry = entry.strip()
        event.framework_info["full_path"] = stripped_entry

        # File modification time is used as a first approximation of the timestamp
        # when the timestamp is not available.
        event.framework_info["file_creation_time"] = os.stat(stripped_entry).st_mtime
        yield event


#############################
#                           #
# DATA EXTRACTION FUNCTIONS #
#                           #
#############################


def timestamp(event):
    # type: (data_event.DataEvent) -> numpy.float64
    """
    Gets the timestamp of a data event retrieved from the filesystem.

    Files written by detectors don't usually contain timestamp information. The
    creation date and time of the file is used as timestamp for the event.

    Arguments:

         event (:class:`~onda.utils.data_event.DataEvent`): an object storing the event
            data.

    Returns:

        numpy.float64: the timestamp of the event in seconds from the Epoch.
    """
    # Returns the file creation time previously stored in the event.
    return event.framework_info["file_creation_time"]


def beam_energy(event):
    # type: (data_event.DataEvent) -> float
    """
    Gets the beam energy for a data event retrieved from the filesystem.

    Files written by detectors don't usually contain beam energy information. This
    function takes the beam energy value from the configuration file, specifically from
    the 'fallback_beam_energy_in_eV' entry in the 'DataRetrievalLayer' parameter group.

    Arguments:

        event (:class:`~onda.utils.data_event.DataEvent`): an object storing the event
            data.

    Returns:

        float: the energy of the beam in eV.
    """
    # Returns the value previously stored in the event.
    return event.framework_info["beam_energy"]


def detector_distance(event):
    # type: (data_event.DataEvent) -> float
    """
    Gets the detector distance for a data event retrieved from the filesystem.

    Files written by detectors don't usually contain detector distance information.
    This function takes it from the configuration file, specifically from the
    'fallback_detector_distance_in_mm' entry in the 'DataRetrievalLayer' parameter
    group.

    Arguments:

        event (:class:`~onda.utils.data_event.DataEvent`): an object storing the event
            data.

    Returns:

        float: the detector distance in mm.
    """
    # Returns the value previously stored in the event.
    return event.framework_info["detector_distance"]
