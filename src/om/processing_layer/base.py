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

This module contains base abstract classes for OM's Proceessing Layer.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple, Union

from om.utils import parameters


class OmMonitor(ABC):
    """
    See documentation for the `__init__` function.
    """

    def __init__(self, monitor_parameters: parameters.MonitorParams) -> None:
        """
        Base class for an OM's Monitor.

        Monitors implement scientific data processing pipelines in OM. A Monitor class
        has methods that define how single data events are processed on the processing
        nodes and how multi-event data is aggregated on the collecting node. Other
        methods describe actions that OM should perform when all data events from a
        source have been processed.

        This class is the base abstract class for all OM's Monitors. It should be
        subclassed to implement each specific Monitor. All its methods are virtual:
        each derived class is expected to provide its own functions that implement the
        Monitor's data processing logic.

        Arguments:

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.
        """
        self._monitor_params = monitor_parameters

    @abstractmethod
    def initialize_processing_node(self, node_rank: int, node_pool_size: int) -> None:
        """
        Initializes an OM processing node.

        This is an abstract method.

        This function is invoked on each processing node when OM starts and it prepares
        the node to begin retrieveing and processing data events: it reads additional
        external data, initializes the algorithms with the required parameters, etc.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        pass

    @abstractmethod
    def initialize_collecting_node(self, node_rank: int, node_pool_size: int) -> None:
        """
        Initializes an OM collecting node.

        This is an abstract method.

        This function is invoked on the collecting node when OM starts and it prepares
        the node for the aggregation of data received from the processing nodes: it
        initializes the algorithms with the required parameters, creates data event
        buffers, etc.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        pass

    @abstractmethod
    def process_data(
        self,
        node_rank: int,
        node_pool_size: int,
        data: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], int]:
        """
        Processes a single frame in a data event.

        This is an abstract method.

        This function is invoked on each processing node for every detector data frame
        in a data event. It receives a dictionary storing the raw frame data as input,
        and returns a dictionary with the processed data. OM's Parallelization Engine
        will make sure that the output of this function is tranferred to the collecting
        node.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

            data: A dictionary containing the data retrieved by OM for the detector
                data frame being processed.

                * The dictionary keys must match the entries in the 'required_data'
                  list in the 'om' parameter group of the configuration file.

                * The corresponding dictionary values must store the retrieved data for
                  the frame currently being processed.

        Returns:

            A tuple whose first entry is a dictionary storing the data that should be
            sent to the collecting node, and whose second entry is the OM rank number
            of the node that processed the information.
        """
        pass

    @abstractmethod
    def collect_data(
        self,
        node_rank: int,
        node_pool_size: int,
        processed_data: Tuple[Dict[str, Any], int],
    ) -> None:
        """
        Collects processed data from a processing node.

        This is an abstract method.

        This function is invoked on the collecting node every time data is transferred
        from a processing node. The function accepts as input the data received from
        the processing node (the object returned by the :func:`process_data` function).
        This function usually computes aggregate statistics on the data received from
        all the nodes.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

            processed_data (Tuple[Dict, int]): A tuple whose first entry is a
                dictionary storing the data received from a processing node, and whose
                second entry is the OM rank number of the node that processed the
                information.
        """
        pass

    def end_processing_on_processing_node(
        self, node_rank: int, node_pool_size: int
    ) -> Union[Dict[str, Any], None]:
        """
        Executes end-of-processing actions on a processing node.

        This function is called by the Parallelization Engine on the processing nodes
        at the end of the processing, immediately before OM stops. The function usually
        does not return any value, but can optionally return a dictionary. In this
        case the Parallelization Engine makes sure that the dictionary is sent to the
        collecting node before the processing node shuts down.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        Returns:

            A dictionary storing information to be sent to the processing node
            (Optional: if this function returns nothing, no information is transferred
            to the processing node).
        """
        return None

    def end_processing_on_collecting_node(
        self, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Executes end-of-processing actions on the collecting node.

        This function is called by the parallelization engine on the collecting node
        at the end of the processing, immediately before OM stops.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        pass
