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

This module contains an MPI-based parallelization engine for OM, based on a
master/worker architecture.
"""
from __future__ import absolute_import, division, print_function

import json
import sys
from typing import Any, Dict, Callable, Optional, Tuple

from mpi4py import MPI

from om.utils import (
    dynamic_import,
    exceptions,
    parameters,
)


# Define some labels for internal MPI communication (just some syntactic sugar).
_NOMORE = 998
_DIETAG = 999
_DEADTAG = 1000


class ParallelizationEngine(object):
    """
    See documentation of the __init__ function.
    """

    def __init__(
        self,
        process_func,  # type: Callable[[Dict[str, Any]], Dict[str, Any]]
        collect_func,  # type: Callable[[Dict[str, Any]], None]
        source,  # type: str
        monitor_params,  # type:  parameters.MonitorParams
    ):
        # type (...) -> None
        """
        An MPI-based master-worker parallelization engine for OM.

        This engine starts several processing worker nodes and an aggregating worker
        node. The nodes  communicate with each other using the MPI protocol. When the
        engine starts, two functions, 'process_func' and 'collect_func', are attached
        to it. The engine operates according to the following rules:

        * On each worker node, the engine retrieves one data event from a source.
          It then executes the 'process_func' function on every frame in the event.
          Each time, it makes sure that the object returned by the function is
          transferred to the master node.

        * On the master node, the engine executes the 'collect_func' function every
          time an object is transferred from a worker node. The engine passes the
          received object to the function.

        * When all events from the source have been processed, the engine performs
          some final clean-up tasks and shuts down.

        NOTE: This class is designed to be subclassed to create an OM monitor.

        Arguments:

            process_func (Callable[[Dict[str, Any]], Dict[str, Any]]): the function
                that will be called on each worker node for every frame in a data
                event. The 'ProcessedData' named tuple returned by this function will
                be transferred to the master node.

            collect_func (Callable[[Dict[str, Any], None]): the function that will run
                on the master node every time a 'ProcessedData' named tuple is
                transferred from a worker node.

            source (str): a string describing a source of event data. The exact format
                of the string depends on the specific Data Recovery Layer currently
                being used. See the documentation of the relevant
                'initialize_event_source' function).

            monitor_params (:class:`~om.utils.parameters.MonitorParams`): an object
                storing the OM monitor parameters from the configuration file.

        Attributes:

            role (str): the role of the current node ('worker' or 'master').

            rank (int): the rank (in MPI terms) of the current node.
        """
        self._map = process_func
        self._reduce = collect_func
        self._source = source
        self._monitor_params = monitor_params

        self._mpi_size = MPI.COMM_WORLD.Get_size()
        self.rank = MPI.COMM_WORLD.Get_rank()
        if self.rank == 0:
            self.role = "master"
        else:
            self.role = "worker"

        data_retrieval_layer_filename = monitor_params.get_param(
            group="om",
            parameter="data_retrieval_layer",
            parameter_type=str,
            required=True,
        )
        data_retrieval_layer = dynamic_import.import_data_retrieval_layer(
            data_retrieval_layer_filename=data_retrieval_layer_filename
        )
        event_handling_functions = dynamic_import.get_event_handling_funcs(
            data_retrieval_layer=data_retrieval_layer
        )

        if self.role == "worker":
            self._event_generator = event_handling_functions["event_generator"]
            self._num_frames_in_event_to_process = monitor_params.get_param(
                group="data_retrieval_layer",
                parameter="num_of_most_recent_frames_in_event_to_process",
                parameter_type=int,
            )
            frames_in_event_to_skip = monitor_params.get_param(
                group="data_retrieval_layer",
                parameter="frame_indexes_to_skip",
                parameter_type=list,
            )
            if frames_in_event_to_skip is not None:
                self._frames_in_event_to_skip = tuple(frames_in_event_to_skip)
            else:
                self._frames_in_event_to_skip = tuple()

        if self.role == "master":
            self._initialize_event_source = event_handling_functions[
                "initialize_event_source"
            ]
            self._num_nomore = 0
            self._num_collected_events = 0

    def start(self):
        # type () -> None
        """
        Starts the parallelization engine.

        * When this function is called on a worker node, the node starts retrieving data
          events and processing them.

        * When this function is called on the master node, the node starts receiving
          data from the worker nodes and aggregating it.
        """
        if self.role == "worker":
            # Flag used to make sure that the MPI messages have been processed.
            req = None
            events = self._event_generator(
                source=self._source,
                node_rank=self.rank,
                node_pool_size=self._mpi_size,
                monitor_params=self._monitor_params,
            )

            for event in events:
                # Listens for requests to shut down.
                if MPI.COMM_WORLD.Iprobe(source=0, tag=_DIETAG):
                    self.shutdown("Shutting down RANK: {0}.".format(self.rank))
                event.open_event()
                n_frames_in_evt = event.get_num_frames_in_event()
                if self._num_frames_in_event_to_process is not None:
                    num_frames_to_process = min(
                        n_frames_in_evt, self._num_frames_in_event_to_process
                    )
                else:
                    num_frames_to_process = n_frames_in_evt
                # Iterates over the last 'num_frames_to_process' frames in the event.
                for frame_offset in range(-num_frames_to_process, 0):
                    current_frame = n_frames_in_evt + frame_offset
                    if current_frame in self._frames_in_event_to_skip:
                        continue
                    event.current_frame = current_frame
                    try:
                        data = event.extract_data()  # type: Dict[str, Any]
                    except exceptions.OmDataExtractionError as exc:
                        print(exc)
                        print("Skipping event...")
                        continue
                    result = self._map(data)
                    if req:
                        req.Wait()
                    req = MPI.COMM_WORLD.isend(result, dest=0, tag=0)
                # Makes sure that the last MPI message has processed.
                if req:
                    req.Wait()
                event.close_event()

            # After finishing iterating over the events to process, sends a message to
            # the master node saying that there are no more events.
            end_dict = {"end": True}
            req = MPI.COMM_WORLD.isend((end_dict, self.rank), dest=0, tag=0)
            if req:
                req.Wait()
            MPI.Finalize()
            exit(0)

        if self.role == "master":
            print("Starting OM with the following parameters:")
            print(
                json.dumps(
                    self._monitor_params.get_all_parameters(), indent=4, sort_keys=True
                )
            )
            print(
                "You are using an OnDA real-time monitor. Please cite: "
                "Mariani et al., J Appl Crystallogr. 2016 May 23;49(Pt 3):1073-1080"
            )
            _ = self._initialize_event_source(
                source=self._source,
                node_pool_size=self._mpi_size,
                monitor_params=self._monitor_params,
            )
            while True:
                try:
                    received_data = MPI.COMM_WORLD.recv(source=MPI.ANY_SOURCE, tag=0)
                    if "end" in received_data["data"].keys():
                        # If the received message announces that a worker node has
                        # finished processing data, keeps track of how many worker
                        # nodes have already finished.
                        print("Finalizing {0}".format(received_data[1]))
                        self._num_nomore += 1
                        # When all workers have finished, calls the 'end_processing'
                        # function then shuts down.
                        if self._num_nomore == self._mpi_size - 1:
                            print("All workers have run out of events.")
                            print("Shutting down.")
                            sys.stdout.flush()
                            self.end_processing()
                            MPI.Finalize()
                            exit(0)
                        else:
                            continue
                    self._reduce(received_data)
                    self._num_collected_events += 1
                except KeyboardInterrupt as exc:
                    print("Received keyboard sigterm...")
                    print(str(exc))
                    print("shutting down MPI.")
                    self.shutdown()
                    print("---> execution finished.")
                    sys.stdout.flush()
                    sys.exit(0)

    def shutdown(self, msg="Reason not provided."):
        # type (Optional[str]) -> None
        """
        Shuts down the parallelization engine.

        * When this function is called on a worker node, the worker communicates to the
          master node that it is shutting down, then shuts down.

        * When this function is called on the master node, the master tells each worker
          to shut down, waits for all the workers to confirm that they done that, then
          shuts down.

        Arguments:

            msg (Optional[str]): reason for shutting down the parallelization engine.
                Defaults to "Reason not provided".
        """
        print("Shutting down:", msg)
        sys.stdout.flush()
        if self.role == "worker":
            _ = MPI.COMM_WORLD.send(dest=0, tag=_DEADTAG)
            MPI.Finalize()
            exit(0)
        if self.role == "master":
            # Tells all the worker nodes that they need to shut down, then waits for
            # confirmation. During the whole process, keeps receiving normal MPI
            # messages from the nodes (MPI cannot shut down if there are unreceived
            # messages).
            try:
                for nod_num in range(1, self._mpi_size()):
                    MPI.COMM_WORLD.isend(0, dest=nod_num, tag=_DIETAG)
                num_shutdown_confirm = 0
                while True:
                    if MPI.COMM_WORLD.Iprobe(source=MPI.ANY_SOURCE, tag=0):
                        _ = MPI.COMM_WORLD.recv(source=MPI.ANY_SOURCE, tag=0)
                    if MPI.COMM_WORLD.Iprobe(source=MPI.ANY_SOURCE, tag=_DEADTAG):
                        num_shutdown_confirm += 1
                    if num_shutdown_confirm == self._mpi_size() - 1:
                        break
                # When all the worker nodes have confirmed, shuts down the master.
                MPI.Finalize()
                exit(0)
            except RuntimeError:
                # In case of error, crashes hard!
                MPI.COMM_WORLD.Abort(0)
                exit(0)

    def end_processing(self):
        # type () -> None
        """
        Executes end-of-processing actions.

        This function is called by the parallelization engine on the master node at the
        end of the processing, immediately before stopping. By default, it prints a
        message to the console and exits. It can be overridden in a derived class to
        implement custom end-of-processing actions.
        """
        print(
            "Processing finished. OnDA has processed {0} events in total.".format(
                self._num_collected_events
            )
        )
        sys.stdout.flush()
