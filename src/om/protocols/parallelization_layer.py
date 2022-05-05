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

from om.protocols import data_extraction_layer as data_ret_layer_protocols
from om.protocols import processing_layer as pl_protocols
from om.utils import parameters


class OmParallelization(ABC):
    """
    See documentation of the `__init__` function.
    """

    @abstractmethod
    def __init__(
        self,
        *,
        data_retrieval_layer: data_ret_layer_protocols.OmDataRetrieval,
        processing_layer: pl_protocols.OmProcessing,
        monitor_parameters: parameters.MonitorParams,
    ) -> None:
        """
        Base class for OM's Parallelization Layer.

        Parallelization classes orchestrate OM's processing and collecting nodes, and
        take care of the communication between them.

        * When OM start, a Parallelization class instance initializes several
          processing nodes, plus a single collecting node.

        * The Parallelization class associates an instance of a Data Retrieval class
          (see [OmDataRetrieval][om.data_retrieval_layer.base.OmDataRetrieval]) and an
          instance of a Processing class (see
          [OmProcessing][om.processing_layer.base.OmProcessing]) to the nodes.

        * Each processing node retrieves an event from a data event source by calling
          the relevant Data Retrieval class methods. It then invokes the appropriate
          Processing class methods on every frame in the event. Finally, it transfers
          the processed data to the collecting node. The node then retrieves another
          event, and the cycle continues until there are no more data events or OM
          shuts down.

        * Every time it receives data from a processing node, the collecting node
          invokes the relevant Processing class methods to aggregate the received data.

        * When all events from the source have been processed, all nodes perform some
          final clean-up tasks by calling the appropriate methods of the Processing
          class. All nodes then shut down.

        This class is the base abstract class from which every Parallelization class
        should inherit. All its methods are abstract: each derived class must provide
        its own implementations tailored to its specific parallelization strategy.

        Arguments:

            data_retrieval_layer: A class defining how data and data events are
                retrieved and handled.

            processing_layer: A class defining how retrieved data is processed.

            monitor_parameters: An object storing OM's configuration parameters.
        """
        pass

    @abstractmethod
    def start(self) -> None:
        """
        Starts OM.

        This function begins operations on the processing and collecting nodes.

        * When this function is called on a processing node, the node starts retrieving
          data events and processing them.

        * When this function is called on the collecting node, the node starts
          receiving data from the processing nodes and aggregating it.
        """
        pass

    @abstractmethod
    def shutdown(self, *, msg: str = "Reason not provided.") -> None:
        """
        Shuts down OM.

        This function stops the processing and collecting nodes.

        * When this function is called on a processing node, the processing node
          communicates to the collecting node that it is shutting down, then shuts
          down.

        * When this function is called on the collecting node, the collecting node
          tells every processing node to shut down, waits for all the processing nodes
          to confirm that they have stopped operating, then shuts itself down.

        Arguments:

            msg: Reason for shutting down. Defaults to "Reason not provided".
        """
        pass
