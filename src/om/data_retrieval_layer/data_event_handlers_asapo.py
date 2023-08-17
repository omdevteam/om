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
Handling of ASAP::O-based data events.

This module contains Data Event Handler classes that manipulate events originating
from the ASAP::O software framework (used at the PETRA III facility).
"""
import sys
import time
from typing import Any, Dict, Generator, List, NamedTuple, Union

import numpy
from numpy.typing import NDArray

from om.lib.exceptions import OmDataExtractionError, OmMissingDependencyError
from om.lib.layer_management import filter_data_sources
from om.lib.parameters import MonitorParameters
from om.protocols.data_retrieval_layer import (
    OmDataEventHandlerProtocol,
    OmDataSourceProtocol,
)

try:
    import asapo_consumer  # type: ignore
except ImportError:
    raise OmMissingDependencyError(
        "The following required module cannot be imported: asapo_consumer"
    )


class _TypeAsapoEvent(NamedTuple):
    # This named tuple is used internally to store ASAP::O event data, metadata and
    # corresponding ASAP::O stream information.
    event_data: Union[NDArray[numpy.float_], NDArray[numpy.int_]]
    event_metadata: Dict[str, Any]
    stream_name: str
    stream_metadata: Dict[str, Any]


class AsapoDataEventHandler(OmDataEventHandlerProtocol):
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
        Data Event Handler for ASAP::O events.

        This class handles data events retrieved from the ASAP::O software framework at
        the PETRA III facility.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        * For this Event Handler, a data event corresponds to the content of an
            individual ASAP::O event.

        * The source string required by this Data Event Handler is either the ID of the
            beamtime for which OM is being used (for online data retrieval) or the ID
            of the beamtime and the name of the ASAP::O stream separated by a colon
            (for offline data retrieval).

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

    def _initialize_asapo_consumer(self) -> Any:
        asapo_url: str = self._monitor_params.get_parameter(
            group="data_retrieval_layer",
            parameter="asapo_url",
            parameter_type=str,
        )
        asapo_path: str = self._monitor_params.get_parameter(
            group="data_retrieval_layer",
            parameter="asapo_path",
            parameter_type=str,
        )
        asapo_data_source: str = self._monitor_params.get_parameter(
            group="data_retrieval_layer",
            parameter="asapo_data_source",
            parameter_type=str,
        )
        asapo_has_filesystem: str = self._monitor_params.get_parameter(
            group="data_retrieval_layer",
            parameter="asapo_has_filesystem",
            parameter_type=bool,
        )
        asapo_token: str = self._monitor_params.get_parameter(
            group="data_retrieval_layer",
            parameter="asapo_token",
            parameter_type=str,
        )
        consumer: Any = asapo_consumer.create_consumer(
            asapo_url,
            asapo_path,
            asapo_has_filesystem,
            self._source.split(":")[0],
            asapo_data_source,
            asapo_token,
            3000,
            instance_id="auto",
            pipeline_step="onda_monitor",
        )

        return consumer

    def _offline_event_generator(
        self, consumer: Any, consumer_group_id: str, stream_name: str
    ) -> Generator[_TypeAsapoEvent, None, None]:
        stream_metadata: Union[Dict[str, Any], None] = None
        while not stream_metadata:
            try:
                stream_metadata = consumer.get_stream_meta(stream_name)
            except asapo_consumer.AsapoNoDataError:
                print(f"Stream {stream_name} doesn't exist.")
                time.sleep(5)

        while True:
            try:
                event_data, event_metadata = consumer.get_next(
                    group_id=consumer_group_id, stream=stream_name, meta_only=False
                )
                yield _TypeAsapoEvent(
                    event_data, event_metadata, stream_name, stream_metadata
                )
            except asapo_consumer.AsapoNoDataError:
                ...
            except asapo_consumer.AsapoEndOfStreamError:
                break

    def _online_event_generator(
        self, consumer: Any, consumer_group_id: str
    ) -> Generator[_TypeAsapoEvent, None, None]:
        stream_list: List[Any] = []
        while len(stream_list) == 0:
            time.sleep(1)
            stream_list = consumer.get_stream_list()
        last_stream: str = stream_list[-1]["name"]
        stream_metadata: Dict[str, Any] = consumer.get_stream_meta(last_stream)
        event_data: Union[NDArray[numpy.float_], NDArray[numpy.int_]]
        event_metadata: Dict[str, Any]
        while True:
            try:
                event_data, event_metadata = consumer.get_last(
                    group_id=consumer_group_id, stream=last_stream, meta_only=False
                )
                yield _TypeAsapoEvent(
                    event_data, event_metadata, last_stream, stream_metadata
                )
            except (
                asapo_consumer.AsapoEndOfStreamError,
                asapo_consumer.AsapoNoDataError,
            ):
                stream_list = consumer.get_stream_list()
                current_stream = stream_list[-1]["name"]
                if current_stream == last_stream:
                    time.sleep(1)
                else:
                    last_stream = current_stream
                    stream_metadata = consumer.get_stream_meta(last_stream)
                continue

    def initialize_event_handling_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes ASAP::O event handling on the collecting node.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        ASAP::O event handling does not need to be initialized on the collecting node,
        so this function actually does nothing.

        Arguments:

            node_rank: The OM rank of the current node int the OM node pool. The rank
                is an integer that unambiguously identifies the node in the pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        pass

    def initialize_event_handling_on_processing_node(
        self, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes ASAP::O event handling on the processing nodes.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node int the OM node pool. The rank
                is an integer that unambiguously identifies the node in the pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
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

    def event_generator(
        self,
        *,
        node_rank: int,
        node_pool_size: int,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Retrieves ASAP::O events.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves data events on the processing nodes. Each retrieved
        event corresponds to a single ASAP::O event.

        Arguments:

            node_rank: The OM rank of the current node int the OM node pool. The rank
                is an integer that unambiguously identifies the node in the pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """

        consumer_group_id: Union[str, None] = self._monitor_params.get_parameter(
            group="data_retrieval_layer",
            parameter="asapo_group_id",
            parameter_type=str,
            required=False,
        )
        if consumer_group_id is None:
            consumer_group_id = "default_om_group"
        consumer: Any = self._initialize_asapo_consumer()

        self._data_sources["timestamp"].initialize_data_source()
        source_name: str
        for source_name in self._required_data_sources:
            self._data_sources[source_name].initialize_data_source()

        data_event: Dict[str, Any] = {}
        data_event["additional_info"] = {}

        source_items: List[str] = self._source.split(":")
        if len(source_items) > 1:
            stream_name: str = ":".join(source_items[1:])
            asapo_events: Generator[
                _TypeAsapoEvent, None, None
            ] = self._offline_event_generator(consumer, consumer_group_id, stream_name)
        else:
            asapo_events = self._online_event_generator(consumer, consumer_group_id)

        asapo_event: _TypeAsapoEvent
        for asapo_event in asapo_events:
            data_event["data"] = asapo_event.event_data
            data_event["metadata"] = asapo_event.event_metadata
            data_event["additional_info"]["stream_name"] = asapo_event.stream_name
            data_event["additional_info"][
                "stream_metadata"
            ] = asapo_event.stream_metadata

            data_event["additional_info"]["timestamp"] = self._data_sources[
                "timestamp"
            ].get_data(event=data_event)

            yield data_event

    def open_event(self, *, event: Dict[str, Any]) -> None:
        """
        Opens an ASAP::O event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        ASAP::O events do not need to be opened, so this function actually does
        nothing.

        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    def close_event(self, *, event: Dict[str, Any]) -> None:
        """
        Closes an ASAP::O event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        ASAP::O events do not need to be closed, so this function actually does
        nothing.

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
        Extracts data from an ASAP::O data event.

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
        Initializes event data retrievals from ASAP::O.

        This function initializes the retrieval of single standalone data events from
        ASAP::O.

        Please see the documentation of the base Protocol class for additional
        information about this method.
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
        self._consumer: Any = self._initialize_asapo_consumer()

        self._data_sources["timestamp"].initialize_data_source()
        source_name: str
        for source_name in self._required_data_sources:
            self._data_sources[source_name].initialize_data_source()

    def retrieve_event_data(self, event_id: str) -> Dict[str, Any]:
        """
        Retrieves all data related to the requested event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves all data related to the event specified by the provided
        identifier. An ASAP::O event identifier corresponds to the ASAP::O stream name
        and the ID of the ASAP::O event within the stream, separated by the "//"
        symbol.

        Arguments:

            event_id: A string that uniquely identifies a data event.

        Returns:

            All data related to the requested event.
        """
        event_id_parts: List[str] = event_id.split("//")
        stream: str = event_id_parts[0].strip()
        asapo_event_id: int = int(event_id_parts[1])

        event_data: Union[NDArray[numpy.float_], NDArray[numpy.int_]]
        event_metadata: Dict[str, Any]
        event_data, event_metadata = self._consumer.get_by_id(
            asapo_event_id,
            stream=stream,
            meta_only=False,
        )
        stream_metadata: Dict[str, Any] = self._consumer.get_stream_meta(stream)

        data_event: Dict[str, Any] = {}
        data_event["data"] = event_data
        data_event["metadata"] = event_metadata
        data_event["additional_info"] = {
            "stream_metadata": stream_metadata,
            "stream_name": stream,
        }

        # Recovers the timestamp from the ASAP::O event (as seconds from the Epoch)
        # and stores it in the event dictionary.
        data_event["additional_info"]["timestamp"] = self._data_sources[
            "timestamp"
        ].get_data(event=data_event)

        return self.extract_data(event=data_event)
