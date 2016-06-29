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


import zmq
import socket
import sys


def init_zmq_to_gui(monitor, publish_ip, publish_port):

    try:
        monitor.zmq_context
    except AttributeError:
        monitor.zmq_context = zmq.Context()

    monitor.zmq_publish = monitor.zmq_context.socket(zmq.PUB)
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
    monitor.zmq_publish.set_hwm(1)
    monitor.zmq_publish.bind('tcp://%s:%d' % (pip, pport))
