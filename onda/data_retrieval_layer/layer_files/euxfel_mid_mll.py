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

import h5py
import numpy
from future.utils import raise_from

from onda.data_retrieval_layer.data_sources import agipd_vds
from onda.data_retrieval_layer.frameworks import karabo_euxfel
from onda.utils import data_event, dynamic_import


def vds_reader_agipd(file_handle, data_label, required_train, required_pulses):

    base_path = "/INSTRUMENT/{0}/DET/{1}CH0:xtdf/image/{2}"

    train_ids = file_handle[base_path.format(data_label, 0, "trainId")][:, 0]
    pulse_ids = file_handle[base_path.format(data_label, 0, "cellId")][:, 0]

    required_train_indices = numpy.where(required_train == train_ids)[0]
    pulse_indices = tuple(
        index for index in required_train_indices if pulse_ids[index] in required_pulses
    )

    data = numpy.zeros((len(pulse_indices), 16 * 512, 128))
    gain = numpy.zeros((len(pulse_indices), 16 * 512, 128))
    for data_idx, pulse_idx in enumerate(pulse_indices):
        for panel_idx in range(0, 16):
            try:
                data[
                    data_idx, panel_idx * 512 : (panel_idx + 1) * 512, :
                ] = file_handle[base_path.format(data_label, panel_idx, "data")][
                    pulse_idx, 0, ...
                ]
                gain[
                    data_idx, panel_idx * 512 : (panel_idx + 1) * 512, :
                ] = file_handle[base_path.format(data_label, panel_idx, "data")][
                    pulse_idx, 1, ...
                ]
            except KeyError:
                continue
    return (data, gain)


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
    source_parts = source.split(":")

    vds_file_path = source_parts[0]
    log_file_path = source_parts[1]

    try:
        with open(log_file_path, "r") as fhandle:
            log_file_lines = fhandle.readlines()
    except (IOError, OSError):
        raise_from(
            exc=RuntimeError("Error reading the {0} log file.".format(log_file_path)),
            cause=None,
        )

    scan_template_lines = tuple(
        line for line in log_file_lines if line.lower().startswith("# scan template")
    )
    if "2d" in scan_template_lines[-1].lower():
        scan_type = 2
    elif "1d" in scan_template_lines[-1].lower():
        scan_type = 1
    else:
        raise RuntimeError("Unknown scan template (not 1D or 2D)")

    device_lines = (
        line for line in log_file_lines if line.lower().startswith("# device")
    )
    try:
        devices = tuple(line.split(":")[1].strip() for line in device_lines)
    except ValueError:
        raise_from(exc=RuntimeError("Error reading devices log file."), cause=None)
    if "KaraboClient" in devices:
        scan_with_karabo = True
        move_offset = 2
    else:
        scan_with_karabo = False
        move_offset = 1

    points_count_lines = tuple(
        line for line in log_file_lines if line.lower().startswith("# steps count")
    )
    try:
        points_count = tuple(int(line.split(":")[1]) + 1 for line in points_count_lines)
    except ValueError:
        raise RuntimeError("Error reading point counts from log file.")

    scan_lines = tuple(
        line for line in log_file_lines if not line.lower().startswith("# ")
    )
    if scan_type == 2:
        temp_scan_lines_with_images = []
        for line_idx, line in enumerate(scan_lines):
            if line_idx % (points_count[0] * move_offset + 1) == 0:
                continue
            temp_scan_lines_with_images.append(line)
        if scan_with_karabo:
            scan_lines_with_images = tuple(
                line
                for line_idx, line in enumerate(temp_scan_lines_with_images)
                if line_idx % 2 == 0
            )
        else:
            scan_lines_with_images = tuple(temp_scan_lines_with_images)
    else:
        if scan_with_karabo:
            scan_lines_with_images = tuple(
                line for line_idx, line in enumerate(scan_lines) if line_idx % 2 == 0
            )
        else:
            scan_lines_with_images = tuple(scan_lines)

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

    lines_curr_node = scan_lines_with_images[slice_current_node]
    range_curr_node = range(0, num_lines_to_process)[slice_current_node]

    data_label = monitor_params.get_param(
        section="DataRetrievalLayer",
        parameter="karabo_data_label",
        type_=str,
        required=True,
    )

    data_extraction_functions = dynamic_import.get_data_extraction_funcs(monitor_params)
    event = data_event.DataEvent(
        open_event_func=karabo_euxfel.open_event,
        close_event_func=karabo_euxfel.close_event,
        get_num_frames_in_event_func=agipd_vds.get_num_frames_in_event,
        data_extraction_funcs=data_extraction_functions,
    )

    event.file_handle = h5py.File(vds_file_path, "r")
    # Fills required frameworks info.
    if "beam_energy" in data_extraction_functions:
        event.framework_info["beam_energy"] = monitor_params.get_param(
            section="DataRetrievalLayer",
            parameter="karabo_fallback_beam_energy_in_eV",
            type_=float,
            required=True,
        )

    if "detector_distance" in data_extraction_functions:
        event.framework_info["detector_distance"] = monitor_params.get_param(
            section="DataRetrievalLayer",
            parameter="karabo_fallback_detector_distance_in_mm",
            type_=float,
            required=True,
        )

    # Connects to the Karabo Bridge using the Karabo API.
    for entry_idx, entry in zip(range_curr_node, lines_curr_node):
        items = entry.strip().split(";")
        if scan_type == 2:
            event.framework_info["motor_positions"] = tuple(
                float(value.strip().split(" ")[0]) for value in items[-2:]
            )
        else:
            event.framework_info["motor_positions"] = (
                float(items[-1].strip().split(" ")[0]),
            )

        event.framework_info["index_in_scan"] = entry_idx

        event.timestamp = numpy.float64(items[3].split(" ")[0])

        if scan_type == 2:
            train_id = int(round(float(items[-3]), 0))
        else:
            train_id = int(round(float(items[-2]), 0))

        event.data, event.framework_info["gain"] = vds_reader_agipd(
            event.file_handle, data_label, train_id, [1]
        )
        yield event


globals()["open_event"] = karabo_euxfel.open_event
globals()["close_event"] = karabo_euxfel.close_event
globals()["get_num_frames_in_event"] = agipd_vds.get_num_frames_in_event


############################
#                          #
# DATA EXTRATION FUNCTIONS #
#                          #
############################


globals()["detector_data"] = agipd_vds.detector_data
globals()["detector_gain_data"] = agipd_vds.detector_data
globals()["timestamp"] = karabo_euxfel.timestamp
globals()["detector_distance"] = karabo_euxfel.detector_distance
globals()["beam_energy"] = karabo_euxfel.beam_energy
globals()["frame_id"] = karabo_euxfel.frame_id


def motor_positions(event):
    """
    Motor positions for a MLL event retrieved from karabo-data at XFEL.

    Extracts the motor positions of an event retrieved from the karabo-data framework
    at the European XFEL facility during a multi-layer lenses experiment.

    Args:

        event (DataEvent): :obj:`onda.utils.data_event.DataEvent` object storing the
            data event.

    Returns:

        tuple[float, float]: a tuple with motor positions for fast-moving and
        slow-moving axis respectively.
    """
    # Returns the motor positions previously stored in the event.
    return event.framework_info["motor_positions"]


def index_in_scan(event):
    """
    Motor positions Timestamp of an event retrieved from karabo-data at XFEL.

    Extracts the timestamp of an event retrieved from the karabo-data framework at the
    European XFEL facility.

    Args:

        event (DataEvent): :obj:`onda.utils.data_event.DataEvent` object storing the
            data event.

    Returns:

        numpy.float64: the timestamp of the event.
    """
    # Returns the timestamp previously store in the event.
    return event.framework_info["index_in_scan"]
