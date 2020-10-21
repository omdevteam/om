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
Parallelization engine base class.

This module contains the abstract class that defines an OM monitor parallelization
engine.
"""
from abc import ABC, abstractmethod
from typing import List, Tuple, Union

from om.data_retrieval_layer import base as data_ret_layer_base
from om.processing_layer import base as process_layer_base
from om.utils import parameters


class OmParallelizationEngine(ABC):
    """
    See documentation of the __init__ function.
    """

    def __init__(
        self,
        data_event_handler: data_ret_layer_base.OmDataEventHandler,
        monitor: process_layer_base.OmMonitor,
        monitor_parameters: parameters.MonitorParams,
    ) -> None:
        """
        The base class for an OM ParallelizationEngine.

        The parallelization engine initializes several processing nodes and a
        collecting node. An OM monitor is attached to the engine when it is created.

        * On each processing node, the engine retrieves one data event from a source.
          It then invokes the OM monitor to process on every frame of the retrieved
          data. The engine makes then sure that the processed data returned by the OM
          monitor is transferred to the collecting node.

        * On the collecting node, the engine invokes the OM monitor to aggregate data
          received from the processing nodes.

        * When all events from the source have been processed, the engine performs
          some final clean-up tasks and shuts down.

        Arguments:

            source: A string describing a source of event data. The exact format of the
                string depends on the specific DataEventHandler class being used.

            event_data_handler: A class defining how data events are handled.

            monitor: A class defining the scientific data processing that the monitor
                performs.

            monitor_parameters: An object storing the OM monitor parameters from the
                configuration file.
        """
        self._data_event_handler: data_ret_layer_base.OmDataEventHandler = (
            data_event_handler
        )
        self._monitor: process_layer_base.OmMonitor = monitor
        self._monitor_params: parameters.MonitorParams = monitor_parameters
        self._num_frames_in_event_to_process: int = self._monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="num_frames_in_event_to_process",
            parameter_type=int,
        )
        frames_in_event_to_skip: List[int] = self._monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="num_frames_in_event_to_process",
            parameter_type=list,
        )
        if frames_in_event_to_skip is not None:
            self._frames_in_event_to_skip: Tuple[int, ...] = tuple(
                frames_in_event_to_skip
            )
        else:
            self._frames_in_event_to_skip = tuple()

    @abstractmethod
    def start(self) -> None:
        """
        Starts the parallelization engine.

        * When this function is called on a processing node, the node starts retrieving
          data events and processing them.

        * When this function is called on the collecting node, the node starts
          receiving data from the processing nodes and aggregating it.
        """
        pass

    @abstractmethod
    def shutdown(self, msg: Union[str, None] = "Reason not provided.") -> None:
        """
        Shuts down the parallelization engine.

        * When this function is called on a processing node, the processing node
          communicates to the collecting node that it is shutting down, then shuts
          down.

        * When this function is called on the collecting node, the collecting node
          tells each processing node to shut down, waits for all the processing nodes
          to confirm that they have done that, then shuts down.

        Arguments:

            msg: Reason for shutting down the parallelization engine. Defaults to
                "Reason not provided".
        """
        pass
