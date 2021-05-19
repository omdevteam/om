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
# You should have received a copy of the GNU General Public License along with OM.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2020 -2021 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
ZMQ utilities to receive data from OnDA Monitors.

This module contains classes and functions that allow external programs to receive
data broadcasted by an OnDA Monitor over a network connection.
"""
from builtins import str as unicode_str
from typing import Any, Dict

import zmq  # type: ignore
from om.utils import exceptions

try:
    from PyQt5 import QtCore  # type: ignore
except ImportError:
    raise exceptions.OmMissingDependencyError(
        "The following required module cannot be imported: PyQt5"
    )


class ZmqDataListener(QtCore.QObject):  # type: ignore
    """
    See documentation for the `__init__` function.
    """

    zmqmessage: Any = QtCore.pyqtSignal(dict)
    """
    Qt signal emitted when a message is received by the GUI.

    This signal is emitted when the GUI receives data from an OnDA Monitor. It brings
    the received data as payload.
    """

    def __init__(
        self,
        url: str,
        tag: str,
    ) -> None:
        """
        ZMQ-based data receiving socket for OM's graphical user interfaces.

        This class implements a ZMQ SUB socket that can be used to receive data from
        an OnDA Monitor. The socket accepts only data tagged with a specified label.
        Every time a message is received, this class emits a custom Qt signal that
        carries the received data as payload. This class is designed to be run in a
        separate Qt thread.

        Arguments:

            url: The URL where the socket will listen for data. It must be a string in
                the format used by ZeroMQ.

            tag: The label used by the socket to filter incoming data. Only data whose
                label matches this argument will be accepted and received.
        """
        QtCore.QObject.__init__(self)

        self._url: str = url
        self._subscription_string: str = tag
        self._zmq_context: Any = zmq.Context()
        self._zmq_subscribe: Any = None
        self._zmq_poller: Any = None

        # Initializes the listening timer. Every time this timer ticks, an instance of
        # this class tries to read from the socket.
        self._listening_timer: Any = QtCore.QTimer()
        self._listening_timer.timeout.connect(self._listen)

    def start_listening(self) -> None:
        """
        Connects to a PUB socket and starts listening for data.

        This function connects the SUB socket to the URL specified when the class is
        instantiated.
        """
        print("Connecting to {0}".format(self._url))
        self._zmq_subscribe = self._zmq_context.socket(zmq.SUB)
        try:
            self._zmq_subscribe.connect(self._url)
        except zmq.error.ZMQError as exc:
            raise RuntimeError(
                "The format of the provided URL is not valid. The URL must be in "
                "the format tcp://hostname:port or in the format "
                "ipc:///path/to/socket, and in the latter case the user must have the "
                "correct permissions to access the socket."
            ) from exc
        self._zmq_subscribe.setsockopt_string(
            option=zmq.SUBSCRIBE,
            optval=unicode_str(self._subscription_string),
        )

        # Sets a high water mark of 1 (A messaging queue that is 1 message long, so no
        # queuing).
        self._zmq_subscribe.set_hwm(1)
        self._zmq_poller = zmq.Poller()
        self._zmq_poller.register(self._zmq_subscribe, zmq.POLLIN)

        self._listening_timer.start()

    def stop_listening(self) -> None:
        """
        Stops listening to a PUB socket and disconnects.

        This function completely disconnects the SUB socket. It needs to be reconnected
        (using the :func:`start_listening` function) to start receiving data again.
        """
        self._listening_timer.stop()
        print("Disconnecting from {0}".format(self._url))
        self._zmq_subscribe.disconnect("{0}".format(self._url))
        self._zmq_poller = None
        self._zmq_subscribe = None

    def _listen(self) -> None:
        # Listens for data and emits a signal when data is received.
        socks = dict(self._zmq_poller.poll(0))
        if self._zmq_subscribe in socks and socks[self._zmq_subscribe] == zmq.POLLIN:
            _ = self._zmq_subscribe.recv_string()
            msg: Dict[str, Any] = self._zmq_subscribe.recv_pyobj()
            # Emits the signal.
            self.zmqmessage.emit(msg)
