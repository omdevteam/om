# This file is part of OnDA.
#
# OnDA is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# OnDA is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with OnDA.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2014-2018 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
MPI-based parallelization engine for OnDA.
"""
from __future__ import absolute_import, division, print_function

import sys

from mpi4py import MPI

from onda.utils import dynamic_import, exceptions


# Define some labels for internal MPI communication (just some syntactic sugar).
_NOMORE = 998
_DIETAG = 999
_DEADTAG = 1000


class ParallelizationEngine(object):
    """
    An MPI-based master-worker parallelization engine for OnDA.

    On each worker node, this engine retrieves a data event from the source specified
    by the user, then executes the 'process_func' function on the data. The engine
    then transfers the returned value to the master node. On the master node, it
    executes the 'collect_func' function every time data is received. This class
    should be subclassed to implement an MPI-based OnDA monitor.
    """

    def __init__(self, process_func, collect_func, source, monitor_params):
        """
        Initializes the ParallelizationEngine class.

        Attributes:

            role (str): role of the node calling the function ('worker' or 'master').

            rank (int): rank (in MPI terms) of the node where the attribute is read.

        Args:

            process_func (function): function to be executed on each worker node after
                recovering a data event.

            collect_func (function): function to be executed on the master node every
                time some data is received from a worker node.

            source (str): string describing a data source, to be passed to a
                'event_generator' function imported from the data retrieval layer.

            monitor_params (MonitorParams): :obj:`~onda.utils.parameters.MonitorParams`
                object containing the monitor parameters from the configuration file.
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

        event_handling_functions = dynamic_import.get_event_handling_funcs(
            monitor_params
        )

        if self.role == "worker":

            self._event_generator = event_handling_functions["event_generator"]

            self._num_frames_in_event_to_process = monitor_params.get_param(
                section="General", parameter="num_frames_in_event_to_process", type_=int
            )

            frames_in_event_to_skip = monitor_params.get_param(
                section="General", parameter="frame_indexes_to_skip", type_=list
            )
            if frames_in_event_to_skip:
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
        """
        Starts the parallelization engine.

        On a worker node, starts recovering and processing the data. On the master
        node, starts listening for communications coming from the worker nodes.
        """
        if self.role == "worker":

            # Flag used to make sure that the MPI messages have been sent.
            req = None

            events = self._event_generator(
                source=self._source,
                node_rank=self.rank,
                mpi_pool_size=self._mpi_size,
                monitor_params=self._monitor_params,
            )

            for event in events:
                # Listens for requests to shut down coming from the master node.
                if MPI.COMM_WORLD.Iprobe(source=0, tag=_DIETAG):
                    self.shutdown("Shutting down RANK: {0}.".format(self.rank))

                event.open_event()
                n_frames_in_evt = event.get_num_frames_in_event()

                if self._num_frames_in_event_to_process:
                    num_frames_to_process = min(
                        n_frames_in_evt, self._num_frames_in_event_to_process
                    )
                else:
                    num_frames_to_process = n_frames_in_evt

                # Iterates over the last n frames in the event, where n is
                # 'num_frames_to_process'.
                for frame_offset in range(-num_frames_to_process, 0):
                    # If the frame must be rejected, skips to next iteration of the
                    # loop.

                    current_frame = n_frames_in_evt + frame_offset
                    if current_frame in self._frames_in_event_to_skip:
                        continue
                    event.current_frame = current_frame

                    try:
                        data = event.extract_data()
                    except exceptions.DataExtractionError as exc:  # pylint: disable=broad-except
                        print(exc)
                        print("Skipping event...")
                        continue

                    result = self._map(data)
                    if req:
                        req.Wait()
                    req = MPI.COMM_WORLD.isend(result, dest=0, tag=0)

                # Makes sure that the last MPI message has been sent.
                if req:
                    req.Wait()

                event.close_event()

            # After finishing iterating over the events to process, sends a message to
            # the master node saying that there are no more events to process.
            end_dict = {"end": True}
            req = MPI.COMM_WORLD.isend((end_dict, self.rank), dest=0, tag=0)
            if req:
                req.Wait()

            MPI.Finalize()
            exit(0)

        if self.role == "master":

            event_source = (
                self._initialize_event_source(  # pylint: disable=unused-variable
                    source=self._source,
                    mpi_pool_size=self._mpi_size,
                    monitor_params=self._monitor_params,
                )
            )
                
            while True:
                try:
                    received_data = MPI.COMM_WORLD.recv(source=MPI.ANY_SOURCE, tag=0)

                    if "end" in received_data[0].keys():
                        # If the message announces a worker node has finished
                        # processing data, keeps track of how many worker nodes have
                        # already finished. When all workers have finished, calls the
                        # 'end_processing' function, then shuts down.
                        print("Finalizing {}".format(received_data[1]))

                        self._num_nomore += 1
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
                    print("Recieved keyboard sigterm...")
                    print(str(exc))
                    print("shutting down MPI.")
                    self.shutdown()
                    print("---> execution finished.")
                    sys.stdout.flush()
                    exit(0)

    def shutdown(self, msg="Reason not provided."):
        """
        Shuts down the parallelization engine.

        On a worker node, this function communicates to the master node that the
        worker is shutting down, then shuts down. On the master node, it tells each
        worker node to shut down, waits for all the workers to confirm that they have
        indeed shut down, then ceases operations.

        Args:

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
            # Tells all the worker nodes to shut down and waits for confirmation.
            # During the whole process, keeps receiving normal MPI messages from the
            # nodes (MPI cannot shut down if there are unreceived messages).
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

                # When all the worker nodes have confirmed, shuts down.
                MPI.Finalize()
                exit(0)
            except RuntimeError:
                # In case of error in the clean shut down procedure, crashes hard!
                MPI.COMM_WORLD.Abort(0)
                exit(0)

    def end_processing(self):
        """
        Executes end-of-processing actions.

        This function executes some final actions at the end of the processing and
        exits. By default, prints a message to the console. This function is called by
        the parallelization engine at the end of the data processing and can be
        overridden in a derived class to implement custom end-of-processing actions.
        """
        print(
            "Processing finished. OnDA has processed {} events in total.".format(
                self._num_collected_events
            )
        )
        sys.stdout.flush()
