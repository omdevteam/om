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
#
#    Copyright 2014-2018 Deutsches Elektronen-Synchrotron DESY,
#    a research centre of the Helmholtz Association.
"""
ZMQ-based data broadcasting and receiving for OnDA.

ZMQ-based functions and classes used by OnDA monitors and GUIs to
broadcast and receive data.
"""
from __future__ import absolute_import, division, print_function

import socket
import sys
import msgpack
import numpy
import msgpack_numpy
import zmq

try:
    from PyQt5 import QtCore
except ImportError:
    from PyQt4 import QtCore


class DataBroadcaster(object):
    """
    ZMQ-based data-broadcasting socket for OnDA monitors.

    A broadcasting socket based on a ZMQ PUB socket. The socket sends
    tagged data, supports multiple clients and has no queuing system:
    it drops messages that are not received by clients. It broadcasts
    the data using the MessagePack protocol, which is
    language-independent.
    """

    def __init__(self, publish_ip=None, publish_port=None):
        """
        Initializes the DataBroadcaster class.

        Args:

            publish_ip (Optional[str]): hostname or IP address of the
                machine where the socket will be opened. If None, the
                IP address will be autodetected. Defaults to None.

            publish_port(Optional[int]): port where the socket will be
                opened. If None, the port number will be set to 12321.
                Defaults to None.
        """
        self._context = zmq.Context()
        self._sock = self._context.socket(
            zmq.PUB  # pylint: disable=no-member
        )

        if publish_ip is not None:
            pip = publish_ip
        else:
            # If required, uses the python socket module to autodetect
            # the hostname of the machine where the OnDA monitor is
            # running.
            pip = [
                (
                    s.connect(('8.8.8.8', 80)),
                    s.getsockname()[0],
                    s.close()
                ) for s in [
                    socket.socket(
                        family=socket.AF_INET,
                        type=socket.SOCK_DGRAM)
                ]
            ][0][1]

        if publish_port is not None:
            pport = publish_port
        else:
            pport = 12321

        print('Binding to tcp://{0}:{1}'.format(pip, pport))
        sys.stdout.flush()

        # Sets a high water mark of 1 (A messaging queue 1 message
        # long, so no queuing).
        self._sock.set_hwm(1)
        self._sock.bind('tcp://%s:%d' % (pip, pport))

    def send_data(self, tag, message):
        """
        Broadcasts data.

        Sends data (a python object) through the broadcasting socket.

        Args:

            tag (str): tag for the sent data.

            message (Any): a python object to be sent.
        """
        # Send the tag and the data in one single ZMQ message.
        self._sock.send(tag.encode(), zmq.SNDMORE)
        msgpack_message = msgpack.packb(message)
        self._sock.send(msgpack_message)


class DataListener(QtCore.QObject):
    """
    ZMQ-based data listening socket for OnDA GUIs and clients.

    A listening socket based on a ZMQ SUB socket. The socket receives
    and filters tagged data, and has no queuing system: messages that
    are not received are dropped. It receives data sent using the
    MessagePack protocol and is designed to be used in a separate Qt
    listening thread. The DataListener checks continuously if data is
    coming through the socket. Every time data comes, it emits a custom
    Qt signal with the received data as payload.
    """

    zmqmessage = QtCore.pyqtSignal(list)
    # Custom Qt signal to be emitted when data is received.

    def __init__(self,
                 pub_hostname,
                 pub_port,
                 subscription_string):
        """
        Initializes the DataListener class.

        Args:

            pub_hostname (str): hostname or IP address of the machine
                where the OnDA monitor is running.

            pub_port (int): port on which the the OnDA monitor is
                broadcasting information.

            subscribe string (str): data tag to which the listener
                should subscribe. Data tagged with other tags is
                discarded.
        """
        QtCore.QObject.__init__(self)

        # The following information is needed to disconnect/reconnect
        # the socket without destroying and reinstantiating the
        # the DataListener.
        self._pub_hostname = pub_hostname
        self._pub_port = pub_port
        self._subscription_string = subscription_string
        self._zmq_context = zmq.Context()
        self._zmq_subscribe = None
        self._zmq_poller = None

        # Initializes the listening timer. Every time this timer ticks,
        # the class tries to read from the socket.
        self._listening_timer = QtCore.QTimer()
        self._listening_timer.timeout.connect(self.listen)

    def start_listening(self):
        """
        Connects and starts listening to a broadcasting socket.
        """
        print(
            "Connecting to tcp://{}:{}".format(
                self._pub_hostname,
                self._pub_port
            )
        )
        self._zmq_subscribe = (
            self._zmq_context.socket(zmq.SUB)  # pylint: disable=E1101
        )
        self._zmq_subscribe.connect(
            'tcp://{0}:{1}'.format(
                self._pub_hostname,
                self._pub_port
            )
        )
        self._zmq_subscribe.setsockopt_string(
            option=zmq.SUBSCRIBE,  # pylint: disable=E1101
            optval=self._subscription_string
        )

        # Sets a high water mark of 1 (A messaging queue 1 message
        # long, so no queuing).
        self._zmq_subscribe.set_hwm(1)
        self._zmq_poller = zmq.Poller()
        self._zmq_poller.register(
            socket=self._zmq_subscribe,
            flags=zmq.POLLIN
        )

        self._listening_timer.start()

    def stop_listening(self):
        """
        Stops listening to a broadcasting socket and disconnects.
        """
        self._listening_timer.stop()
        print(
            "Disconnecting from tcp://{}:{}".format(
                self._pub_hostname,
                self._pub_port
            )
        )

        self._zmq_subscribe.disconnect(
            "tcp://{}:{}".format(
                self._pub_hostname,
                self._pub_port
            )
        )

        self._zmq_poller = None
        self._zmq_subscribe = None

    def listen(self):
        """
        Listens for data.

        When data comes, this function emits a signal, adding the
        received data as payload.
        """
        socks = dict(self._zmq_poller.poll(0))
        if (
                self._zmq_subscribe in socks and
                socks[self._zmq_subscribe] == zmq.POLLIN
        ):
            full_msg = self._zmq_subscribe.recv_multipart()
            msgpack_msg = full_msg[1]

            # Deserializes the message and emits the signal.
            msg = msgpack.unpackb(msgpack_msg)
            self.zmqmessage.emit(msg)



def _patched_encode(obj, chain=None):
    # This function is the 'encode' function from msgpack-numpy,
    # patched to use the 'data' method as opposed to the 'tobytes' one.
    if isinstance(obj, numpy.ndarray):
        # If the dtype is structured, store the interface description;
        # otherwise, store the corresponding array protocol type string:
        if obj.dtype.kind == 'V':
            kind = b'V'
            descr = obj.dtype.descr
        else:
            kind = b''
            descr = obj.dtype.str
        return {b'nd': True,
                b'type': descr,
                b'kind': kind,
                b'shape': obj.shape,
                b'data': obj.data}
    elif isinstance(obj, (numpy.bool_, numpy.number)):
        return {b'nd': False,
                b'type': obj.dtype.str,
                b'data': obj.data}
    elif isinstance(obj, complex):
        return {b'complex': True,
                b'data': obj.__repr__()}
    else:
        return obj if chain is None else chain(obj)

# Monkey-patching msgpack-python to have non-copy serialization.
msgpack_numpy.encode = _patched_encode

# Initialization of msgpack-python.
msgpack_numpy.patch()
