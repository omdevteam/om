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
import os
import os.path
import signal
import sys
import time
from collections import namedtuple

import numpy
import pyqtgraph as pg
import scipy.consta nts

from onda.cfelpyutils import crystfel_utils, geometry_utils
from onda.utils import zmq

try:
    from PyQt5 import QtCore
except ImportError:
    from PyQt4 import QtCore

class MainWindow(QtGui.QMainWindow):
    """
    Main GUI class.

    A class implementing the main GUI code. Upon startup,
    call the 'gui_init_func' function defined by the user
    to setup the GUI. Then call at regular intervals the
    'gui_update_func' function defined by the user to update the GUI.
    Instantiate a listening thread to receive data from the OnDA
    monitor, and make new data available to the user in the 'data'
    attribute as soon as it is available.

    Attributes:

        data (Dict): dictionary containing the last data received
            from the OnDA monitor.
    """
    _listening_thread_start_processing = QtCore.pyqtSignal()
    _listening_thread_stop_processing = QtCore.pyqtSignal()

    def __init__(self,
                 rec_ip,
                 rec_port,
                 gui_init_func,
                 gui_update_func):
        """
        Initialize the 

        super(MainWindow, self).__init__()

        gui_init_func()
        self._gui_update_func = gui_update_func()
        self._refresh_timer = QtCore.QTimer()
        self._refresh_timer.timeout.connect(self._gui_update_func)
        self._refresh_timer.start(500)
        self.show()

    def _init_listening_thread(self, rec_ip, rec_port):
        self._zeromq_listener_thread = QtCore.QThread()
        self._zeromq_listener = zgut.ZMQListener(rec_ip, rec_port, u'ondadata')
        self._zeromq_listener.zmqmessage.connect(self._data_received)
        self._listening_thread_start_processing.connect(self._zeromq_listener.start_listening)
        self._listening_thread_stop_processing.connect(self._zeromq_listener.stop_listening)
        self._zeromq_listener.moveToThread(self._zeromq_listener_thread)
        self._zeromq_listener_thread.start()
        self._listening_thread_start_processing.emit()

    def _data_received(self, datdict):
        self.data = copy.deepcopy(datdict)
