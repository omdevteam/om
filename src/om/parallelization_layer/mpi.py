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
MPI-based parallelization engine for OM.

This module contains an MPI-based parallelization engine for OM.
"""
from __future__ import absolute_import, division, print_function

import sys
from typing import Any, Dict, Tuple, Union

from mpi4py import MPI  # type: ignore

from om.data_retrieval_layer import base as data_ret_layer_base
from om.parallelization_layer import base as par_layer_base
from om.processing_layer import base as process_layer_base
from om.utils import exceptions, parameters

# Define some labels for internal MPI communication (just some syntactic sugar).
_NOMORE = 998  # type: int
_DIETAG = 999  # type: int
_DEADTAG = 1000  # type: int


class MpiProcessingCollectingEngine(par_layer_base.OmParallelizationEngine):
    """
    See documentation of the __init__ function.
    """

    def __init__(
        self,
        data_event_handler,  # type: data_ret_layer_base.OmDataEventHandler
        monitor,  # type: process_layer_base.OmMonitor
        monitor_parameters,  # type: parameters.MonitorParams
    ):
        # type: (...) -> None
        """
        An MPI-based parallelization engine for OM.

        See documentation of the constructor of the base class:
        :func:`~om.parallelization_layer.base.OmParallelizationEngine.__init__` .
        In the MPI implementation of the parallelization engine, the nodes communicate
        with each other using the MPI protocol.
        """
        super(MpiProcessingCollectingEngine, self).__init__(
            data_event_handler=data_event_handler,
            monitor=monitor,
            monitor_parameters=monitor_parameters,
        )

        self._mpi_size = MPI.COMM_WORLD.Get_size()  # type: int
        self._rank = MPI.COMM_WORLD.Get_rank()  # type: int

        if self._rank == 0:
            self._data_event_handler.initialize_event_handling_on_collecting_node(
                self._rank, self._mpi_size
            )
            self._num_nomore = 0  # type: int
            self._num_collected_events = 0  # type: int
        else:
            self._data_event_handler.initialize_event_handling_on_processing_node(
                self._rank, self._mpi_size
            )

    # def get_rank(self):
    #     # type: () -> int
    #     """
    #     Retrieves the rank of the current node in the MPI parallelization engine.

    #     See documentation of the function in the base class:
    #     :func:`~om.parallelization_layer.base.OmParallelizationEngine.get_rank`

    #     For the MPI-based parallelization engine, the node rank corresponds to the MPI
    #     rank.
    #     """
    #     return self._rank

    # def get_node_pool_size(self):
    #     # type: () -> int
    #     """
    #     Retrieves the size of the OM node pool in the MPI parallelization engine.

    #     See documentation of the function in the base class:
    #     :func:`~om.parallelization_layer.base.OmParallelizationEngine.get_node_pool_size`

    #     For the MPI-based parallelization engine, the node pool size is equivalent to
    #     the MPI pool size.
    #     """
    #     return self._mpi_size

    def start(self):  # noqa: C901
        # type: () -> None
        """
        Starts the MPI parallelization engine.

        See documentation of the function in the base class:
        :func:`~om.parallelization_layer.base.OmParallelizationEngine.start` .
        """
        if self._rank == 0:
            print("Starting OM with the following parameters:")
            # print(
            #     json.dumps(
            #         self._monitor_params.get_all_parameters(),
            #         indent=4,
            #         sort_keys=True
            #     )
            # )
            print(
                "You are using an OM real-time monitor. Please cite: "
                "Mariani et al., J Appl Crystallogr. 2016 May 23;49(Pt 3):1073-1080"
            )
            self._monitor.initialize_collecting_node(self._rank, self._mpi_size)

            while True:
                try:
                    received_data = MPI.COMM_WORLD.recv(
                        source=MPI.ANY_SOURCE, tag=0
                    )  # type: Tuple[Dict[str, Any], int]
                    if "end" in received_data[0].keys():
                        # If the received message announces that a processing node has
                        # finished processing data, keeps track of how many processing
                        # nodes have already finished.
                        print("Finalizing {0}".format(received_data[1]))
                        self._num_nomore += 1
                        # When all processing nodes have finished, calls the
                        # 'end_processing' function then shuts down.
                        if self._num_nomore == self._mpi_size - 1:
                            print("All processing nodes have run out of events.")
                            print("Shutting down.")
                            sys.stdout.flush()
                            self._monitor.end_processing_on_collecting_node(
                                self._rank, self._mpi_size
                            )
                            MPI.Finalize()
                            exit(0)
                        else:
                            continue
                    self._monitor.collect_data(
                        self._rank, self._mpi_size, received_data
                    )
                    self._num_collected_events += 1
                except KeyboardInterrupt as exc:
                    print("Received keyboard sigterm...")
                    print(str(exc))
                    print("shutting down MPI.")
                    self.shutdown()
                    print("---> execution finished.")
                    sys.stdout.flush()
                    sys.exit(0)
        else:
            self._monitor.initialize_processing_node(self._rank, self._mpi_size)

            # Flag used to make sure that the MPI messages have been processed.
            req = None
            events = self._data_event_handler.event_generator(
                node_rank=self._rank, node_pool_size=self._mpi_size,
            )

            for event in events:
                # Listens for requests to shut down.
                if MPI.COMM_WORLD.Iprobe(source=0, tag=_DIETAG):
                    self.shutdown("Shutting down RANK: {0}.".format(self._rank))

                self._data_event_handler.open_event(event)
                n_frames_in_evt = self._data_event_handler.get_num_frames_in_event(
                    event
                )  # type: int
                if self._num_frames_in_event_to_process is not None:
                    num_frames_to_process = min(
                        n_frames_in_evt, self._num_frames_in_event_to_process
                    )  # type: int
                else:
                    num_frames_to_process = n_frames_in_evt
                # Iterates over the last 'num_frames_to_process' frames in the event.
                for frame_offset in range(-num_frames_to_process, 0):
                    current_frame = n_frames_in_evt + frame_offset  # type: int
                    if current_frame in self._frames_in_event_to_skip:
                        continue
                    event["current_frame"] = current_frame
                    try:
                        data = self._data_event_handler.extract_data(
                            event
                        )  # type: Dict[str, Any]
                    except exceptions.OmDataExtractionError as exc:
                        print(exc)
                        print("Skipping event...")
                        continue
                    processed_data = self._monitor.process_data(
                        self._rank, self._mpi_size, data
                    )  # type: Tuple[Dict[str, Any], int]
                    if req:
                        req.Wait()
                    req = MPI.COMM_WORLD.isend(processed_data, dest=0, tag=0)
                # Makes sure that the last MPI message has processed.
                if req:
                    req.Wait()
                self._data_event_handler.close_event(event)

            # After finishing iterating over the events to process, sends a message to
            # the collecting node saying that there are no more events.
            end_dict = {"end": True}
            req = MPI.COMM_WORLD.isend((end_dict, self._rank), dest=0, tag=0)
            if req:
                req.Wait()
            self._monitor.end_processing_on_processing_node(self._rank, self._mpi_size)
            MPI.Finalize()
            exit(0)

    def shutdown(self, msg="Reason not provided."):
        # type: (Union[str, None]) -> None
        """
        Shuts down the MPI parallelization engine.

        See documentation of the function in the base class:
        :func:`~om.parallelization_layer.base.OmParallelizationEngine.shutdown` .
        """
        print("Shutting down:", msg)
        sys.stdout.flush()
        if self._rank == 0:
            # Tells all the processing nodes that they need to shut down, then waits
            # for confirmation. During the whole process, keeps receiving normal MPI
            # messages from the nodes (MPI cannot shut down if there are unreceived
            # messages).
            try:
                for nod_num in range(1, self._mpi_size):
                    MPI.COMM_WORLD.isend(0, dest=nod_num, tag=_DIETAG)
                num_shutdown_confirm = 0
                while True:
                    if MPI.COMM_WORLD.Iprobe(source=MPI.ANY_SOURCE, tag=0):
                        _ = MPI.COMM_WORLD.recv(source=MPI.ANY_SOURCE, tag=0)
                    if MPI.COMM_WORLD.Iprobe(source=MPI.ANY_SOURCE, tag=_DEADTAG):
                        num_shutdown_confirm += 1
                    if num_shutdown_confirm == self._mpi_size - 1:
                        break
                # When all the processing nodes have confirmed, shuts down the
                # collecting node.
                MPI.Finalize()
                exit(0)
            except RuntimeError:
                # In case of error, crashes hard!
                MPI.COMM_WORLD.Abort(0)
                exit(0)
        else:
            _ = MPI.COMM_WORLD.send(dest=0, tag=_DEADTAG)
            MPI.Finalize()
            exit(0)
