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
Processing Layer's Protocol classes.

This module contains base Protocol classes for OM's Processing Layer.
"""

from typing import Any, Dict, Protocol, Tuple, Union

from om.lib.parameters import MonitorParameters


class OmProcessingProtocol(Protocol):
    """
    See documentation for the `__init__` function.
    """

    def __init__(self, *, monitor_parameters: MonitorParameters) -> None:
        """
        Protocol for OM's Processing classes.

        Processing classes implement scientific data processing pipelines in OM. A
        Processing class defines how each individual retrieved data event is analyzed
        on the processing nodes and how multiple events are aggregated on the
        collecting node. A Processing class also determined which actions OM performs
        at the beginning and at the end of the data processing.

        This Protocol class describes the interface that every Processing class in OM
        must implement.

        Arguments:

            monitor_parameters: An object storing OM's configuration parameters.
        """
        ...

    def initialize_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes an OM processing node.

        This function is invoked on each processing node when OM starts. It performs
        all the operations needed to prepares the node to retrieve and process data
        events (recovering additional needed external data, initializing the algorithms
        with all required parameters, etc.)

        Arguments:

            node_rank: The OM rank of the current node int the OM node pool. The rank
                is an integer that unambiguously identifies the node in the pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        ...

    def initialize_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes an OM collecting node.

        This function is invoked on the collecting node when OM starts. It performs all
        the operation needed to prepare the collecting node to aggregate events
        received from the processing nodes (creating memory buffers,
        initializing the collecting algorithm, etc.)

        Arguments:

            node_rank: The OM rank of the current node int the OM node pool. The rank
                is an integer that unambiguously identifies the node in the pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        ...

    def process_data(
        self,
        *,
        node_rank: int,
        node_pool_size: int,
        data: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], int]:
        """
        Processes a single data event.

        This function is invoked on each processing node for every retrieved data
        event. It receives the data event as input and returns processed data. The
        output of this function is transferred by OM to the collecting node.

        Arguments:

            node_rank: The OM rank of the current node int the OM node pool. The rank
                is an integer that unambiguously identifies the node in the pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

            data: A dictionary containing the data retrieved by OM for the data event
                being processed.

                * The dictionary keys must be the names of the Data Sources for which
                  OM retrieves data. The keys in this dictionary must match the Data
                  Source names listed in the `required_data` entry of OM's `om`
                  configuration parameter group.

                * The corresponding dictionary values must store the the data that OM
                  retrieved for each of the Data Sources.

        Returns:

            A tuple with two entries, with the first entry being a dictionary storing
                the processed data that should be sent to the collecting node, and the
                second being the OM rank number of the node that processed the
                information.
        """
        ...

    def wait_for_data(
        self,
        *,
        node_rank: int,
        node_pool_size: int,
    ) -> None:
        """
        Performs operations on the collecting node when no data is received.

        This function is called on the collecting node continuously, when the node is
        not receiving data from any processing node (When data is received, the
        [`collect_data`][om.protocols.processing_layer.OmProcessingProtocol.collect_data]
        is invoked instead). This function can be used to perform operations that need
        to be carried out even when the data stream is not active (reacting to external
        commands and requests, updating graphical interfaces, etc.)

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        ...

    def collect_data(
        self,
        *,
        node_rank: int,
        node_pool_size: int,
        processed_data: Tuple[Dict[str, Any], int],
    ) -> Union[Dict[int, Dict[str, Any]], None]:
        """
        Collects processed data from a processing node.

        This function is invoked on the collecting node every time data is received
        from a processing node (When data is not being received, the collecting node
        continuously calls the
        [`wait_for_data`][om.protocols.processing_layer.OmProcessingProtocol.wait_for_data]
        function instead). The function accepts as input the data received from
        the processing node (the tuple returned by the
        [`process_data`][om.protocols.processing_layer.OmProcessingProtocol.process_data]
        method of this class), and performs calculations that must be carried out on
        aggregated data (computing cumulative statistics, preparing data for external
        programs or visualization, etc.)

        The function usually does not return any value, but can optionally return a
        nested dictionary (a dictionary whose values are other dictionaries). When this
        happens, the data in the dictionary is provided as feedback data to the
        processing nodes. The nested dictionary must have the following format:

        * The keys of the outer dictionary must match the OM rank numbers of the
          processing nodes which receive the feedback data. A key value of 0 can be
          used to send feedback data to all the processing nodes at the same time.

        * The value corresponding to each key of the outer dictionary must in turn be a
          dictionary that stores the feedback data that is sent to the node defined by
          the key.

        * On each processing node, the feedback data dictionary, when received, is
          merged with the `data` argument of the
          [`process_data`][om.protocols.processing_layer.OmProcessingProtocol.process_data]
          function the next time the function is called.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

            processed_data (Tuple[Dict, int]): A tuple whose first entry is a
                dictionary storing the data received from a processing node, and whose
                second entry is the OM rank number of the node that processed the
                information.

        Returns:

            Usually nothing. Optionally, a nested dictionary that can be used to send
                feedback data to the processing nodes.
        """
        ...

    def end_processing_on_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> Union[Dict[str, Any], None]:
        """
        Executes end-of-processing actions on a processing node.

        This function is called on each processing node at the end of the data
        processing, immediately before OM stops. It performs clean up and shut down
        operations (closing communication sockets, computing final statistics, etc.).
        This function usually does not return any value, but can optionally return a
        dictionary. If this happens, the dictionary is transferred to the collecting
        node before the processing node shuts down.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        Returns:

            Usually nothing. Optionally, a dictionary storing information that must be
                sent to the processing node.
        """
        ...

    def end_processing_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Executes end-of-processing actions on the collecting node.

        This function is called on the collecting node at the end of the data
        processing, immediately before OM stops. It often performs clean up and shut
        operations (closing communication sockets, computing final statistics, etc.).

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        ...
