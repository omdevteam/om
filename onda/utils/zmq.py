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


from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import zmq
import socket
import sys

try:
    from cPickle import loads
except ImportError:
    from pickle import loads
try:
    from PyQt5 import QtCore
except ImportError:
    from PyQt4 import QtCore


class ZMQListener(QtCore.QObject):
    """
    ZMQ Listener class, to be used for GUIs and data receivers in general.
    It is designed to be run in a separate Qt thread. It instantiates
    a SUB socket that connects to a ZMQ PUB socket. A custom zmqmessage
    signal is emitted every data is received through the SUB socket.
    The signal brings the received data as payload
    """

    zmqmessage = QtCore.pyqtSignal(dict)

    def __init__(self, sub_ip, sub_port, subscribe_string):

        QtCore.QObject.__init__(self)

        self._sub_ip = sub_ip
        self._sub_port = sub_port
        self._zmq_context = zmq.Context()

        print('Connecting to tcp://{0}:{1}'.format(self._sub_ip, self._sub_port))
        self._zmq_subscribe = self._zmq_context.socket(zmq.SUB)
        self._zmq_subscribe.set_hwm(1)
        self._zmq_subscribe.connect('tcp://{0}:{1}'.format(self._sub_ip, self._sub_port))
        self._zmq_subscribe.setsockopt_string(zmq.SUBSCRIBE, subscribe_string)

        self._zmq_poller = zmq.Poller()
        self._zmq_poller.register(self._zmq_subscribe, zmq.POLLIN)

        self._listening_timer = QtCore.QTimer()
        self._listening_timer.timeout.connect(self.listen)

    def start_listening(self):
        self._listening_timer.start()

    def stop_listening(self):
        self._listening_timer.stop()
        print('Disconnecting from tcp://{0}:{1}'.format(self.rec_ip, self.rec_port))
        self._zmq_subscribe.disconnect('tcp://{0}:{1}'.format(self.rec_ip, self.rec_port))

    def listen(self):
        socks = dict(self._zmq_poller.poll(0))
        if self._zmq_subscribe in socks and socks[self._zmq_subscribe] == zmq.POLLIN:
            full_msg = self._zmq_subscribe.recv_multipart()
            msg = full_msg[1]
            zmq_dict = loads(msg)
            self.zmqmessage.emit(zmq_dict)


class ZMQOndaPublisherSocket:
    def __init__(self, publish_ip, publish_port):

        self._context = zmq.Context()
        self._sock = self._context.socket(zmq.PUB)

        if publish_ip is not None:
            pip = publish_ip
        else:
            pip = [(s.connect(('8.8.8.8', 80)), s.getsockname()[0],
                    s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]
        if publish_port is not None:
            pport = publish_port
        else:
            pport = 12321
        print('Binding to tcp://{0}:{1}'.format(pip, pport))
        sys.stdout.flush()
        self._sock.set_hwm(1)
        self._sock.bind('tcp://%s:%d' % (pip, pport))

    def send_data(self, tag, message):
        self._sock.send(tag.encode(), zmq.SNDMORE)
        self._sock.send_pyobj(message)