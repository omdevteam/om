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
Retrieval and handling of data from ZMQ stream.

This module contains Data Event Handlers and Data Retrieval classes that deal with data
retrieved from ZMQ stream.
"""
import zmq
import sys
from typing import Any, Dict, Generator, List, Tuple

from om.data_retrieval_layer import base as drl_base
from om.data_retrieval_layer import data_sources_zmq as ds_zmq
from om.data_retrieval_layer import data_sources_generic as ds_generic
from om.utils import exceptions, parameters


class _Jungfrau1MZmqDataEventHandler(drl_base.OmDataEventHandler):
    """
    See documentation of the `__init__` function.

    Base class: [`OmDataEventHandler`][om.data_retrieval_layer.base.OmDataEventHandler]
    """

    def __init__(
        self,
        *,
        source: str,
        data_sources: Dict[str, drl_base.OmDataSource],
        monitor_parameters: parameters.MonitorParams,
    ) -> None:
        """
        Data Event Handler for events recovered from Jungfrau ZMQ receiver.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class handles data events recovered from the Jungfrau detector ZMQ stream.
        It is a subclass of the
        [`OmDataEventHandler`][om.data_retrieval_layer.base.OmDataEventHandler] base
        class.

        The source string for this Data Event Handler is the URL where Jungfrau ZMQ
        receiver broadcasts the data.

        Arguments:

            source: A string describing the data source.

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.
        """
        self._source: str = source
        self._monitor_params: parameters.MonitorParams = monitor_parameters
        self._data_sources: Dict[str, drl_base.OmDataSource] = data_sources

    def initialize_event_handling_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> Any:
        """
        Initializes Jungfrau 1M ZMQ event handling on the collecting node.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        The Jungfrau 1M ZMQ data source does not need to be initialized on the
        collecting node, so this function actually does nothing.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        Returns:

            An optional initialization token.
        """
        pass

    def initialize_event_handling_on_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> Any:
        """
        Initializes Jungfrau 1M ZMQ event handling on the processing nodes.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        Returns:

            An optional initialization token.
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

        This Data Event Handler retrieved events broadcasted by Jungfrau ZMQ receiver.
        Jungfrau ZMQ receiver takes care of the distributing events between processing
        nodes.

        Each retrieved event contains a single detector frame.

        This generator function yields a dictionary storing the data for the current
        event.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        url: str = self._source
        zmq_context: Any = zmq.Context()
        print("Node {0} connecting to {1}".format(node_rank, url))
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

        data_event: Dict[str, Dict[str, Any]] = {}
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

        Jungfrau 1M ZMQ events do not need to be opened, so this function actually does
        nothing.

        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    def close_event(self, *, event: Dict[str, Any]) -> None:
        """
        Closes a Pilatus single-frame file event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Jungfrau 1M ZMQ events do not need to be closed, so this function actually does
        nothing.
        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    def get_num_frames_in_event(self, *, event: Dict[str, Any]) -> int:
        """
        Gets the number of frames in a Jungfrau 1M ZMQ event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Each Jungfrau 1M ZMQ event stores data associated with a single detector frame,
        so this function always returns 1.

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

            * Each dictionary key identifies the Data Source from which the data has
              been retrieved.

            * The corresponding dictionary value stores the data that was extracted
              from the Data Source for the provided event.
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
                        "to the following error: {exc_type.__name__}: {exc_value}"
                    )

        return data


class Jungfrau1MZmqDataRetrieval(drl_base.OmDataRetrieval):
    """
    See documentation of the `__init__` function.

    Base class: [`OmDataRetrieval`][om.data_retrieval_layer.base.OmDataRetrieval]
    """

    def __init__(self, *, monitor_parameters: parameters.MonitorParams, source: str):
        """
        Data Retrieval for Jungfrau 1M ZMQ stream.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class implements the operations needed to retrieve data from ZMQ messages
        sent by Jungfrau ZMQ receiver.

        This class considers an individual data event as equivalent to the content of a
        ZMQ message sent by Jungfrau ZMQ receiver, which stores data related to a
        single detector frame. Jungfrau ZMQ stream provides detector data, timestamp
        and frame ID for each event. Jungfrau ZMQ stream does not contain any detector
        distance or beam energy information: their values need to be provided to OM
        through its configuration parameters (specifically, the
        `fallback_detector_distance_in_mm` and `fallback_beam_energy_in_eV` entries in
        the `data_retrieval_layer` parameter group). The source string for this Data
        Retrieval class is the URL where Jungfrau ZMQ receiver broadcasts the data.

        Arguments:

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.

            source: A string describing the data source.
        """

        data_sources: Dict[str, drl_base.OmDataSource] = {
            "timestamp": ds_zmq.TimestampJungfrau1MZmq(
                data_source_name="timestamp", monitor_parameters=monitor_parameters
            ),
            "event_id": ds_zmq.EventIdJungfrau1MZmq(
                data_source_name="eventid", monitor_parameters=monitor_parameters
            ),
            "frame_id": ds_generic.FrameIdZero(
                data_source_name="frameid", monitor_parameters=monitor_parameters
            ),
            "detector_data": ds_zmq.Jungfrau1MZmq(
                data_source_name="detector", monitor_parameters=monitor_parameters
            ),
            "beam_energy": ds_generic.FloatEntryFromConfiguration(
                data_source_name="fallback_beam_energy",
                monitor_parameters=monitor_parameters,
            ),
            "detector_distance": ds_generic.FloatEntryFromConfiguration(
                data_source_name="fallback_detector_distance",
                monitor_parameters=monitor_parameters,
            ),
        }

        self._data_event_handler: drl_base.OmDataEventHandler = (
            _Jungfrau1MZmqDataEventHandler(
                source=source,
                monitor_parameters=monitor_parameters,
                data_sources=data_sources,
            )
        )

    @property
    def data_event_handler(self) -> drl_base.OmDataEventHandler:
        return self._data_event_handler
