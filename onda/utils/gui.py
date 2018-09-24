#!/usr/bin/env python
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
"""
Base GUI class.

This module contains the implementation of the base OnDA GUI class.
This class should be subclassed to create OnDA GUIs.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import copy
import time

from onda.utils import zmq

try:
    from PyQt5 import QtCore, QtGui
except ImportError:
    from PyQt4 import QtCore, QtGui


class OndaGui(QtGui.QMainWindow):
    """
    See __init_ for documentation.
    """

    _listening_thread_start_processing = QtCore.pyqtSignal()
    _listening_thread_stop_processing = QtCore.pyqtSignal()

    def __init__(self,
                 pub_hostname,
                 pub_port,
                 subscription_string,
                 gui_update_func,):
        """
        Main GUI class.

        A class implementing the common GUI elements. It should be
        subclassed to create an OnDA GUI. Let the user set up the GUI
        in the constructor method of the derived class. Then make then
        sure that the 'gui_update_func' function is called at regular
        intervals to update the GUI. Furthermore, instantiate a
        listening thread to receive data from an OnDA monitor and make
        the data available to the derived class as soon as it is
        received.

        Attributes:

            data (Dict): dictionary containing the last data received
                from the OnDA monitor.

            listening (bool): the state of the listening thread. True
                if the thread is listening for data from the OnDA
                monitor, False if it is not.

        Args:

            pub_hostname (str): hostname or IP address of the machine
                where the OnDA monitor is running.

            pub_port (int): port on which the the OnDA monitor is
                broadcasting information.

            subscription_string (str): the subscription string used to
                filter data received from the OnDA monitor.

            gui_update_func (Callable): function that updates the GUI,
                to be called at regular intervals.
        """
        super(OndaGui, self).__init__()

        self._gui_update_func = gui_update_func
        self.data = None
        self.listening = False

        # Initialize an empty status bar
        self.statusBar().showMessage('')

        # Create and initialize the ZMQ listening thread.
        self._data_listener_thread = QtCore.QThread()
        self._data_listener = zmq.DataListener(
            pub_hostname=pub_hostname,
            pub_port=pub_port,
            subscription_string=subscription_string
        )

        self._data_listener.zmqmessage.connect(self._data_received)

        self._listening_thread_start_processing.connect(
            self._data_listener.start_listening
        )

        self._listening_thread_stop_processing.connect(
            self._data_listener.stop_listening
        )

        self._data_listener.moveToThread(
            self._data_listener_thread
        )

        self._data_listener_thread.start()
        self.start_listening()

        # Set and start the timer that will call the GUI update
        # function at regular intervals (hardcoded to 500ms).
        self._refresh_timer = QtCore.QTimer()
        self._refresh_timer.timeout.connect(self._gui_update_func)
        self._refresh_timer.start(500)

    def start_listening(self):
        """
        Start listening for data from the OnDA monitor.
        """
        if not self.listening:
            self.listening = True
            self._listening_thread_start_processing.emit()

    def stop_listening(self):
        """
        Stop listening for data from the OnDA monitor.
        """
        if self.listening:
            self.listening = False
            self._listening_thread_stop_processing.emit()

    def _data_received(self,
                       data_dictionary):
        # This function is called when the listening thread receives data.

        # Store the received dictionary as an attribute.
        self.data = copy.deepcopy(data_dictionary)

        # Compute the esimated delay and print it into the status bar.
        # (A GUI is supposed to be a MainWindow widget, so it is suppposed
        # to have a status bar.)
        # Use the timestamp of the last event accumulated event to
        # compute the estimated delay.
        timestamp = self.data[-1][b'timestamp']
        timenow = time.time()
        self.statusBar().showMessage(
            "Estimated delay: {} seconds".format(
                round(timenow - timestamp, 6)
            )
        )
