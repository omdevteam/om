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
Data Extraction Layer's base classes.

This module contains base abstract classes for OM's Data Extraction Layer.
"""
from abc import ABC, abstractmethod, abstractproperty
from typing import Any, Dict, Generator, List

from om.utils import exceptions, parameters


class OmDataEventHandler(ABC):
    """
    See documentation of the `__init__` function.

    Base class: `ABC`
    """

    def __init__(
        self,
        *,
        source: str,
        monitor_parameters: parameters.MonitorParams,
        additional_info: Dict[str, Any] = {},
    ) -> None:
        """
        Base class for an OM's Data Event Handler.

        Data Event Handlers are classes that deal with data events and their sources
        in OM. They have methods to initialize sources, retrieve events from them,
        open and close events, and examine their content.

        This class is the base abstract class from which every Data Event Handler
        should inherit. All its methods are abstract. Each derived class must provide
        its own specific implementations tailored to a particular facility, detector or
        software framework.

        Arguments:

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file..

            source: A string describing the data source.

            additional_info: A dictionary storing any additional information needed for
                the initialization of the Data Event Handler.
        """
        pass

    @abstractmethod
    def initialize_event_handling_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> Any:
        """
        Initializes event handling on the collecting node.

        This function is called on the collecting node when OM starts, and initializes
        the data event handling on the node.

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
        self, *, node_rank: int, node_pool_size: int
    ) -> Any:
        """
        Initializes event handling on a processing node.

        This function is called on a processing node when OM starts and initializes the
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
        *,
        node_rank: int,
        node_pool_size: int,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Retrieves events from the source.

        This function retrieves data events from a source. OM calls this function on
        each processing node when it starts to retrieve events. The function is a
        generator and it returns an iterator over the events that the calling node
        should process.

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
    def open_event(self, *, event: Dict[str, Any]) -> None:
        """
        Opens an event.

        This function processes a data event in such a way that the content of the
        event is retrievable by OM. OM calls this function on each processing node
        before the [extract_data]
        [om.data_retrieval_layer.base.OmDataEventHandler.extract_data] function.

        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    @abstractmethod
    def close_event(self, *, event: Dict[str, Any]) -> None:
        """
        Closes an event.

        This function processes a data event in such a way that the event is ready to
        be discared by OM. OM calls this function on each processing node after the
        [extract_data][om.data_retrieval_layer.base.OmDataEventHandler.extract_data]
        function.

        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    @abstractmethod
    def get_num_frames_in_event(self, *, event: Dict[str, Any]) -> int:
        """
        Gets the number of detector frames in an event.

        This function returns the number of detector frames stored in a data event. OM
        calls it after each data event is retrieved to determine how many frames it
        contains.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The number of frames in the event.
        """
        pass

    @abstractmethod
    def extract_data(
        self,
        *,
        event: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extracts data from a frame stored in an event.

        This function extracts data from a frame stored in an event. It works by
        calling, one after the other, all the required Data Extraction Functions,
        passing the event as input to each of them. The data extracted by each function
        is collected and returned to the caller.

        For data events with multiple frames, OM calls this function on each frame in
        the event in sequence. The function always passes the full event to each Data
        Extraction Function at every call: an internal flag keeps track of which frame
        should be processed in for each particular call.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A dictionary storing the extracted data.

            * Each dictionary key identifies the Data Source from which the data has
              been retrieved.

            * The corresponding dictionary value stores the data that was extracted
              from the Data Source for the provided event.
        """
        pass


class OmDataSource(ABC):
    """
    See documentation of the `__init__` function.

    Base class: `ABC`
    """

    @abstractmethod
    def __init__(
        self,
        *,
        data_source_name: str,
        monitor_parameters: parameters.MonitorParams,
    ) -> None:
        """
        Base class for an OM's Data Source.

        Data sources are classes that perform all the operations needed in OM to
        retrieve data form any sensor or detector, from simple diodes, to wave
        digitizers, to big x-ray or optical detectors.

        Data Source classes always provide one method that prepares OM to read data
        from the sensor, and another that retrieves data for each event.

        This class is the base abstract class from which every Data Source class should
        inherit. All its methods are abstract. Each derived class must provide its own
        detector- or sensor-specific implementations.

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, for communication with the user or retrieval of
                initialization parameters.

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.
        """
        pass

    @abstractmethod
    def initialize_data_source(
        self,
    ) -> None:
        """
        Data source initialization.

        This method prepares OM to retrieve data from the sensor or detector, after
        reading all the necessary configuration parameters and retrieving any
        additional required external data.
        """

    @abstractmethod
    def get_data(
        self,
        *,
        event: Dict[str, Any],
    ) -> Any:  # noqa: F821
        """
        Data Retrieval.

        This function retrieves all the data generated by the sensor or detector that
        are related to the provided event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            Data from the sensor.
        """
        pass


class OmDataRetrieval(ABC):
    """
    See documentation of the `__init__` function.

    Base class: `ABC`
    """

    @abstractmethod
    def __init__(
        self,
        *,
        source: str,
        monitor_parameters: parameters.MonitorParams,
    ) -> None:
        """
        Base class for an OM's Data Retrieval.

        Data Retrieval classes implement the data retrieval layer for a specific
        beamline, experiment or facility.

        At initialization, a Data Retrieval class must be provided with a set of
        data sources, from which data will be retrieved, and with a Data Event Handler,
        which will determine how data events are handled and manipulated.

        This class is the base abstract class from which every Data Retrieval class
        should inherit. All its methods are abstract. Each derived class must provide
        its own implementations tailored to a specific beamline, facility or
        experiment.

        Arguments:

            source_name: the name of the current data source, used to identify the
                source when needed (communication with the user, retrieval of
                initialization parameters.

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.
        """
        pass

    @abstractproperty
    def data_event_handler(self) -> OmDataEventHandler:
        """
        Retrieves the Data Event Handler for the current Data Retrieval layer.

        Returns:

            The Data Event Handler currently associated with the Data Retrieval Layer.
        """
        pass


def filter_data_sources(
    *,
    data_sources: Dict[str, OmDataSource],
    required_data: List[str],
) -> List[str]:
    """
    Selects only the data sources needed by the required data.

    This function filters the list of all Data Sources associated with a
    [`OmDataRetrieval`][om.data_retrieval_layer.base.OmDataSource] class down to only
    the entries need to retrieve the required data.

    Arguments:

        data_sources: A list containing the names of all data source available for the
            Data Retrieval class.

        required_data: A list of required data items.

    Returns:

        A list Data Source names containing only the required Data Sources.
    """
    required_data_sources: List[str] = []
    entry: str
    for entry in required_data:
        if entry == "timestamp":
            continue
        if entry in data_sources:
            required_data_sources.append(entry)
        else:
            raise exceptions.OmMissingDataExtractionFunctionError(
                f"Data source {entry} is not defined"
            )
    return required_data_sources
