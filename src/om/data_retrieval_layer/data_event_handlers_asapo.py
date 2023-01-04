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
Handling of ASAP::O-based data events.

This module contains Data Event Handler classes that manipulate events originating from
the ASAP::O software framework (used at the PETRA III facility).
"""
import sys
import time
from typing import Any, Dict, Generator, List, Union, NamedTuple

import numpy
from numpy.typing import NDArray

from om.abcs import data_retrieval_layer as drl_abcs
from om.utils import exceptions, parameters

try:
    import asapo_consumer  # type: ignore
except ImportError:
    raise exceptions.OmMissingDependencyError(
        "The following required module cannot be imported: asapo_consumer"
    )


class _TypeAsapoEvent(NamedTuple):
    # This named tuple is used internally to store ASAPO event data, metadata and
    # corresponding ASAPO stream information.
    event_data: Union[NDArray[numpy.float_], NDArray[numpy.int_]]
    event_metadata: Dict[str, Any]
    stream_name: str
    stream_metadata: Dict[str, Any]


class AsapoDataEventHandler(drl_abcs.OmDataEventHandlerBase):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        source: str,
        data_sources: Dict[str, drl_abcs.OmDataSourceBase],
        monitor_parameters: parameters.MonitorParams,
    ) -> None:
        """
        Data Event Handler for ASAP::O events.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class handles data events retrieved from the ASAP::O software framework at
        the PETRA III facility.

        * For this Event Handler, a data event corresponds to the content of an
          individual ASAP::O event.

        * The source string required by this Data Event Handler is either just the ID
          of the current beamtime for online data retrieval, or the ID of a beamtime
          and the name of an ASAP::O stream name separated by a colon for offline
          data retrieval.

        Arguments:

            source: A string describing the data event source.

            data_sources: A dictionary containing a set of Data Sources.

                * Each dictionary key must define the name of a data source.

                * The corresponding dictionary value must store the instance of the
                  [Data Source class][om.abcs.data_retrieval_layer.OmDataSourceBase]
                  that describes the source.

            monitor_parameters: An object storing OM's configuration parameters.
        """

        self._source: str = source
        self._monitor_params: parameters.MonitorParams = monitor_parameters
        self._data_sources: Dict[str, drl_abcs.OmDataSourceBase] = data_sources

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
        stream_exists: bool = False
        while not stream_exists:
            try:
                stream_metadata: Dict[str, Any] = consumer.get_stream_meta(stream_name)
                stream_exists = True
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
                pass
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

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        ASAP::O event sources do not need to be initialized on the collecting node, so
        this function actually does nothing.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        pass

    def initialize_event_handling_on_processing_node(
        self, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes ASAPO event handling on the processing nodes.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        required_data: List[str] = self._monitor_params.get_parameter(
            group="data_retrieval_layer",
            parameter="required_data",
            parameter_type=list,
            required=True,
        )

        self._required_data_sources = drl_abcs.filter_data_sources(
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

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves events for processing (each event corresponds to a
        single ASAP::O event).

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

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

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        ASAP::O events do not need to be opened, so this function actually does nothing.

        Arguments:

            event: a dictionary storing the event data.
        """
        pass

    def close_event(self, *, event: Dict[str, Any]) -> None:
        """
        Closes an ASAP::O event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        ASAP::O events do not need to be closed, so this function actually does
        nothing.

        Arguments:

            event: a dictionary storing the event data.
        """
        pass

    def get_num_frames_in_event(self, *, event: Dict[str, Any]) -> int:
        """
        Gets the number of frames in an ASAP::O event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Each ASAPO event stores data associated with a single detector frame, so this
        function always returns 1.

        Arguments:

            event: a dictionary storing the event data.

        Returns:

            int: the number of frames in the event.
        """
        return 1

    def extract_data(
        self,
        *,
        event: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extracts data from an ASAP::O data event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A dictionary storing the extracted data.

                * Each dictionary key identifies a Data Source in the event for which
                data has been retrieved.

                * The corresponding dictionary value stores the data extracted from the
                Data Source for the frame being processed.
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
                    raise exceptions.OmDataExtractionError(
                        f"OM Warning: Cannot interpret {source_name} event data due "
                        f"to the following error: {exc_type.__name__}: {exc_value}"
                    )

        return data

    def initialize_frame_data_retrieval(self) -> None:
        """
        Initializes frame data retrieval from ASAP::O.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the retrieval of a single standalone detector data
        frame, with all its related information, from ASAP::O.
        """
        required_data: List[str] = self._monitor_params.get_parameter(
            group="data_retrieval_layer",
            parameter="required_data",
            parameter_type=list,
            required=True,
        )
        self._required_data_sources = drl_abcs.filter_data_sources(
            data_sources=self._data_sources,
            required_data=required_data,
        )
        self._consumer: Any = self._initialize_asapo_consumer()

        self._data_sources["timestamp"].initialize_data_source()
        source_name: str
        for source_name in self._required_data_sources:
            self._data_sources[source_name].initialize_data_source()

    def retrieve_frame_data(self, event_id: str, frame_id: str) -> Dict[str, Any]:
        """
        Retrieves from ASAP::O all data related to the requested detector frame.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves frame data,  from the event specified by the provided
        psana unique event identifier. An ASAP::O event identifier corresponds to the name of an ASAP::O stream and
        the ID of an ASAP::O event within the stream separated by the "//" symbol.
        Since ASAP::O data events are based around single detector frames, the unique
        frame identifier must always be the string "0".

        Arguments:

            event_id: a string that uniquely identifies a data event.

            frame_id: a string that identifies a particular frame within the data
                event.

        Returns:

            All data related to the requested detector data frame.
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

        # Recovers the timestamp from the ASAPO event (as seconds from the Epoch)
        # and stores it in the event dictionary.
        data_event["additional_info"]["timestamp"] = self._data_sources[
            "timestamp"
        ].get_data(event=data_event)

        return self.extract_data(event=data_event)
