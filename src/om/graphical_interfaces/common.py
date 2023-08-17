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
Base classes for OM's graphical interfaces.

This module contains common base classes and functions used by all of OM's graphical
user interfaces and viewers.
"""
import copy
from abc import ABCMeta
from typing import Any, Callable, Dict, List, Union  # noqa: F401

from om.lib.exceptions import OmMissingDependencyError
from om.lib.zmq_qt import ZmqDataListener

try:
    from PyQt5 import QtCore, QtWidgets
except ImportError:
    raise OmMissingDependencyError(
        "The following required module cannot be imported: PyQt5"
    )


class _QtMetaclass(type(QtCore.QObject), ABCMeta):  # type: ignore
    # This metaclass is used internally to resolve an issue with classes that inherit
    # from Qt and non-Qt classes at the same time.
    pass


class OmGuiBase(QtWidgets.QMainWindow, metaclass=_QtMetaclass):
    """
    See documentation of the `__init__` function.
    """

    # Signals to connect or disconnect from an OM monitor.
    _listening_thread_start_processing: Any = QtCore.pyqtSignal()
    _listening_thread_stop_processing: Any = QtCore.pyqtSignal()

    def __init__(self, *, url: str, tag: str):
        """
        Base class for OM's graphical user interfaces.

        This class implements elements that are common to all of OM's graphical
        interfaces. When initialized, this class creates a listening thread that
        receives data from an OnDA Monitor (filtered according to a provided tag). It
        additionally lays out the basic widget structure of the interface. Finally, it
        makes sure that a function that updates the graphical elements of the interface
        is called at regular intervals.

        The class has methods to start and stop the listening thread, effectively
        attaching and detaching the graphical interface from the OnDA Monitor
        broadcasting the data

        This base class should be subclassed to create specific graphical interfaces.
        Each derived class should always call the constructor of this class during
        initialization, and must additionally provide its own specific implementation
        of the abstract
        [update_gui][om.graphical_interfaces.common.OmGuiBase.update_gui] function.

        Arguments:

            url: The URL at which the GUI will connect and listen for data. This must
                be a string in the format used by the ZeroMQ protocol.

            tag: A string used to filter the data received from an OnDA Monitor. The
                GUI only receives data whose tag matches this argument.
        """
        super(OmGuiBase, self).__init__()

        self._received_data: Dict[str, Any] = {}
        self.listening: bool = False

        # Initializes an empty status bar
        self.statusBar().showMessage("")

        self._data_listener_thread: Any = QtCore.QThread(parent=self)
        self._data_listener: ZmqDataListener = ZmqDataListener(url=url, tag=tag)
        self._data_listener.zmqmessage.connect(self._data_received)
        self._listening_thread_start_processing.connect(
            self._data_listener.start_listening
        )
        self._listening_thread_stop_processing.connect(
            self._data_listener.stop_listening
        )
        self._data_listener.moveToThread(self._data_listener_thread)
        self._data_listener_thread.start()
        self.start_listening()

        self._refresh_timer = QtCore.QTimer()
        self._refresh_timer.timeout.connect(self.update_gui)
        self._refresh_timer.start(500)

    def start_listening(self) -> None:
        """
        Connects to an OnDA Monitor and starts listening for broadcast data.

        This function instructs the listening thread to connect to an OnDA Monitor and
        start receiving data.
        """
        if not self.listening:
            self.listening = True
            self._listening_thread_start_processing.emit()

    def stop_listening(self) -> None:
        """
        Disconnects from an OnDA Monitor and stops listening for data.

        This function instructs the listening thread to disconnect from an OnDA Monitor
        and stop receiving data.
        """
        if self.listening:
            self.listening = False
            self._listening_thread_stop_processing.emit()

    def update_gui(self) -> None:
        """
        Updates GUI elements.

        This function is called at regular intervals by this class. It updates plots
        and other elements of the graphical interface.

        This function is an abstract method of this base class: each derived graphical
        interface class must provide its own implementation.
        """

    def _data_received(self, received_data: Dict[str, Any]) -> None:
        # This function is called internally by this class every time the listening
        # thread receives data from an OM monitor. It makes a copy of the received data
        # which then made available to the main GUI thread for further processing.
        self._received_data = copy.deepcopy(received_data)
