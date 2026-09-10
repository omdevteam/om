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
Handling of psana2-based data events.

This module contains Data Event Handler classes that manipulate events originating from
the psana2 software framework (used at the LCLS facility).
"""

import sys
from typing import Any, ContextManager, Generator, Literal, cast

from om.data_retrieval_layer.data_event_handlers_common import (
    instantiate_data_sources,
)
from om.lib.exceptions import (
    OmDataExtractionError,
    OmMissingDependencyError,
)
from om.lib.logging import log_error_and_exit
from om.lib.parameters import DataRetrievalLayerParameters
from om.lib.protocols import OmDataEventHandlerProtocol, OmDataSourceProtocol

try:
    import _xtcpp  # type: ignore[import-untyped]
except ImportError:
    raise OmMissingDependencyError(
        "The following required module cannot be imported: _xtcpp"
    )


class XtcppDataEventHandler(OmDataEventHandlerProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        source: str,
        parameters: DataRetrievalLayerParameters,
    ) -> None:
        """
        Data Event Handler for psana events.

        This class handles data events retrieved from the psana software framework at
        the LCLS facility.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        * For this Event Handler, a data event corresponds to the content of an
          individual psana event.

        * The source string required by this Data Event Handler is a string of the type
          used by psana to identify specific runs, experiments, or live data streams.

        Arguments:

            source: A string describing the data event source.

            data_sources: A dictionary containing a set of Data Source class instances.

                * Each dictionary key must define the name of a data source.

                * The corresponding dictionary value must store the instance of the
                  [Data Source class][om.protocols.data_retrieval_layer.OmDataSourceProtocol]  # noqa: E501
                  that describes the source.

            parameters: An object storing OM's configuration parameters.
        """
        self._data_retrieval_parameters: DataRetrievalLayerParameters = parameters

        self._source_dict: dict[str, str | int] = {}
        source_items: list[str] = source.split(",")
        item: str
        for item in source_items:
            if item.startswith("exp="):
                self._source_dict["exp"] = item.split("exp=")[1].strip().lstrip()
            elif item.startswith("run="):
                self._source_dict["run"] = int(item.split("run=")[1].strip().lstrip())
            elif item.startswith("events_per_read="):
                self._source_dict["events_per_read"] = int(
                    item.split("events_per_read=")[1].strip().lstrip()
                )
            else:
                log_error_and_exit(
                    "Part of the source string for xtcpp cannot be parsed: {item}"
                )

    def designated_collector_rank(self) -> Literal["first", "last"]:
        return "first"

    def skip_rank_finalization(self) -> bool:
        """ """
        return False

    def initialize_event_handling_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes psana event handling on the collecting node.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Psana event handling does not need to be initialized on the collecting node, so
        this function actually does nothing.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        self._xtcpp_data_source: Generator[Any] = cast(
            Generator[Any],
            _xtcpp.MPIDataSource(  # pyright: ignore[reportUnknownMemberType]
                self._source_dict["exp"], self._source_dict["run"], 40000
            ),
        )

        self._instantiated_data_sources: dict[str, OmDataSourceProtocol] = (
            instantiate_data_sources(
                data_sources=self._data_retrieval_parameters.data_sources,
                modules=["data_sources_xtcpp", "data_sources_common"],
                additional_info={"data_source": self._xtcpp_data_source},
            )
        )

    def initialize_event_handling_on_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes psana event handling on the processing nodes.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Psana event handling does not need to be initialized on the processing nodes,
        so this function actually does nothing.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        self._xtcpp_data_source: Generator[Any] = cast(
            Generator[Any],
            _xtcpp.MPIDataSource(  # pyright: ignore[reportUnknownMemberType]
                self._source_dict["exp"], self._source_dict["run"], 40000
            ),
        )

        self._instantiated_data_sources: dict[str, OmDataSourceProtocol] = (
            instantiate_data_sources(
                data_sources=self._data_retrieval_parameters.data_sources,
                modules=["data_sources_xtcpp", "data_sources_common"],
                additional_info={"data_source": self._xtcpp_data_source},
            )
        )

    def event_generator(
        self,
        *,
        node_rank: int,
        node_pool_size: int,
    ) -> Generator[dict[str, Any], None, None]:
        """
        Retrieves psana events.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves data events on the processing nodes. Each retrieved
        event corresponds to a single psana event.

        When OM retrieves real-time data at the LCLS facility, each processing node
        receives data from a shared memory server operated by the facility, running on
        the same machine as the node. The server takes care of distributing the data
        events. When instead OM uses the psana framework to read offline data, this
        function tries to distribute the events as evenly as possible across all the
        processing nodes, with each node ideally processing the same number of events.
        If the total number of events cannot be split evenly, the last last node
        processes fewer events than the others.

        Arguments:

            node_rank: The OM rank of the current node int the OM node pool. The rank
                is an integer that unambiguously identifies the node in the pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        # TODO: Check types of Generator
        data_event: dict[str, Any] = {}
        data_event["additional_info"] = {}

        xtcpp_event: Any
        # for xtcpp_event in self._xtcpp_data_source:
        for xtcpp_event in range(40000):
            data_event["data"] = xtcpp_event
            data_event["additional_info"]["timestamp"] = (
                self._instantiated_data_sources["timestamp"].get_data(event=data_event)
            )

            yield data_event

    def extract_data(
        self,
        *,
        event: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Extracts data from a psana data event.

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
        data: dict[str, Any] = {}
        data["timestamp"] = event["additional_info"]["timestamp"]
        source_name: str

        for source_name in self._instantiated_data_sources:
            # data[source_name] = self._instantiated_data_sources[source_name].get_data(
            #     event=event
            # )
            try:
                data[source_name] = self._instantiated_data_sources[
                    source_name
                ].get_data(event=event)
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
        Initializes event data retrievals from psana.

        This function initializes the retrieval of single standalone data events from
        psana.

        Please see the documentation of the base Protocol class for additional
        information about this method.
        """
        raise NotImplementedError

    def retrieve_event_data(self, event_id: str) -> dict[str, Any]:
        """
        Retrieves all data related to the requested event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves all data related to the event specified by the provided
        identifier. The psana unique event identifier is a string combining psana's
        timestamp and fiducial information, with the following format:
        `{timestamp: seconds}-{timestamp: nanoseconds}-{fiducials}`.

        Arguments:

            event_id: A string that uniquely identifies a data event.

        Returns:

            All data related to the requested event.

        Raises:

            OmMissingDataEventError: Raised when an event cannot be retrieved from the
                data source.
        """
        raise NotImplementedError
