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
import multiprocessing
import queue
import sys
import zmq
from concurrent.futures import process
from email import message
from pickle import NONE
from sqlite3 import connect
from typing import Any, Dict, List, Tuple, Union

from om.abcs import data_retrieval_layer as drl_abcs
from om.abcs import parallelization_layer as parl_abcs
from om.abcs import processing_layer as prol_abcs
from om.utils import exceptions, parameters, zmq_monitor
from om.utils.rich_console import console, get_current_timestamp


def _om_processing_node(
    *,
    rank: int,
    node_pool_size: int,
    #data_queue: "multiprocessing.Queue[Tuple[Dict[str, Any], int]]",
    #message_pipe: multiprocessing.connection.Connection,
    data_event_handler: drl_abcs.OmDataEventHandlerBase,
    processing_layer: prol_abcs.OmProcessingBase,
    monitor_params: parameters.MonitorParams,
) -> None:
    # This function implements a processing node. It is designed to be run as a
    # subprocess
    # We need to creat two ZMQ sockets (Push, Sub) e.g. taskwork.py, wuproxy.py 
    num_frames_in_event_to_process: int = monitor_params.get_parameter(
        group="data_retrieval_layer",
        parameter="num_frames_in_event_to_process",
        parameter_type=int,
    )
    
    context = zmq.Context()

    sender_push = context.socket(zmq.PUSH)
    sender_push.connect(f"tcp://{zmq_monitor.get_current_machine_ip()}:5555")

    
    # This is where the worker servers recieve instruction (Sub)
    # from collecting layer (Pub)
    
    socket_sub = context.socket(zmq.SUB)
    socket_sub.connect(f"tcp://{zmq_monitor.get_current_machine_ip()}:5556")

    
    # subscription to specific string that matches with rank/string number
    # "{}#".format(rank)  [i.e. "hello {}".format(name)
    # f"Hello {name}" 
    # Hence, we can use, f"{rank}#" to avoid partial matching
    # i.e rank = 4,  string output : "4#" for rank = 4
    # socket.setsockopt_string(zmq.SUBSCRIBE, zip_filter)

    socket_sub.setsockopt_string(
        option=zmq.SUBSCRIBE,
        optval=f"{rank}#"
    )
    
    socket_sub.setsockopt_string(
        option=zmq.SUBSCRIBE,
        optval="all#"
    )

    zmq_poller = zmq.Poller()
    zmq_poller.register(socket_sub, zmq.POLLIN)

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

    event: Dict[str, Any]
    for event in events:

        feedback_dict: Dict[str, Any] = {}
        # We need to check if there's message in the (Sub) socket, instead of message in the pipe. 
        # Remember to initilize the ZMQ context first.  
        
        socks = dict(zmq_poller.poll(0))
        if socket_sub in socks and socks[socket_sub] == zmq.POLLIN:
  
        # Look into: send_pyobj, recieve_obj 
        #------------------------------------------------------------------  
            _ = socket_sub.recv_string()
            message: Dict[str, Any] = socket_sub.recv_pyobj()
            if "stop" in message:
                console.print(f"{get_current_timestamp()} Shutting down RANK: {rank}.")
                sender_push.send_pyobj(({"stopped": True}, rank))
                return
            else:
                feedback_dict = message
                


        data_event_handler.open_event(event=event)
        n_frames_in_evt: int = data_event_handler.get_num_frames_in_event(event=event)
        if num_frames_in_event_to_process is not None:
            num_frames_to_process: int = min(
                n_frames_in_evt, num_frames_in_event_to_process
            )
        else:
            num_frames_to_process = n_frames_in_evt
        # Iterates over the last 'num_frames_to_process' frames in the event.
        
        
        frame_offset: int
        for frame_offset in range(-num_frames_to_process, 0):
            current_frame: int = n_frames_in_evt + frame_offset
            event["current_frame"] = current_frame
            try:
                data: Dict[str, Any] = data_event_handler.extract_data(event=event)
            except exceptions.OmDataExtractionError as exc:
                console.print(f"{get_current_timestamp()} {exc}", style="warning")
                console.print(
                    f"{get_current_timestamp()} Skipping event...", style="warning"
                )
                continue
            data.update(feedback_dict)
            processed_data: Tuple[Dict[str, Any], int] = processing_layer.process_data(
                node_rank=rank, node_pool_size=node_pool_size, data=data
            )
            sender_push.send_pyobj(processed_data)
        # Makes sure that the last MPI message has processed.
        data_event_handler.close_event(event=event)

    # After finishing iterating over the events to process, calls the
    # end_processing function, and if the function returns something, sends it
    # to the processing node.
    final_data: Union[
        Dict[str, Any], None
    ] = processing_layer.end_processing_on_processing_node(
        node_rank=rank, node_pool_size=node_pool_size
    )
    if final_data is not None:
        sender_push.send_pyobj((final_data, rank))

    # Sends a message to the collecting node saying that there are no more
    # events.
    end_dict = {"end": True}
    sender_push.send_pyobj((end_dict, rank))
    return


class ZmqParallelization(parl_abcs.OmParallelizationBase):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        data_retrieval_layer: drl_abcs.OmDataRetrievalBase,
        processing_layer: prol_abcs.OmProcessingBase,
        monitor_parameters: parameters.MonitorParams,
    ) -> None:
        """
        Multiprocessing-based Parallelization Layer for OM.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class implements a Parallelization Layer based on Python's multiprocessing
        module. Each processing node is spawned as a subprocess. The parent process
        acts as a collecting node and additionally manages the child processes. This
        method generates all the subprocesses, and sets up all the comunication
        channels through which data and control commands are received and dispatched.

        Arguments:

            data_retrieval_layer: A class defining how data and data events are
                retrieved and handled.

            processing_layer: A class defining how retrieved data is processed.

            monitor_parameters: An object storing OM's configuration parameters.
        """
        
        #self._subscription_string: str = tag
        self._zmq_context: Any = zmq.Context()

        self._receiver_pull = self._zmq_context.socket(zmq.PULL)
        self._receiver_pull.bind(f"tcp://{zmq_monitor.get_current_machine_ip()}:5555")

        self._socket_pub = self._zmq_context.socket(zmq.PUB)
        self._socket_pub.bind(f"tcp://{zmq_monitor.get_current_machine_ip()}:5556")
    
        self._zmq_poller = zmq.Poller()
        self._zmq_poller.register(self._receiver_pull, zmq.POLLIN)
     
 
        self._data_event_handler: drl_abcs.OmDataEventHandlerBase = (
            data_retrieval_layer.get_data_event_handler()
        )
        self._processing_layer: prol_abcs.OmProcessingBase = processing_layer
        self._monitor_params: parameters.MonitorParams = monitor_parameters

        self._num_frames_in_event_to_process: int = self._monitor_params.get_parameter(
            group="data_retrieval_layer",
            parameter="num_frames_in_event_to_process",
            parameter_type=int,
        )

        self._node_pool_size: int = self._monitor_params.get_parameter(
            group="om", parameter="node_pool_size", parameter_type=int, required=True
        )


        #Initilize two the ZMQ sockets (Pull, Pub) e.g. tasksink.py, wuserver.py
        self._processing_nodes: List[multiprocessing.Process] = []
        #self._message_pipes: List[multiprocessing.connection.Connection] = []
        #self._data_queue: multiprocessing.queues.Queue[
        #    Tuple[Dict[str, Any], int]
        #] = multiprocessing.Queue()
        
        # context = zmq.Context()

        # receiver_pull = context.socket(zmq.PULL)
        # receiver_pull.bind("tcp://127.0.0.1:5555")
        
        # socket_pub = context.socket(zmq.PUB)
        # socket_pub.bind("tcp://127.0.0.1:5556")



        processing_node_rank: int
        for processing_node_rank in range(1, self._node_pool_size):
            #message_pipe: Tuple[
            #    multiprocessing.connection.Connection,
            #   multiprocessing.connection.Connection,
            #] = multiprocessing.Pipe(duplex=False)
            #self._message_pipes.append(message_pipe[1])
            
            
            processing_node = multiprocessing.Process(
                target=_om_processing_node,
                kwargs={
                    "rank": processing_node_rank,
                    "node_pool_size": self._node_pool_size,
            #        "data_queue": self._data_queue,
            #        "message_pipe": message_pipe[0],
                    "data_event_handler": self._data_event_handler,
                    "processing_layer": self._processing_layer,
                    "monitor_params": self._monitor_params,
                },
            )
            self._processing_nodes.append(processing_node)

        self._rank: int = 0
        self._data_event_handler.initialize_event_handling_on_collecting_node(
            node_rank=self._rank, node_pool_size=self._node_pool_size
        )
        self._num_nomore: int = 0
        self._num_collected_events: int = 0
        print("debug ZMQ")

    def start(self) -> None:  # noqa: C901
        """
        Starts the multiprocessing parallelization.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        The function starts the nodes and manages all of their interactions
        """
        console.rule(
            "You are using an OM real-time monitor. Please cite: "
            "Mariani et al., J Appl Crystallogr. 2016 May 23;49(Pt 3):1073-1080",
        )
        for processing_node in self._processing_nodes:
            processing_node.start()

        self._processing_layer.initialize_collecting_node(
            node_rank=self._rank, node_pool_size=self._node_pool_size
        )
        
      
        
        while True:
            try:
                socks = dict(self._zmq_poller.poll(0))
                if self._receiver_pull in socks and socks[self._receiver_pull] == zmq.POLLIN:
                    received_data: Tuple[ 
                        Dict[str, Any], int 
                    ] = self._receiver_pull.recv_pyobj()

                    if "end" in received_data[0]:
                        # If the received message announces that a processing node has
                        # finished processing data, keeps track of how many processing
                        # nodes have already finished.
                        console.print(
                            f"{get_current_timestamp()} Finalizing {received_data[1]}"
                        )
                        self._num_nomore += 1
                        # When all processing nodes have finished, calls the
                        # 'end_processing_on_collecting_node' function then shuts down.
                        if self._num_nomore == self._node_pool_size - 1:
                            console.print(
                                f"{get_current_timestamp()} All processing nodes have run "
                                "out of events."
                            )
                            console.print(f"{get_current_timestamp()} Shutting down.")
                            sys.stdout.flush()
                            self._processing_layer.end_processing_on_collecting_node(
                                node_rank=self._rank,
                                node_pool_size=self._node_pool_size,
                            )
                            for processing_node in self._processing_nodes:
                                processing_node.join()
                                # join() means wait for processing to close and terminate
                            sys.exit(0)
                        else:
                            continue
                    feedback_data: Union[
                        Dict[int, Dict[str, Any]], None
                    ] = self._processing_layer.collect_data(
                        node_rank=self._rank,
                        node_pool_size=self._node_pool_size,
                        processed_data=received_data,
                    )
                    self._num_collected_events += 1
                    if feedback_data is not None:
                        receiving_rank: int
                        for receiving_rank in feedback_data.keys():
                            if receiving_rank == 0:
                                   #send the string to all
                                   #send_pyobj through the pub socket  f"all#" and f"rankno.#" 
                                   #send one object through the socket to all. 
                                   # self._sock.send_string(tag, zmq.SNDMORE)
                                   # self._sock.send_pyobj(message)
                                   #self._socket_pub
                                   
                                self._socket_pub.send_string("all#", zmq.SNDMORE)
                                self._socket_pub.send_pyobj(feedback_data[0])   
                            else:
                                self._socket_pub.send_string(f"{receiving_rank}#", zmq.SNDMORE)
                                self._socket_pub.send_pyobj(feedback_data[receiving_rank])
                                
                                # self._message_pipes[receiving_rank - 1].send(
                                    # feedback_data[receiving_rank]    #send_pyobj through the pub socket  
                                # )
            
                                
                else:
                    self._processing_layer.wait_for_data(
                        node_rank=self._rank,
                        node_pool_size=self._node_pool_size,
                    )

            except KeyboardInterrupt as exc:
                console.print(f"{get_current_timestamp()} Received keyboard sigterm...")
                console.print(f"{get_current_timestamp()} {str(exc)}")
                console.print(f"{get_current_timestamp()} Shutting down.")
                self.shutdown()
                sys.stdout.flush()

    def shutdown(self, *, msg: str = "Reason not provided.") -> None:
        """
        Shuts down the multiprocessing parallelization.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function stops OM, closing all the communication channels between the
        nodes and managing a controlled shutdown of OM's resources. Additionally, it
        terminates the processing node subprocesseses in an orderly fashion.

        Arguments:

            msg: Reason for shutting down. Defaults to "Reason not provided".
        """
        
        console.print(f"{get_current_timestamp()} Shutting down: {msg}")
        sys.stdout.flush()
        if self._rank == 0:
            # Tells all the processing nodes that they need to shut down, then waits
            # for confirmation. During the whole process, keeps receiving normal MPI
            # messages from the nodes (MPI cannot shut down if there are unreceived
            # messages).
            try:
                # message_pipe: multiprocessing.connection.Connection
                # for message_pipe in self._message_pipes:
                # message_pipe.send({"stop": True})
                
                self._sock.send_string("all#", zmq.SNDMORE)
                self._sock.send_pyobj({"stop": True})   
                num_shutdown_confirm = 0
                while True:
                    # message: Tuple[Dict[str, Any], int] = self._data_queue.get()
                    message: Tuple[ 
                        Dict[str, Any], int 
                    ] = self._receiver_pull.recv_pyobj()
                    if "stopped" in message[0]:
                        num_shutdown_confirm += 1
                    if num_shutdown_confirm == self._node_pool_size - 1:
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
