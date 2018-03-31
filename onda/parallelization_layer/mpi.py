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
An MPI-based parallelization engine for OnDA.

Exports:

    Classes:

        ParallelizationEngine (class): An implementation of an
        MPI-based parallelization engine.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import sys

from mpi4py import MPI

from onda.utils import dynamic_import


# Define some labels for internal MPI communication (just some
# syntactic sugar).
_NOMORE = 998
_DIETAG = 999
_DEADTAG = 1000


class ParallelizationEngine(object):
    """
    An MPI-based master-worker parallelization engine for OnDA.

    An MPI-based parallelization engine that uses a master-worker
    architecture. It is initialized with a data source (a python
    generator) and two functions that are be executed on the worker and
    the master nodes (respectively).

    Each worker node recovers a data event by getting a value from the
    data source. It then executes the map_func function on the
    recovered data. The dictionary returned by the map_func function is
    then transfered to the master node, which executes the reduce_func
    function every time it receives data from a worker node.

    This class should be subclassed to create an OnDA monitor.

    Attributes:

        role (str): 'worker' or 'master', depending the role of the
            node where the attribute is read.

        rank (int): rank (in MPI terms) of the node where the attribute
            is read.
    """

    def __init__(self,
                 map_func,
                 reduce_func,
                 source,
                 monitor_params):
        """
        Initialize the ParallelizationEngine class.

        Args:

            map_func (function): function executed by each worker node
                after recovering a data event.

            reduce_func (function): function executed by the master
                node every time something is received from a worker
                node.

            source (function): a python generator function from which
                worker nodes can recover data (by iterating over it).

            monitor_params (MonitorParams): a MonitorParams object
                containing the monitor parameters from the
                configuration file.
        """
        # Store some initialization parameters into attributes.
        self._map = map_func
        self._reduce = reduce_func
        self._source = source
        self._mon_params = monitor_params

        # Instrospect role of the node, then set the 'role', the 'rank'
        # and the 'mpi_size' attributes accordingly.
        self._mpi_size = MPI.COMM_WORLD.Get_size()
        self.rank = MPI.COMM_WORLD.Get_rank()
        if self.rank == 0:
            self.role = 'master'
        else:
            self.role = 'worker'

        # Call a function that imports the correct event-handling
        # functions from the various layers, then store the imported
        # functions as attributes.
        ehf = dynamic_import.init_event_handling_funcs(
            self._mon_params
        )
        self._initialize_event_source = ehf.initialize_event_source
        self._event_generator = ehf.event_generator
        self._open_event = ehf.open_event
        self._close_event = ehf.close_event
        self._get_num_frames_in_event = ehf.get_num_frames_in_event
        if self.role == 'master':
            # Initialize several counters:
            #
            # num_nomore: when shutting down the monitor, keeps track
            #   of how many worker nodes have already shut down.
            #
            # num_reduced_events: keeps track of the events seen by the
            #   master node.
            self._num_nomore = 0
            self._num_collected_events = 0

        if self.role == 'worker':
            # Instantiate the EventFilter class from the data
            # recovery layer and call a function that recovers the
            # required data extractions functions from the various
            # layers.
            data_rec_layer = dynamic_import.import_data_recovery_layer(
                self._mon_params
            )
            self._event_filter = data_rec_layer.EventFilter(
                self._mon_params
            )

            self._data_extr_funcs = dynamic_import.init_data_extraction_funcs(
                self._mon_params
            )

            # Read from the configuration file (and store) the number
            # of frames that must be processed from each event.
            self._num_frames_in_event_to_process = (
                monitor_params.get_param(
                    section='General',
                    parameter='num_frames_in_event_to_process',
                    type_=int,
                    required=True
                )
            )

    def start(self):
        """
        Start the parallelization engine.

        When called on a worker node, start recovering data and
        processing it. When called on the master node, start listening
        for communications from the worker nodes.
        """

        if self.role == 'master':

            # Initialize the event source.
            self._initialize_event_source(
                source=self._source,
                node_rank=self.rank,
                mpi_pool_size=self._mpi_size,
                monitor_params=self._mon_params
            )

        if self.role == 'worker':

            req = None

            # Iterate over the events provided by the event generator.
            events = self._event_generator(
                source=self._source,
                node_rank=self.rank,
                mpi_pool_size=self._mpi_size,
                monitor_params=self._mon_params
            )
            for event in events:

                # Listen for requests to shut down coming from the
                # master node. If such a request comes, call the
                # shutdown method.
                if MPI.COMM_WORLD.Iprobe(
                        source=0,
                        tag=_DIETAG
                ):
                    self.shutdown(
                        "Shutting down RANK: {0}.".format(self.rank)
                    )

                # Check with if the event filter if the event should be
                # rejected. If it should, skip to next iteration of the
                # loop.
                if self._event_filter.should_reject(event):
                    continue

                # Recover the number of frames in the event and check
                # if the number of frames that should be processed is
                # higher than the number of frames in the event. If it
                # is, limit the number of frames that should be
                # processed.
                n_frames = self._get_num_frames_in_event(event)
                if n_frames < self._num_frames_in_event_to_process:
                    self._num_frames_in_event_to_process = n_frames

                # Open the event and the monitor parameters to the
                # event dictionary, in order for the extraction
                # functions to be able to read the parameters.
                self._open_event(event)
                event['monitor_params'] = self._mon_params

                # Iterate over the frames that should be processed.
                # Assuming than n is the number of frames to be
                # processed, iterate over the last n frames in the
                # event, in the order in which they appear in the
                # event.
                for frame_offset in range(
                        -self._num_frames_in_event_to_process,
                        0
                ):
                    # Add the frame offset to the event dictionary, in
                    # order for the extraction function to know which
                    # frame in the event is currently being processed.
                    event['frame_offset'] = frame_offset

                    # Create a dictionary that will store the extracted
                    # data, then try to extract the data by calling the
                    # data extraction functions one after the other.
                    # Store the values returned by the functions in the
                    # data dictionary, each with a key corresponding to
                    # the name of the extraction function. Skip to the
                    # next event exception if something bad happens.
                    data = {}
                    try:
                        for func in self._data_extr_funcs:
                            data[func.__name__] = func(
                                event=event
                            )
                    except Exception as exc:  # pylint: disable=W0703
                        print(
                            "OnDA Warning: Cannot interpret some event"
                            "data:"
                        )
                        print(
                            "Error extracting {0}: {1}".format(
                                func.__name__,
                                exc
                            )
                        )
                        print("Skipping event.....")
                        continue

                    # Pass the dictionary with extracted data to the
                    # processing function, then send the results to the
                    # master node.
                    result = self._map(data)
                    if req:
                        req.Wait()
                    req = MPI.COMM_WORLD.isend(
                        result,
                        dest=0,
                        tag=0
                    )

                if req:
                    req.Wait()

                # Close the event.
                self._close_event(event)

            # After finishing iterating over the events to process,
            # send a message to the master node saying that there are
            # no more events to process. Then shut down.
            end_dict = {'end': True}
            if req:
                req.Wait()

            MPI.COMM_WORLD.isend(
                buf=(end_dict, self.rank),
                dest=0,
                tag=0
            )
            MPI.Finalize()
            exit(0)
        elif self.role == 'master':
            # Loop continuously, receiving processed data from workers.
            while True:
                try:
                    received_data = MPI.COMM_WORLD.recv(
                        source=MPI.ANY_SOURCE,
                        tag=0
                    )

                    # If the message announces that the worker node has
                    # finished processing data, keep track of how many
                    # worker nodes have already finshed. If all worker
                    # nodes have salready finished, shut down.
                    if 'end' in received_data[0].keys():
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

                    # Execute the collecting function on the received
                    # data, and increase the counter of collected
                    # events.
                    self._reduce(received_data)
                    self._num_collected_events += 1
                except KeyboardInterrupt as exc:
                    # If the user stops the parallelization via the
                    # keyboard, clean up and shut down.
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

        Shut down the parallelization engine. When called on a worker
        node, communicate to the master node that the a shut down is
        going on, then shut down. When called on the master node, tell
        each worker node that it needs to shut down, wait for all the
        workers to confirm that they have indeed shut down, then cease
        operations.

        Args:

            msg (Optional[str]): reason for the shut down of the
                parallelization engine. Defaults to "Reason not
                provided".
        """
        print("Shutting down:", msg)
        sys.stdout.flush()

        if self.role == 'worker':
            # If the function is called on a worker node, tell the
            # master node that you are shutting down, then shut down.
            _ = MPI.COMM_WORLD.send(
                dest=0,
                tag=_DEADTAG
            )
            MPI.Finalize()
            exit(0)

        if self.role == 'master':
            # If the function is called on the master node, tell all
            # the worker nodes to shut down then wait for all the
            # worker nodes to confirm that they have shut down. Each
            # time a worker nodes confirms that it has shutting down,
            # keep track of how many have already confirmed. When all
            # worker nodes have confirmed, stop listening and shut
            # down. During the whole process, keep receiving normal MPI
            # messages from the nodes: MPI cannot shut down if there
            # are unreceived messages.
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
