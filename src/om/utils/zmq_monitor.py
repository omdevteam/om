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
to external programs over a ZMQ socket.
"""
import socket
import sys
from typing import Any, Dict, Union

import zmq  # type: ignore

from om.utils import exceptions
from om.utils import parameters as param_utils


def get_current_machine_ip() -> str:
    """
    Retrieves the IP address of the local machine.

    This function uses Python's `socket` module to autodetect the IP addess of the
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

    def __init__(
        self,
        *,
        url: Union[str, None] = None,
        parameters: Union[Dict[str, Any], None] = None,
    ) -> None:
        """
        Data-broadcasting socket for OnDA Monitors.

        This class manages a broadcasting socket that can be used by OnDA Monitors
        to transmit data to outside programs. The class must be initialized with the
        URL, in ZeroMQ format, were the socket should operate. Each data item broadcast
        by the socket can be tagged with a different label, and external programs can
        use this label to filter incoming data. The socket can transmit to multiple
        clients at the same time but has no queuing system: broadcast data will be lost
        to the clients if not received before the next transmission takes place.

        This class creates a ZMQ PUB socket that accepts connections from ZMQ PUB
        sockets.

        Arguments:

            url: The URL where the socket will be opened. It must be a string in
                the format used by ZeroMQ, or None. If the value of this argument is
                None, the IP address of the local machine will be autodetected, and the
                socket will be opened at port 12321 using the 'tcp://' protocol.
                Defaults to None.
        """
        if parameters is not None:
            url = param_utils.get_parameter_from_parameter_group(
                group=parameters, parameter="data_broadcast_url", parameter_type=str
            )
        else:
            print(
                "OM Warning: Initializing the ZmqDataBroadcaster class with "
                "individual parameters (url) is deprecated and will be removed in a "
                "future version of OM. Please use the new parameter group-based "
                "initialization interface (which requires only the parameters "
                "argument)."
            )

        self._context: Any = zmq.Context()
        self._sock: Any = self._context.socket(zmq.PUB)
        # TODO: Fix types

        if url is None:
            url = "tcp://{}:12321".format(get_current_machine_ip())

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

    def send_data(self, *, tag: str, message: Dict[str, Any]) -> None:
        """
        Broadcasts data from the ZMQ PUB socket.

        This function transmits the provided data from the broadcasting socket. The
        data must have the format of a python dictionary. When broadcast, the data is
        tagged with the specified label.

        Arguments:

            tag: The label that will be used to tag the data.

            message: A dictionary storing the data to be transmitted.

                * The dictionary keys must store the names of the data units being
                  broadcast.

                * The corresponding dictionary values must store the data content to be
                  transsmitted (strictly in the format of Python objects).
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
        url: Union[str, None] = None,
        parameters: Union[Dict[str, Any], None] = None,
    ) -> None:
        """
        ZMQ-based responding socket for OnDA Monitors.

        This class manages a socket that can be used by an OnDA Monitor to receive
        requests from external programs, and respond to them. The class must be
        initialized with the URL, in ZeroMQ format, were the socket should operate.
        The socket will then accept requests from external sources, and it can be used
        to transmit data that satisfy the requests, if necessary.

        This class creates a ZMQ REP socket that can accept requests from REQ sockets
        in external programs and respond to them.

        Arguments:

            url: The URL where the socket will be opened. It must be a string in
                the format used by ZeroMQ, or None. If the value of this argument is
                None, the IP address of the local machine will be autodetected, and the
                socket will be opened at port 12322 using the 'tcp://' protocol.
                Defaults to None.
        """
        if parameters is not None:
            url = param_utils.get_parameter_from_parameter_group(
                group=parameters, parameter="responding_url", parameter_type=str
            )
        else:
            print(
                "OM Warning: Initializing the ZmqResponder class with individual "
                "parameters (url) is deprecated and will be removed in a future "
                "version of OM. Please use the new parameter group-based "
                "initialization interface (which requires only the parameters "
                "argument)."
            )

        self._context: Any = zmq.Context()
        self._sock: Any = self._context.socket(zmq.REP)
        # TODO: Fix types

        if url is None:
            url = "tcp://{}:12322".format(get_current_machine_ip())

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
        Gets a request from the responding socket, if present.

        This function checks if a request has been received by the socket. In the
        affirmative case, it returns the content of the request, otherwise it returns
        None. This function is non-blocking.

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

    def send_data(self, *, message: Dict[str, Any]) -> None:
        """
        Send data from the ZMQ REP socket.

        This function transmits data to an external program that has previously sent a
        request to the socket. The response must have the format of a python
        dictionary.

        Arguments:

            message: A dictionary containing information to be transmitted.
        """
        self._sock.send(message)
