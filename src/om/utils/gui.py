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
Base OnDA graphical user interface object.

This module contains a class that implements the common infrastructure of all OnDA
python GUIs (e.g.: management of the data transimission, reporting of the estimated
delay, etc.)
"""
from __future__ import absolute_import, division, print_function

import copy
import time
from typing import Any, Callable, Dict, List

from onda.utils import zmq_gui

try:
    from PyQt5 import QtCore, QtWidgets as qt_widget_module
except ImportError:
    from PyQt4 import QtCore, QtGui as qt_widget_module


class OndaGui(qt_widget_module.QMainWindow):
    """
    See documentation of the '__init__' function.
    """

    # Signals to connect or disconnect from an OnDA monitor.
    _listening_thread_start_processing = QtCore.pyqtSignal()
    _listening_thread_stop_processing = QtCore.pyqtSignal()

    def __init__(self, hostname, port, tag, gui_update_func):
        # type: (str, int, str, Callable) -> None
        """
        Main OnDA graphical user interface class.

        This class implements the common elements of all OnDA graphical interfaces and
        must be subclassed to implement specific interfaces and viewers. A derived
        class can set up the main GUI infrastructure by calling the constructor of this
        class. This class also instantiates a listening thread that receives filtered
        data from the broadcasting socket of an OnDA monitor. Additionally, it makes
        sure that the 'gui_update_func' function, attached when an instance is created,
        is invoked at regular intervals to update the GUI.

        NOTE: This class is designed to be subclassed to implement specific OnDA GUIs.

        Arguments:

            hostname (str): the hostname or IP address where the GUI will listen for
                data.

            port(int): the port at which the GUI will listen for data.

            tag (str): a string used to filter the data received from an OnDA monitor.
                Only data whose label matches this argument will be accepted and
                received.

        Attributes:

            received_data (List[Dict[bytes, Any]]): the latest data received from
                an OnDA monitor. A list of aggregated event data entries, each stored
                in a dictionary.

            is_gui_listening (bool): the state of the listening thread. True if the
                GUI is currently listening to an OnDA monitor, False otherwise.
        """
        super(OndaGui, self).__init__()

        self._gui_update_func = gui_update_func
        self.received_data = None
        self.listening = False

        # Initializes an empty status bar
        self.statusBar().showMessage("")

        self._data_listener_thread = QtCore.QThread()
        self._data_listener = zmq_gui.ZmqDataListener(
            hostname=hostname, port=port, tag=tag
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
        self._refresh_timer.timeout.connect(self._gui_update_func)
        self._refresh_timer.start(500)

    def start_listening(self):
        # type: () -> None
        """
        Connects to an OnDA monitor and starts listening for broadcasted data.
        """
        if not self.listening:
            self.listening = True
            self._listening_thread_start_processing.emit()

    def stop_listening(self):
        # type: () -> None
        """
        Disconnects from an OnDA monitor and stops listening to broadcasted data.
        """
        if self.listening:
            self.listening = False
            self._listening_thread_stop_processing.emit()

    def _data_received(self, received_data):
        # type: (List[Dict[str, Any]]) -> None
        # This function is called every time the listening thread receives data from an
        # OnDA monitor. The received data has the format of a list of event data
        # entries, each stored in a dictionary.
        self.received_data = copy.deepcopy(received_data)

        # Computes the estimated age of the received data and prints it into the status
        # bar (a GUI is supposed to be a Qt MainWindow widget, so it is supposed to
        # have a status bar). The timestamp of the last event in the received list is
        # used to compute the age of the data.
        timestamp = self.received_data[-1][b"timestamp"]
        timenow = time.time()
        self.statusBar().showMessage(
            "Estimated delay: {0} seconds".format(round(timenow - timestamp, 6))
        )
