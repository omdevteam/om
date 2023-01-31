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
OnDA Test Monitor.

This module contains an OnDA Monitor that can be used for testing.
"""
import sys
import time
from typing import Any, Dict, Tuple, Union

from om.abcs import processing_layer as prol_abcs
from om.library import parameters, zmq_collecting
from om.library.rich_console import console, get_current_timestamp


class TestProcessing(prol_abcs.OmProcessingBase):
    """
    See documentation for the `__init__` function.
    """

    def __init__(self, *, monitor_parameters: parameters.MonitorParameters) -> None:
        """
        OnDA Test Monitor.

        This Processing class implements an OnDA Monitor that can be used for testing
        purposes. The monitor retrieves data events, but does not process the them. It
        simply broadcasts the timestamp of each data event over a ZMQ socket.

        Arguments:

            monitor_parameters: An object storing OM's configuration parameters.
        """
        self._monitor_params = monitor_parameters

    def initialize_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes the processing nodes for the Test Monitor.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function does not actually perform any task.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        console.print(f"{get_current_timestamp()} Processing node {node_rank} starting")
        sys.stdout.flush()

    def initialize_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes the collecting node for the Test Monitor.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function simply initializes some internal counters and prepares the data
        broadcasting socket.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        self._speed_report_interval: int = self._monitor_params.get_parameter(
            group="crystallography",
            parameter="speed_report_interval",
            parameter_type=int,
            required=True,
        )

        self._data_broadcast_interval: int = self._monitor_params.get_parameter(
            group="crystallography",
            parameter="data_broadcast_interval",
            parameter_type=int,
            required=True,
        )

        self._data_broadcast_socket: zmq_collecting.ZmqDataBroadcaster = (
            zmq_collecting.ZmqDataBroadcaster(
                parameters=self._monitor_params.get_parameter_group(
                    group="crystallography"
                )
            )
        )

        self._responding_socket: zmq_collecting.ZmqResponder = (
            zmq_collecting.ZmqResponder(
                parameters=self._monitor_params.get_parameter_group(
                    group="crystallography"
                )
            )
        )

        self._num_events: int = 0
        self._old_time: float = time.time()
        self._time: Union[float, None] = None

        console.print(f"{get_current_timestamp()} Starting the monitor...")
        sys.stdout.flush()

    def process_data(
        self, *, node_rank: int, node_pool_size: int, data: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], int]:
        """
        Processes a data event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function processes data events but does nothing with them. It simply
        extracts the timestamp information for each data event.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

            data: A dictionary containing the data that OM retrieved for the detector
                data frame being processed.

                * The dictionary keys describe the Data Sources for which OM has
                    retrieved data. The keys must match the source names listed in the
                    `required_data` entry of OM's `om` configuration parameter group.

                * The corresponding dictionary values must store the the data that OM
                    retrieved for each of the Data Sources.

        Returns:

            A tuple with two entries. The first entry is a dictionary storing the
                processed data that should be sent to the collecting node. The second
                entry is the OM rank number of the node that processed the information.
        """
        processed_data: Dict[str, Any] = {}

        console.print(f"{get_current_timestamp()} Processing Node - Retrieved data")
        console.print(f"{get_current_timestamp()}   Timestamp: {data['timestamp']}")

        processed_data["timestamp"] = data["timestamp"]

        return (processed_data, node_rank)

    def wait_for_data(
        self,
        *,
        node_rank: int,
        node_pool_size: int,
    ) -> None:
        """
        Performs operations on the processing node when no data is received.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This monitor does not need to perform any operation on the processing node if
        no data is received, therefore this function does nothing.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        """
        del node_rank
        del node_pool_size

    def collect_data(
        self,
        *,
        node_rank: int,
        node_pool_size: int,
        processed_data: Tuple[Dict[str, Any], int],
    ) -> Union[Dict[int, Dict[str, Any]], None]:
        """
        Computes aggregated data and broadcasts it over the network.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function receives data from the processing node, but does nothing with it.
        It simply broadcasts over a socket the value of an event counter and the
        timestamp of each received event.

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
        received_data: Dict[str, Any] = processed_data[0]
        self._num_events += 1

        console.print(f"{get_current_timestamp()} Collecting Node - Received data")
        console.print(
            f"{get_current_timestamp()}   Timestamp: {received_data['timestamp']}"
        )

        if self._num_events % self._data_broadcast_interval == 0:
            self._data_broadcast_socket.send_data(
                tag="omdata",
                message={
                    "timestamp": received_data["timestamp"],
                    "event_counter": self._num_events,
                },
            )

        if self._num_events % self._speed_report_interval == 0:
            now_time: float = time.time()
            time_diff: float = now_time - self._old_time
            events_per_second: float = float(self._speed_report_interval) / float(
                now_time - self._old_time
            )
            console.print(
                f"{get_current_timestamp()} Processed: {self._num_events} in "
                f"{time_diff:.2f} seconds ({events_per_second:.3f} Hz)"
            )

            sys.stdout.flush()
            self._old_time = now_time

        return {0: {"timestamp_of_last_event": received_data["timestamp"]}}

    def end_processing_on_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> Union[Dict[str, Any], None]:
        """
        Ends processing on the processing nodes.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function prints a message on the console and ends the processing.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        Returns:

            Usually nothing. Optionally, a dictionary storing information to be sent to
                the processing node.
        """
        console.print(
            f"{get_current_timestamp()} Processing node {node_rank} shutting down."
        )
        sys.stdout.flush()
        return None

    def end_processing_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Ends processing on the collecting node.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function prints a message on the console and ends the processing.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        console.print(
            f"{get_current_timestamp()} Processing finished. OM has processed "
            f"{self._num_events} events in total."
        )
        sys.stdout.flush()
