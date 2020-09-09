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

This module contains the abstract classes for the Data Extraction Layer of an OM
monitor parallelization.
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

        The event handler deals with event and event sources, and implements functions
        to initialize the sources, recover events from them, opening and closing event,
        and investigate the event content.

        Arguments:

            monitor_params (:class:`~om.utils.parameters.MonitorParams`): an object
                storing the OM monitor parameters from the configuration file.

            source (str): a string describing the data source.

            additional_info (Dict[str, Any]): Dictionary story any additional
                information needed by the Data Event Handler.
        """
        self._monitor_params: parameters.MonitorParams = monitor_parameters
        self._source: str = source
        self._additional_info: Dict[str, Any] = additional_info

    @abstractproperty
    def data_extraction_funcs(
        self,
    ) -> Dict[str, Callable[[Dict[str, Dict[str, Any]]], Any]]:
        """
        Retrieves Data Extraction Functions for the current Data Handler.

        This functions retrieves the Data Retrieval Functions that are available for
        the current Event Data Handler.

        Returns:

            Dict[str, Callable[[Dict[str, Dict[str, Any]]], Any]]: a dictionary
            storing the implementations of the Data Extraction functions available to
            the current Data Event Handler.

            * Each dictionary key defines the name of a function.

            * The corresponding dictionary value stores the function
              implementation.
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

            node_rank (int): the rank, in the OM pool, of the processing node calling
                the function.

            node_pool_size (int): the total number of nodes in the OM pool, including
                all the processing nodes and the collecting node.
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

            node_rank (int): the rank, in the OM pool, of the processing node calling
                the function.

            node_pool_size (int): the total number of nodes in the OM pool, including
                all the processing nodes and the collecting node.
        """
        pass

    @abstractmethod
    def event_generator(
        self, node_rank: int, node_pool_size: int,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Retrieves events to process.

        This function initializes the retrieval of events on a processing node and
        starts retrieveing the events. The function is a generator and it returns an
        iterator over the events that the calling node must process.

        Arguments:

            node_rank (int): the rank, in the OM pool, of the processing node calling
                the function.

            node_pool_size (int): the total number of nodes in the OM pool, including
                all the processing nodes and the collecting node.

        Yields:

            :class:`~om.utils.Dict[str, Dict[str,Any]]`: a dictionary storing the event
            data.
        """
        pass

    @abstractmethod
    def open_event(self, event: Dict[str, Any]) -> None:
        """
        Opens an event.

        Processes an event in such a way that the data content of the event is
        retrievable by OM (opens files, unpacks binary content, etc.)

        Arguments:

            event (Dict[str, Any]): a dictionary storing the event data.
        """
        pass

    @abstractmethod
    def close_event(self, event: Dict[str, Any]) -> None:
        """
        Closes an event.

        Processes an event in such a way that the event is ready to be discared by OM
            (closes files, frees memory, etc.)

        Arguments:

            event (Dict[str, Any]): a dictionary storing the event data.
        """
        pass

    @abstractmethod
    def get_num_frames_in_event(self, event: Dict[str, Any]) -> int:
        """
        Gets the number of frames in an event.

        Returns the number of detector data frames in a data event.

        Arguments:

            event (Dict[str, Any]): a dictionary storing the event data.

        Returns:

            int: the number of frames in the event.
        """
        pass

    @final
    def extract_data(self, event: Dict[str, Any],) -> Dict[str, Any]:
        """
        Extracts data from an event.

        This function calls in sequence all the Data Extraction functions, passing the
        event to event as input to each of them. The function then returns the
        extracted data.

        Arguments:

            data_extraction_funcs \
(Dict[str, Callable[[Dict[str, Dict[str, Any]]], Any]]):
                a dictionary containing the Data Extraction functions to be called.

                * Each dictionary key must define the name of a function.

                * The corresponding dictionary value must store a function
                  implementation.

        Returns:

            Dict[str, Any]: a dictionary storing the values returned by the Data
            Extraction functions.

            * Each dictionary key identifies the Data Extraction function used to
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
    Filters the list of data extraction functions based on the required data.

    This function requires as input a dictionary storing all the data extraction
    functions supported by the Data Event Handler. It returns a smaller dictionary
    containing only a subset of functions based on data required by the monitor.

    Arguments:

        data_extraction_funcs (Dict[str, Callable[[Dict[str, Dict[str,Any]]], Any]]):
            a dictionary containing the Data Extraction functions supported by the
            Data Event Handler.

            * Each dictionary key must define the name of a function.

            * The corresponding dictionary value must store a function implementation.

        required_data: (List[str]): a list of data items required by the monitor, used
            to select the required Data Extraction functions.
    """
    required_data_extraction_funcs: Dict[
        str, Callable[[Dict[str, Dict[str, Any]]], Any]
    ] = ({})
    func_name: str
    for func_name in required_data:
        try:
            required_data_extraction_funcs[func_name] = data_extraction_funcs[func_name]
        except AttributeError as exc:
            raise exceptions.OmMissingDataExtractionFunctionError(
                "Data extraction function {0} not defined".format(func_name)
            ) from exc

    return required_data_extraction_funcs
