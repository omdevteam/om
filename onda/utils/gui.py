# This file is part of OnDA.
#
# OnDA is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# OnDA is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with OnDA.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Base OnDA GUI class and custom OnDA widget.
"""
from __future__ import absolute_import, division, print_function

import copy
import time
from typing import Any, Callable, Dict, List  # pylint: disable=unused-import

from onda.utils import data_transmission

try:
    from PyQt5 import QtCore, QtGui
except ImportError:
    from PyQt4 import QtCore, QtGui


class OndaGui(QtGui.QMainWindow):
    """
    See documentation of the '__init__' function.
    """

    # Signals to connect or disconnect from an OnDA monitor.
    _listening_thread_start_processing = QtCore.pyqtSignal()
    _listening_thread_stop_processing = QtCore.pyqtSignal()

    def __init__(self, hostname, port, subscription_string, gui_update_func):
        # type: (str, int, str, Callable) -> None
        """
        Main GUI class.

        This class implements all the common OnDA GUI elements. It is designed to be
        subclassed to implement specific OnDA GUIs. It lets the derived class set up
        the main GUI infrastructure by calling its contructor. It also makes sure that
        the 'gui_update_func' function, attached to instances of this class at creation
        time, is invoked at regular intervals to update the GUI. Additionally, it
        instantiates a listening thread to receive filtered data from the broadcasting
        socket of an OnDA monitor.

        Attributes:

            received_data (List[Dict[bytes, Any], ...]): the latest data received from
                an OnDA monitor. A list of aggregated event data entries, each stored
                in a dictionary.

            is_gui_listening (bool): the state of the listening thread. True if the
                thread is connected to an OnDA monitor, False otherwise.

        Arguments:

            hostname (str): hostname or IP address of the machine where the OnDA
                monitor is broadcasting data.

            port (int): port where the OnDA monitor is broadcasting data.

            subscription_string (str): a string used to filter the data received from
                the OnDA monitor.

            gui_update_func (Callable): function that updates the GUI, to be called at
                regular intervals.
        """
        super(OndaGui, self).__init__()

        self._gui_update_func = gui_update_func
        self.aggregated_data = None
        self.listening = False

        # Initializes an empty status bar
        self.statusBar().showMessage("")

        self._data_listener_thread = QtCore.QThread()
        self._data_listener = data_transmission.ZmqDataListener(
            hostname=hostname, port=port, tag=subscription_string
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

    def _data_received(self, aggregated_data):
        # type: (List[Dict[str, Any]]) -> None
        # This function is called every time the listening thread receives data from an
        # OnDA monitor. The received data has the format of a list of event data
        # entries, each stored in a dictionary.
        self.aggregated_data = copy.deepcopy(aggregated_data)

        # Computes the estimated age of the received data and prints it into the status
        # bar (a GUI is supposed to be a Qt MainWindow widget, so it is supposed to
        # have a status bar). The timestamp of the last event in the received list is
        # used to compute the age of the data.
        timestamp = self.aggregated_data[-1][b"timestamp"]
        timenow = time.time()
        self.statusBar().showMessage(
            "Estimated delay: {} seconds".format(round(timenow - timestamp, 6))
        )
