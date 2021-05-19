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
# Copyright 2020 -2021 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Retrieval and handling of data events from HiDRA.

This module contains Data Event Handlers for events retrieved from the HiDRA software
framework (used at the Petra III facility).
"""
import io
import pathlib
import socket
import sys
from typing import Any, Callable, Dict, Generator, List, cast

import fabio  # type: ignore
import numpy  # type: ignore
from om.utils import exceptions

try:
    from hidra_api import Transfer, transfer  # type: ignore
except ImportError:
    raise exceptions.OmMissingDependencyError(
        "The following required module cannot be imported: hidra_api"
    )


from om.data_retrieval_layer import base as drl_base
from om.data_retrieval_layer import functions_pilatus
from om.utils import exceptions, parameters


def _create_hidra_info(
    source: str, node_pool_size: int, monitor_params: parameters.MonitorParams
) -> Dict[str, Any]:
    # Creates the HidraInfo object needed to initialize the HiDRA event source.

    # Reads the requested transfer type from the configuration file. If it is not
    # specified there, imports the suggested transfer type from the data extraction
    # layer and use that.

    query_text: str = "QUERY_NEXT"
    data_base_path: str = ""

    base_port: int = monitor_params.get_param(
        group="data_retrieval_layer",
        parameter="hidra_base_port",
        parameter_type=int,
        required=True,
    )

    # Search the configuration file for a HiDRA selection string. If the selection
    # string is not found, use the file extensions from the detector layer as
    # selection string.
    hidra_selection_string: str = monitor_params.get_param(
        group="data_retrieval_layer",
        parameter="hidra_selection_string",
        parameter_type=str,
    )
    if hidra_selection_string is None:
        hidra_selection_string = functions_pilatus.get_file_extensions()

    # Add an empty target at the beginning to cover the collecting node. In this way,
    # the index of a node in the target list will match its OM rank.
    targets: List[List[str]] = [["", "", str(1), ""]]

    # Create the HiDRA query object, as requested by the HiDRA API.
    rank: int
    for rank in range(1, node_pool_size):
        target_entry: List[str] = [
            socket.gethostname(),
            str(base_port + rank),
            str(1),
            hidra_selection_string,
        ]
        targets.append(target_entry)

    query = Transfer(connection_type=query_text, signal_host=source, use_log=False)

    return {
        "query": query,
        "targets": targets,
        "data_base_path": data_base_path,
    }


class P11Petra3DataEventHandler(drl_base.OmDataEventHandler):
    """
    See documentation of the `__init__` function.

    Base class: [`OmDataEventHandler`][om.data_retrieval_layer.base.OmDataEventHandler]
    """

    def __init__(
        self, monitor_parameters: parameters.MonitorParams, source: str
    ) -> None:
        """
        Data Event Handler for events retrieved from HiDRA at P11 (PETRA III).

        This Data Event Handler deals with events retrieved from the HiDRA software
        framework at the P11 beamline of the Petra III facility. It is a subclass of
        the generic [OmDataEventHandler]
        [om.data_retrieval_layer.base.OmDataEventHandler] base class.

        The source string for this Data Event Handler is the host name or IP address of
        the machine where the HiDRA server is running. HiDRA streams events based on
        files written by detectors, with each event usually corresponding to the
        content of one file. At P11, the x-ray detector is a 1M Pilatus. This detector
        writes files in CBF format. Each HiDRA event therefore corresponds to the
        content of a single CBF file, which usually stores 1 detector frame.

        Arguments:

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.

            source: A string describing the data source.
        """
        super(P11Petra3DataEventHandler, self).__init__(
            monitor_parameters=monitor_parameters,
            source=source,
        )

    @property
    def data_extraction_funcs(
        self,
    ) -> Dict[str, Callable[[Dict[str, Dict[str, Any]]], Any]]:
        """
        Retrieves the Data Extraction Functions for HiDRA events at P11.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Returns:

            A dictionary storing the Data Extraction functions available to the current
            Data Event Handler.

            * Each dictionary key defines the name of a function.

            * The corresponding dictionary value stores the function implementation.
        """
        return {
            "timestamp": functions_pilatus.timestamp,
            "beam_energy": functions_pilatus.beam_energy,
            "detector_distance": functions_pilatus.detector_distance,
            "detector_data": functions_pilatus.detector_data,
            "event_id": functions_pilatus.event_id,
            "frame_id": functions_pilatus.frame_id,
        }

    def initialize_event_handling_on_collecting_node(
        self, node_rank: int, node_pool_size: int
    ) -> Any:
        """
        Initializes P11 HiDRA event handling on the collecting node.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function announces OM to the HiDRA server. It configures HiDRA to send
        data events to the processing nodes.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        Returns:

            An optional initialization token.

        Raises:

            OmHidraAPIError: A [OmHidraAPIError][om.utils.exceptions.OmHidraAPIError]
                exception is raised if the initial connection to HiDRA fails.
        """
        print("Announcing OM to HiDRA.")
        sys.stdout.flush()

        # TODO: Type this dict
        hidra_info: Dict[str, Any] = _create_hidra_info(
            source=self._source,
            node_pool_size=node_pool_size,
            monitor_params=self._monitor_params,
        )

        try:
            hidra_info["query"].initiate(hidra_info["targets"][1:])
        except transfer.CommunicationFailed as exc:
            raise exceptions.OmHidraAPIError(
                "Failed to contact HiDRA: {0}".format(exc)
            ) from exc

        return hidra_info

    def initialize_event_handling_on_processing_node(
        self, node_rank: int, node_pool_size: int
    ) -> Any:
        """
        Initializes P11 HiDRA event handling on the processing nodes.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function configures each processing node to receive events from the HiDRA
        server.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        Raises:

            OmHidraAPIError: A [OmHidraAPIError][om.utils.exceptions.OmHidraAPIError]
                exception is raised if the initial connection to HiDRA fails.
        """
        required_data: List[str] = self._monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="required_data",
            parameter_type=list,
            required=True,
        )
        self._required_data_extraction_funcs: Dict[
            str, Callable[[Dict[str, Dict[str, Any]]], Any]
        ] = drl_base.filter_data_extraction_funcs(
            self.data_extraction_funcs, required_data
        )

        # Fills the event info dictionary with static data that will be retrieved
        # later.
        self._event_info_to_append: Dict[str, Any] = {}
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
        node_rank: int,
        node_pool_size: int,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Retrieves HiDRA events at P11.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves events from the HiDRA server. At the P11 beamline of
        the Petra III facility, each HiDRA event corresponds to the content of a single
        CBF file written by a Pilatus 1M detector.

        This generator function yields a dictionary storing the data for the current
        event.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        Raises:

            OmHidraAPIError: A [OmHidraAPIError][om.utils.exceptions.OmHidraAPIError]
                exception is raised if the initial connection to HiDRA fails.
        """
        hidra_info: Dict[str, Any] = _create_hidra_info(
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
            raise exceptions.OmHidraAPIError(
                "Failed to contact HiDRA: {0}".format(exc)
            ) from exc

        data_event: Dict[str, Dict[str, Any]] = {}
        data_event["data_extraction_funcs"] = self._required_data_extraction_funcs
        data_event["additional_info"] = {}
        data_event["additional_info"].update(self._event_info_to_append)

        while True:
            recovered_metadata: Dict[str, Any]
            recovered_data: Dict[str, Any]
            recovered_metadata, recovered_data = hidra_info["query"].get()
            data_event["data"] = recovered_data
            data_event["metadata"] = recovered_metadata
            data_event["additional_info"]["full_path"] = (
                pathlib.Path(hidra_info["data_base_path"])
                / recovered_metadata["relative_path"]
                / recovered_metadata["filename"],
            )
            data_event["additional_info"]["timestamp"] = numpy.float64(
                recovered_metadata["file_create_time"]
            )

            yield data_event

    def open_event(self, event: Dict[str, Any]) -> None:
        """
        Opens a P11 HiDRA event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        At P11, each HiDRA event contains data from a single CBF file from a 1M Pilatus
        detector. This function associates the content of the CBF file to the 'data'
        key of the 'event' dictionary.

        Arguments:

            event: A dictionary storing the event data.
        """
        # Wraps the binary data that HiDRA sends to OM in a BytesIO object.
        byio_data: io.BytesIO = io.BytesIO(cast(bytes, event["data"]))

        # Reads the data using the fabio library and stores the content as a cbf_obj
        # object.
        cbf_image: Any = fabio.cbfimage.CbfImage()
        event["data"] = cbf_image.read(byio_data)

    def close_event(self, event: Dict[str, Any]) -> None:
        """
        Closes a P11 HiDRA data event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        An event recovered from HiDRA at P11 does not need to be closed, therefore this
        function does nothing..

        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    def get_num_frames_in_event(self, event: Dict[str, Any]) -> int:
        """
        Gets the number of frames in a P11 HiDRA data event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        At P11, each HiDRA event contains data from a single CBF file from a 1M Pilatus
        detector. These files usually store just one detector frame. This function
        therefore always returns 1.

        Arguments:

            event: A dictionary storing the event data.
        """
        return 1
