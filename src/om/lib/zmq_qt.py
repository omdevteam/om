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
# Copyright 2020 -2023 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
ZMQ utilities to receive data from OnDA Monitors.

This module contains classes and functions that allow external programs to receive data
from an OnDA Monitor over a ZMQ socket.
"""
from builtins import str as unicode_str
from typing import Any, Dict, Union

import zmq

from om.lib.exceptions import OmInvalidZmqUrl, OmMissingDependencyError
from om.lib.rich_console import console, get_current_timestamp

try:
    from PyQt5 import QtCore
except ImportError:
    raise OmMissingDependencyError(
        "The following required module cannot be imported: PyQt5"
    )


class ZmqDataListener(QtCore.QObject):
    """
    See documentation for the `__init__` function.
    """

    zmqmessage: Any = QtCore.pyqtSignal(dict)
    """
    Qt signal emitted when data is received.

    This signal is emitted by this class when it receives data from an OnDA Monitor. It
    brings the received data as payload.
    """

    def __init__(
        self,
        *,
        url: str,
        tag: str,
    ) -> None:
        """
        Data receiving socket for external programs.

        This class manages a listening socket that can receive data broadcast by an
        OnDA Monitor. The class must be initialized with the URL address, in ZeroMQ
        format, of the broadcasting socket of the monitor. It then creates a receiving
        socket that listens for data, but only when is tagged with a specific label,
        provided to the class when it is initialized. Every time the socket receives
        data, this class emits a Qt signal carrying the received data as payload. This
        class is designed to be run in a separate thread from the main graphical
        interface program. The main program can listen for the signal emitted by this
        class to determine when new data has been received.

        This class is designed to be executed in a Qt thread. It creates a ZMQ SUB
        socket that connects to an OM's PUB socket, subscribing to a single specific
        topic. When the socket receives data, this class emits a
        [`zmqmessage`][om.lib.zmq_qt.ZmqDataListener.zmqmessage] Qt signal that other
        threads can listen to. The signal carries the received data.

        Arguments:

            url: The URL to which the PUB socket will connect. It must be a URL string
                in the format used by ZeroMQ.

            tag: The label used by the socket to filter incoming data. Only data whose
                label matches this argument will be accepted and received.
        """
        QtCore.QObject.__init__(self)
        self._url: Union[str, None] = url
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
        Connects to a OM's broadcasting socket and starts listening for data.

        This function connects the listening socket to a data source broadcasting at
        the URL provided to the class at initialization. The socket starts receiving
        data immediately.

        Raises:

            OmInvalidZmqUrl: Raised if any error happens while the socket is being
                connected to the data broadcasting source.
        """
        console.print(f"{get_current_timestamp()} Connecting to {self._url}")
        self._zmq_subscribe = self._zmq_context.socket(zmq.SUB)
        try:
            self._zmq_subscribe.connect(self._url)
        except zmq.error.ZMQError as exc:
            raise OmInvalidZmqUrl(
                "The format of the provided URL is not valid. The URL must be in "
                "the format tcp://hostname:port or in the format "
                "ipc:///path/to/socket, and in the latter case the user must have the "
                "correct permissions to access the socket."
            ) from exc
        self._zmq_subscribe.setsockopt_string(
            zmq.SUBSCRIBE,
            unicode_str(self._subscription_string),
        )

        # Sets a high water mark of 1 (A messaging queue that is 1 message long, so no
        # queuing).
        self._zmq_subscribe.set_hwm(1)
        self._zmq_poller = zmq.Poller()
        self._zmq_poller.register(self._zmq_subscribe, zmq.POLLIN)

        self._listening_timer.start()

    def stop_listening(self) -> None:
        """
        Stops listening to an OM's broadcasting socket and disconnects.

        This function completely disconnects the listening socket from the broadcasting
        source. The socket needs to be reconnected (using the
        [`start_listening`][om.lib.zmq_qt.ZmqDataListener.start_listening] function) to
        start receiving data again.
        """
        self._listening_timer.stop()
        console.print(f"{get_current_timestamp()} Disconnecting from {self._url}.")
        self._zmq_subscribe.disconnect(f"{self._url}")
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
