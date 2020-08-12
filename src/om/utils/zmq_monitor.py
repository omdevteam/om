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
ZMQ utilities for broadcasting data from an OM monitor.

This module contains classes and functions that allow OM monitors to broadcast data
to external programs over a network connection.
"""
from __future__ import absolute_import, division, print_function

import socket
import sys
from typing import Any, Dict, Union

import zmq  # type: ignore
from future.utils import raise_from  # type: ignore

from om.utils import exceptions


class ZmqDataBroadcaster(object):
    """
    See documentation of the '__init__' function.
    """

    def __init__(self, url):
        # type: (Union[str, None]) -> None
        """
        ZMQ-based data-broadcasting socket for OM monitors.

        This class implements a ZMQ PUB socket that can be used to broadcast data. The
        socket supports multiple clients and broadcasts the data using the MessagePack
        protocol. The data is tagged with a label. The socket has no queuing system:
        data that has not been picked up by a receiver will be lost when the next
        broadcast takes place.

        Args:

            hostname (Union[str, None]): the hostname or IP address where the socket
                will be opened. If None it will be autodetected. Defaults to None.

            port(Union[int, None]): the port where the socket will be opened. If None,
                the socket will be opened at port 12321. Defaults to None.
        """
        self._context = zmq.Context()  # type: Any
        self._sock = self._context.socket(zmq.PUB)  # type: Any
        if url is None:
            # If required, uses the python socket module to autodetect the hostname of
            # the machine where the OM monitor is running.
            # TODO: Check mypy output for these lines.
            hostname = [
                (
                    s.connect(("8.8.8.8", 80)),  # type: ignore
                    s.getsockname()[0],
                    s.close(),  # type: ignore
                )
                for s in [socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)]
            ][0][1]
            # TODO: Fix types
            url = "tcp://{0}:12321".format(hostname)

        # Sets a high water mark of 1 (A messaging queue that is 1 message long, so no
        # queuing).
        self._sock.set_hwm(1)
        try:
            self._sock.bind(url)
        except zmq.error.ZMQError as exc:
            raise_from(
                exc=exceptions.OmInvalidDataBroadcastUrl(
                    "The format of the provided data broadcasting URL is not valid. "
                    "The URL must be in the format tcp://hostname:port or in the "
                    "format ipc:///path/to/socket, and in the latter case the user "
                    "must have the correct permissions to access the socket."
                ),
                cause=exc,
            )
        print("Broadcasting data at {0}".format(url))
        sys.stdout.flush()

    def send_data(self, tag, message):
        # type: (str, Dict[str, Any]) -> None
        """
        Broadcasts data from the ZMQ PUB socket.

        This function broadcasts the data in the form of a MessagePack object. The data
        must be tagged with a label.

        Arguments:

            tag (str): the label that will be attached to the broadcasted data.

            message (List[Dict[str, Any]]): a list of dictionaries. For each
                dictionary, the keys are names of information elements to be
                broadcasted through the broadcasting socket, and the corresponding
                values are the information elements to be sent (MessagePack-compatible
                python objects).
        """
        self._sock.send_string(tag, zmq.SNDMORE)
        self._sock.send_pyobj(message)
