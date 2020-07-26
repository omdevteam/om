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
Monitor base class.

This module contains the abstract class that defines an OM monitor.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple

from om.utils import parameters


class OmMonitor(ABC):
    """
    See documentation for the '__init__' function.
    """

    def __init__(self, monitor_parameters):
        # type: (parameters.MonitorParams) -> None
        """
        The base class for an OM Monitor

        The OM monitor performs the scientific data processing. It implements functions
        to process retrieved data on the processing nodes, to aggregate data on the
        processing nodes and, optionally, to perform some end-of-processing tasks.

        Arguments:

            monitor_params (:class:`~om.utils.parameters.MonitorParams`): an object
                storing the OM monitor parameters from the configuration file.
        """
        self._monitor_params = monitor_parameters

    @abstractmethod
    def initialize_node(self, role, rank):
        # type: (str, int) -> None
        """
        Initializes an OM node.

        Performs initialization of an OM node.

        Arguments:

            role (str): the OM role of the current node ('processing' or 'collecting').

            rank (int): the OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.
        """

    @abstractmethod
    def process_data(self, role, rank, data):
        # type: (str, int, Dict[str, Any]) -> Tuple[Dict[str, Any], int]
        """
        Processes a single frame in a data event.

        The function that each processing node will invoke on every frame in a data
        event. The function receives as input a dictionary storing the retrieved data
        for the frame being processed. The output of the function, storing the
        processed data, will be transferred to the collecting node.

        Arguments:

            role (str): the OM role of the current node ('processing' or 'collecting').

            rank (int): the OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            data(Dict[str, Any]): a dictionary containing the data retrieved by
                OM for the frame being processed.

                * The dictionary keys must match the entries in the 'required_data'
                  list found in the 'om' configuration parameter group.

                * The corresponding dictionary values must store the retrieved data.

        Returns:

            Tuple[Dict, int]: a tuple whose first entry is a dictionary storing the
            data that should be sent to the collecting node, and whose second entry is
            the OM rank number of the node that processed the information.
        """
        pass

    @abstractmethod
    def collect_data(self, role, rank, processed_data):
        # type: (str, int, Tuple[Dict[str, Any], int]) -> None
        """
        The function that the collecting node will invoke every time data is
        transferred from a processing node. The function accepts as input the
        processed data received from the processing node.

        Arguments:

            role (str): the OM role of the current node ('processing' or 'collecting').

            rank (int): the OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            processed_data (Tuple[Dict, int]): a tuple whose first entry is a
                dictionary storing the data received from a processing node, and whose
                second entry is the OM rank number of the node that processed the
                information.
        """
        pass

    def end_processing(self, role, rank):
        # type: (str, int) -> None
        """
        Executes end-of-processing actions.

        This function is called by the parallelization engine on the processing and
        collecting nodes at the end of the processing, immediately before stopping.

        Arguments:

            role (str): the OM role of the current node ('processing' or 'collecting').

            rank (int): the OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.
        """
        del role
        del rank
