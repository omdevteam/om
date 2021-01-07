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
# Copyright 2020 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Base OM graphical user interface object.

This module contains base abstract classes for OM GUIs.
"""
import copy
from abc import ABCMeta, abstractmethod
from typing import Any, Callable, Dict, List, Union  # noqa: F401

from om.utils import zmq_gui

from PyQt5 import QtCore, QtWidgets  # type: ignore


class QtMetaclass(type(QtCore.QObject), ABCMeta):  # type: ignore
    """
    Metaclass for ABC classes with Qt inheritance.
    """

    pass


class OmGui(QtWidgets.QMainWindow, metaclass=QtMetaclass):  # type: ignore
    """
    See documentation of the '__init__' function.
    """

    # Signals to connect or disconnect from an OM monitor.
    _listening_thread_start_processing: Any = QtCore.pyqtSignal()
    _listening_thread_stop_processing: Any = QtCore.pyqtSignal()

    def __init__(self, url: str, tag: str):
        """
        Main OM graphical user interface class.

        This class implements the common elements of all OM graphical interfaces and
        should be subclassed to implement specific interfaces and viewers. A derived
        class can set up the main GUI infrastructure by calling the constructor of this
        class: this class instantiates a listening thread that receives filtered data
        from the broadcasting socket of an OM monitor. It sets up the basic widget
        structure of the GUI and it makes sure that the GUI update function, attached
        to this class at instantiation, is called at regular intervals to update the
        GUI.

        Arguments:

            url (str): the URL at which the GUI will connect and listen for data. This
                must be a string in the format used by thh ZeroMQ Protocol.

            tag (str): a string used to filter the data received from an OM monitor.
                Only data whose tag label matches this argument will be accepted and
                received.

        Attributes:

            received_data (List[Dict[bytes, Any]]): the latest data received from
                an OM monitor. A list of aggregated event data entries, each stored
                in a dictionary.

            is_gui_listening (bool): the state of the listening thread. True if the
                GUI is currently listening to an OM monitor, False otherwise.
        """
        super(OmGui, self).__init__()

        self._received_data: Dict[str, Any] = {}
        self.listening: bool = False

        # Initializes an empty status bar
        self.statusBar().showMessage("")

        self._data_listener_thread: Any = QtCore.QThread(parent=self)
        self._data_listener: zmq_gui.ZmqDataListener = zmq_gui.ZmqDataListener(
            url=url, tag=tag
        )
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
        Connects to an OM monitor and starts listening for broadcasted data.
        """
        if not self.listening:
            self.listening = True
            self._listening_thread_start_processing.emit()

    def stop_listening(self) -> None:
        """
        Disconnects from an OM monitor and stops listening.
        """
        if self.listening:
            self.listening = False
            self._listening_thread_stop_processing.emit()

    def _data_received(self, received_data: Dict[str, Any]) -> None:
        # This function is called every time the listening thread receives data from an
        # OM monitor. The received data has the format of a list of event data
        # entries, each stored in a dictionary.
        self._received_data = copy.deepcopy(received_data)

    @abstractmethod
    def update_gui(self) -> None:
        """
        Updates GUI elements.

        This function is called at regular intervals and updates the elements of the
        GUI as required.
        """
        pass
