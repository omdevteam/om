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
MPI-based Parallelization Layer for OM.

This module contains a Parallelization Layer based on the MPI protocol.
"""
import sys
from typing import Any, Dict, Tuple, Union

from mpi4py import MPI  # type: ignore

from om.monitor import om_print as print
from om.protocols import data_extraction_layer as data_ret_layer_protocols
from om.protocols import parallelization_layer as par_layer_protocols
from om.protocols import processing_layer as pl_protocols
from om.utils import exceptions, parameters

# Define some labels for internal MPI communication (just some syntactic sugar).
_DIETAG: int = 999
_DEADTAG: int = 1000
_DATATAG: int = 1001
_FEEDBACKTAG: int = 1002


class MpiParallelization(par_layer_protocols.OmParallelization):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        data_retrieval_layer: data_ret_layer_protocols.OmDataRetrieval,
        processing_layer: pl_protocols.OmProcessing,
        monitor_parameters: parameters.MonitorParams,
    ) -> None:
        """
        MPI-based Parallelization Layer for OM.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class implements a Parallelization Layer based on the MPI protocol. The
        nodes communicate with each other using an implementation of the MPI protocol
        supported by the Python language (OpenMPI or MPICH).

        Arguments:

            data_retrieval_layer: A class defining how data and data events are
                retrieved and handled.

            processing_layer: A class defining how retrieved data is processed.

            monitor_parameters: An object storing OM's configuration parameters.
        """
        self._data_event_handler: data_ret_layer_protocols.OmDataEventHandler = (
            data_retrieval_layer.get_data_event_handler()
        )
        self._processing_layer: pl_protocols.OmProcessing = processing_layer
        self._monitor_params: parameters.MonitorParams = monitor_parameters

        self._num_frames_in_event_to_process: int = self._monitor_params.get_parameter(
            group="data_retrieval_layer",
            parameter="num_frames_in_event_to_process",
            parameter_type=int,
        )

        self._mpi_size: int = MPI.COMM_WORLD.Get_size()
        self._rank: int = MPI.COMM_WORLD.Get_rank()

        if self._rank == 0:
            self._data_event_handler.initialize_event_handling_on_collecting_node(
                node_rank=self._rank, node_pool_size=self._mpi_size
            )
            self._num_nomore: int = 0
            self._num_collected_events: int = 0
        else:
            self._data_event_handler.initialize_event_handling_on_processing_node(
                node_rank=self._rank, node_pool_size=self._mpi_size
            )

    def start(self) -> None:  # noqa: C901
        """
        Starts the MPI parallelization.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function sets up the communication between OM's collecting and processing
        nodes using the MPI protocol. The function starts the nodes and manages all of
        their interactions, organizing the receiving and dispatching of data and
        control commands over MPI channels.
        """
        if self._rank == 0:
            print(
                "You are using an OM real-time monitor. Please cite: "
                "Mariani et al., J Appl Crystallogr. 2016 May 23;49(Pt 3):1073-1080"
            )
            self._processing_layer.initialize_collecting_node(
                node_rank=self._rank, node_pool_size=self._mpi_size
            )

            req: Any = 0

            while True:
                try:
                    received_data: Tuple[Dict[str, Any], int] = MPI.COMM_WORLD.recv(
                        source=MPI.ANY_SOURCE, tag=_DATATAG
                    )
                    if "end" in received_data[0].keys():
                        # If the received message announces that a processing node has
                        # finished processing data, keeps track of how many processing
                        # nodes have already finished.
                        print(f"Finalizing {received_data[1]}")
                        self._num_nomore += 1
                        # When all processing nodes have finished, calls the
                        # 'end_processing_on_collecting_node' function then shuts down.
                        if self._num_nomore == self._mpi_size - 1:
                            print("All processing nodes have run out of events.")
                            print("Shutting down.")
                            sys.stdout.flush()
                            self._processing_layer.end_processing_on_collecting_node(
                                node_rank=self._rank, node_pool_size=self._mpi_size
                            )
                            MPI.Finalize()
                            exit(0)
                        else:
                            continue
                    feedback_data: Union[
                        Dict[int, Dict[str, Any]], None
                    ] = self._processing_layer.collect_data(
                        node_rank=self._rank,
                        node_pool_size=self._mpi_size,
                        processed_data=received_data,
                    )
                    self._num_collected_events += 1
                    if feedback_data is not None:
                        receiving_rank: int
                        for receiving_rank in feedback_data.keys():
                            if receiving_rank == 0:
                                target_rank: int
                                for target_rank in range(1, self._mpi_size):
                                    if req:
                                        req.Wait()
                                    req = MPI.COMM_WORLD.isend(
                                        feedback_data[0],
                                        dest=target_rank,
                                        tag=_FEEDBACKTAG,
                                    )
                            else:
                                if req:
                                    req.Wait()
                                req = MPI.COMM_WORLD.isend(
                                    feedback_data[receiving_rank],
                                    dest=receiving_rank,
                                    tag=_FEEDBACKTAG,
                                )

                except KeyboardInterrupt as exc:
                    print("Received keyboard sigterm...")
                    print(str(exc))
                    print("shutting down MPI.")
                    self.shutdown()
                    print("---> execution finished.")
                    sys.stdout.flush()
                    sys.exit(0)
        else:
            self._processing_layer.initialize_processing_node(
                node_rank=self._rank, node_pool_size=self._mpi_size
            )

            # Flag used to make sure that the MPI messages have been processed.
            req = None
            events = self._data_event_handler.event_generator(
                node_rank=self._rank,
                node_pool_size=self._mpi_size,
            )

            event: Dict[str, Any]
            for event in events:
                # Listens for requests to shut down.
                if MPI.COMM_WORLD.Iprobe(source=0, tag=_DIETAG):
                    self.shutdown(msg=f"Shutting down RANK: {self._rank}.")

                feedback_dict: Dict[str, Any] = {}
                if MPI.COMM_WORLD.Iprobe(source=0, tag=_FEEDBACKTAG):
                    feedback_dict = MPI.COMM_WORLD.recv(source=0, tag=_FEEDBACKTAG)

                self._data_event_handler.open_event(event=event)
                n_frames_in_evt: int = self._data_event_handler.get_num_frames_in_event(
                    event=event
                )
                if self._num_frames_in_event_to_process is not None:
                    num_frames_to_process: int = min(
                        n_frames_in_evt, self._num_frames_in_event_to_process
                    )
                else:
                    num_frames_to_process = n_frames_in_evt
                # Iterates over the last 'num_frames_to_process' frames in the event.
                frame_offset: int
                for frame_offset in range(-num_frames_to_process, 0):
                    current_frame: int = n_frames_in_evt + frame_offset
                    event["current_frame"] = current_frame
                    try:
                        data: Dict[str, Any] = self._data_event_handler.extract_data(
                            event=event
                        )
                    except exceptions.OmDataExtractionError as exc:
                        print(exc)
                        print("Skipping event...")
                        continue
                    data.update(feedback_dict)
                    processed_data: Tuple[
                        Dict[str, Any], int
                    ] = self._processing_layer.process_data(
                        node_rank=self._rank, node_pool_size=self._mpi_size, data=data
                    )
                    if req:
                        req.Wait()
                    req = MPI.COMM_WORLD.isend(processed_data, dest=0, tag=_DATATAG)
                # Makes sure that the last MPI message has processed.
                if req:
                    req.Wait()
                self._data_event_handler.close_event(event=event)

            # After finishing iterating over the events to process, calls the
            # end_processing function, and if the function returns something, sends it
            # to the processing node.
            final_data: Union[
                Dict[str, Any], None
            ] = self._processing_layer.end_processing_on_processing_node(
                node_rank=self._rank, node_pool_size=self._mpi_size
            )
            if final_data is not None:
                if req:
                    req.Wait()
                req = MPI.COMM_WORLD.isend(
                    (final_data, self._rank), dest=0, tag=_DATATAG
                )
                if req:
                    req.Wait()

            # Sends a message to the collecting node saying that there are no more
            # events.
            end_dict = {"end": True}
            if req:
                req.Wait()
            req = MPI.COMM_WORLD.isend((end_dict, self._rank), dest=0, tag=_DATATAG)
            if req:
                req.Wait()
            MPI.Finalize()
            exit(0)

    def shutdown(self, *, msg: str = "Reason not provided.") -> None:
        """
        Shuts down the MPI parallelization.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function stops OM, closing all the communication channels between the
        nodes and managing a controlled shutdown of OM's resources. Additionally, it
        terminates the MPI processes in an orderly fashion.

        Arguments:

            msg: Reason for shutting down. Defaults to "Reason not provided".
        """
        print("Shutting down:", msg)
        sys.stdout.flush()
        if self._rank == 0:
            # Tells all the processing nodes that they need to shut down, then waits
            # for confirmation. During the whole process, keeps receiving normal MPI
            # messages from the nodes (MPI cannot shut down if there are unreceived
            # messages).
            try:
                node_num: int
                for node_num in range(1, self._mpi_size):
                    MPI.COMM_WORLD.isend(0, dest=node_num, tag=_DIETAG)
                num_shutdown_confirm = 0
                while True:
                    if MPI.COMM_WORLD.Iprobe(source=MPI.ANY_SOURCE, tag=_DATATAG):
                        _ = MPI.COMM_WORLD.recv(source=MPI.ANY_SOURCE, tag=_DATATAG)
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
            req = MPI.COMM_WORLD.send(dest=0, tag=_DEADTAG)
            if req:
                req.Wait()
            MPI.Finalize()
            exit(0)
