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
from copy import deepcopy
from datetime import datetime
try:
    from PyQt5 import QtCore, QtGui
except ImportError:
    from PyQt4 import QtCore, QtGui
from signal import signal, SIGINT, SIG_DFL

from GUI.utils.zmq_gui_utils import ZMQListener
try:
    from GUI.UI.onda_mll_viewer_ui_qt5 import Ui_MainWindow
except:
    from GUI.UI.onda_mll_viewer_ui_qt4 import Ui_MainWindow

class MainFrame(QtGui.QMainWindow):

    listening_thread_start_processing = QtCore.pyqtSignal()
    listening_thread_stop_processing = QtCore.pyqtSignal()

    def __init__(self, rec_ip, rec_port):
        super(MainFrame, self).__init__()

        self.data = {}
        self.img = None
        self.alt_img = None

        self.init_listening_thread(rec_ip, rec_port)

        pg.setConfigOption('background', 0.2)

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.init_ui()

        self.bot_axis = self.ui.imageView.view.getAxis('bottom')
        self.lef_axis = self.ui.imageView.view.getAxis('left')

        self.ui.imageView.scene.sigMouseClicked.connect(self.mouse_clicked)
 
        self.data = {}
        self.local_data = {}
        self.pos = (0, 0)
        self.scale = (0, 0)
        self.curr_run_num = 0
        self.curr_type = 0
        self.img = None

        self.init_timer()

    def init_listening_thread(self, rec_ip, rec_port):
        self.zeromq_listener_thread = QtCore.QThread()
        self.zeromq_listener = ZMQListener(rec_ip, rec_port, u'ondadata')
        self.zeromq_listener.zmqmessage.connect(self.data_received)
        self.listening_thread_start_processing.connect(self.zeromq_listener.start_listening)
        self.listening_thread_stop_processing.connect(self.zeromq_listener.stop_listening)
        self.zeromq_listener.moveToThread(self.zeromq_listener_thread)
        self.zeromq_listener_thread.start()
        self.listening_thread_start_processing.emit()

    def init_timer(self):
        self.refresh_timer = QtCore.QTimer()
        self.refresh_timer.timeout.connect(self.update_image)
        self.refresh_timer.start(500)

    def init_ui(self):
        self.ui.imageView = pg.ImageView(view=pg.PlotItem())
        self.ui.imageViewLayout.addWidget(self.ui.imageView)
        self.ui.imageView.ui.menuBtn.hide()
        self.ui.imageView.ui.roiBtn.hide()

        self.ui.stxmButton.setEnabled(False)
        self.ui.dpcButton.setEnabled(False)
        self.ui.ssIntegrButton.setEnabled(False)
        self.ui.fsIntegrButton.setEnabled(False)

        self.ui.stxmButton.clicked.connect(self.draw_image)
        self.ui.dpcButton.clicked.connect(self.draw_image)
        self.ui.ssIntegrButton.clicked.connect(self.draw_image)
        self.ui.fsIntegrButton.clicked.connect(self.draw_image)

        self.ui.rescaleButton.clicked.connect(self.rescale_image)
        
        self.resize(800, 800)
        self.show()

    def mouse_clicked(self, evt):
        if self.ui.imageView.getView().sceneBoundingRect().contains(evt.scenePos()):
            mouse_point = self.ui.imageView.getView().vb.mapSceneToView(evt.scenePos())
            self.ui.lastClickedPosLabel.setText(
                'Last clicked position:    ss {0:.6f} / fs: {1:.6f}'.format(mouse_point.y(), mouse_point.x())
            )

    def data_received(self, datdict):
        self.data = deepcopy(datdict)

    def rescale_image(self):
        self.ui.imageView.setLevels(self.img.min(), self.img.max())
        self.draw_image()

    def draw_image(self):

        if self.curr_type == 2:
            if self.ui.stxmButton.isChecked():
                self.img = self.local_data['stxm']
            else:
                self.img = self.local_data['dpc']
  
        if self.curr_type == 1:
            if self.ui.ssIntegrButton.isChecked():
                self.img = self.local_data['ss_integr_image']
            else:
                self.img = self.local_data['fs_integr_image']
        self.ui.imageView.setImage(self.img, autoRange=False, autoLevels=False, pos=self.pos, scale=self.scale)
        QtGui.QApplication.processEvents()

        timestamp = self.local_data['timestamp']
        if timestamp is not None:
            timenow = datetime.now()
            self.ui.delayLabel.setText('Estimated delay: ' + str((timenow - timestamp).seconds) + '.' +
                                       str((timenow - timestamp).microseconds)[0:3] + ' seconds')
        else:
            self.ui.delayLabel.setText('Estimated delay: -')

        QtGui.QApplication.processEvents()        
 
    def update_image(self):

        if len(self.data) != 0:
            self.local_data = self.data
            self.data = {}
        else:
            return

        QtGui.QApplication.processEvents()

        autorange = False

        scan_type = self.local_data['scan_type']

        if self.local_data['num_run'] > self.curr_run_num:
            print('Starting new run.')
         
            self.bot_axis.setLabel(self.local_data['fs_name'])
            self.curr_run_num = self.local_data['num_run']

            if self.local_data['scan_type'] == 2:
                self.lef_axis.setLabel(self.local_data['ss_name'])
                self.pos = (self.local_data['fs_start'], self.local_data['ss_start'])
                self.scale = (
                    (self.local_data['fs_end'] - self.local_data['fs_start']) / (self.local_data['fs_steps']),
                    (self.local_data['ss_end'] - self.local_data['ss_start']) / (self.local_data['ss_steps'])
                )
            else:
                self.lef_axis.setLabel('')
                self.pos = (self.local_data['fs_start'], 0)
                self.scale = (
                    (self.local_data['fs_end'] - self.local_data['fs_start']) / (self.local_data['fs_steps']),
                    1.0
                )

            if self.scale[1] > self.scale[0]:
                ratio = max(self.scale)/min(self.scale)
            else:
                ratio = min(self.scale)/max(self.scale)

            self.ui.imageView.getView().setAspectLocked(True, ratio=ratio)
            
            self.ui.lastClickedPosLabel.setText('Last clicked position:    ss: - / fs: -')
            
            autorange = True

        if scan_type != self.curr_type:
    
            if scan_type == 2:
                self.ui.stxmButton.setEnabled(True)
                self.ui.stxmButton.setChecked(True)
                self.ui.dpcButton.setEnabled(True)
                self.ui.ssIntegrButton.setEnabled(False)
                self.ui.fsIntegrButton.setEnabled(False)
 
            QtGui.QApplication.processEvents()

            if scan_type == 1:
                self.ui.stxmButton.setEnabled(False)
                self.ui.dpcButton.setEnabled(False)
                self.ui.ssIntegrButton.setEnabled(True)
                self.ui.ssIntegrButton.setChecked(True)
                self.ui.fsIntegrButton.setEnabled(True)
 
            self.curr_type = scan_type
       
        QtGui.QApplication.processEvents()
        
        self.draw_image()
        if autorange:
            self.ui.imageView.autoRange()


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
        print('Usage: onda-mll-gui.py <listening ip> <listening port>')
        sys.exit()

    _ = MainFrame(rec_ip, rec_port)
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
