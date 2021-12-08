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
Retrieval and handling of data from the http/REST interface.

This module contains Data Event Handlers and Data Retrieval classes that deal with data
retrieved from the http/REST interface.
"""
import requests  # type: ignore
import sys
import time

from io import BytesIO
from typing import Any, Dict, Generator, List, Union, Literal, cast

from om.data_retrieval_layer import base as drl_base
from om.data_retrieval_layer import data_sources_http as ds_http
from om.data_retrieval_layer import data_sources_generic as ds_generic
from om.utils import exceptions, parameters


class _Eiger16MHttpDataEventHandler(drl_base.OmDataEventHandler):
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
        Data Event Handler for events recovered from Eiger 16M http/REST interface.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class handles data events recovered from the Eiger 16M http/REST interface.
        It is a subclass of the
        [`OmDataEventHandler`][om.data_retrieval_layer.base.OmDataEventHandler] base
        class.

        The source string for this Data Event Handler is the base URL of the detector
        subsystem: http://<address_of_dcu>/monitor/api/<version>.

        Arguments:

            source: A string describing the data source.

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.
        """
        self._source: str = source
        self._monitor_params: parameters.MonitorParams = monitor_parameters
        self._data_sources: Dict[str, drl_base.OmDataSource] = data_sources

    def _check_detector_monitor_mode(
        self, count_down: int = 12, wait_time: int = 5
    ) -> Union[Literal["enabled", "disabled"], None]:
        # Checks if the detector is available. If not, keeps retrying for 1 minute.
        # If detector is available, returns the state of the detector monitor mode.
        while count_down > 0:
            count_down -= 1
            try:
                response: requests.Response = requests.get(
                    f"{self._source}/config/mode"
                )
                if response.status_code == 200:
                    return cast(
                        Literal["enabled", "disabled"], response.json()["value"]
                    )
            except Exception:
                pass
            time.sleep(wait_time)
        return None

    def initialize_event_handling_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> Any:
        """
        Initializes Eiger 16M http/REST event handling on the collecting node.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes Eiger 16M http/REST monitor mode and sets its
        parameters.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        Returns:

            An optional initialization token.
        """
        print("Configuring detector...")
        if not self._check_detector_monitor_mode():
            raise exceptions.OmEigerHttpInterfaceInitializationError(
                "Cannot connect to the detector:"
                "please make sure the detector is connected and swiched on."
            )

        response: requests.Response = requests.put(
            f"{self._source}/config/mode", json={"value": "enabled"}
        )
        if not response.status_code == 200:
            raise exceptions.OmEigerHttpInterfaceInitializationError(
                "Cannot enable 'monitor' mode of the detector."
            )

        response = requests.put(
            f"{self._source}/config/discard_new", json={"value": False}
        )
        if not response.status_code == 200:
            raise exceptions.OmEigerHttpInterfaceInitializationError(
                "Cannot enable 'overwrite buffer' mode of the detector."
            )

        buffer_size: int = self._monitor_params.get_parameter(
            group="data_retrieval_layer",
            parameter="eiger_monitor_buffer_size",
            parameter_type=int,
            required=True,
        )
        response = requests.put(
            f"{self._source}/config/buffer_size", json={"value": buffer_size}
        )
        if not response.status_code == 200:
            raise exceptions.OmEigerHttpInterfaceInitializationError(
                "Cannot set the buffer size of the detector monitor mode."
            )

    def initialize_event_handling_on_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> Any:
        """
        Initializes Eiger 16M http/REST event handling on the processing nodes.

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

        while self._check_detector_monitor_mode() != "enabled":
            time.sleep(0.5)

    def event_generator(
        self,
        *,
        node_rank: int,
        node_pool_size: int,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Retrieves Eiger 16M events from http/REST interface.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This Data Event Handler retrieved events ...

        Each retrieved event contains a single detector frame.

        This generator function yields a dictionary storing the data for the current
        event.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        self._data_sources["timestamp"].initialize_data_source()
        source_name: str
        for source_name in self._required_data_sources:
            self._data_sources[source_name].initialize_data_source()

        data_event: Dict[str, Any] = {}
        data_event["additional_info"] = {}

        while True:
            response: requests.Response = requests.get(f"{self._source}/images/next")
            if response.status_code == 200:
                image_file: BytesIO = BytesIO(response.content)
                data_event["additional_info"]["image_file"] = image_file
                data_event["additional_info"]["timestamp"] = self._data_sources[
                    "timestamp"
                ].get_data(event=data_event)

                yield data_event

            elif response.status_code == 408:
                print(f"Processing node {node_rank}: No image available")
                time.sleep(0.5)

            else:
                msg: str = (
                    f"Response from Detector: {response.status_code} - "
                    f"{response.reason}"
                )
                print(f"Processing node {node_rank}: {msg}")
                time.sleep(0.5)

    def open_event(self, *, event: Dict[str, Any]) -> None:
        """
        Opens an Eiger 16M http/REST event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Eiger 16M http/REST events do not need to be opened, so this function actually
        does nothing.

        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    def close_event(self, *, event: Dict[str, Any]) -> None:
        """
        Closes an Eiger 16M http/REST event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Eiger 16M http/REST events do not need to be closed, so this function actually
        does nothing.
        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    def get_num_frames_in_event(self, *, event: Dict[str, Any]) -> int:
        """
        Gets the number of frames in an Eiger 16M http/REST event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Each Eiger 16M http/REST event stores data associated with a single detector
        frame, so this function always returns 1.

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
        Extracts data from a Eiger 16M http/REST event.

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


class Eiger16MHttpDataRetrieval(drl_base.OmDataRetrieval):
    """
    See documentation of the `__init__` function.

    Base class: [`OmDataRetrieval`][om.data_retrieval_layer.base.OmDataRetrieval]
    """

    def __init__(self, *, monitor_parameters: parameters.MonitorParams, source: str):
        """
        Data Retrieval for Eiger 16M http/REST interface.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class implements the operations needed to retrieve data from Eiger 16M
        http/REST monitor interface.

        This class considers an individual data event as equivalent to the content of a
        tif file retrieved from Eiger 16M http/REST interface, which stores data related
        to a single detector frame. Eiger 16M http/REST interface provides detector
        data, timestamp and frame ID for each event. Eiger 16M http/REST monitor
        interface does not contain any detector distance or beam energy information:
        their values need to be provided to OM through its configuration parameters
        (specifically, the `fallback_detector_distance_in_mm` and
        `fallback_beam_energy_in_eV` entries in the `data_retrieval_layer` parameter
        group). The source string for this Data Retrieval class is the base URL of the
        detector subsystem: http://<address_of_dcu>/monitor/api/<version>
                .

        Arguments:

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.

            source: A string describing the data source.
        """

        data_sources: Dict[str, drl_base.OmDataSource] = {
            "timestamp": ds_http.TimestampEiger16MHttp(
                data_source_name="timestamp", monitor_parameters=monitor_parameters
            ),
            "event_id": ds_http.EventIdEiger16MHttp(
                data_source_name="eventid", monitor_parameters=monitor_parameters
            ),
            "frame_id": ds_generic.FrameIdZero(
                data_source_name="frameid", monitor_parameters=monitor_parameters
            ),
            "detector_data": ds_http.Eiger16MHttp(
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
            _Eiger16MHttpDataEventHandler(
                source=source,
                monitor_parameters=monitor_parameters,
                data_sources=data_sources,
            )
        )

    @property
    def data_event_handler(self) -> drl_base.OmDataEventHandler:
        return self._data_event_handler
