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
MPI-based Parallelization Engine for OM.

This module contains a Parallelization Engine for OM which uses the MPI communication
rotocol to manage the communication between the nodes.
"""
import sys
from typing import Any, Dict, Tuple, Union

from mpi4py import MPI  # type: ignore

from om.data_retrieval_layer import base as data_ret_layer_base
from om.parallelization_layer import base as par_layer_base
from om.processing_layer import base as process_layer_base
from om.utils import exceptions, parameters

# Define some labels for internal MPI communication (just some syntactic sugar).
_NOMORE: int = 998
_DIETAG: int = 999
_DEADTAG: int = 1000


class MpiParallelizationEngine(par_layer_base.OmParallelizationEngine):
    """
    See documentation of the `__init__` function.

    Base class: [`OmParallelizationEngine`]
    [om.parallelization_layer.base.OmParallelizationEngine]
    """

    def __init__(
        self,
        data_event_handler: data_ret_layer_base.OmDataEventHandler,
        monitor: process_layer_base.OmMonitor,
        monitor_parameters: parameters.MonitorParams,
    ) -> None:
        """
        MPI-based Parallelization Engine for OM.

        This class implements a Parallelization Engine based on the MPI protocol. It is
        a subclass of the [OmParallelizationEngine]
        [om.parallelization_layer.base.OmParallelizationEngine] base class. In this
        Engine, the nodes communicate with each other using an implementation of the
        MPI protocol supported by the Python language.

        Arguments:

            data_event_handler: A class defining how data events are retrieved and
                handled.

            monitor: A class defining the how the retrieved data must be processed.

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.
        """
        super(MpiParallelizationEngine, self).__init__(
            data_event_handler=data_event_handler,
            monitor=monitor,
            monitor_parameters=monitor_parameters,
        )

        self._mpi_size: int = MPI.COMM_WORLD.Get_size()
        self._rank: int = MPI.COMM_WORLD.Get_rank()

        if self._rank == 0:
            self._data_event_handler.initialize_event_handling_on_collecting_node(
                self._rank, self._mpi_size
            )
            self._num_nomore: int = 0
            self._num_collected_events: int = 0
        else:
            self._data_event_handler.initialize_event_handling_on_processing_node(
                self._rank, self._mpi_size
            )

    def start(self) -> None:  # noqa: C901
        """
        Starts the MPI parallelization engine.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function sets up the communication between OM's collecting and processing
        nodes using the MPI protocol. Additionally, it manages the interaction between
        the nodes while OM is running, receiving and dispatching data and control
        commands over MPI channels.
        """
        if self._rank == 0:
            print(
                "You are using an OM real-time monitor. Please cite: "
                "Mariani et al., J Appl Crystallogr. 2016 May 23;49(Pt 3):1073-1080"
            )
            self._monitor.initialize_collecting_node(self._rank, self._mpi_size)

            while True:
                try:
                    received_data: Tuple[Dict[str, Any], int] = MPI.COMM_WORLD.recv(
                        source=MPI.ANY_SOURCE, tag=0
                    )
                    if "end" in received_data[0].keys():
                        # If the received message announces that a processing node has
                        # finished processing data, keeps track of how many processing
                        # nodes have already finished.
                        print("Finalizing {0}".format(received_data[1]))
                        self._num_nomore += 1
                        # When all processing nodes have finished, calls the
                        # 'end_processing_on_collecting_node' function then shuts down.
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
                node_rank=self._rank,
                node_pool_size=self._mpi_size,
            )

            event: Dict[str, Any]
            for event in events:
                # Listens for requests to shut down.
                if MPI.COMM_WORLD.Iprobe(source=0, tag=_DIETAG):
                    self.shutdown("Shutting down RANK: {0}.".format(self._rank))

                self._data_event_handler.open_event(event)
                n_frames_in_evt: int = self._data_event_handler.get_num_frames_in_event(
                    event
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
                            event
                        )
                    except exceptions.OmDataExtractionError as exc:
                        print(exc)
                        print("Skipping event...")
                        continue
                    processed_data: Tuple[
                        Dict[str, Any], int
                    ] = self._monitor.process_data(self._rank, self._mpi_size, data)
                    if req:
                        req.Wait()
                    req = MPI.COMM_WORLD.isend(processed_data, dest=0, tag=0)
                # Makes sure that the last MPI message has processed.
                if req:
                    req.Wait()
                self._data_event_handler.close_event(event)

            # After finishing iterating over the events to process, calls the
            # end_processing function, and if the function returns something, sends it
            # to the processing node.
            final_data: Union[
                Dict[str, Any], None
            ] = self._monitor.end_processing_on_processing_node(
                self._rank, self._mpi_size
            )
            if final_data is not None:
                req = MPI.COMM_WORLD.isend((final_data, self._rank), dest=0, tag=0)
                if req:
                    req.Wait()

            # Sends a message to the collecting node saying that there are no more
            # events.
            end_dict = {"end": True}
            req = MPI.COMM_WORLD.isend((end_dict, self._rank), dest=0, tag=0)
            if req:
                req.Wait()
            MPI.Finalize()
            exit(0)

    def shutdown(self, msg: Union[str, None] = "Reason not provided.") -> None:
        """
        Shuts down the MPI parallelization engine.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        When OM stops, this function closes the communication between the processing
        and collecting nodes, and manages a controlled shutdown of OM's resources,
        terminating the MPI processes in an orderly fashion.

        Arguments:

            msg: Reason for shutting down the parallelization engine. Defaults to
                "Reason not provided".
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
