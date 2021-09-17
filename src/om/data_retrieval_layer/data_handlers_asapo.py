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
Retrieval and handling of data events from ASAP::O.

This module contains Data Event Handlers for events retrieved from the ASAP::O software
framework (used at the Petra III facility).
"""
from typing import Any, Callable, Dict, Generator, List, TextIO, Tuple
from om.data_retrieval_layer import base as drl_base
from om.data_retrieval_layer import functions_asapo
from om.utils import exceptions, parameters

import asapo_consumer
import time
import sys

class Petra3AsapoEventHandler(drl_base.OmDataEventHandler):
    """
    See documentation of the `__init__` function.

    Base class: [`OmDataEventHandler`][om.data_retrieval_layer.base.OmDataEventHandler]
    """

    def __init__(
        self, monitor_parameters: parameters.MonitorParams, source: str
    ) -> None:
        """
        Data Event Handler for events retrieved from ASAP::O at P11 (PETRA III).

        Arguments:

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.

            source: A string describing the data source.
        """
        super(Petra3AsapoEventHandler, self).__init__(
            monitor_parameters=monitor_parameters,
            source=source,
        )

    @property
    def data_extraction_funcs(
        self,
    ) -> Dict[str, Callable[[Dict[str, Dict[str, Any]]], Any]]:
        """
        """
        return {
            "timestamp": functions_asapo.timestamp,
            "beam_energy": functions_asapo.beam_energy,
            "detector_distance": functions_asapo.detector_distance,
            "detector_data": functions_asapo.detector_data,
            "event_id": functions_asapo.event_id,
            "frame_id": functions_asapo.frame_id,
        }

    def initialize_event_handling_on_collecting_node(
        self, node_rank: int, node_pool_size: int
    ) -> Any:
        """
        """
        pass

    def initialize_event_handling_on_processing_node(
        self, node_rank: int, node_pool_size: int
    ) -> Any:
        """
        """
        required_data: List[str] = self._monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="required_data",
            parameter_type=list,
            required=True,
        )

        self._required_data_extraction_funcs = drl_base.filter_data_extraction_funcs(
            data_extraction_funcs=self.data_extraction_funcs,
            required_data=required_data,
        )

        # Fills the event info dictionary with static data that will be retrieved
        # later.
        self._event_info_to_append: Dict[str, Any] = {}

    def event_generator(
        self,
        node_rank: int,
        node_pool_size: int,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        """
        asapo_path: str = self._monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="asapo_path",
            parameter_type=str,
        )
        asapo_beamtime: str = self._monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="asapo_beamtime",
            parameter_type=str,
        )
        asapo_data_source: str = self._monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="asapo_data_source",
            parameter_type=str,
        )
        asapo_has_filesystem: str = self._monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="asapo_has_filesystem",
            parameter_type=bool,
        )
        asapo_token: str = self._monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="asapo_token",
            parameter_type=str,
        )
        consumer: Any = asapo_consumer.create_consumer(
            self._source, 
            asapo_path,
            asapo_has_filesystem,
            asapo_beamtime,
            asapo_data_source,
            asapo_token,
            1000
        )

        data_event: Dict[str, Dict[str, Any]] = {}
        data_event["data_extraction_funcs"] = self._required_data_extraction_funcs
        data_event["additional_info"] = {}
        data_event["additional_info"].update(self._event_info_to_append)

        last_processed_event_timestamp: int = 0
        stream_list: List[Any] = []
        while len(stream_list) == 0:
            stream_list = consumer.get_stream_list()
        last_stream: str = stream_list[-1]["name"]
        stream_metadata: Dict[str, Any] = consumer.get_stream_meta(last_stream)
        last_processed_event_id: int = -1000
        while True:
            current_stream_size: int = consumer.get_current_size(stream=last_stream)
            event_id: int = (
                current_stream_size // (node_pool_size - 1) * (node_pool_size - 1) - node_rank + 1
            )
            if event_id == last_processed_event_id:
                stream_list = consumer.get_stream_list()
                current_stream: str = stream_list[-1]["name"]
                if current_stream == last_stream:
                    time.sleep(1)
                else:
                    last_stream = current_stream
                    stream_metadata: Dict[str, Any] = consumer.get_stream_meta(last_stream)
                    last_processed_event_id: int = -1000
                continue
            if event_id < 0:
                continue

            print(node_rank, last_stream, event_id)
            sys.stdout.flush()
            last_processed_event_id = event_id
            event_data: numpy.ndarray
            event_metadata: Dict[str, Any]
            event_data, event_metadata = consumer.get_by_id(
                event_id,
                stream=last_stream,
                meta_only=False,
            )

            data_event["data"] = event_data
            data_event["metadata"] = event_metadata
            data_event["additional_info"]["stream_metadata"] = stream_metadata
            data_event["additional_info"]["stream_name"] = last_stream

            yield data_event

    def open_event(self, event: Dict[str, Any]) -> None:
        """
        """
        pass

    def close_event(self, event: Dict[str, Any]) -> None:
        """
        """
        pass

    def get_num_frames_in_event(self, event: Dict[str, Any]) -> int:
        """
        Gets the number of frames in a P11 ASAP::O data event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Arguments:

            event: A dictionary storing the event data.
        """
        return 1
