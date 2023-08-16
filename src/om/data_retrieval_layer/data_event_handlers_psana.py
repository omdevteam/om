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
Handling of psana-based data events.

This module contains Data Event Handler classes that manipulate events originating from
the psana software framework (used at the LCLS facility).
"""
import sys
from typing import Any, Dict, Generator, List

import numpy

from om.lib.exceptions import (
    OmDataExtractionError,
    OmMissingDataEventError,
    OmMissingDependencyError,
)
from om.lib.layer_management import filter_data_sources
from om.lib.parameters import MonitorParameters
from om.lib.rich_console import console, get_current_timestamp
from om.protocols.data_retrieval_layer import (
    OmDataEventHandlerProtocol,
    OmDataSourceProtocol,
)

try:
    import psana  # type: ignore
except ImportError:
    raise OmMissingDependencyError(
        "The following required module cannot be imported: psana"
    )


def _psana_offline_event_generator(
    *, psana_source: Any, node_rank: int, mpi_pool_size: int
) -> Any:
    # Computes how many events the current processing node should process. Splits the
    # events as equally as possible amongst the processing nodes. If the number of
    # events cannot be exactly divided by the number of processing nodes, an additional
    # processing node is assigned the residual events.
    run: Any
    for run in psana_source.runs():
        times: Any = run.times()
        num_events_curr_node: int = int(
            numpy.ceil(len(times) / float(mpi_pool_size - 1))
        )
        events_curr_node: Any = times[
            (node_rank - 1) * num_events_curr_node : node_rank * num_events_curr_node
        ]
        evt: Any
        for evt in events_curr_node:
            yield run.event(evt)


class PsanaDataEventHandler(OmDataEventHandlerProtocol):
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

            monitor_parameters: An object storing OM's configuration parameters.
        """

        self._source: str = source
        self._monitor_params: MonitorParameters = monitor_parameters
        self._data_sources: Dict[str, OmDataSourceProtocol] = data_sources

    def _initialize_psana_data_source(self) -> Any:
        # This private method contains all the common psana initialization code needed
        # by other methods of the class

        # If the psana calibration directory is provided in the configuration file, it
        # is added as an option to psana before the DataSource is set.
        psana_calib_dir: str = self._monitor_params.get_parameter(
            group="data_retrieval_layer",
            parameter="psana_calibration_directory",
            parameter_type=str,
        )
        if psana_calib_dir is not None:
            psana.setOption("psana.calib-dir", psana_calib_dir)
        else:
            console.print(
                f"{get_current_timestamp} OM Warning: Calibration directory not "
                "provided or not found.",
                style="warning",
            )

        psana_source: Any = psana.DataSource(self._source)

        self._data_sources["timestamp"].initialize_data_source()
        source_name: str
        for source_name in self._required_data_sources:
            self._data_sources[source_name].initialize_data_source()

        return psana_source

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
        pass

    def initialize_event_handling_on_processing_node(
        self, node_rank: int, node_pool_size: int
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
        # Detects if data is being read from an online or offline source.
        if "shmem" in self._source:
            offline: bool = False
        else:
            offline = True
        if offline and not self._source[-4:] == ":idx":
            self._source += ":idx"

        psana_source: Any = self._initialize_psana_data_source()

        data_event: Dict[str, Any] = {}
        data_event["additional_info"] = {}

        # Initializes the psana event source and starts retrieving events.
        if offline:
            psana_events: Any = _psana_offline_event_generator(
                psana_source=psana_source,
                node_rank=node_rank,
                mpi_pool_size=node_pool_size,
            )
        else:
            psana_events = psana_source.events()

        psana_event: Any
        for psana_event in psana_events:
            data_event["data"] = psana_event

            # Recovers the timestamp from the psana event (as seconds from the Epoch)
            # and stores it in the event dictionary to be retrieved later.
            data_event["additional_info"]["timestamp"] = self._data_sources[
                "timestamp"
            ].get_data(event=data_event)

            yield data_event

    def open_event(self, *, event: Dict[str, Any]) -> None:
        """
        Opens a psana event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Psana events do not need to be opened, so this function actually does nothing.

        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    def close_event(self, *, event: Dict[str, Any]) -> None:
        """
        Closes a psana event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Psana events do not need to be closed, so this function actually does nothing.

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
        Initializes event data retrievals from psana.

        This function initializes the retrieval of single standalone data events from
        psana.

        Please see the documentation of the base Protocol class for additional
        information about this method.
        """
        if self._source[-4:] != ":idx":
            self._source += ":idx"

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

        psana_source: Any = self._initialize_psana_data_source()
        self._run = next(psana_source.runs())

    def retrieve_event_data(self, event_id: str) -> Dict[str, Any]:
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
        event_id_parts: List[str] = event_id.split("-")
        evt_id_timestamp: int = int(event_id_parts[0])
        evt_id_timestamp_ns: int = int(event_id_parts[1])
        evt_id_fiducials: int = int(event_id_parts[2])
        event_time: Any = psana.EventTime(  # pyright: ignore[reportGeneralTypeIssues]
            int((evt_id_timestamp << 32) | evt_id_timestamp_ns), evt_id_fiducials
        )
        retrieved_event: Any = self._run.event(event_time)
        if retrieved_event is None:
            raise OmMissingDataEventError(
                f"Data event {event_id} cannot be retrieved from the data event source"
            )
        data_event: Dict[str, Any] = {}
        data_event["additional_info"] = {}
        data_event["data"] = retrieved_event

        # Recovers the timestamp from the psana event (as seconds from the Epoch)
        # and stores it in the event dictionary.
        data_event["additional_info"]["timestamp"] = self._data_sources[
            "timestamp"
        ].get_data(event=data_event)

        return self.extract_data(event=data_event)
