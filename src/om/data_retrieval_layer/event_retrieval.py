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
This module contains classes that deals with the retrieval of single standalone events.
"""


from pathlib import Path
from typing import Any, Dict, Generator, List, TextIO, Type

from pydantic import BaseModel, ValidationError

from om.lib.exceptions import OmConfigurationFileSyntaxError, OmInvalidSourceError
from om.lib.layer_management import import_class_from_layer
from om.lib.protocols import (
    OmDataEventHandlerProtocol,
    OmDataRetrievalProtocol,
    OmDataSourceProtocol,
)


class _OmParameters(BaseModel):
    data_retrieval_layer: str


class _MonitorParameters(BaseModel):
    om: _OmParameters
    data_retrieval_layer: Dict[str, Any]


class OmEventDataRetrieval:
    """
    See documentation for the `__init__` function.
    """

    def __init__(self, *, parameters: Dict[str, Any], source: str) -> None:
        """
        Retrieval of single standalone data events.

        This class deals with the retrieval of single standalone data events from a
        data source.

        Arguments:

            monitor_parameters: An object storing OM's configuration parameters.

            source: A string describing the data event source.
        """

        try:
            self._parameters = _MonitorParameters.model_validate(parameters)
        except ValidationError as exception:
            raise OmConfigurationFileSyntaxError(
                "Error parsing OM's configuration parameters: " f"{exception}"
            )

        data_retrieval_layer_class: Type[OmDataRetrievalProtocol] = (
            import_class_from_layer(
                layer_name="data_retrieval_layer",
                class_name=self._parameters.om.data_retrieval_layer,
            )
        )

        data_retrieval_layer: OmDataRetrievalProtocol = data_retrieval_layer_class(
            parameters=parameters["data_retrieval_layer"],
            source=source,
        )

        self._data_event_handler: OmDataEventHandlerProtocol = (
            data_retrieval_layer.get_data_event_handler()
        )

        self._data_event_handler.initialize_event_data_retrieval()

    def retrieve_event_data(self, event_id: str) -> Dict[str, Any]:
        """
        Retrieves all data attached to the requested data event.

        This function retrieves all the information associated with the data event
        specified by the provided identifier. The data is returned in the form of a
        dictionary.

        * Each dictionary key identifies a Data Source in the event for which
          information has been retrieved.

        * The corresponding dictionary values store the data associated with each
          Data Source.

        Arguments:

            event_id: a string that uniquely identifies a data event.

        Returns:

            A dictionary storing all data related the retrieved event.
        """
        return self._data_event_handler.retrieve_event_data(event_id=event_id)


class EventListDataRetrieval(OmDataRetrievalProtocol):
    """
    See documentation for the `__init__` function.
    """

    def __init__(
        self, *, parameters: Dict[str, Any], source: str, event_list_file: Path
    ) -> None:
        """
        Data retrieval from event lists.

        This class implements OM's Data Retrieval Layer for a set of event IDs for a
        certain data retrieval protocol.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        TODO: write documentation.

        Arguments:

            monitor_parameters: An object storing OM's configuration parameters.

            source: A string describing the data event source.

            event_list_file: A string describing the path to the event list file.
        """
        self._data_event_handler: EventListEventHandler = EventListEventHandler(
            source=source,
            event_list_file=event_list_file,
            data_sources={},
            parameters=parameters,
        )

    def get_data_event_handler(self) -> OmDataEventHandlerProtocol:
        """
        Retrieves the Data Event Handler used by the class.

        This function returns the Data Event Handler used by the Data Retrieval class
        to manipulate data events.

        Returns:

            The Data Event Handler used by the Data Retrieval class.
        """
        return self._data_event_handler


class EventListEventHandler(OmDataEventHandlerProtocol):
    """
    See documentation for the `__init__` function.
    """

    def __init__(
        self,
        *,
        source: str,
        parameters: Dict[str, Any],
        data_sources: Dict[str, OmDataSourceProtocol],
        event_list_file: Path,
    ) -> None:
        """
        Data event handler for event list files.

        This class deals with the retrieval of single standalone data events from a
        data source.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        Arguments:

            source: A string describing the data event source.

            event_list_file: A string describing the path to the event list file.

            data_sources: A dictionary containing a set of Data Source class instances.

                * Each dictionary key must define the name of a data source.

                * The corresponding dictionary value must store the instance of the
                  [Data Source class][om.protocols.data_retrieval_layer.OmDataSourceProtocol]  # noqa: E501
                  that describes the source.

            monitor_parameters: An object storing OM's configuration parameters.
        """
        self._source: str = source
        self._event_list_file: Path = event_list_file
        self._monitor_parameters: Dict[str, Any] = parameters

    def initialize_event_handling_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes the event handling on the collecting node.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node int the OM node pool. The rank
                is an integer that unambiguously identifies the node in the pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        pass

    def initialize_event_handling_on_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes the event handling on a processing node.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node int the OM node pool. The rank
                is an integer that unambiguously identifies the node in the pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        self._event_retrieval = OmEventDataRetrieval(
            parameters=self._monitor_parameters,
            source=self._source,
        )
        try:
            fh: TextIO
            with open(self._event_list_file, "r") as fh:
                event_list: List[str] = fh.readlines()
        except (IOError, OSError) as exc:
            raise OmInvalidSourceError(
                f"Error reading the {self._source} event list file."
            ) from exc

        self._events_curr_node: List[str] = event_list[
            (node_rank - 1) :: (node_pool_size - 1)
        ]

    def event_generator(
        self, *, node_rank: int, node_pool_size: int
    ) -> Generator[Dict[str, Any], None, None]:
        """ """

        event_id: str
        for event_id in self._events_curr_node:
            event_id = event_id[:-1]
            yield self._event_retrieval.retrieve_event_data(event_id=event_id)

    def extract_data(
        self,
        *,
        event: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extracts data from an event.

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
        return event

    def initialize_event_data_retrieval(self) -> None:
        """
        Initializes event data retrieval.

        Please see the documentation of the base Protocol class for additional
        information about this method.
        """
        raise NotImplementedError

    def retrieve_event_data(self, event_id: str) -> Dict[str, Any]:
        """
        Retrieves all data related to the requested event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            event_id: A string that uniquely identifies a data event.

        Returns:

            All data related to the requested event.
        """
        raise NotImplementedError
