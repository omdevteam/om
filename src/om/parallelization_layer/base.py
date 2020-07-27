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
from __future__ import absolute_import, division, print_function

from abc import ABCMeta, abstractmethod
from typing import List, Tuple, Union

from om.data_retrieval_layer import base as data_ret_layer_base
from om.processing_layer import base as process_layer_base
from om.utils import parameters


ABC = ABCMeta("ABC", (object,), {"__slots__": ()})


class OmParallelizationEngine(ABC):  # type: ignore
    """
    See documentation of the __init__ function.
    """

    def __init__(
        self,
        source,  # type: str
        data_event_handler,  # type: data_ret_layer_base.OmDataEventHandler
        monitor,  # type: process_layer_base.OmMonitor
        monitor_parameters,  # type: parameters.MonitorParams
    ):
        # type: (...) -> None
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

            source (str): a string describing a source of event data. The exact format
                of the string depends on the specific DataEventHandler class being
                used.

            event_data_handler(:class:`~om.data_retrieval_layer.base.\
DataEventHandler`): a class defining how data events are handled.

            monitor(:class:`~om.processing_layer.base.\
OmMonitor`): a class defining the scientific data processing that the monitor
                performs.

            monitor_parameters (:class:`~om.utils.parameters.MonitorParams`): an object
                storing the OM monitor parameters from the configuration file.
        """
        self._source = source  # type: str
        self._data_event_handler = (
            data_event_handler
        )  # type: data_ret_layer_base.OmDataEventHandler
        self._monitor = monitor  # type: process_layer_base.OmMonitor
        self._monitor_params = monitor_parameters
        self._num_frames_in_event_to_process = self._monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="num_frames_in_event_to_process",
            parameter_type=str,
        )  # type: int
        frames_in_event_to_skip = self._monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="num_frames_in_event_to_process",
            parameter_type=list,
        )  # type: List[int]
        if frames_in_event_to_skip is not None:
            self._frames_in_event_to_skip = tuple(
                frames_in_event_to_skip
            )  # type: Tuple[int, ...]
        else:
            self._frames_in_event_to_skip = tuple()

    @abstractmethod
    def get_role(self):
        # type: () -> str
        """
        Retrieves the OM role of the current node.

        The returned string describers the role of the current node ('processing' or
        'collecting').
        """
        pass

    @abstractmethod
    def get_rank(self):
        # type: () -> int
        """
        Retrieves the OM rank of the current node.

        Returns an integer that unambiguously identifies the current node in the OM
        node pool.
        """
        pass

    @abstractmethod
    def get_node_pool_size(self):
        # type: () -> int
        """
        Retrieves the size of the OM node pool.

        Returns the total number of nodes in the OM pool, including all the processing
        nodes and the collecting node.
        """

    @abstractmethod
    def start(self):
        # type: () -> None
        """
        Starts the parallelization engine.

        * When this function is called on a processing node, the node starts retrieving
          data events and processing them.

        * When this function is called on the collecting node, the node starts
          receiving data from the processing nodes and aggregating it.
        """
        pass

    @abstractmethod
    def shutdown(self, msg="Reason not provided."):
        # type: (Union[str, None]) -> None
        """
        Shuts down the parallelization engine.

        * When this function is called on a processing node, the processing node
          communicates to the collecting node that it is shutting down, then shuts
          down.

        * When this function is called on the collecting node, the collecting node
          tells each processing node to shut down, waits for all the processing nodes
          to confirm that they have done that, then shuts down.

        Arguments:

            msg (Union[str, None]): reason for shutting down the parallelization
                engine. Defaults to "Reason not provided".
        """
        pass
