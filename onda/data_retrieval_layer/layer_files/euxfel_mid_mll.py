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
# Copyright 2014-2018 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Data retrieval at the SPB beamline of XFEL.

Classes and functions used to retrieve and extract data from saved files at the
MID beamline of the European XFEL facility during MLL experiments.
"""
from __future__ import absolute_import, division, print_function

import numpy
from future.utils import raise_from

import karabo_data
from karabo_data import components

from onda.utils import data_event
from onda.data_retrieval_layer.data_sources import agipd_karabodata
from onda.data_retrieval_layer.frameworks import karabo_euxfel


############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################


globals()["initialize_event_source"] = karabo_euxfel.initialize_event_source


def event_generator(source, node_rank, mpi_pool_size, monitor_params):
    """
    Initializes the recovery of events from karabo-data, filtered by trainids.

    Returns an iterator over the events that should be processed by the worker that
    calls the function. This function must be called on each worker node after the
    :obj:`initialize_event_source` function has been called on the master node.

    Args:

        source (str): the full path to the run directory and the full path to a
            MLL log file scan, separated by a colon. (i.e:
            <path_to_run_dir>:<path_to_log_file>)

        node_rank (int): rank of the node where the function is called.

        mpi_pool_size (int): size of the node pool that includes the node where the
            function is called.

        monitor_params (MonitorParams): a :obj:`~onda.utils.parameters.MonitorParams`
            object containing the monitor parameters from the configuration file.

    Yields:

        Dict: A dictionary containing the metadata and data of an event
        (1 event = 1file).
    """
    del monitor_params
    source_parts = source.split(":")

    karabo_run_dir_path = source_parts[0]
    log_file_path = source_parts[1]

    try:
        with open(log_file_path, "r") as fhandle:
            log_file_lines = fhandle.readlines()
    except (IOError, OSError):
        raise_from(
            exc=RuntimeError("Error reading the {0} log file.".format(source)),
            cause=None,
        )

    scan_template_lines = (
        line for line in log_file_lines if line.lower().startswith("scan template")
    )
    if "2d" in scan_template_lines[-1].lower():
        scan_type = 2
    elif "1d" in scan_template_lines[-1].lower():
        scan_type = 1
    else:
        raise RuntimeError("Unknown scan template (not 1D or 2D)")

    points_count_lines = (
        line for line in log_file_lines if line.lower().startswith("steps count")
    )
    try:
        point_counts = (int(line.split(":")[1]) for line in points_count_lines)
    except ValueError:
        raise RuntimeError("Error reading point counts from log file.")

    # start_point_lines = (line for line in log_file_lines if line.lower().startswith('start point'))
    # try:
    #     start_points = (float(line.split(':')[1]) for line in start_point_lines)
    # except ValueError:
    #     raise RuntimeError("Error reading start points from log file.")

    # end_point_lines = (line for line in log_file_lines if line.lower().startswith('end point'))
    # try:
    #     end_points = (float(line.split(':')[1]) for line in end_point_lines)
    # except ValueError:
    #     raise RuntimeError("Error reading end points from log file.")

    # step_size_lines = (line for line in log_file_lines if line.lower().startswith('step size'))
    # try:
    #     step_sizes = (float(line.split(':')[1]) for line in step_size_lines)
    # except ValueError:
    #     raise RuntimeError("Error reading step sizes from log file.")

    scan_lines = (
        line
        for line in log_file_lines
        if not line.lower().startswith("# scan template")
    )
    if scan_type == 1:
        scan_lines_with_images = list(scan_lines)
    else:
        scan_lines_with_images = []
        for line_idx, line in enumerate(scan_lines):
            if line_idx % (point_counts[0] + 1) == 0:
                continue
            scan_lines_with_images.append(line)

    num_lines_to_process = len(scan_lines_with_images)

    # Computes how many lines the current worker node should process. Splits the lines
    # as equally as possible amongst the workers with the last worker getting a
    # smaller number of files if the number of lines to be processed cannot be exactly
    # divided by the number of workers.
    num_files_curr_node = int(
        numpy.ceil(num_lines_to_process / float(mpi_pool_size - 1))
    )
    slice_current_node = slice(
        ((node_rank - 1) * num_files_curr_node), (node_rank * num_files_curr_node)
    )

    print(
        "Initializing karabo-data data collection for run {0} on node {1}".format(
            karabo_run_dir_path, node_rank
        )
    )
    try:
        karabo_data_coll = karabo_data.RunDirectory(karabo_run_dir_path)
    except Exception:
        raise RuntimeError(
            "Error opening Karabo run directory: {0}.".format(karabo_run_dir_path)
        )
    print(
        "Done initializing karabo-data data collection for run {0} on node {1}".format(
            karabo_run_dir_path, node_rank
        )
    )

    lines_curr_node = scan_lines_with_images[slice_current_node]
    range_curr_node = range(0, num_lines_to_process)[slice_current_node]

    event = data_event.DataEvent(
        open_event_func=karabo_euxfel.open_event,
        close_event_func=karabo_euxfel.close_event,
        get_num_frames_in_event_func=agipd_karabodata.get_num_frames_in_event,
    )

    for entry_idx, entry in zip(range_curr_node, lines_curr_node):
        items = entry.strip().split(";")
        if scan_type == 2:
            event.framework_info["motor_positions"] = tuple(
                float(value) for value in items[-2:]
            )
        else:
            event.framework_info["motor_positions"] = tuple(float(items[-1]))

        event.framework_info["index_in_scan"] = entry_idx

        if scan_type == 2:
            train_id = int(items[-3])
        else:
            train_id = int(items[-2])

        train = karabo_data_coll.select_trains(karabo_data.by_id[[train_id]])
        event.data = components.AGIPD1M(train)
        yield event


globals()["open_event"] = karabo_euxfel.open_event
globals()["close_event"] = karabo_euxfel.close_event
globals()["get_num_frames_in_event"] = agipd_karabodata.get_num_frames_in_event
