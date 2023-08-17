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
# Copyright 2020 -2023 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Handling of HTTP/REST-based data events.

This module contains Data Event Handler classes that manipulate events originating from
the HTTP/REST interface of detectors manufactured by company Dectris.
"""
import sys
import time
from io import BytesIO
from typing import Any, Dict, Generator, List, Literal, Union, cast

import requests  # type: ignore

from om.lib.exceptions import OmDataExtractionError, OmHttpInterfaceInitializationError
from om.lib.layer_management import filter_data_sources
from om.lib.parameters import MonitorParameters
from om.protocols.data_retrieval_layer import (
    OmDataEventHandlerProtocol,
    OmDataSourceProtocol,
)


class EigerHttpDataEventHandler(OmDataEventHandlerProtocol):
    """
    See documentation of the `__init__` function.

    """

    def __init__(
        self,
        *,
        source: str,
        data_sources: Dict[str, OmDataSourceProtocol],
        monitor_parameters: MonitorParameters,
    ) -> None:
        """
        Data Event Handler for Eiger's HTTP/REST events.

        This class handles data events recovered from the HTTP/REST interface of an
        Eiger detector.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        * For this Event Handler, a data event corresponds to the content of an
          individual event retrieved from the HTTP/REST interface (usually
          a single detector data frame)

        * The source string for this Data Event Handler is the base URL of the
          'monitor' subsystem of the Eiger detector HTTP/REST interface. The string has
          the following format: `http://<address_of_dcu>/monitor/api/<version>`.

        Arguments:

            source: A string describing the data event source.

            data_sources: A dictionary containing a set of Data Source class instances.

                * Each dictionary key must define the name of a data source.

                * The corresponding dictionary value must store the instance of the
                  [Data Source class][om.protocols.data_retrieval_layer.OmDataSourceProtocol]  # noqa: E501
                  that describes the source.

            monitor_parameters: An object storing OM's configuration parameters.
        """
        self._source: str = source
        self._monitor_params: MonitorParameters = monitor_parameters
        self._data_sources: Dict[str, OmDataSourceProtocol] = data_sources

    def _check_detector_monitor_mode(
        self, count_down: int = 12, wait_time: int = 5
    ) -> Union[Literal["enabled", "disabled"], None]:
        # Checks if the detector is available. If not, keeps retrying for 1 minute.
        # If detector is available, returns the state of the detector monitor mode.
        while count_down > 0:
            count_down -= 1
            try:
                response: requests.Response = requests.get(
                    f"{self._source}/config/mode"
                )
                if response.status_code == 200:
                    return cast(
                        Literal["enabled", "disabled"], response.json()["value"]
                    )
            except Exception:
                pass
            time.sleep(wait_time)
        return None

    def initialize_event_handling_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes Eiger's HTTP/REST event handling on the collecting node.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node int the OM node pool. The rank
                is an integer that unambiguously identifies the node in the pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        Raises:

            OmHttpInterfaceInitializationError: Raised when an error happens during the
                initialization of the Eiger'S HTTP/REST interface.
        """
        print("Configuring detector...")
        if not self._check_detector_monitor_mode():
            raise OmHttpInterfaceInitializationError(
                "Cannot connect to the detector: "
                "please make sure the detector is connected and switched on."
            )

        response: requests.Response = requests.put(
            f"{self._source}/config/mode", json={"value": "enabled"}
        )
        if not response.status_code == 200:
            raise OmHttpInterfaceInitializationError(
                "Cannot enable 'monitor' mode of the detector."
            )

        response = requests.put(
            f"{self._source}/config/discard_new", json={"value": False}
        )
        if not response.status_code == 200:
            raise OmHttpInterfaceInitializationError(
                "Cannot enable 'overwrite buffer' mode of the detector."
            )

        buffer_size: int = self._monitor_params.get_parameter(
            group="data_retrieval_layer",
            parameter="eiger_monitor_buffer_size",
            parameter_type=int,
            required=True,
        )
        response = requests.put(
            f"{self._source}/config/buffer_size", json={"value": buffer_size}
        )
        if not response.status_code == 200:
            raise OmHttpInterfaceInitializationError(
                "Cannot set the buffer size of the detector monitor mode."
            )

    def initialize_event_handling_on_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> Any:
        """
        Initializes Eiger's HTTP/REST event handling on the processing nodes.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node int the OM node pool. The rank
                is an integer that unambiguously identifies the node in the pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        Returns:

            An optional initialization token.
        """
        required_data: List[str] = self._monitor_params.get_parameter(
            group="data_retrieval_layer",
            parameter="required_data",
            parameter_type=list,
            required=True,
        )

        self._required_data_sources = filter_data_sources(
            data_sources=self._data_sources,
            required_data=required_data,
        )

        while self._check_detector_monitor_mode() != "enabled":
            time.sleep(0.5)

    def event_generator(
        self,
        *,
        node_rank: int,
        node_pool_size: int,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Retrieves events from Eiger's HTTP/REST interface.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves data events on the processing nodes. Each retrieved
        event corresponds to a single event from Eiger's HTTP/REST interface (a single
        detector data frame).

        Arguments:

            node_rank: The OM rank of the current node int the OM node pool. The rank
                is an integer that unambiguously identifies the node in the pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        data_event: Dict[str, Any] = {}
        data_event["additional_info"] = {}

        self._data_sources["timestamp"].initialize_data_source()
        source_name: str
        for source_name in self._required_data_sources:
            self._data_sources[source_name].initialize_data_source()

        while True:
            response: requests.Response = requests.get(f"{self._source}/images/next")
            if response.status_code == 200:
                image_file: BytesIO = BytesIO(response.content)
                data_event["additional_info"]["image_file"] = image_file
                data_event["additional_info"]["timestamp"] = self._data_sources[
                    "timestamp"
                ].get_data(event=data_event)

                yield data_event

            elif response.status_code == 408:
                # print(f"Processing node {node_rank}: No image available")
                time.sleep(0.5)

            else:
                msg: str = (
                    f"Response from Detector: {response.status_code} - "
                    f"{response.reason}"
                )
                print(f"Processing node {node_rank}: {msg}")
                time.sleep(0.5)

    def open_event(self, *, event: Dict[str, Any]) -> None:
        """
        Opens an Eiger's HTTP/REST interface event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Events from Eiger's HTTP/REST interface do not need to be opened, so this
        function actually does nothing.

        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    def close_event(self, *, event: Dict[str, Any]) -> None:
        """
        Closes an Eiger's HTTP/REST interface event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Events from Eiger's HTTP/REST interface do not need to be closed, so this
        function actually does nothing.

        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    def extract_data(
        self,
        *,
        event: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extracts data from an Eiger HTTP/REST event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A dictionary storing the extracted data.

                * Each dictionary key identifies a Data Source in the event for which
                data has been retrieved.

                * The corresponding dictionary value stores the data extracted from the
                Data Source for the event being processed.

        Raises:

            OmDataExtractionError: Raised when data cannot be extracted from the event.
        """
        data: Dict[str, Any] = {}
        data["timestamp"] = event["additional_info"]["timestamp"]
        source_name: str
        for source_name in self._required_data_sources:
            try:
                data[source_name] = self._data_sources[source_name].get_data(
                    event=event
                )
            # One should never do the following, but it is not possible to anticipate
            # every possible error raised by the facility frameworks.
            except Exception:
                exc_type, exc_value = sys.exc_info()[:2]
                if exc_type is not None:
                    raise OmDataExtractionError(
                        f"OM Warning: Cannot interpret {source_name} event data due "
                        f"to the following error: {exc_type.__name__}: {exc_value}"
                    )

        return data

    def initialize_event_data_retrieval(self) -> None:
        """
        Initializes event data retrievals from from Eiger's HTTP/REST interface.

        Eiger's HTTP/REST interface does not allow the retrieval of single standalone
        data events, so this function has no implementation.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Raises:

            NotImplementedError: This functionality has not been implemented for this
                Data Event Handler.
        """
        raise NotImplementedError

    def retrieve_event_data(self, event_id: str) -> Dict[str, Any]:
        """
        Retrieves all data related to the requested event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Eiger's HTTP/REST interface does not allow the retrieval of standalone data
        events, so this function has no implementation.

        Arguments:

            event_id: A string that uniquely identifies a data event.

        Returns:

            All data related to the requested detector event.
        Raises:

            NotImplementedError: This functionality has not been implemented for this
                Data Event Handler.
        """
        raise NotImplementedError
