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


import zmq
import pickle
import PyQt4.QtCore


class ZMQListener(PyQt4.QtCore.QObject):
    """
    ZMQ Listener class, to be used for GUIs and data receivers in general.
    It is designed to be run in a separate Qt thread. It instantiates
    a SUB socket that connects to a ZMQ PUB socket. A custom zmqmessage
    signal is emitted every data is received through the SUB socket.
    The signal brings the received data as payload
    """

    zmqmessage = PyQt4.QtCore.pyqtSignal(dict)

    def __init__(self, sub_ip, sub_port, subscribe_string):

        PyQt4.QtCore.QObject.__init__(self)

        self.sub_ip = sub_ip
        self.sub_port = sub_port
        self.zmq_context = zmq.Context()

        print('Connecting to tcp://{0}:{1}'.format(self.sub_ip, self.sub_port))
        self.zmq_subscribe = self.zmq_context.socket(zmq.SUB)
        self.zmq_subscribe.set_hwm(1)
        self.zmq_subscribe.connect('tcp://{0}:{1}'.format(self.sub_ip, self.sub_port))
        self.zmq_subscribe.setsockopt_string(zmq.SUBSCRIBE, subscribe_string)

        self.zmq_poller = zmq.Poller()
        self.zmq_poller.register(self.zmq_subscribe, zmq.POLLIN)

        self.listening_timer = PyQt4.QtCore.QTimer()
        self.listening_timer.timeout.connect(self.listen)

    def start_listening(self):
        self.listening_timer.start()

    def stop_listening(self):
        self.listening_timer.stop()
        print('Disconnecting from tcp://{0}:{1}'.format(self.rec_ip, self.rec_port))
        self.zmq_subscribe.disconnect('tcp://{0}:{1}'.format(self.rec_ip, self.rec_port))

    def listen(self):
        socks = dict(self.zmq_poller.poll(0))
        if self.zmq_subscribe in socks and socks[self.zmq_subscribe] == zmq.POLLIN:
            full_msg = self.zmq_subscribe.recv_multipart()
            msg = full_msg[1]
            zmq_dict = pickle.loads(msg)
            self.zmqmessage.emit(zmq_dict)
