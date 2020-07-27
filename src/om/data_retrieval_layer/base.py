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
from __future__ import absolute_import, division, print_function

import sys
from abc import ABCMeta, abstractmethod
from typing import Any, Dict, Generator

from future.utils import iteritems  # type: ignore
from typing_extensions import final

from om.utils import exceptions, parameters


ABC = ABCMeta("ABC", (object,), {"__slots__": ()})


class OmDataEventHandler(ABC):  # type: ignore
    """
    See documentation of the __init__ function.
    """

    def __init__(
        self, monitor_parameters,
    ):
        # type: (parameters.MonitorParams) -> None
        """
        The base class for an OM DataEventHandler.

        The event handler deals with event and event sources, and implements functions
        to initialize the sources, recover events from them, opening and closing event,
        and investigate the event content.

        Arguments:

            monitor_params (:class:`~om.utils.parameters.MonitorParams`): an object
                storing the OM monitor parameters from the configuration file.
        """
        self._monitor_params = monitor_parameters

    @abstractmethod
    def initialize_event_source(self, source, node_pool_size):
        # type: (str, int) -> Any
        """
        Initializes the event source.

        This function must be called on the collecting node before the
        :func:`event_generator` function is called on the processing nodes, and
        performs all the operation needed to initialize the event source (announcement
        of OM, etc.)

        Arguments:

            source (str): a psana-style DataSource string.

            node_pool_size (int): the total number of nodes in the OM pool, including
                all the processing nodes and the collecting node.
        """
        pass

    @abstractmethod
    def event_generator(
        self,
        source,  # type: str
        node_rank,  # type: int
        node_pool_size,  # type: int
    ):
        # type: (...) -> Generator[Dict[str, Any], None, None]
        """
        Retrieves events to process.

        This function must be called on each processing node after the
        :func:`initialize_event_source` function has been called on the collecting node.
        The function is a generator and it returns an iterator over the events that the
        calling node must process.

        Arguments:

            source (str): a string describing the data source. The exact format of the
                string depends on the specific Data Recovery Layer currently being
                used. See the documentation of the relevant 'initialize_event_source'
                function.

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
    def open_event(self, event):
        # type: (Dict[str, Any]) -> None
        """
        Opens an event.

        Processes an event in such a way that the data content of the event is
        retrievable by OM (opens files, unpacks binary content, etc.)

        Arguments:

            event (Dict[str, Any]): a dictionary storing the event data.
        """
        del event

    @abstractmethod
    def close_event(self, event):
        # type: (Dict[str, Any]) -> None
        """
        Closes an event.

        Processes an event in such a way that the event is ready to be discared by OM
            (closes files, frees memory, etc.)

        Arguments:

            event (Dict[str, Any]): a dictionary storing the event data.
        """
        del event

    @abstractmethod
    def get_num_frames_in_event(self, event):
        # type: (Dict[str,Any]) -> int
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
    def extract_data(
        self, event,  # type: Dict[str, Any]
    ):
        # type: (...) -> Dict[str, Any]
        """
        Extracts data from an event.

        This function calls in sequence all the Data Extraction functions, passing the
        event to event as input to each of them. The function then returns the
        extracted data.

        Arguments:

            data_extraction_funcs (Dict[str, Callable[[~om.utils.Dict[str,\
Dict[str,Any]]], Any]]): a dictionary containing Data Extraction
                functions to be attached to the class instance being created.

                * Each dictionary value must store a function implementation.

                * The corresponding dictionary key will define the name with which the
                  function will be attached to the class instance.

        Returns:

            Dict[str, Any]: a dictionary storing the values returned by the Data
            Extraction functions.

            * Each dictionary key identifies a function attached to the event.

            * The corresponding dictionary value stores the data returned by the
              function.
        """
        data = {}  # type: Dict[str, Any]
        for f_name, func in iteritems(event["data_extraction_funcs"]):
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
