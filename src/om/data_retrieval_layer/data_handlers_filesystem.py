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
# You should have received a copy of the GNU General Public License along with OM.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2020 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Retrieval and handling of data events from the filesystem.

This module contains classes that retrieve and process data events from files written
on disk.
"""
from __future__ import absolute_import, division, print_function

import os.path
from typing import Any, Callable, Dict, Generator, List

import fabio  # type: ignore
import numpy  # type: ignore
from future.utils import raise_from  # type: ignore

from om.data_retrieval_layer import base as data_ret_layer_base
from om.data_retrieval_layer import functions_pilatus
from om.utils import exceptions, parameters


class PilatusFilesDataEventHandler(data_ret_layer_base.OmDataEventHandler):
    """
    See documentation of the __init__ function.
    """

    def __init__(
        self, monitor_parameters,
    ):
        # type: (parameters.MonitorParams) -> None
        """
        Data event handler for Pilatus files read from the filesystem.

        See documentation of the constructor of the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler` .
        """
        super(PilatusFilesDataEventHandler, self).__init__(
            monitor_parameters=monitor_parameters,
        )

        self._data_extraction_funcs = {
            "timestamp": functions_pilatus.timestamp,
            "beam_energy": functions_pilatus.beam_energy,
            "detector_distance": functions_pilatus.detector_distance,
            "detector_data": functions_pilatus.detector_data,
            "event_id": functions_pilatus.event_id,
            "frame_id": functions_pilatus.frame_id,
        }  # type: Dict[str, Callable[ [Dict[str,Dict[str,Any]]],Any]]

        required_data = self._monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="required_data",
            parameter_type=list,
            required=True,
        )  # type: List[str]

        self._required_data_extraction_funcs = (
            {}
        )  # type: Dict[str, Callable[ [Dict[str,Dict[str,Any]]],Any]]
        for func_name in required_data:
            try:
                self._required_data_extraction_funcs[
                    func_name
                ] = self._data_extraction_funcs[func_name]
            except AttributeError as exc:
                raise_from(
                    exc=exceptions.OmMissingDataExtractionFunctionError(
                        "Data extraction function {0} not defined".format(func_name)
                    ),
                    cause=exc,
                )

        # Fills the event info dictionary with static data that will be retrieved
        # later.
        self._event_info_to_append = {}  # type: Dict[str, Any]

        calibration = self._monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="calibration",
            parameter_type=bool,
            required=True,
        )
        self._event_info_to_append["calibration"] = calibration
        if calibration is True:
            calibration_info_filename = self._monitor_params.get_param(
                group="data_retrieval_layer",
                parameter="calibration_filename",
                parameter_type=str,
            )
        self._event_info_to_append[
            "calibration_info_filename"
        ] = calibration_info_filename

        if "beam_energy" in required_data:
            self._event_info_to_append["beam_energy"] = self._monitor_params.get_param(
                group="data_retrieval_layer",
                parameter="fallback_beam_energy_in_eV",
                parameter_type=float,
                required=True,
            )
        if "detector_distance" in required_data:
            self._event_info_to_append[
                "detector_distance"
            ] = self._monitor_params.get_param(
                group="data_retrieval_layer",
                parameter="fallback_detector_distance_in_mm",
                parameter_type=float,
                required=True,
            )

    def initialize_event_source(self, source, node_pool_size):
        # type: (str, int) -> Any
        """
        Initializes the Pilatus filesystem event source.

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.\
initialize_event_source`.

        There is no need to initialize the filesystem source, so this function does
        nothing.
        """
        del source
        del node_pool_size

    def event_generator(
        self,
        source,  # type: str
        node_rank,  # type: int
        node_pool_size,  # type: int
    ):
        # type: (...) -> Generator[Dict[str,Any], None, None]
        """
        Retrieves Pilatus data events to process from the filesystem.

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.event_generator`.

        The files to process are split evenly amongst the processing nodes, with the
        exception of the last node, which might get a lower number depending on how
        the number of files can is split.
        """
        # Computes how many files the current processing node should process. Splits
        # the files as equally as possible amongst the processing nodes with the last
        # processing node getting a smaller number of files if the number of files to
        # be processed cannot be exactly divided by the number of processing nodes.
        try:
            with open(source, "r") as fhandle:
                filelist = fhandle.readlines()  # type: List[str]
        except (IOError, OSError) as exc:
            raise_from(
                exc=RuntimeError("Error reading the {0} source file.".format(source)),
                cause=exc,
            )
        num_files_curr_node = int(
            numpy.ceil(len(filelist) / float(node_pool_size - 1))
        )  # type: int
        files_curr_node = filelist[
            ((node_rank - 1) * num_files_curr_node) : (node_rank * num_files_curr_node)
        ]  # type: List[str]

        print("Num files current node:", node_rank, num_files_curr_node)

        data_event = {}  # type: Dict[str, Dict[str, Any]]
        data_event["data_extraction_funcs"] = self._required_data_extraction_funcs
        data_event["info"] = {}
        data_event["info"].update(self._event_info_to_append)

        for entry in files_curr_node:
            stripped_entry = entry.strip()  # type: str
            data_event["info"]["full_path"] = stripped_entry

            # File modification time is used as a first approximation of the timestamp
            # when the timestamp is not available.
            data_event["info"]["file_creation_time"] = numpy.float64(
                os.stat(stripped_entry).st_mtime
            )

            yield data_event

    def open_event(self, event):
        # type: (Dict[str,Any]) -> None
        """
        Opens an event retrieved from Pilatus files.

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.open_event`.

        For Pilatus data files, an event corresponds to the full content of a single
        Pilatus CBF file. This function makes the content of the file available in the
        'data' field of the 'event' object.
        """
        event["data"] = fabio.open(event["info"]["full_path"])

    def close_event(self, event):
        # type: (Dict[str,Any]) -> None
        """
        Closes an event retrieved from Pilatus files.

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.close_event` .

        Since an event corresponds to a CBF data file, which does not need to be closed,
        this function actually does nothing.
        """
        pass

    def get_num_frames_in_event(self, event):
        # type: (Dict[str,Any]) -> int
        """
        Gets the number of frames in an event retrieved from Pilatus files.

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.\
get_num_frames_in_event`.

        For the Pilatus detector, an event corresponds to the content of a single CBF
        data file. Since the Pilatus detector writes one frame per file, this function
        always returns 1.

        Returns:

            int: the number of frames in the event.
        """
        del event

        return 1
