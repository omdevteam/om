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
# Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Data broadcasting and receiving in OnDA.
"""
from __future__ import absolute_import, division, print_function

import socket
import sys
from builtins import str as unicode_str

from typing import Optional  # pylint: disable=unused-import

import msgpack
import msgpack_numpy
import numpy
import zmq

try:
    from PyQt5 import QtCore
except ImportError:
    from PyQt4 import QtCore


class ZmqDataBroadcaster(object):
    """
    See documentation of the '__init__' function.
    """

    def __init__(self, hostname=None, port=None):
        # type: (Optional[str], Optional[int]) -> None
        """
        ZMQ-based data-broadcasting socket for OnDA monitors.

        This class implements a ZMQ PUB socket that broadcasts tagged data. The socket
        supports multiple clients and broadcasts the data using the MessagePack
        protocol. It has no queuing system: data that has not been picked up by a
        receiver will be lost when the next broadcast takes place.

        Args:

            hostname (Optional[str]): the hostname or IP address where the socket will
                be opened. If None it will be autodetected. Defaults to None.

            port(Optional[int]): the port where the socket will be opened. If None, the
                socket will be opened at port 12321. Defaults to None.
        """
        self._context = zmq.Context()
        self._sock = self._context.socket(zmq.PUB)  # pylint: disable=no-member
        if hostname is not None:
            bhostname = hostname
        else:
            # If required, uses the python socket module to autodetect the hostname of
            # the machine where the OnDA monitor is running.
            # TODO: Check mypy output for these lines.
            bhostname = [
                (s.connect(("8.8.8.8", 80)), s.getsockname()[0], s.close())
                for s in [socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)]
            ][0][1]
        if port is not None:
            bport = port
        else:
            bport = 12321
        # Sets a high water mark of 1 (A messaging queue that is 1 message long, so no
        # queuing).
        self._sock.set_hwm(1)
        self._sock.bind("tcp://%s:%d" % (bhostname, bport))
        print("Broadcasting data at {0}:{1}".format(bhostname, bport))
        sys.stdout.flush()

    def send_data(self, tag, message):
        # type (str, Hashable) -> None
        """
        Broadcasts data from the ZMQ PUB socket.

        This function broadcasts the data in the form of a MessagePack object.

        Arguments:

            tag (str): the tag that will be attached to the broadcasted data.

            message (Any): Any MessagePack-compatible python object.
        """
        self._sock.send(tag.encode(), zmq.SNDMORE)
        msgpack_message = msgpack.packb(message)
        self._sock.send(msgpack_message)


class ZmqDataListener(QtCore.QObject):
    # type: (Optional[str], Optional[int]) -> None
    """
    See documentation for the '__init__' function.
    """

    zmqmessage = QtCore.pyqtSignal(list)
    # Custom Qt signal to be emitted when data is received.

    def __init__(self, hostname, port, tag):
        # type: (str, int, str) -> None
        """
        ZMQ-based data receviing socket for OnDA GUIs and clients.

        This class implements a listening socket based on a ZMQ SUB socket. The socket
        receives and filters tagged data, and has no queuing system.  The received data
        message must follow the the MessagePack protocol. This class is designed to be
        run in a separate Qt thread. Every time a message is received, this class emits
        a custom Qt signal that carries the received data as payload.

        Arguments:

            hostname (str): the hostname or IP address where the receiver will listen
                for data.

            port(int): the port at which the receiver will listen for data.

            subscribe string (str): tag used by the listener to filter incoming data.
        """
        QtCore.QObject.__init__(self)

        self._sub_hostname = hostname
        self._sub_port = port
        self._subscription_string = tag
        self._zmq_context = zmq.Context()
        self._zmq_subscribe = None
        self._zmq_poller = None

        # Initializes the listening timer. Every time this timer ticks, this object
        # tries to read from the socket.
        self._listening_timer = QtCore.QTimer()
        self._listening_timer.timeout.connect(self._listen)

    def start_listening(self):
        # type: () -> None
        """
        Connects to a PUB socket and starts listening.
        """
        print("Connecting to tcp://{}:{}".format(self._sub_hostname, self._sub_port))
        self._zmq_subscribe = self._zmq_context.socket(  # pylint: disable=no-member
            zmq.SUB  # pylint: disable=no-member
        )
        self._zmq_subscribe.connect(
            "tcp://{0}:{1}".format(self._sub_hostname, self._sub_port)
        )
        self._zmq_subscribe.setsockopt_string(
            option=zmq.SUBSCRIBE,  # pylint: disable=no-member
            optval=unicode_str(self._subscription_string),
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
            "Disconnecting from tcp://{}:{}".format(self._pub_hostname, self._pub_port)
        )
        self._zmq_subscribe.disconnect(
            "tcp://{}:{}".format(self._pub_hostname, self._pub_port)
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


# Monkey-patches the encode function in msgpack_numpy for python 2 compatibility.
msgpack_numpy.encode = _patched_encode
msgpack_numpy.patch()
