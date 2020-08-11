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
Retrieval and handling of data events from HiDRA.

This module contains classes that retrieve and process data events from the HiDRA
framework.
"""
from __future__ import absolute_import, division, print_function

import io
import os.path
import socket
import sys
from typing import Any, Callable, Dict, Generator, List, Tuple, cast

import fabio  # type: ignore
import numpy  # type: ignore
from future.utils import raise_from  # type: ignore

from hidra_api import Transfer, transfer  # type: ignore
from om.data_retrieval_layer import base as drl_base
from om.data_retrieval_layer import functions_pilatus
from om.utils import exceptions, parameters


def _create_hidra_info(source, node_pool_size, monitor_params):
    # type: (str, int, parameters.MonitorParams) -> Dict[str, Any]

    # Creates the HidraInfo object needed to initialize the HiDRA event source.

    # Reads the requested transfer type from the configuration file. If it is not
    # specified there, imports the suggested transfer type from the data extraction
    # layer and use that.

    query_text = "QUERY_NEXT"  # type: str
    data_base_path = ""  # type: str

    base_port = monitor_params.get_param(
        group="data_retrieval_layer",
        parameter="hidra_base_port",
        parameter_type=int,
        required=True,
    )  # type: int

    # Search the configuration file for a HiDRA selection string. If the selection
    # string is not found, use the file extensions from the detector layer as
    # selection string.
    hidra_selection_string = monitor_params.get_param(
        group="data_retrieval_layer",
        parameter="hidra_selection_string",
        parameter_type=str,
    )  # type: str
    if hidra_selection_string is None:
        hidra_selection_string = functions_pilatus.get_file_extensions()

    # Add an empty target at the beginning to cover the collecting node. In this way,
    # the index of a node in the target list will match its OM rank.
    targets = [["", "", str(1), ""]]  # type: List[List[str]]

    # Create the HiDRA query object, as requested by the HiDRA API.
    for rank in range(1, node_pool_size):
        target_entry = [
            socket.gethostname(),
            str(base_port + rank),
            str(1),
            hidra_selection_string,
        ]  # type: List[str]
        targets.append(target_entry)

    query = Transfer(connection_type=query_text, signal_host=source, use_log=False)

    return {
        "query": query,
        "targets": targets,
        "data_base_path": data_base_path,
    }


class P11Petra3DataEventHandler(drl_base.OmDataEventHandler):
    """
    See documentation of the __init__ function.
    """

    def __init__(self, monitor_parameters, source):
        # type: (parameters.MonitorParams, str) -> None
        """
        Data event handler for events recovered from HiDRA at P11 (PETRA III).

        See documentation of the constructor of the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler`.

        This class handles Pilatus detector data events recovered from HiDRA at the
        P11 beamtime of the PETRA III facility.
        """
        super(P11Petra3DataEventHandler, self).__init__(
            monitor_parameters=monitor_parameters, source=source,
        )

    @property
    def data_extraction_funcs(self):
        # type: () -> Dict[str, Callable[[Dict[str, Dict[str, Any]]], Any]]
        """
        Retrieves the Data Extraction Functions for Pilatus files.

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.\
data_extraction_funcs`.
        """
        return {
            "timestamp": functions_pilatus.timestamp,
            "beam_energy": functions_pilatus.beam_energy,
            "detector_distance": functions_pilatus.detector_distance,
            "detector_data": functions_pilatus.detector_data,
            "event_id": functions_pilatus.event_id,
            "frame_id": functions_pilatus.frame_id,
        }

    def initialize_event_handling_on_collecting_node(self, node_rank, node_pool_size):
        # type: (int, int) -> Any
        """
        Initializes event handling on the collecting node for P11 (Petra III).

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.\
initialize_event_source`.

        This function announces OM to HiDRA and configures HiDRA to send data event to
        the processing nodes.

        Raises:

            :class:`~om.utils.exceptions.OmHidraAPIError`: if the initial connection to
                HiDRA fails.
        """
        print("Announcing OM to HiDRA.")
        sys.stdout.flush()
        hidra_info = _create_hidra_info(
            source=self._source,
            node_pool_size=node_pool_size,
            monitor_params=self._monitor_params,
        )

        try:
            hidra_info["query"].initiate(hidra_info["targets"][1:])
        except transfer.CommunicationFailed as exc:
            raise_from(
                exc=exceptions.OmHidraAPIError(
                    "Failed to contact HiDRA: {0}".format(exc)
                ),
                cause=exc,
            )

        return hidra_info

    def initialize_event_handling_on_processing_node(self, node_rank, node_pool_size):
        # type: (int, int) -> Any
        """
        Initializes event handling on the processing nodes for Pilatus files.

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.\
initialize_event_source`.
        """
        required_data = self._monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="required_data",
            parameter_type=list,
            required=True,
        )  # type: List[str]

        self._required_data_extraction_funcs = drl_base.filter_data_extraction_funcs(
            self.data_extraction_funcs, required_data
        )  # type: Dict[str, Callable[ [Dict[str,Dict[str,Any]]],Any]]

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

    def event_generator(
        self,
        node_rank,  # type: int
        node_pool_size,  # type: int
    ):
        # type: (...) -> Generator[Dict[str, Any], None, None]
        """
        Retrieves events to process from HiDRA at Petra III.

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.event_generator`.

        Raises:

            :class:`~om.utils.exceptions.OmHidraAPIError`: if the initial connection to
                HiDRA fails.
        """
        hidra_info = _create_hidra_info(
            source=self._source,
            node_pool_size=node_pool_size,
            monitor_params=self._monitor_params,
        )
        print(
            "Worker {0} listening at port {1}".format(
                node_rank, hidra_info["targets"][node_rank][1]
            )
        )
        sys.stdout.flush()
        try:
            hidra_info["query"].start(hidra_info["targets"][node_rank][1])
        except transfer.CommunicationFailed as exc:
            raise_from(
                exc=exceptions.OmHidraAPIError(
                    "Failed to contact HiDRA: {0}".format(exc)
                ),
                cause=exc,
            )

        data_event = {}  # type: Dict[str, Dict[str, Any]]
        data_event["data_extraction_funcs"] = self._required_data_extraction_funcs
        data_event["additional_info"] = {}
        data_event["additional_info"].update(self._event_info_to_append)

        while True:
            recovered_metadata, recovered_data = hidra_info[
                "query"
            ].get()  # type: Tuple[Dict[str,Any], Dict[str,Any]]
            data_event["data"] = recovered_data
            data_event["metadata"] = recovered_metadata
            data_event["additional_info"]["full_path"] = os.path.join(
                hidra_info["data_base_path"],
                recovered_metadata["relative_path"],
                recovered_metadata["filename"],
            )
            data_event["additional_info"]["timestamp"] = numpy.float64(
                recovered_metadata["file_create_time"]
            )

            yield data_event

    def open_event(self, event):
        # type: (Dict[str,Any]) -> None
        """
        Opens an event retrieved from HiDRA at P11 (Petra III).

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.open_event`.

        For the Pilatus detector, a HiDRA event corresponds to the full content of a
        single Pilatus CBF data file. This function makes the content of the file
        available in the 'data' entry of the 'event' dictionary.
        """
        # Wraps the binary data that HiDRA sends to OM in a BytesIO object.
        byio_data = io.BytesIO(cast(bytes, event["data"]))  # type: io.BytesIO

        # Reads the data using the fabio library and stores the content as a cbf_obj
        # object.
        cbf_image = fabio.cbfimage.CbfImage()  # type: Any
        event["data"] = cbf_image.read(byio_data)

    def close_event(self, event):
        # type: (Dict[str,Any]) -> None
        """
        Closes an event retrieved from HiDRA at P11 (Petra III)

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.close_event` .

        An HiDRA event does not need to be closed, so this function actually does
        nothing.
        """
        del event

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
        """
        del event

        return 1
