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


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


import sys
import pyqtgraph as pg
from collections import deque
from copy import deepcopy
try:
    from PyQt5 import QtCore, QtGui
except ImportError:
    from PyQt4 import QtCore, QtGui
from signal import signal, SIGINT, SIG_DFL

from GUI.utils.zmq_gui_utils import ZMQListener
try:
    from GUI.UI.onda_mll_frame_viewer_ui_qt5 import Ui_MainWindow
except ImportError:
    from GUI.UI.onda_mll_frame_viewer_ui_qt4 import Ui_MainWindow

class MainFrame(QtGui.QMainWindow):

    listening_thread_start_processing = QtCore.pyqtSignal()
    listening_thread_stop_processing = QtCore.pyqtSignal()
    
    def __init__(self, rec_ip, rec_port):
        super(MainFrame, self).__init__()

        self.img = None

        self.rec_ip, self.rec_port = rec_ip, rec_port
        self.data = deque(maxlen=20)
        self.data_index = -1

        self.init_listening_thread()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.init_ui()

        self.refresh_timer = QtCore.QTimer()
        self.init_timer()
        self.show()

    def init_ui(self):

        self.ui.imageView.ui.menuBtn.hide()
        self.ui.imageView.ui.roiBtn.hide()

        self.ui.backButton.clicked.connect(self.back_button_clicked)
        self.ui.forwardButton.clicked.connect(self.forward_button_clicked)
        self.ui.playPauseButton.clicked.connect(self.play_pause_button_clicked)

    def back_button_clicked(self):
        if self.data_index > 0:
            self.data_index -= 1
            self.update_image_plot()
    
    def forward_button_clicked(self):
        if (self.data_index + 1) < len(self.data):
            self.data_index += 1
            self.update_image_plot()
    
    def play_pause_button_clicked(self):
        if self.refresh_timer.isActive():
            self.refresh_timer.stop()
            self.data_index = len(self.data) - 1
        else:
            self.refresh_timer.start(self.image_update_us)

    def init_listening_thread(self):
        self.zeromq_listener_thread = QtCore.QThread()
        self.zeromq_listener = ZMQListener(self.rec_ip, self.rec_port, u'ondarawdata')
        self.zeromq_listener.zmqmessage.connect(self.data_received)
        self.zeromq_listener.start_listening()
        self.listening_thread_start_processing.connect(self.zeromq_listener.start_listening)
        self.listening_thread_stop_processing.connect(self.zeromq_listener.stop_listening)
        self.zeromq_listener.moveToThread(self.zeromq_listener_thread)
        self.zeromq_listener_thread.start()
        self.listening_thread_start_processing.emit()

    def init_timer(self):
        self.refresh_timer.timeout.connect(self.update_image_plot)
        self.refresh_timer.start(250)

    def data_received(self, datdict):
        self.data.append(deepcopy(datdict))

    def update_image_plot(self):
        if len(self.data) > 0:
            data = self.data[self.data_index]
            self.img = data['raw_data']
            self.ui.imageView.setImage(self.img.T, autoLevels=False, autoRange=False, autoHistogramRange=False)


def main():
    signal(SIGINT, SIG_DFL)
    app = QtGui.QApplication(sys.argv)
    if len(sys.argv) == 1:
        rec_ip = '127.0.0.1'
        rec_port = 12321
    elif len(sys.argv) == 3:
        rec_ip = sys.argv[1]
        rec_port = int(sys.argv[2])
    else:
        print('Usage: onda_mll_frame_viewer_gui.py <listening ip> <listening port>')
        sys.exit()

    _ = MainFrame(rec_ip, rec_port)
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
