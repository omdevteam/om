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
Handling of data events from a ZMQ stream.

This module contains Data Event Handler classes that deal with events retrieved from a
a ZMQ stream.
"""
import sys
from typing import Any, Dict, Generator, List, Tuple

import zmq  # type: ignore

from om.data_retrieval_layer import base as drl_base
from om.utils import exceptions, parameters


class Jungfrau1MZmqDataEventHandler(drl_base.OmDataEventHandler):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        source: str,
        data_sources: Dict[str, drl_base.OmDataSource],
        monitor_parameters: parameters.MonitorParams,
    ) -> None:
        """
        Data Event Handler for Jungfrau 1M's ZMQ stream.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class handles data events recovered from a ZMQ stream generated by a
        Jungfrau 1M detector.

        * For this Event Handler, an event corresponds to all the information
          associated with an individual detector frame (the content of a single
          ZMQ message).

        * The source string required by this Data Event Handler is the URL (in
          ZeroMQ format) where the Jungfrau 1M detector broadcasts its data stream.

        Arguments:

            source: A string describing the data event source.

            data_sources: A dictionary containing a set of Data Sources.

                * Each dictionary key must define the name of a data source.

                * The corresponding dictionary value must store an instance of the
                  corresponding
                  [Data Source][om.data_retrieval_layer.base.OmDataSource] class.

            monitor_parameters: A [MonitorParams][om.utils.parameters.MonitorParams]
        """
        self._source: str = source
        self._monitor_params: parameters.MonitorParams = monitor_parameters
        self._data_sources: Dict[str, drl_base.OmDataSource] = data_sources

    def initialize_event_handling_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes Jungfrau 1M ZMQ event handling on the collecting node.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        The Jungfrau 1M ZMQ data stream does not need to be initialized on the
        collecting node, so this function actually does nothing.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        pass

    def initialize_event_handling_on_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes Jungfrau 1M ZMQ event handling on the processing nodes.

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

        self._required_data_sources = drl_base.filter_data_sources(
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
        Retrieves Jungfrau 1M events from a ZMQ stream.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves events for processing (each event corresponds to the
        content of an individual ZMQ message, which stores a single detector frame
        with all the associated data). The events are retrieved from a ZMQ data stream,
        and the server broadcasting the stream takes care of distributing the events
        across all processing nodes.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        url: str = self._source
        zmq_context: Any = zmq.Context()
        print(f"Node {node_rank} connecting to {url}")
        zmq_socket: Any = zmq_context.socket(zmq.PULL)
        zmq_socket.setsockopt(zmq.CONFLATE, 1)
        try:
            zmq_socket.connect(url)
        except zmq.error.ZMQError as exc:
            raise RuntimeError(
                "The format of the provided URL is not valid. The URL must be in "
                "the format tcp://hostname:port or in the format "
                "ipc:///path/to/socket, and in the latter case the user must have the "
                "correct permissions to access the socket."
            ) from exc

        self._data_sources["timestamp"].initialize_data_source()
        source_name: str
        for source_name in self._required_data_sources:
            self._data_sources[source_name].initialize_data_source()

        data_event: Dict[str, Any] = {}
        data_event["additional_info"] = {}

        while True:
            msg: Tuple[Dict[str, Any], Dict[str, Any]] = zmq_socket.recv_pyobj()
            data_event["data"] = msg
            data_event["additional_info"]["timestamp"] = self._data_sources[
                "timestamp"
            ].get_data(event=data_event)

            yield data_event

    def open_event(self, *, event: Dict[str, Any]) -> None:
        """
        Opens a Jungfrau 1M ZMQ event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Jungfrau 1M data events retrived from a ZMQ stream do not need to be opened, so
        this function actually does nothing.

        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    def close_event(self, *, event: Dict[str, Any]) -> None:
        """
        Closes a Jungfrau 1M ZMQ event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Jungfrau 1M data events retrieved from a ZMQ stream do not need to be closed,
        so this function actually does nothing.

        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    def get_num_frames_in_event(self, *, event: Dict[str, Any]) -> int:
        """
        Gets the number of frames in a Jungfrau 1M ZMQ event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Each Jungfrau 1M event retrieved from a ZMQ stream stores data associated with
        a single detector frame, so this function always returns 1.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The number of frames in the event.
        """
        return 1

    def extract_data(
        self,
        *,
        event: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extracts data from a Jungfrau 1M ZMQ event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A dictionary storing the extracted data.

            * Each dictionary key identifies a Data Source in the event for which data
              has been retrieved.

            * The corresponding dictionary value stores the data extracted from the
              Data Source for the frame being processed.
        """
        data: Dict[str, Any] = {}
        source_name: str
        data["timestamp"] = event["additional_info"]["timestamp"]
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
