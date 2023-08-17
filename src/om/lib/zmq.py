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
ZMQ utilities to broadcast data from an OnDA Monitor.

This module contains classes and functions that allow OnDA Monitors to broadcast data
to external programs over a ZMQ socket.
"""
import socket
import sys
from typing import Any, Dict, Tuple, Union

import zmq

from om.lib.exceptions import OmInvalidZmqUrl
from om.lib.parameters import get_parameter_from_parameter_group
from om.lib.rich_console import console, get_current_timestamp


def get_current_machine_ip() -> str:
    """
    Retrieves the IP address of the local machine.

    This function uses Python's `socket` module to autodetect the IP address of the
    the machine where it is invoked.

    Returns:

        A string storing the IP address of the machine where the function was invoked.
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

    def __init__(
        self,
        *,
        parameters: Dict[str, Any],
    ) -> None:
        """
        Data-broadcasting socket for OnDA Monitors.

        This class manages a broadcasting socket that can be used by OnDA Monitors
        to transmit data to external programs. The class must be initialized with the
        URL, in ZeroMQ format, were the socket should operate. The created socket can
        then be used to broadcast data. Each data item broadcast by the socket can be
        tagged with a different label, and external programs can use this label to
        filter their incoming data. The socket can also transmit to multiple
        clients at the same time but has no queuing system: broadcast data will be lost
        to the clients if not received before the next transmission takes place.

        This class creates a ZMQ PUB socket that accepts connections from ZMQ PUB
        sockets.

        Arguments:

           parameters: A set of OM configuration parameters collected together in a
                parameter group. The parameter group must contain the following
                entries:

                * `url`: The URL where the socket will be opened. It must be a string
                in the format used by ZeroMQ, or None. If the value of this argument is
                None, the IP address of the local machine is auto-detected, and the
                socket is opened at port 12321 using the 'tcp://' protocol. Defaults to
                None.
        """
        url: Union[str, None] = get_parameter_from_parameter_group(
            group=parameters, parameter="data_broadcast_url", parameter_type=str
        )
        if url is None:
            current_machine_ip: str = get_current_machine_ip()
            url = f"tcp://{current_machine_ip}:12321"

        # Sets a high water mark of 1 (A messaging queue that is 1 message long, so no
        # queuing).
        # TODO: Fix types
        self._context: Any = zmq.Context()
        self._sock: Any = self._context.socket(zmq.PUB)
        self._sock.set_hwm(1)
        try:
            self._sock.bind(url)
        except zmq.error.ZMQError as exc:
            # TODO: fix_types
            exc_type, exc_value = sys.exc_info()[:2]
            if exc_type is not None:
                raise OmInvalidZmqUrl(
                    "The setup of the data broadcasting socket failed. The requested"
                    "URL is not valid due to the following reason: "
                    f"{exc_type.__name__}: {exc_value}."
                ) from exc
        console.print(f"{get_current_timestamp()} Broadcasting data at {url}")
        sys.stdout.flush()

    def send_data(self, *, tag: str, message: Dict[str, Any]) -> None:
        """
        Broadcasts data from the ZMQ PUB socket.

        This function transmits the provided data from the broadcasting socket. The
        data must have the format of a python dictionary strictly containing only
        Python objects. When broadcast, the data is tagged with the specified label.

        Arguments:

            tag: The label used to tag the broadcast data.

            message: A dictionary storing the data to be transmitted.

                * The dictionary keys must store the names of the data units being
                  broadcast.

                * The corresponding dictionary values must store the data content,
                  associated to each data unit, to be transmitted.
        """
        self._sock.send_string(tag, zmq.SNDMORE)
        self._sock.send_pyobj(message)


class ZmqResponder:
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        parameters: Dict[str, Any],
        blocking: bool = False,
    ) -> None:
        """
        ZMQ-based responding socket for OnDA Monitors.

        This class manages a socket that can be used by an OnDA Monitor to receive
        requests from external programs, and to respond to them. The class must be
        initialized with the URL, in ZeroMQ format, were the socket should operate.
        The socket can then be used to receive requests and to satisfy them by sending
        data, if necessary. The socket can be of blocking or non-blocking type. In the
        first case, the socket waits for a request and does not allow the monitor to
        proceed until one is received. In the second case, the socket retrieves a
        request if one is available, but proceeds otherwise. Unless a blocking socket
        is requested when the class is initialized, the class creates a non-blocking
        socket.

        This class creates a ZMQ ROUTER socket that can accept requests from REQ
        sockets in external programs and respond to them.

        Arguments:

            parameters: A set of OM configuration parameters collected together in a
                parameter group. The parameter group must contain the following
                entries:

                * `url`: The URL where the socket will be opened. It must be a string
                in the format used by ZeroMQ, or None. If the value of this argument is
                None, the IP address of the local machine is auto-detected, and the
                socket is opened at port 12321 using the 'tcp://' protocol. Defaults to
                None.

            blocking: whether the socket should be of blocking type. Defaults to False.
        """
        url: Union[str, None] = get_parameter_from_parameter_group(
            group=parameters, parameter="responding_url", parameter_type=str
        )
        if url is None:
            current_machine_ip: str = get_current_machine_ip()
            url = f"tcp://{current_machine_ip}:12322"
        # TODO: Fix types

        self._blocking = blocking

        # Sets a high water mark of 1 (A messaging queue that is 1 message long, so no
        # queuing).
        self._context: Any = zmq.Context()
        self._sock: Any = self._context.socket(zmq.ROUTER)
        self._sock.set_hwm(1)
        try:
            self._sock.bind(url)
        except zmq.error.ZMQError as exc:
            # TODO: fix_types
            exc_type, exc_value = sys.exc_info()[:2]
            if exc_type is not None:
                raise OmInvalidZmqUrl(
                    "The setup of the data requesting socket failed. The requested"
                    "URL is not valid due to the following reason: "
                    f"{exc_type.__name__}: {exc_value}."
                ) from exc

        self._zmq_poller: Any = zmq.Poller()
        self._zmq_poller.register(self._sock, zmq.POLLIN)
        console.print(f"{get_current_timestamp()} Answering requests at {url}")
        sys.stdout.flush()

    def get_request(self) -> Union[Tuple[bytes, bytes], None]:
        """
        Gets a request from the responding socket, if present.

        This function checks if a request has been received by the responding socket.
        If the socket has been set up as blocking, this function does not return until
        a request is received. The function then returns a tuple storing the
        identity of the requester and the content of the request. If the socket is
        instead non-blocking, the function return the same information if a request is
        present when the function is called, and None otherwise. The identity of the
        requester must be stored by the program invoking the function and provided
        later to the [send_data][om.lib.zmq.ZmqResponder.send_data] function to answer
        the request, if necessary.

        Returns:

            request: If a request was received by the socket, a tuple storing the
                identity of the caller as the first entry, and a string with the
                request's content as the second entry. If no request has been received
                by the socket, None.
        """
        if self._blocking:
            request: Tuple[bytes, bytes, bytes] = self._sock.recv_multipart()
            return (request[0], request[2])
        else:
            socks: Dict[Any, Any] = dict(self._zmq_poller.poll(0))
            if self._sock in socks and socks[self._sock] == zmq.POLLIN:
                request = self._sock.recv_multipart()
                return (request[0], request[2])
            else:
                return None

    def send_data(
        self, *, identity: bytes, message: Union[Dict[str, Any], bytes]
    ) -> None:
        """
        Send data from the ZMQ REP socket.

        This function transmits data to an external program that has previously sent a
        request to the socket. The response must either have the format of a python
        dictionary or of a sequence of bytes (an ASCII string, for example)

        Arguments:

            identity: The identity of the requester to which the data should sent. This
                information is returned by the
                [get_request][om.lib.zmq.ZmqResponder.get_request].

            message: A dictionary containing the information to be transmitted.
        """
        self._sock.send_multipart((identity, b"", message))
