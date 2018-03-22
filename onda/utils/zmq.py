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
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import socket
import sys

import zmq


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
        self._sock = self._context.socket(zmq.PUB)
        if publish_ip is not None:
            pip = publish_ip
        else:
            # Use the socket module to autodetect the hostname / IP
            # where the OnDA monitor is running.
            pip = [
                (
                    s.connect(
                        address=('8.8.8.8', 80)
                    ),
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
