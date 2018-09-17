#    This file is part of OnDA.
#
#    OnDA is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    OnDA is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with OnDA.  If not, see <http://www.gnu.org/licenses/>.
"""
MPI-based parallelization engine.

This module contains the implementation of an MPI-based parallelization
engine for OnDA.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import sys

from future.utils import iteritems
from mpi4py import MPI

from onda.utils import dynamic_import

# Define some labels for internal MPI communication (just some
# syntactic sugar).
_NOMORE = 998
_DIETAG = 999
_DEADTAG = 1000


class ParallelizationEngine(object):
    """
    See __init__ for documentation.
    """

    def __init__(self,
                 process_func,
                 collect_func,
                 source,
                 monitor_params):
        """
        An MPI-based master-worker parallelization engine for OnDA.

        On each worker node, retrieve a data event from the source
        specified by the user, then execute the 'process_func' function
        on the data. Transfer the returned value to the master node.
        On the master node, execute the 'collect_func' function
        every time data is received. This class should be subclassed
        to implement an MPI-based OnDA monitor.

        Attributes:

            role (str): role of the node calling the function
                ('worker' or 'master').

            rank (int): rank (in MPI terms) of the node where the
                attribute is read.

        Args:

            process_func (function): function to be executed on each
                worker node after recovering a data event.

            collect_func (function): function to be executed on the
                master node every time some data is received from a
                worker node.

            source (str): a string describing a data source, to be
                passed to a 'event_generator' function imported from
                the data retrieval layer.

            monitor_params (MonitorParams): a
                :obj:`~onda.utils.parameters.MonitorParams` object
                containing the monitor parameters from the
                configuration file.
        """
        self._map = process_func
        self._reduce = collect_func
        self._source = source
        self._mon_params = monitor_params

        self._mpi_size = MPI.COMM_WORLD.Get_size()
        self.rank = MPI.COMM_WORLD.Get_rank()
        if self.rank == 0:
            self.role = 'master'
        else:
            self.role = 'worker'

        evt_han_fns = dynamic_import.get_event_handling_funcs(
            self._mon_params
        )
        self._initialize_event_source = evt_han_fns['initialize_event_source']
        self._event_generator = evt_han_fns['event_generator']
        self._open_event = evt_han_fns['open_event']
        self._close_event = evt_han_fns['close_event']
        self._get_num_frames_in_event = evt_han_fns['get_num_frames_in_event']

        if self.role == 'worker':
            self._event_filter = evt_han_fns['EventFilter'](self._mon_params)
            self._frame_filter = evt_han_fns['FrameFilter'](self._mon_params)
            self._data_extr_funcs = dynamic_import.get_data_extraction_funcs(
                self._mon_params
            )

            self._num_frames_in_event_to_process = (
                monitor_params.get_param(
                    section='General',
                    parameter='num_frames_in_event_to_process',
                    type_=int
                )
            )

            if not self._num_frames_in_event_to_process:
                self._num_frames_in_event_to_process = 1


        if self.role == 'master':
            self._num_nomore = 0
            self._num_collected_events = 0

    def start(self):
        """
        Start the parallelization engine.

        On a worker node, start recovering and processing the data.
        On the master node, start listening for communications coming
        from the worker nodes.
        """
        if self.role == 'worker':

            # Flag used to make sure that the MPI messages have been
            # sent.
            req = None

            events = self._event_generator(
                source=self._source,
                node_rank=self.rank,
                mpi_pool_size=self._mpi_size,
                monitor_params=self._mon_params
            )

            for event in events:

                # Listen for requests to shut down coming from the
                # master node.
                if MPI.COMM_WORLD.Iprobe(
                        source=0,
                        tag=_DIETAG
                ):
                    self.shutdown(
                        "Shutting down RANK: {0}.".format(self.rank)
                    )

                # If the event must be rejected, skip to next iteration
                # of the loop.
                if self._event_filter.should_reject(event):
                    continue

                self._open_event(event)
                n_frames_in_evt = self._get_num_frames_in_event(event)
                if n_frames_in_evt < self._num_frames_in_event_to_process:
                    self._num_frames_in_event_to_process = n_frames_in_evt

                # Add the monitor parameters to the event dictionary,
                # in order for the extraction functions to be able to
                # read the parameters.
                event['monitor_params'] = self._mon_params

                # Iterate over the last n frames in the event, wher n
                # is 'num_frames_in_event_to_process'.
                for frame_offset in range(
                        -self._num_frames_in_event_to_process,
                        0
                ):
                    # If the frame must be rejected, skip to next
                    # iteration of the loop.
                    if self._frame_filter.should_reject(
                            num_frames_in_event=n_frames_in_evt,
                            frame_offset=frame_offset
                    ):
                        continue

                    event['frame_offset'] = frame_offset
                    data = {}

                    # Try to extract the data by calling the data
                    # extraction functions one after the other. Store
                    # the values returned by the functions in the data
                    # dictionary, each with a key corresponding to
                    # the name of the extraction function.
                    try:
                        for f_name, func in iteritems(self._data_extr_funcs):
                            data[f_name] = func(event)
                    except Exception as exc:  # pylint: disable=W0703
                        print(
                            "OnDA Warning: Cannot interpret some event"
                            "data:"
                        )
                        print(
                            "Error extracting {}: {}".format(
                                func.__name__,
                                exc
                            )
                        )
                        print("Skipping event.....")
                        continue

                    result = self._map(data)
                    if req:
                        req.Wait()
                    req = MPI.COMM_WORLD.isend(
                        result,
                        dest=0,
                        tag=0
                    )

                # Make sure that the last MPI message has been sent.
                if req:
                    req.Wait()

                self._close_event(event)

            # After finishing iterating over the events to process,
            # send a message to the master node saying that there are
            # no more events to process.
            end_dict = {'end': True}
            req = MPI.COMM_WORLD.isend(
                buf=(end_dict, self.rank),
                dest=0,
                tag=0
            )
            if req:
                req.Wait()

            MPI.Finalize()
            exit(0)

        if self.role == 'master':
            self._initialize_event_source(
                source=self._source,
                node_rank=self.rank,
                mpi_pool_size=self._mpi_size,
                monitor_params=self._mon_params
            )

            while True:
                try:
                    received_data = MPI.COMM_WORLD.recv(
                        source=MPI.ANY_SOURCE,
                        tag=0
                    )

                    if 'end' in received_data[0].keys():

                        # If the message announces a worker node has
                        # finished processing data, keep track of how
                        # many worker nodes have already finished. When
                        # all workers have finished, call the
                        # 'end_processing' function, then shut down.
                        print(
                            "Finalizing {}".format(received_data[1])
                        )

                        self._num_nomore += 1
                        if self._num_nomore == self._mpi_size - 1:
                            print("All workers have run out of events.")
                            print("Shutting down.")
                            sys.stdout.flush()
                            self.end_processing()

                            MPI.Finalize()
                            exit(0)

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
        Shut down the parallelization engine.

        On a worker node, communicate to the master node that the
        worker is shutting down, then shut down. On the master node,
        tell each worker node to shut down, wait for all the workers to
        confirm that they have indeed shut down, then cease operations.

        Args:

            msg (Optional[str]): reason for shutting down of the
                parallelization engine. Defaults to "Reason not
                provided".
        """
        print("Shutting down:", msg)
        sys.stdout.flush()

        if self.role == 'worker':
            _ = MPI.COMM_WORLD.send(
                dest=0,
                tag=_DEADTAG
            )
            MPI.Finalize()
            exit(0)

        if self.role == 'master':

            # Tell all the worker nodes to shut down and wait for
            # confirmation. During the whole process, keep receiving
            # normal MPI messages from the nodes: MPI cannot shut down
            # if there are unreceived messages.
            try:
                for nod_num in range(1, self._mpi_size()):
                    MPI.COMM_WORLD.isend(
                        0,
                        dest=nod_num,
                        tag=_DIETAG
                    )

                num_shutdown_confirm = 0
                while True:

                    if MPI.COMM_WORLD.Iprobe(
                            source=MPI.ANY_SOURCE,
                            tag=0
                    ):
                        _ = MPI.COMM_WORLD.recv(
                            source=MPI.ANY_SOURCE,
                            tag=0
                        )

                    if MPI.COMM_WORLD.Iprobe(
                            source=MPI.ANY_SOURCE,
                            tag=_DEADTAG
                    ):
                        num_shutdown_confirm += 1

                    if num_shutdown_confirm == self._mpi_size() - 1:
                        break

                # When all the worker nodes have confirmed, shut down.
                MPI.Finalize()
                exit(0)

            except RuntimeError:

                # In case of error in the clean shut down procedure,
                # crash hard!
                MPI.COMM_WORLD.Abort(0)
                exit(0)

    def end_processing(self):
        """
        Execute end-of-processing actions.

        Execute some final actions at the end of the processing and
        exit. By default, print a message to the console. This function
        is called by the parallelization engine at the end of the data
        processing and can be overridden in a derived class to
        implement custom end-of-processing actions.
        """
        print(
            "Processing finished. OnDA has processed {} events in "
            "total.".format(
                self._num_collected_events
            )
        )
        sys.stdout.flush()
