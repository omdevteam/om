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
Data extraction layer base classes.

This module contains base abstract classes for the Data Extraction Layer of OM.
"""
import sys
from abc import ABC, abstractmethod, abstractproperty
from typing import Any, Callable, Dict, Generator, List

from typing_extensions import final

from om.utils import exceptions, parameters


class OmDataEventHandler(ABC):
    """
    See documentation of the __init__ function.
    """

    def __init__(
        self,
        source: str,
        monitor_parameters: parameters.MonitorParams,
        additional_info: Dict[str, Any] = {},
    ) -> None:
        """
        The base class for an OM DataEventHandler.

        DataEventHandlers deal with data events and data event sources, and implement
        functions to initialize the sources, recover events from them, open and close
        events, and examine their content.

        Arguments:

            monitor_parameters: An object storing the OM monitor parameters from the
                configuration file.

            source: A string describing the data source.

            additional_info: A dictionary storing any additional information needed for
                the initialization of the DataEventHandler.
        """
        self._monitor_params: parameters.MonitorParams = monitor_parameters
        self._source: str = source
        self._additional_info: Dict[str, Any] = additional_info

    @abstractproperty
    def data_extraction_funcs(
        self,
    ) -> Dict[str, Callable[[Dict[str, Dict[str, Any]]], Any]]:
        """
        Data Extraction Functions for the current DataEventHandler.

        This property can be used to retrieve the Data Extractions Functions that are
        available to the current DataEventHandler.

        Returns:

            A dictionary storing the implementations of the Data Extraction functions
            available to the current DataEventHandler.

            * Each dictionary key defines the name of a function.

            * The corresponding dictionary value stores the function implementation.
        """
        pass

    @abstractmethod
    def initialize_event_handling_on_collecting_node(
        self, node_rank: int, node_pool_size: int
    ) -> Any:
        """
        Initializes event handling on the collecting node.

        This function is called on the collecting node at start up and initializes the
        data event handling on the node.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        Returns:

            An optional initialization token.
        """
        pass

    @abstractmethod
    def initialize_event_handling_on_processing_node(
        self, node_rank: int, node_pool_size: int
    ) -> Any:
        """
        Initializes event handling on the processing node.

        This function is called on the processing node at start up and initializes the
        data event handling on the node.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        Returns:

            An optional initialization token.
        """
        pass

    @abstractmethod
    def event_generator(
        self,
        node_rank: int,
        node_pool_size: int,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Retrieves events to process.

        This function initializes the retrieval of data events on a processing node and
        starts retrieving the events. The function is a generator and it returns an
        iterator over the data events that the calling node should process.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including
                all the processing nodes and the collecting node.

        Yields:

            A dictionary storing the data for the current event.
        """
        pass

    @abstractmethod
    def open_event(self, event: Dict[str, Any]) -> None:
        """
        Opens an event.

        This function processes an event in such a way that the content of the event is
        retrievable by OM (opens files, unpacks binary content, etc.)

        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    @abstractmethod
    def close_event(self, event: Dict[str, Any]) -> None:
        """
        Closes an event.

        This function processes an event in such a way that the event is ready to be
        discared by OM (closes files, frees memory, etc.)

        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    @abstractmethod
    def get_num_frames_in_event(self, event: Dict[str, Any]) -> int:
        """
        Gets the number of detector frames in an event.

        This function returns the number of detector frames stored in an event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The number of frames in the event.
        """
        pass

    @final
    def extract_data(
        self,
        event: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extracts data from an event.

        This function calls in sequence all the Data Extraction Functions associated
        with an event, passing the event itself as input to each of them. The function
        then returns the extracted data.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A dictionary storing the values returned by the Data Extraction functions.

            * Each dictionary key identifies the Data Extraction Function used to
              extract the data.

            * The corresponding dictionary value stores the data returned by the
              function.
        """
        data: Dict[str, Any] = {}
        f_name: str
        func: Callable[[Dict[str, Dict[str, Any]]], Any]
        for f_name, func in event["data_extraction_funcs"].items():
            try:
                data[f_name] = func(event)
            # One should never do the following, but it is not possible to anticipate
            # every possible error raised by the facility frameworks.
            except Exception:
                exc_type, exc_value = sys.exc_info()[:2]
                if exc_type is not None:
                    raise exceptions.OmDataExtractionError(
                        "OM Warning: Cannot interpret {0} event data due to the "
                        "following error: {1}: {2}".format(
                            func.__name__, exc_type.__name__, exc_value
                        )
                    )

        return data


def filter_data_extraction_funcs(
    data_extraction_funcs: Dict[str, Callable[[Dict[str, Dict[str, Any]]], Any]],
    required_data: List[str],
) -> Dict[str, Callable[[Dict[str, Dict[str, Any]]], Any]]:
    """
    Filters the list of Data Extraction Functions based on the required data.

    This function takes a dictionary storing a set of Data Extraction Functions
    as input, in addition to a list of required data entries. It returns a smaller
    dictionary containing only the subset of Extraction Functions needed to retrieve
    the required data.

    Arguments:

        data_extraction_funcs: A dictionary containing a set of Data Extraction
            Functions.

            * Each dictionary key must define the name of a function.

            * The corresponding dictionary value must store a function implementation.

        required_data: A list of required data entries, used to select the necessary
            Data Extraction Functions.

    Returns:

        A dictionary containing only the required Data Extraction Functions.

        * Each dictionary key must define the name of a function.

        * The corresponding dictionary value must store a function implementation.
    """
    required_data_extraction_funcs: Dict[
        str, Callable[[Dict[str, Dict[str, Any]]], Any]
    ] = {}
    func_name: str
    for func_name in required_data:
        try:
            required_data_extraction_funcs[func_name] = data_extraction_funcs[func_name]
        except AttributeError as exc:
            raise exceptions.OmMissingDataExtractionFunctionError(
                "Data extraction function {0} not defined".format(func_name)
            ) from exc

    return required_data_extraction_funcs
