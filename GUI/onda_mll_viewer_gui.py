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

try:
    from PyQt5 import QtCore, QtGui
except ImportError:
    from PyQt4 import QtCore, QtGui
from collections import namedtuple
import copy
import datetime
import pyqtgraph as pg
import signal
import sys

try:
    from GUI.UI.onda_mll_viewer_ui_qt5 import Ui_MainWindow
except ImportError:
    from GUI.UI.onda_mll_viewer_ui_qt4 import Ui_MainWindow
import ondautils.onda_zmq_gui_utils as zgut


_Scale = namedtuple('Scaled', ['fs', 'ss'])


class MainFrame(QtGui.QMainWindow):

    listening_thread_start_processing = QtCore.pyqtSignal()
    listening_thread_stop_processing = QtCore.pyqtSignal()

    def __init__(self, rec_ip, rec_port):
        super(MainFrame, self).__init__()

        self._data = {}
        self._img = None
        self._alt_img = None

        self._init_listening_thread(rec_ip, rec_port)

        pg.setConfigOption('background', 0.2)

        self._ui = Ui_MainWindow()
        self._ui.setupUi(self)
        self._init_ui()

        self._bot_axis = self._ui.imageView.view.getAxis('bottom')
        self._lef_axis = self._ui.imageView.view.getAxis('left')

        self._ui.imageView.scene.sigMouseClicked.connect(self._mouse_clicked)
 
        self._data = {}
        self._local_data = {}
        self._pos = (0, 0)
        self._scale = (0, 0)
        self._curr_run_num = 0
        self._curr_type = 0
        self._img = None

        self._init_timer()

    def _init_listening_thread(self, rec_ip, rec_port):
        self.zeromq_listener_thread = QtCore.QThread()
        self.zeromq_listener = zgut.ZMQListener(rec_ip, rec_port, u'ondadata')
        self.zeromq_listener.zmqmessage.connect(self._data_received)
        self.listening_thread_start_processing.connect(self.zeromq_listener.start_listening)
        self.listening_thread_stop_processing.connect(self.zeromq_listener.stop_listening)
        self.zeromq_listener.moveToThread(self.zeromq_listener_thread)
        self.zeromq_listener_thread.start()
        self.listening_thread_start_processing.emit()

    def _init_timer(self):
        self.refresh_timer = QtCore.QTimer()
        self.refresh_timer.timeout.connect(self._update_image)
        self.refresh_timer.start(500)

    def _init_ui(self):
        self._ui.imageView = pg.ImageView(view=pg.PlotItem())
        self._ui.imageViewLayout.addWidget(self._ui.imageView)
        self._ui.imageView.ui.menuBtn.hide()
        self._ui.imageView.ui.roiBtn.hide()

        self._ui.stxmButton.setEnabled(False)
        self._ui.dpcButton.setEnabled(False)
        self._ui.ssIntegrButton.setEnabled(False)
        self._ui.fsIntegrButton.setEnabled(False)

        self._ui.stxmButton.clicked.connect(self._draw_image)
        self._ui.dpcButton.clicked.connect(self._draw_image)
        self._ui.ssIntegrButton.clicked.connect(self._draw_image)
        self._ui.fsIntegrButton.clicked.connect(self._draw_image)

        self._ui.rescaleButton.clicked.connect(self._rescale_image)
        
        self.resize(800, 800)
        self.show()

    def _mouse_clicked(self, evt):
        if self._ui.imageView.getView().sceneBoundingRect().contains(evt.scenePos()):
            mouse_point = self._ui.imageView.getView().vb.mapSceneToView(evt.scenePos())
            self._ui.lastClickedPosLabel.setText(
                'Last clicked position:    ss {0:.6f} / fs: {1:.6f}'.format(mouse_point.y(), mouse_point.x())
            )

    def _data_received(self, datdict):
        self._data = copy.deepcopy(datdict)

    def _rescale_image(self):
        self._ui.imageView.setLevels(self._img.min(), self._img.max())
        self._draw_image()

    def _draw_image(self):

        if self._curr_type == 2:
            if self._ui.stxmButton.isChecked():
                self._img = self._local_data['stxm']
            else:
                self._img = self._local_data['dpc']
  
        if self._curr_type == 1:
            if self._ui.ssIntegrButton.isChecked():
                self._img = self._local_data['ss_integr_image']
            else:
                self._img = self._local_data['fs_integr_image']
        self._ui.imageView.setImage(self._img, autoRange=False, autoLevels=False, pos=self._pos, scale=self._scale)
        QtGui.QApplication.processEvents()

        timestamp = self._local_data['timestamp']
        if timestamp is not None:
            timenow = datetime.datetime.now()
            self._ui.delayLabel.setText('Estimated delay: ' + str((timenow - timestamp).seconds) + '.' +
                                        str((timenow - timestamp).microseconds)[0:3] + ' seconds')
        else:
            self._ui.delayLabel.setText('Estimated delay: -')

        QtGui.QApplication.processEvents()        
 
    def _update_image(self):

        if len(self._data) != 0:
            self._local_data = self._data
            self._data = {}
        else:
            return

        QtGui.QApplication.processEvents()

        autorange = False

        scan_type = self._local_data['scan_type']

        if self._local_data['num_run'] > self._curr_run_num:
            print('Starting new run.')
         
            self._bot_axis.setLabel(self._local_data['fs_name'])
            self._curr_run_num = self._local_data['num_run']

            if self._local_data['scan_type'] == 2:
                self._lef_axis.setLabel(self._local_data['ss_name'])
                self._pos = (self._local_data['fs_start'], self._local_data['ss_start'])
                self._scale = _Scale(
                    (self._local_data['fs_end'] - self._local_data['fs_start']) / (self._local_data['fs_steps']),
                    (self._local_data['ss_end'] - self._local_data['ss_start']) / (self._local_data['ss_steps'])
                )
            else:
                self._lef_axis.setLabel('')
                self._pos = (self._local_data['fs_start'], 0)
                self._scale = (
                    (self._local_data['fs_end'] - self._local_data['fs_start']) / (self._local_data['fs_steps']),
                    1.0
                )

            if self._scale.ss > self._scale.fs:
                ratio = max(self._scale) / min(self._scale)
            else:
                ratio = min(self._scale) / max(self._scale)

            self._ui.imageView.getView().setAspectLocked(True, ratio=ratio)
            
            self._ui.lastClickedPosLabel.setText('Last clicked position:    ss: - / fs: -')
            
            autorange = True

        if scan_type != self._curr_type:
    
            if scan_type == 2:
                self._ui.stxmButton.setEnabled(True)
                self._ui.stxmButton.setChecked(True)
                self._ui.dpcButton.setEnabled(True)
                self._ui.ssIntegrButton.setEnabled(False)
                self._ui.fsIntegrButton.setEnabled(False)
 
            QtGui.QApplication.processEvents()

            if scan_type == 1:
                self._ui.stxmButton.setEnabled(False)
                self._ui.dpcButton.setEnabled(False)
                self._ui.ssIntegrButton.setEnabled(True)
                self._ui.ssIntegrButton.setChecked(True)
                self._ui.fsIntegrButton.setEnabled(True)
 
            self._curr_type = scan_type
       
        QtGui.QApplication.processEvents()
        
        self._draw_image()
        if autorange:
            self._ui.imageView.autoRange()


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
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
