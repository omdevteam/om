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
'''
Helper functions and classes to use zmq sockets in OnDA monitors.
'''

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import socket
import sys

import zmq

# try:
#     from cPickle import loads
# except ImportError:
#     from pickle import loads
# try:
#     from PyQt5 import QtCore
# except ImportError:
#     from PyQt4 import QtCore


# class ZMQListener(QtCore.QObject):
#     '''
#     ZMQ Listener class, to be used for GUIs and data receivers in general.
#     It is designed to be run in a separate Qt thread. It instantiates
#     a SUB socket that connects to a ZMQ PUB socket. A custom zmqmessage
#     signal is emitted every data is received through the SUB socket.
#     The signal brings the received data as payload
#     '''

#     zmqmessage = QtCore.pyqtSignal(dict)

#     def __init__(self, sub_ip, sub_port, subscribe_string):

#         QtCore.QObject.__init__(self)

#         self._sub_ip = sub_ip
#         self._sub_port = sub_port
#         self._zmq_context = zmq.Context()

#         print('Connecting to tcp://{0}:{1}'.format(
#             self._sub_ip, self._sub_port
#         ))
#         self._zmq_subscribe = self._zmq_context.socket(zmq.SUB)
#         self._zmq_subscribe.set_hwm(1)
#         self._zmq_subscribe.connect('tcp://{0}:{1}'.format(
#             self._sub_ip, self._sub_port)
#         )
#         self._zmq_subscribe.setsockopt_string(
#             zmq.SUBSCRIBE, subscribe_string
#         )

#         self._zmq_poller = zmq.Poller()
#         self._zmq_poller.register(self._zmq_subscribe, zmq.POLLIN)

#         self._listening_timer = QtCore.QTimer()
#         self._listening_timer.timeout.connect(self.listen)

#     def start_listening(self):
#         self._listening_timer.start()

#     def stop_listening(self):
#         self._listening_timer.stop()
#         print('Disconnecting from tcp://{0}:{1}'.format(
#              self.rec_ip, self.rec_port)
#         )
#         self._zmq_subscribe.disconnect('tcp://{0}:{1}'.format(
#              self.rec_ip, self.rec_port
#         ))

#     def listen(self):
#         socks = dict(self._zmq_poller.poll(0))
#         if (
#               self._zmq_subscribe in socks and
#               socks[self._zmq_subscribe] == zmq.POLLIN
#         ):
#             full_msg = self._zmq_subscribe.recv_multipart()
#             msg = full_msg[1]
#             zmq_dict = loads(msg)
#             self.zmqmessage.emit(zmq_dict)


class ZMQOndaPublisherSocket:
    '''
    ZMQ socket to send data out of the monitor.

    A ZMQ PUB socket to send data to GUIs and other receivers. The socket
    has a high water mark of 1 (i.e. no queuing of outgoing messages takes
    place).
    '''

    def __init__(self, publish_ip=None, publish_port=None):
        '''
        Initialize the ZMQOndaPublisherSocket class.

        Args:

            publish_ip (Optional[str]): hostname or IP address of the machine
                where the socket will be opened. If None, the hostname
                will be autodetected based on where the OnDA monitor is
                running. Defaults to None.

            publish_port(Optional[int]): port where the socket will be opened.
                If None, the port number will be set to 12321.
                Defaults to None.
        '''

        # Create the zmq context.
        self._context = zmq.Context()

        # Intantiate a PUB socket.
        self._sock = self._context.socket(zmq.PUB)

        if publish_ip is not None:
            # If the IP address is provided, use it.
            pip = publish_ip
        else:
            # Otherwise autodetect the IP address.
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
            # If the port is provided, use it.
            pport = publish_port
        else:
            # Otherwise use the value 12321.
            pport = 12321

        # Print a message on the console.
        print('Binding to tcp://{0}:{1}'.format(pip, pport))
        sys.stdout.flush()

        # Set the high water mark to 1.
        self._sock.set_hwm(1)

        # Bind the socket.
        self._sock.bind('tcp://%s:%d' % (pip, pport))

    def send_data(self, tag, message):
        '''
        Send data through the PUB socket.

        Args:

            tag (str): tag for the sent data.

            message (Any): data to be sent. Any python object.
        '''

        # Create and send the zmq message.
        self._sock.send(tag.encode(), zmq.SNDMORE)
        self._sock.send_pyobj(message)
