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
# You should have received a copy of the GNU General Public License along with OnDA.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2020 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
ZMQ utilities for receiving data from OnDA monitors.

This module contains classes and functions that allow external programs to receive
data broadcasted by an OnDA monitor over a network connection.
"""
from __future__ import absolute_import, division, print_function

from builtins import str as unicode_str

from typing import Optional

import msgpack
import msgpack_numpy
import numpy
import zmq

try:
    from PyQt5 import QtCore
except ImportError:
    from PyQt4 import QtCore


class ZmqDataListener(QtCore.QObject):
    # type: (Optional[str], Optional[int]) -> None
    """
    See documentation for the '__init__' function.
    """

    zmqmessage = QtCore.pyqtSignal(list)
    """
    A Qt signal emitted when a message is received.

    The signal brings the received data as payload.
    """

    def __init__(self, hostname, port, tag):
        # type: (str, int, str) -> None
        """
        ZMQ-based data receiving socket for OnDA GUIs and clients.

        This class implements a ZMQ SUB socket that can be used to receive data. The
        socket receives and filters data tagged with a label, and has no queuing
        system. It receives messages that follow the MessagePack protocol. This class
        is designed to be run in a separate Qt thread. Every time a message is
        received, this class emits a custom Qt signal that carries the received data as
        payload.

        Arguments:

            hostname (str): the hostname or IP address where the socket will listen for
                data.

            port(int): the port at which the socket will listen for data.

            tag (str): the label used by the socket to filter incoming data. Only data
                whose label matches this argument will be accepted and received.
        """
        QtCore.QObject.__init__(self)

        self._sub_hostname = hostname
        self._sub_port = port
        self._subscription_string = tag
        self._zmq_context = zmq.Context()
        self._zmq_subscribe = None
        self._zmq_poller = None

        # Initializes the listening timer. Every time this timer ticks, an instance of
        # this class tries to read from the socket.
        self._listening_timer = QtCore.QTimer()
        self._listening_timer.timeout.connect(self._listen)

    def start_listening(self):
        # type: () -> None
        """
        Connects to a PUB socket and starts listening.
        """
        print("Connecting to tcp://{0}:{1}".format(self._sub_hostname, self._sub_port))
        self._zmq_subscribe = self._zmq_context.socket(zmq.SUB)
        self._zmq_subscribe.connect(
            "tcp://{0}:{1}".format(self._sub_hostname, self._sub_port)
        )
        self._zmq_subscribe.setsockopt_string(
            option=zmq.SUBSCRIBE, optval=unicode_str(self._subscription_string),
        )

        # Sets a high water mark of 1 (A messaging queue that is 1 message long, so no
        # queuing).
        self._zmq_subscribe.set_hwm(1)
        self._zmq_poller = zmq.Poller()
        self._zmq_poller.register(socket=self._zmq_subscribe, flags=zmq.POLLIN)

        self._listening_timer.start()

    def stop_listening(self):
        # type: () -> None
        """
        Stops listening to a PUB socket and disconnects.
        """
        self._listening_timer.stop()
        print(
            "Disconnecting from tcp://{0}:{1}".format(
                self._sub_hostname, self._sub_port
            )
        )
        self._zmq_subscribe.disconnect(
            "tcp://{0}:{1}".format(self._sub_hostname, self._sub_port)
        )
        self._zmq_poller = None
        self._zmq_subscribe = None

    def _listen(self):
        # type: () -> None
        # Listens for data and emits a signal when data is received.
        socks = dict(self._zmq_poller.poll(0))
        if self._zmq_subscribe in socks and socks[self._zmq_subscribe] == zmq.POLLIN:
            full_msg = self._zmq_subscribe.recv_multipart()
            msgpack_msg = full_msg[1]

            # Deserializes the message and emits the signal.
            msg = msgpack.unpackb(msgpack_msg)
            self.zmqmessage.emit(msg)


def _patched_encode(obj, chain=None):
    # This function is the 'encode' function from msgpack-numpy, patched to use the
    # 'tobytes' method as opposed to the 'data' one. This is needed for python 2
    # compatibility.
    if isinstance(obj, numpy.ndarray):
        # If the dtype is structured, store the interface description; otherwise,
        # store the corresponding array protocol type string:
        if obj.dtype.kind == "V":
            kind = b"V"
            descr = obj.dtype.descr
        else:
            kind = b""
            descr = obj.dtype.str
        return {
            b"nd": True,
            b"type": descr,
            b"kind": kind,
            b"shape": obj.shape,
            b"data": obj.tobytes(),
        }
    elif isinstance(obj, (numpy.bool_, numpy.number)):
        return {b"nd": False, b"type": obj.dtype.str, b"data": obj.tobytes()}
    elif isinstance(obj, complex):
        return {b"complex": True, b"data": obj.__repr__()}
    else:
        return obj if chain is None else chain(obj)


msgpack_numpy.patch()
