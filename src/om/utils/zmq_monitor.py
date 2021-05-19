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
ZMQ utilities to broadcast data from an OnDA Monitor.

This module contains classes and functions that allow OnDA Monitors to broadcast data
to external programs over a network connection.
"""
import socket
import sys
from typing import Any, Dict, Union

import zmq  # type: ignore

from om.utils import exceptions


def get_current_machine_ip() -> str:
    """
    Retrieves the IP address of the local machine.

    This function uses the python 'socket' module to autodetect the IP addess of the
    the machine where it is invoked.

    Returns:

        A string storing the IP address of the machine in the format XXX.XXX.XXX.XXX.
    """
    ip: str = [
        (
            s.connect(("8.8.8.8", 80)),  # type: ignore
            s.getsockname()[0],
            s.close(),  # type: ignore
        )
        for s in [socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)]
    ][0][1]

    return ip


class ZmqDataBroadcaster:
    """
    See documentation of the `__init__` function.
    """

    def __init__(self, url: Union[str, None]) -> None:
        """
        ZMQ-based data-broadcasting socket for OnDA Monitors.

        This class implements a ZMQ PUB socket that can be used to broadcast data from
        an OnDA Monitor. The data must be tagged with a label when broadcast. The
        socket supports multiple simultaneous clients, but has no queuing system:
        broadcast data will be lost to the clients if not received before the next
        transmission takes place.

        Arguments:

            url: The URL where the socket will be opened. It must be a string in
                the format used by ZeroMQ, or None. If the value of this argument is
                None, the IP address of the local machine will be autodetected, and the
                socket will be opened at port 12321 using the 'tcp://' protocol.
                Defaults to None.
        """
        self._context: Any = zmq.Context()
        self._sock: Any = self._context.socket(zmq.PUB)
        # TODO: Fix types
        if url is None:
            url = "tcp://127.0.0.1:12321"

        # Sets a high water mark of 1 (A messaging queue that is 1 message long, so no
        # queuing).
        self._sock.set_hwm(1)
        try:
            self._sock.bind(url)
        except zmq.error.ZMQError as exc:
            # TODO: fix_types
            exc_type, exc_value = sys.exc_info()[:2]
            if exc_type is not None:
                raise exceptions.OmInvalidDataBroadcastUrl(
                    "The setup of the data broadcasting socket failed due to the "
                    "following error: {0}: {1}.".format(exc_type.__name__, exc_value)
                ) from exc
        print("Broadcasting data at {0}".format(url))
        sys.stdout.flush()

    def send_data(self, tag: str, message: Dict[str, Any]) -> None:
        """
        Broadcasts data from the ZMQ PUB socket.

        This function broadcasts data in the format of a python dictionary. The data is
        tagged with the specified label when broadcast.

        Arguments:

            tag: The label that will be attached to the data.

            message: A dictionary, where the keys are names of information elements to
                be broadcasted through the broadcasting socket, and the corresponding
                values are the information elements to be sent (python objects).
        """
        self._sock.send_string(tag, zmq.SNDMORE)
        self._sock.send_pyobj(message)


class ZmqResponder:
    """
    See documentation of the `__init__` function.
    """

    def __init__(self, url: Union[str, None]) -> None:
        """
        ZMQ-based responding socket for OnDA Monitors.

        This class implements a ZMQ REP socket that an OnDA Monitor can use to respond
        to requests from an external program. The responding socket can receive
        requests from ZMQ REQ sockets and send, in response, data in the format of a
        python dictionary.

        Arguments:

            url: The URL where the socket will be opened. It must be a string in
                the format used by ZeroMQ, or None. If the value of this argument is
                None, the IP address of the local machine will be autodetected, and the
                socket will be opened at port 12322 using the 'tcp://' protocol.
                Defaults to None.
        """
        self._context: Any = zmq.Context()
        self._sock: Any = self._context.socket(zmq.REP)
        # TODO: Fix types
        if url is None:
            url = "tcp://127.0.0.1:12322"

        # Sets a high water mark of 1 (A messaging queue that is 1 message long, so no
        # queuing).
        try:
            self._sock.bind(url)
        except zmq.error.ZMQError as exc:
            # TODO: fix_types
            exc_type, exc_value = sys.exc_info()[:2]
            if exc_type is not None:
                raise exceptions.OmInvalidRespondingUrl(
                    "The setup of the responding socket failed due to the "
                    "following error: {0}: {1}.".format(exc_type.__name__, exc_value)
                ) from exc

        self._zmq_poller: Any = zmq.Poller()
        self._zmq_poller.register(self._sock, zmq.POLLIN)
        print("Answering requests at {0}".format(url))
        sys.stdout.flush()

    def get_request(self) -> Union[str, None]:
        """
        Gets a request from the ZMQ REP socket if present.

        This function checks if a request has been received by the responding socket.
        If the socket received a request, this function returns it. Otherwise the
        function returns None. This function is non-blocking.

        Returns:

            request: A string containing the request, or None if no request has been
            received by the socket.
        """
        socks: Dict[Any, Any] = dict(self._zmq_poller.poll(0))
        if self._sock in socks and socks[self._sock] == zmq.POLLIN:
            request: Union[str, None] = self._sock.recv_string()
        else:
            request = None
        return request

    def send_data(self, message: Dict[str, Any]) -> None:
        """
        Send data from the ZMQ REP socket.

        This function sends data to an external program that has previously sent a
        request to the socket. The response must have the format of a python
        dictionary.

        Arguments:

            message: A dictionary containing information to be sent.
        """
        self._sock.send(message)
