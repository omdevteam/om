#    This file is part of cfelpyutils.
#
#    cfelpyutils is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    cfelpyutils is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with cfelpyutils.  If not, see <http://www.gnu.org/licenses/>.
"""
Helper functions and classes to use zmq sockets in OnDA monitors.

Exports:

    Classes:

         ZMQOndaPublisherSocket: one-way ZMQ PUB socket for
            sending data to clients.

        ZMQListener(QtCore.QObject): receiving SUB socket for
            receiving data from an OnDA monitor.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import socket
import sys

import zmq

try:
    from cPickle import loads
except ImportError:
    from pickle import loads

try:
    from PyQt5 import QtCore
except ImportError:
    from PyQt4 import QtCore


class ZMQOndaPublisherSocket:
    """
    ZMQ socket to send data out to clients.

    A ZMQ PUB socket to send data to GUIs and other receivers. The
    socket supports multiple clients and has a ZMQ high water mark of 1
    (i.e. no queuing of outgoing messages takes place).
    """

    def __init__(self, publish_ip=None, publish_port=None):
        """
        Initialize the ZMQOndaPublisherSocket class.

        Args:

            publish_ip (Optional[str]): hostname or IP address of the
                machine where the socket will be opened. If None, the
                hostname will be autodetected based on where the OnDA
                monitor is running. Defaults to None.

            publish_port(Optional[int]): port where the socket will be
                opened. If None, the port number will be set to 12321.
                Defaults to None.
        """
        self._context = zmq.Context()
        self._sock = self._context.socket(zmq.PUB)  # pylint: disable=E1101
        if publish_ip is not None:
            pip = publish_ip
        else:
            # Use the socket module to autodetect the hostname / IP
            # where the OnDA monitor is running.
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
        self._sock.set_hwm(1)
        self._sock.bind('tcp://%s:%d' % (pip, pport))

    def send_data(self, tag, message):
        """
        Send data through the PUB socket.

        Send data (a python object) through the socket.

        Args:

            tag (str): tag for the data to be sent.

            message (Any): data to be sent.
        """
        self._sock.send(tag.encode(), zmq.SNDMORE)
        self._sock.send_pyobj(message)


class ZMQListener(QtCore.QObject):
    """
    Listener socket for OnDA GUIs.

    ZMQ Listener class, to be used for GUIs and data receivers in
    general. Instantiate a SUB socket that connects to a ZMQ PUB
    socket. Check continuously if data is coming to the socket. Emit
    a custom zmqmessage signal every time data is received through the
    socket. Send the data together with the signal.
    """

    zmqmessage = QtCore.pyqtSignal(dict)

    def __init__(self,
                 pub_hostname,
                 pub_port,
                 subscribe_string):
        """
        Initialize the ZMQListener class.

        Args:

            sub_hostname (str): hostname or IP address of the host
               where the PUB socket is running.

            sub_port (int): port on the host where the PUB socket is
               running.

            subscribe string (str): tag in the PUB stream to which the
               SUB socket should subscribe.
        """
        QtCore.QObject.__init__(self)

        self._pub_hostname = pub_hostname
        self._pub_port = pub_port
        self._subscribe_string = subscribe_string
        self._zmq_context = zmq.Context()

        # Attributes that stores the listening socket and the
        # poller.
        self._zmq_subscribe = None
        self._zmq_poller = None

        # Initialize the listening timer. Every time this timer ticks,
        # try to read from the socket.
        self._listening_timer = QtCore.QTimer()
        self._listening_timer.timeout.connect(self.listen)

    def start_listening(self):
        """
        Start listening.

        Connect to the socket and start listening.
        """
        # Connect to the PUB socket with the subscription requested by
        # the user. Set a ZMQ high water mark level of 1 so that
        # messages do not pile up at the socket.
        print(
            "Connecting to tcp://{}:{}".format(
                self._pub_hostname,
                self._pub_port
            )
        )

        self._zmq_subscribe = (
            self._zmq_context.socket(zmq.SUB)  # pylint: disable=E1101
        )

        self._zmq_subscribe.set_hwm(1)
        self._zmq_subscribe.connect(
            'tcp://{0}:{1}'.format(
                self._pub_hostname,
                self._pub_port
            )
        )
        self._zmq_subscribe.setsockopt_string(
            opt=zmq.SUBSCRIBE,  # pylint: disable=E1101
            unicode_optval=self.subscribe_string
        )

        # Instantiate a poller that can be used to check if there is
        # data in the socket queue.
        self._zmq_poller = zmq.Poller()
        self._zmq_poller.register(
            socket=self._zmq_subscribe,
            flags=zmq.POLLIN
        )

        # Start the listening timer.
        self._listening_timer.start()

    def stop_listening(self):
        """
        Stop listening.

        Stop the listening and disconnect from the socket.
        """
        # Stop the listening timer and disconnect from the socket.
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
                self.rec_port
            )
        )

        self._zmq_poller = None
        self._zmq_subscribe = None

    def listen(self):
        """
        Listen.

        Listen for data. Check the poller to see if there is some data
        in the socket queue, and if there is, read it. Then emit the
        custom zmq message signal adding the data as payload.
        """
        socks = dict(self._zmq_poller.poll(0))
        if (
                self._zmq_subscribe in socks and
                socks[self._zmq_subscribe] == zmq.POLLIN
        ):
            full_msg = self._zmq_subscribe.recv_multipart()
            msg = full_msg[1]
            zmq_dict = loads(msg)
            self.zmqmessage.emit(zmq_dict)
