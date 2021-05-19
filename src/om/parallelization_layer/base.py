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
Parallelization Layer's base classes.

This module contains base abstract classes for OM's Parallelization Layer.
"""
from abc import ABC, abstractmethod
from typing import List, Tuple, Union

from om.data_retrieval_layer import base as data_ret_layer_base
from om.processing_layer import base as process_layer_base
from om.utils import parameters


class OmParallelizationEngine(ABC):
    """
    See documentation of the `__init__` function.

    Base class: `ABC`
    """

    def __init__(
        self,
        data_event_handler: data_ret_layer_base.OmDataEventHandler,
        monitor: process_layer_base.OmMonitor,
        monitor_parameters: parameters.MonitorParams,
    ) -> None:
        """
        Base class for an OM's Parallelization Engine.

        Parallelization Engines orchestrate OM's processing and collecting nodes, and
        take care of the communication between them.

        This class is the base abstract class for all of OM's Parallelization Engines,
        and it should be subclassed to implement every Engine. All its methods are
        abstract: derived classes are expected to provide their own functions that
        implement a specific Parallelization Engine.

        * When OM start, each Parallelization Engine initializes several processing
          nodes and a single collecting node. A Data Event Handler (an instance of a
          class derived from
          [OmDataEventHandler][om.data_retrieval_layer.base.OmDataEventHandler]) and a
          Monitor (an instance of a class derived from
          [OmMonitor][om.processing_layer.base.OmMonitor]) must be provided to its
          constructor.

        * On each processing node, the Engine retrieves one data event from a source by
          calling the relevant Data Event Handler methods. It then invokes the
          appropriate Monitor methods to process every frame in the retrieved event.
          The Engine also makes sure that the processed data is transferred to the
          collecting node.

        * On the collecting node, the Engine invokes the relevant Monitor methods to
          aggregate data received from the processing nodes.

        * When all events from the source have been processed, the Engine performs
          some final clean-up tasks defined in the Data Event Handler, then it shuts
          all the nodes down.

        Arguments:

            data_event_handler: A class defining how data events are retrieved and
                handled.

            monitor: A class defining the how the retrieved data must be processed.

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.
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

    @abstractmethod
    def start(self) -> None:
        """
        Starts the parallelization engine.

        This function begins operations on the processing and collecting nodes.

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

        This function stops the processing and collecting nodes.

        * When this function is called on a processing node, the processing node
          communicates to the collecting node that it is shutting down, then shuts
          down.

        * When this function is called on the collecting node, the collecting node
          tells each processing node to shut down, waits for all the processing nodes
          to confirm that they have stopped operating, then shuts itself down.

        Arguments:

            msg: Reason for shutting down the parallelization engine. Defaults to
                "Reason not provided".
        """
        pass
