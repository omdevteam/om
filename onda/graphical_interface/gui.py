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
Module with basic GUI class.

Exports:

    Classes:

        MainWindow: basic GUI class.
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
    Main GUI class.

    A class implementing the main GUI code. Upon startup,
    call the 'gui_init_func' function defined by the user
    to setup the GUI. Then call at regular intervals the
    'gui_update_func' function defined by the user to update the GUI.
    Instantiate a listening thread to receive data from the OnDA
    monitor, and make new data available to the user in the 'data'
    attribute as soon as it is received. This class can be subclassed
    to create OnDA GUIs.

    Attributes:

        data (Dict): dictionary containing the last data received
            from the OnDA monitor.
    """
    _listening_thread_start_processing = QtCore.pyqtSignal()
    _listening_thread_stop_processing = QtCore.pyqtSignal()
    # Two custom signals to start and stop the ZMQ listener.

    def __init__(self,
                 pub_hostname,
                 pub_port,
                 gui_update_func,
                 subscription_string):
        """
        Initialize the OndaGUI class.

        Args:

            pub_hostname (str): hostname or IP address of the host
                where OnDA is running.

            pub_hostname (int): port of the OnDA monitor's PUB socket.

            gui_init_function (Callable): function that implements the
                GUI initialization.

            gui_update_func (Callable): function that implements the
                updating of the GUI with new data.

            subscription_string (str): the subscription string for the
                SUB socket.
        """
        super(OndaGui, self).__init__()

        # Create the attribute that will store the data received from
        # the ZMQ listener.
        self.data = None

        self.listening = False

        # Create and initialize the ZMQ listening thread.
        self._zeromq_listener_thread = QtCore.QThread()
        self._zeromq_listener = zmq.ZMQListener(
            pub_hostname=pub_hostname,
            pub_port=pub_port,
            subscription_string=subscription_string
        )
        self._zeromq_listener.zmqmessage.connect(self._data_received)
        self._listening_thread_start_processing.connect(
            self._zeromq_listener.start_listening
        )
        self._listening_thread_stop_processing.connect(
            self._zeromq_listener.stop_listening
        )
        self._zeromq_listener.moveToThread(
            self._zeromq_listener_thread
        )
        self._zeromq_listener_thread.start()
        self.start_listening()

        # Store the function to initialize the GUI in an attribute.
        # Then set and start the timer that will call the update
        # function at regular intervals.
        self._gui_update_func = gui_update_func
        self._refresh_timer = QtCore.QTimer()
        self._refresh_timer.timeout.connect(self._gui_update_func)
        self._refresh_timer.start(500)

    def start_listening(self):
        if not self.listening:
            self.listening = True
            self._listening_thread_start_processing.emit()

    def stop_listening(self):
        if self.listening:
            self.listening = False
            self._listening_thread_stop_processing.emit()

    def _data_received(self,
                       datdict):
        # Copy the data received via the signal into an attribute.
        self.data = copy.deepcopy(datdict)

        # Compute the esimated delay and print it int the status bar.
        timestamp = self.data['timestamp']
        if timestamp is not None:
            timenow = time.time()
            self.statusBar().showMessage(
                "Estimated delay: {} seconds".format(
                    round(timenow - timestamp, 6)
                )
            )
        else:
            self.statusBar.showMessage(
                "Estimated delay: -"
            )
