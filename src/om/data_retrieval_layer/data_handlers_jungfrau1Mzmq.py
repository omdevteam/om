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
Retrieval and handling of data events from the filesystem.

This module contains classes that retrieve and process data events from files written
on disk.
"""
from typing import Any, Callable, Dict, Generator, List, TextIO, Tuple

import zmq  # type: ignore
import numpy  # type: ignore

from om.algorithms import calibration_algorithms as calib_algs
from om.data_retrieval_layer import base as drl_base
from om.data_retrieval_layer import functions_jungfrau1Mzmq
from om.utils import parameters


class Jungfrau1MzmqEventHandler(drl_base.OmDataEventHandler):
    """
    See documentation of the __init__ function.
    """

    def __init__(
        self, monitor_parameters: parameters.MonitorParams, source: str
    ) -> None:
        """
        Data event handler for events recovered from Jungfrau ZMQ receiver.

        See documentation of the constructor of the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler`.

        This class handles Jungfrau detector data events recovered from ZMQ stream.
        """
        super(Jungfrau1MzmqEventHandler, self).__init__(
            monitor_parameters=monitor_parameters, source=source,
        )

    @property
    def data_extraction_funcs(
        self,
    ) -> Dict[str, Callable[[Dict[str, Dict[str, Any]]], Any]]:
        """
        Retrieves the Data Extraction Functions for Pilatus files.

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.\
data_extraction_funcs`.
        """
        return {
            "timestamp": functions_jungfrau1Mzmq.timestamp,
            "beam_energy": functions_jungfrau1Mzmq.beam_energy,
            "detector_distance": functions_jungfrau1Mzmq.detector_distance,
            "detector_data": functions_jungfrau1Mzmq.detector_data,
            "event_id": functions_jungfrau1Mzmq.event_id,
            "frame_id": functions_jungfrau1Mzmq.frame_id,
        }

    def initialize_event_handling_on_collecting_node(
        self, node_rank: int, node_pool_size: int
    ) -> Any:
        """
        Initializes event handling on the collecting node for Jungfrau events received 
        from ZMQ stream.

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.\
initialize_event_source`.

        There is no need to initialize the source on collecting node, so this function
        does nothing.
        """
        pass

    def initialize_event_handling_on_processing_node(
        self, node_rank: int, node_pool_size: int
    ) -> Any:
        """
        Initializes event handling on the processing nodes for Jungfrau events received 
        from ZMQ stream.

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.\
initialize_event_source`.
        """
        required_data: List[str] = self._monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="required_data",
            parameter_type=list,
            required=True,
        )
        self._required_data_extraction_funcs: Dict[
            str, Callable[[Dict[str, Dict[str, Any]]], Any]
        ] = drl_base.filter_data_extraction_funcs(
            self.data_extraction_funcs, required_data
        )

        # Fills the event info dictionary with static data that will be retrieved
        # later.
        self._event_info_to_append: Dict[str, Any] = {}

        calibration: bool = self._monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="calibration",
            parameter_type=bool,
            required=True,
        )
        self._event_info_to_append["calibration"] = calibration
        if calibration is True:
            calibration_dark_filenames: List[str] = self._monitor_params.get_param(
                group="data_retrieval_layer",
                parameter="calibration_dark_filenames",
                parameter_type=list,
                required=True,
            )
            calibration_gain_filenames: List[str] = self._monitor_params.get_param(
                group="data_retrieval_layer",
                parameter="calibration_gain_filenames",
                parameter_type=list,
                required=True,
            )
            calibration_photon_energy_kev: float = self._monitor_params.get_param(
                group="data_retrieval_layer",
                parameter="calibration_photon_energy_kev",
                parameter_type=float,
                required=True,
            )
            self._event_info_to_append[
                "calibration_algorithm"
            ] = calib_algs.Jungfrau1MCalibration(
                calibration_dark_filenames,
                calibration_gain_filenames,
                calibration_photon_energy_kev,
            )

        if "beam_energy" in required_data:
            self._event_info_to_append["beam_energy"] = self._monitor_params.get_param(
                group="data_retrieval_layer",
                parameter="fallback_beam_energy_in_eV",
                parameter_type=float,
                required=True,
            )
        if "detector_distance" in required_data:
            self._event_info_to_append[
                "detector_distance"
            ] = self._monitor_params.get_param(
                group="data_retrieval_layer",
                parameter="fallback_detector_distance_in_mm",
                parameter_type=float,
                required=True,
            )

    def event_generator(
        self, node_rank: int, node_pool_size: int,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Retrieves events to process from Jungfrau ZMQ receiver.

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.event_generator`.

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

        data_event: Dict[str, Dict[str, Any]] = {}
        data_event["data_extraction_funcs"] = self._required_data_extraction_funcs
        data_event["additional_info"] = {}
        data_event["additional_info"].update(self._event_info_to_append)

        while True:
            msg: Tuple[Dict[str, Any], Dict[str, Any]]
            msg = zmq_socket.recv_pyobj()
            data_event["data"] = msg

            yield data_event

    def open_event(self, event: Dict[str, Any]) -> None:
        """
        Opens an event retrieved from Jungfrau ZMQ receiver.

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.open_event`.
        """
        pass

    def close_event(self, event: Dict[str, Any]) -> None:
        """
        Closes an event retrieved from Jungfrau ZMQ receiver

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.close_event` .
        """
        pass

    def get_num_frames_in_event(self, event: Dict[str, Any]) -> int:
        """
        Gets the number of frames in an event retrieved from Jungfrau ZMQ receiver.

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.\
get_num_frames_in_event`.
        """
        return 1

