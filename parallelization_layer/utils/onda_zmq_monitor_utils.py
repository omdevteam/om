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


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from socket import socket, AF_INET, SOCK_DGRAM
from zmq import Context, PUB
from sys import stdout


def init_zmq_to_gui(monitor, publish_ip, publish_port):

    try:
        monitor.zmq_context
    except AttributeError:
        monitor.zmq_context = Context()

    monitor.zmq_publish = monitor.zmq_context.socket(PUB)
    if publish_ip is not None:
        pip = publish_ip
    else:
        pip = [(s.connect(('8.8.8.8', 80)), s.getsockname()[0],
               s.close()) for s in [socket(AF_INET, SOCK_DGRAM)]][0][1]
    if publish_port is not None:
        pport = publish_port
    else:
        pport = 12321
    print('Binding to tcp://{0}:{1}'.format(pip, pport))
    stdout.flush()
    monitor.zmq_publish.set_hwm(1)
    monitor.zmq_publish.bind('tcp://%s:%d' % (pip, pport))
