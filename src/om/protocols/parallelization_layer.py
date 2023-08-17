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
Parallelization Layer's Protocol classes.

This module contains base Protocol classes for OM's Parallelization Layer.
"""

from typing import Protocol

from om.lib.parameters import MonitorParameters
from om.protocols.data_retrieval_layer import OmDataRetrievalProtocol
from om.protocols.processing_layer import OmProcessingProtocol


class OmParallelizationProtocol(Protocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        data_retrieval_layer: OmDataRetrievalProtocol,
        processing_layer: OmProcessingProtocol,
        monitor_parameters: MonitorParameters,
    ) -> None:
        """
        Protocol for OM's Parallelization classes.

        Parallelization classes orchestrate OM's processing and collecting nodes, and
        take care of the communication between them.

        * When OM start, a Parallelization class instance initializes several
          processing nodes, plus a single collecting node. The class then associates an
          instance of a Data Retrieval class (see
          [OmDataRetrievalProtocol;][om.protocols.data_retrieval_layer.OmDataRetrievalProtocol])  # noqa: E501
          and an instance of a Processing class (see
          OmProcessingProtocol][om.protocols.processing_layer.OmProcessingProtocol])
          with  each node.

        * Each processing node retrieves an event from a data event source by calling
          the relevant Data Retrieval class methods. It then invokes the appropriate
          Processing class methods on the event. Finally, it transfers the processed
          data to the collecting node. The node then retrieves another event, and the
          cycle continues until there are no more data events or OM shuts down.

        * Every time it receives data from a processing node, the collecting node
          invokes the relevant Processing class methods to aggregate the received data.

        * When all events from the source have been processed, all nodes perform some
          final clean-up tasks by calling the appropriate methods of the Processing
          class. All nodes then shut down.

        This Protocol class describes the interface that every Parallelization class in
        OM must implement.

        Arguments:

            data_retrieval_layer: A class instance defining how data and data events are
                retrieved and handled.

            processing_layer: A class instance defining how retrieved data is processed.

            monitor_parameters: An object storing OM's configuration parameters.
        """
        ...

    def start(self) -> None:
        """
        Starts OM.

        This function begins operations on the processing and collecting nodes.

        When this function is called on a processing node, the processing node starts
        retrieving data events and processing them. When instead this function is
        called on the collecting node, the node starts receiving data from the
        processing nodes and aggregating it.
        """
        ...

    def shutdown(self, *, msg: str = "Reason not provided.") -> None:
        """
        Shuts down OM.

        This function stops the processing and collecting nodes.

        When this function is called on a processing node, the processing node
        communicates to the collecting node that it is shutting down, then shuts down.
        When instead this function is called on the collecting node, the collecting
        node tells every processing node to shut down, waits for all the nodes to
        confirm that they have stopped operating, then shuts itself down.

        Arguments:

            msg: Reason for shutting down. Defaults to "Reason not provided".
        """
        ...
