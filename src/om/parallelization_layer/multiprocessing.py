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
Multiprocessing Parallelization Layer for OM.

This module contains a Parallelization Layer based on Python's multiprocessing module.
"""

import queue
import sys
from multiprocessing import Pipe, Process, Queue, connection, queues
from random import randrange
from typing import Any, Literal

from om.lib.exceptions import OmDataExtractionError
from om.lib.logging import log
from om.lib.parameters import DataRetrievalLayerParameters
from om.lib.protocols import (
    OmDataEventHandlerProtocol,
    OmParallelizationProtocol,
    OmProcessingProtocol,
)


def _om_processing_node(
    *,
    rank: int,
    node_pool_size: int,
    data_queue: "Queue[tuple[dict[str, Any], int]]",
    message_pipe: connection.Connection,
    data_event_handler: OmDataEventHandlerProtocol,
    processing_layer: OmProcessingProtocol,
) -> None:
    # This function implements a processing node. It is designed to be run as a
    # subprocess.
    data_event_handler.initialize_event_handling_on_processing_node(
        node_rank=rank, node_pool_size=node_pool_size
    )

    processing_layer.initialize_processing_node(
        node_rank=rank, node_pool_size=node_pool_size
    )

    events = data_event_handler.event_generator(
        node_rank=rank,
        node_pool_size=node_pool_size,
    )

    event: dict[str, Any]
    for event in events:
        feedback_dict: dict[str, Any] = {}
        if message_pipe.poll():
            message: dict[str, Any] = message_pipe.recv()
            if "stop" in message:
                log.info(f"Shutting down RANK: {rank}.")
                data_queue.put(({"stopped": True}, rank))
                return
            else:
                feedback_dict = message

        try:
            data: dict[str, Any] = data_event_handler.extract_data(event=event)
        except OmDataExtractionError as exc:
            log.warning(f"{exc}. Skipping event...")
            continue
        data.update(feedback_dict)
        processed_data: tuple[dict[str, Any], int] = processing_layer.process_data(
            node_rank=rank, node_pool_size=node_pool_size, data=data
        )
        data_queue.put(processed_data)

    # After finishing iterating over the events to process, calls the
    # end_processing function, and if the function returns something, sends it
    # to the processing node.
    final_data: dict[str, Any] | None = (
        processing_layer.end_processing_on_processing_node(
            node_rank=rank, node_pool_size=node_pool_size
        )
    )
    if final_data is not None:
        data_queue.put((final_data, rank))

    # Sends a message to the collecting node saying that there are no more
    # events.
    end_dict = {"end": True}
    data_queue.put((end_dict, rank))
    return


class MultiprocessingParallelization(OmParallelizationProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        data_retrieval_layer: OmDataEventHandlerProtocol,
        processing_layer: OmProcessingProtocol,
        parameters: DataRetrievalLayerParameters,
    ) -> None:
        """
        Multiprocessing-based Parallelization Layer for OM.

        This class implements a Parallelization Layer based on Python's multiprocessing
        module. Each processing node is spawned as a subprocess. The parent process
        acts as the collecting node and additionally manages the child processes. This
        class manages all the subprocesses, and sets up all the communication channels
        through which data and control commands are received and dispatched.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        Arguments:

            data_retrieval_layer: A class defining how data and data events are
                retrieved and handled.

            processing_layer: A class defining how retrieved data is processed.

            parameters: An object storing OM's configuration parameters.
        """
        self._data_event_handler: OmDataEventHandlerProtocol = data_retrieval_layer
        self._processing_layer: OmProcessingProtocol = processing_layer

        self._node_pool_size: int = parameters.node_pool_size

        designated_collector: Literal["first", "last"] = (
            self._data_event_handler.designated_collector_rank()
        )

        if designated_collector == "first":
            self._collector_rank: int = 0
        else:
            self._collector_rank = self._node_pool_size - 1

        self._skip_rank_finalization: bool = (
            self._data_event_handler.skip_rank_finalization()
        )

        self._processing_nodes: list[Process] = []
        self._message_pipes: dict[int, connection.Connection] = {}
        self._data_queue: queues.Queue[tuple[dict[str, Any], int]] = Queue()

        processing_node_rank: int
        for processing_node_rank in range(0, self._node_pool_size):
            if processing_node_rank == self._collector_rank:
                continue
            message_pipe: tuple[
                connection.PipeConnection,
                connection.PipeConnection,
            ] = Pipe(duplex=False)
            self._message_pipes[processing_node_rank] = message_pipe[1]
            processing_node = Process(
                target=_om_processing_node,
                kwargs={
                    "rank": processing_node_rank,
                    "node_pool_size": self._node_pool_size,
                    "data_queue": self._data_queue,
                    "message_pipe": message_pipe[0],
                    "data_event_handler": self._data_event_handler,
                    "processing_layer": self._processing_layer,
                },
            )
            self._processing_nodes.append(processing_node)

        self._rank: int = self._collector_rank
        self._data_event_handler.initialize_event_handling_on_collecting_node(
            node_rank=self._rank, node_pool_size=self._node_pool_size
        )
        self._deceased_ranks: list[bool] = [False] * self._node_pool_size
        self._deceased_ranks[self._collector_rank] = True
        self._num_collected_events: int = 0

    def start(self) -> None:  # noqa: C901
        """
        Starts the multiprocessing parallelization.

        The function starts the nodes and manages all of their interactions, organizing
        the receiving and dispatching of data and control commands.

        Please see the documentation of the base Protocol class for additional
        information about this method.
        """
        log.info(
            "You are using an OM real-time monitor. Please cite: "
            "Mariani et al., J Appl Crystallogr. 2016 May 23;49(Pt 3):1073-1080",
        )
        log.info("---")
        for processing_node in self._processing_nodes:
            processing_node.start()

        self._processing_layer.initialize_collecting_node(
            node_rank=self._rank, node_pool_size=self._node_pool_size
        )
        while True:
            try:
                try:
                    received_data: tuple[dict[str, Any], int] = (
                        self._data_queue.get_nowait()
                    )
                    if "end" in received_data[0]:
                        # If the received message announces that a processing node has
                        # finished processing data, keeps track of how many processing
                        # nodes have already finished.
                        self._deceased_ranks[received_data[1]] = True

                        # When all processing nodes have finished, calls the
                        # 'end_processing_on_collecting_node' function then shuts
                        # down.
                        if all(self._deceased_ranks):
                            log.info("All processing nodes have run out of events.")
                            log.info("Shutting down.")
                            self._processing_layer.end_processing_on_collecting_node(
                                node_rank=self._rank,
                                node_pool_size=self._node_pool_size,
                            )
                            for processing_node in self._processing_nodes:
                                processing_node.join()
                            sys.exit(0)
                        else:
                            continue
                    feedback_data: dict[str, dict[str, Any]] | None = (
                        self._processing_layer.collect_data(
                            node_rank=self._rank,
                            node_pool_size=self._node_pool_size,
                            processed_data=received_data,
                        )
                    )

                    self._num_collected_events += 1
                    if feedback_data is not None:
                        receiving_rank: str
                        for receiving_rank in feedback_data.keys():
                            if receiving_rank == "all":
                                processing_node_rank: int
                                for processing_node_rank in range(
                                    0, self._node_pool_size
                                ):
                                    if processing_node_rank == self._collector_rank:
                                        continue
                                    self._message_pipes[processing_node_rank].send(
                                        feedback_data["all"]
                                    )
                            elif receiving_rank == "random":
                                random_rank: int = 0
                                while True:
                                    random_rank = randrange(0, self._node_pool_size)
                                    if self._deceased_ranks[random_rank] is False:
                                        break
                                self._message_pipes[random_rank].send(
                                    feedback_data["random"]
                                )
                            else:
                                log.error(
                                    "The target for feedback data must be one of "
                                    "the following: 'random', 'all'"
                                )
                except queue.Empty:
                    self._processing_layer.wait_for_data(
                        node_rank=self._rank,
                        node_pool_size=self._node_pool_size,
                    )

            except KeyboardInterrupt as exc:
                log.info("Received keyboard sigterm...")
                log.info(f"{str(exc)}")
                log.info("Shutting down.")
                self.shutdown()

    def shutdown(self, *, msg: str = "Reason not provided.") -> None:
        """
        Shuts down the multiprocessing parallelization.

        This function stops OM, closing all the communication channels between the
        nodes and managing a controlled shutdown of OM's resources. Additionally, it
        terminates all the subprocesses in an orderly fashion.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            msg: Reason for shutting down. Defaults to "Reason not provided".
        """
        log.info(f"Shutting down: {msg}")
        if self._rank == 0:
            # Tells all the processing nodes that they need to shut down, then waits
            # for confirmation. During the whole process, keeps receiving normal MPI
            # messages from the nodes (MPI cannot shut down if there are unreceived
            # messages).
            try:
                node_num: int
                for node_num in range(0, self._node_pool_size):
                    if self._deceased_ranks[node_num] is True:
                        continue
                    self._message_pipes[node_num].send({"stop": True})
                while True:
                    message: tuple[dict[str, Any], int] = self._data_queue.get()
                    if "stopped" in message[0]:
                        self._deceased_ranks[message[1]] = True
                    if all(self._deceased_ranks):
                        break
                # When all the processing nodes have confirmed, shuts down the
                # collecting node.
                for processing_node in self._processing_nodes:
                    processing_node.join()
                sys.exit(0)
            except RuntimeError:
                # In case of error, crashes hard!
                for processing_node in self._processing_nodes:
                    processing_node.join()
                sys.exit(0)
