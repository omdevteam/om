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
import copy
import datetime
import numpy
import pyqtgraph as pg
import scipy.constants
import signal
import sys

try:
    from GUI.UI.onda_crystallography_ui_qt5 import Ui_MainWindow
except ImportError:
    from GUI.UI.onda_crystallography_ui_qt4 import Ui_MainWindow
import cfelpyutils.cfel_geom as cgm
import ondautils.onda_zmq_gui_utils as zgut


class MainFrame(QtGui.QMainWindow):

    listening_thread_start_processing = QtCore.pyqtSignal()
    listening_thread_stop_processing = QtCore.pyqtSignal()

    def __init__(self, geom_filename, rec_ip, rec_port):
        super(MainFrame, self).__init__()

        self.title = 'CSPAD Crystallography Monitor'
        self.data = {}
        self.rec_ip = rec_ip
        self.rec_port = rec_port
        self.geom_filename = geom_filename
        self.local_data = {'peak_list': ([], [], []), 'hit_rate': 0, 'hit_flag': True, 'sat_rate': 0,
                           'time_string': None}
        self.pixel_maps, self.slab_shape, self.img_shape = cgm.pixel_maps_for_image_view(self.geom_filename)
        self.image_center = (self.img_shape[0]/2, self.img_shape[1]/2)
        self.coffset = cgm.coffset_from_geometry_file(self.geom_filename)
        self.res = cgm.res_from_geometry_file(self.geom_filename)
        self.img = numpy.zeros(self.img_shape, dtype=numpy.float32)
        self.sum_img = numpy.zeros(self.img_shape, dtype=numpy.float32)
        self.hitrate_history_size = 10000
        self.hitrate_history = self.hitrate_history_size * [0.0]
        self.satrate_history_size = 10000
        self.satrate_history = self.satrate_history_size * [0.0]
        self.resolution_rings_in_A = [10.0, 9.0, 8.0, 7.0, 6.0, 5.0, 4.0, 3.0]
        self.resolution_rings_textitems = []

        self.init_listening_thread()

        self.resolution_rings_pen = pg.mkPen('w', width=0.5)
        self.resolution_rings_canvas = pg.ScatterPlotItem()
        self.vertical_lines = []
        self.resolution_rings_regex = QtCore.QRegExp('[0-9\.\,]+')
        self.resolution_rings_validator = QtGui.QRegExpValidator()
        self.resolution_rings_validator.setRegExp(self.resolution_rings_regex)
        pg.setConfigOption('background', 0.2)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.init_ui()

        self.proxy = pg.SignalProxy(self.ui.hitRatePlotWidget.scene().sigMouseClicked,
                                    rateLimit=60, slot=self.mouse_clicked)
        self.hitrate_plot = self.ui.hitRatePlotWidget.plot(self.hitrate_history)
        self.satrate_plot = self.ui.saturationPlotViewer.plot(self.satrate_history)
        for ti in self.resolution_rings_textitems:
            self.ui.imageView.getView().addItem(ti)

        self.refresh_timer = QtCore.QTimer()
        self.init_timer()
        self.show()

    def init_listening_thread(self):
        self.zeromq_listener_thread = QtCore.QThread()
        self.zeromq_listener = zgut.ZMQListener(self.rec_ip, self.rec_port, u'ondadata')
        self.zeromq_listener.zmqmessage.connect(self.data_received)
        self.listening_thread_start_processing.connect(self.zeromq_listener.start_listening)
        self.listening_thread_stop_processing.connect(self.zeromq_listener.stop_listening)
        self.zeromq_listener.moveToThread(self.zeromq_listener_thread)
        self.zeromq_listener_thread.start()
        self.listening_thread_start_processing.emit()

    def init_timer(self):
        self.refresh_timer.timeout.connect(self.update_image_plot)
        self.refresh_timer.start(500)

    def init_ui(self):

        self.ui.imageView.ui.menuBtn.hide()
        self.ui.imageView.ui.roiBtn.hide()

        self.ui.imageView.getView().addItem(self.resolution_rings_canvas)

        self.ui.hitRatePlotWidget.setTitle('Hit Rate vs. Events')
        self.ui.hitRatePlotWidget.setLabel('bottom', text='Events')
        self.ui.hitRatePlotWidget.setLabel('left', text='Hit Rate')
        self.ui.hitRatePlotWidget.showGrid(True, True)
        self.ui.hitRatePlotWidget.setYRange(0, 1.0)

        self.ui.saturationPlotViewer.setTitle('Fraction of hits with too many saturated peaks')
        self.ui.saturationPlotViewer.setLabel('bottom', text='Events')
        self.ui.saturationPlotViewer.setLabel('left', text='Saturation rate')
        self.ui.saturationPlotViewer.showGrid(True, True)
        self.ui.saturationPlotViewer.setYRange(0, 1.0)
        self.ui.saturationPlotViewer.setXLink(self.ui.hitRatePlotWidget)

        self.ui.accumulatedPeaksCheckBox.setChecked(True)
        self.ui.accumulatedPeaksCheckBox.stateChanged.connect(self.toggle_acc)
        self.ui.resetPeaksButton.clicked.connect(self.reset_peaks)
        self.ui.resetPlotsButton.clicked.connect(self.reset_plots)

        self.ui.accumulatedPeaksCheckBox.stateChanged.connect(self.toggle_acc)

        self.ui.resolutionRingsCheckBox.setChecked(True)
        self.ui.resolutionRingsCheckBox.stateChanged.connect(self.draw_resolution_rings)

        self.ui.resolutionRingsLineEdit.setValidator(self.resolution_rings_validator)
        self.ui.resolutionRingsLineEdit.setText(','.join(str(x) for x in self.resolution_rings_in_A))
        self.ui.resolutionRingsLineEdit.editingFinished.connect(self.update_resolution_rings)

        self.ui.resolutionRingsCheckBox.setEnabled(False)
        self.ui.resolutionRingsLineEdit.setEnabled(False)

    def mouse_clicked(self, mouse_evt):
        mouse_pos_in_scene = mouse_evt[0].scenePos()
        if self.ui.hitRatePlotWidget.plotItem.sceneBoundingRect().contains(mouse_pos_in_scene):
            if mouse_evt[0].button() == QtCore.Qt.MiddleButton:
                mouse_x_pos_in_data = self.ui.hitRatePlotWidget.plotItem.vb.mapSceneToView(mouse_pos_in_scene).x()
                new_vertical_lines = []
                for vert_line in self.vertical_lines:
                    if abs(vert_line.getPos()[0] - mouse_x_pos_in_data) < 5:
                        self.ui.hitRatePlotWidget.removeItem(vert_line)
                    else:
                        new_vertical_lines.append(vert_line)
                if len(new_vertical_lines) != len(self.vertical_lines):
                    self.vertical_lines = new_vertical_lines
                    return
                vertical_line = pg.InfiniteLine(mouse_x_pos_in_data, angle=90, movable=False)
                self.vertical_lines.append(vertical_line)
                self.ui.hitRatePlotWidget.addItem(vertical_line, ignoreBounds=True)

    def data_received(self, datdict):
        self.data = copy.deepcopy(datdict)

    def update_resolution_rings(self):
        items = str(self.ui.resolutionRingsLineEdit.text()).split(',')
        for ti in self.resolution_rings_textitems:
            self.ui.imageView.getView().removeItem(ti)
        if len(items) == 0:
            self.resolution_rings_in_A = [] 
        self.resolution_rings_in_A = [float(item) for item in items if item != '' and float(item) != 0.0]
        self.resolution_rings_textitems = [pg.TextItem(str(x)+'A',
                                                       anchor=(0.5, 0.8)) for x in self.resolution_rings_in_A]
        for ti in self.resolution_rings_textitems:
            self.ui.imageView.getView().addItem(ti)
        self.draw_resolution_rings()

    def reset_plots(self):
        self.hitrate_history = self.hitrate_history_size * [0.0]
        self.satrate_history = self.satrate_history_size * [0.0]
        self.hitrate_plot.setData(self.hitrate_history)
        self.satrate_plot.setData(self.satrate_history)

    def reset_peaks(self):
        self.sum_img = numpy.zeros(self.img_shape, dtype=numpy.float32)
        self.ui.imageView.setImage(self.sum_img.T, autoHistogramRange=False, autoLevels=False, autoRange=False)

    def toggle_acc(self):
        if self.ui.accumulatedPeaksCheckBox.isChecked():
            self.ui.imageView.setImage(self.sum_img.T, autoHistogramRange=False, autoLevels=False, autoRange=False)
        else:
            self.ui.imageView.setImage(self.img.T, autoHistogramRange=False, autoLevels=False, autoRange=False)

    def draw_resolution_rings(self):

        try:

            lambd = scipy.constants.h * scipy.constants.c / (scipy.constants.e * self.local_data['beam_energy'])
            resolution_rings_in_pix = [1.0]

            resolution_rings_in_pix.extend([2.0 * self.res *
                                            (self.local_data['detector_distance'] * 10e-4 + self.coffset) *
                                            numpy.tan(2.0*numpy.arcsin(lambd/(2.0*resolution*10e-11)))
                                            for resolution in self.resolution_rings_in_A])

        except TypeError:

            print('Beam energy or detector distance are not available. Resolution rings cannot be computed.')
            self.resolution_rings_canvas.setData([], [])
            for index, item in enumerate(self.resolution_rings_textitems):
                item.setText('')

        else:

            if self.ui.resolutionRingsCheckBox.isEnabled() and self.ui.resolutionRingsCheckBox.isChecked():

                self.resolution_rings_canvas.setData(
                    [self.image_center[0]]*len(resolution_rings_in_pix),
                    [self.image_center[1]]*len(resolution_rings_in_pix),
                    symbol='o',
                    size=resolution_rings_in_pix,
                    pen=self.resolution_rings_pen,
                    brush=(0, 0, 0, 0), pxMode=False)
                for index, item in enumerate(self.resolution_rings_textitems):
                    item.setText(str(self.resolution_rings_in_A[index])+'A')
                    item.setPos(self.image_center[0], self.image_center[1] + resolution_rings_in_pix[index+1] / 2.0)

            else:
                self.resolution_rings_canvas.setData([], [])
                for index, item in enumerate(self.resolution_rings_textitems):
                    item.setText('')

    def update_image_plot(self):

        if len(self.data) != 0:
            self.local_data = self.data
            self.data = {}
        else:
            return

        QtGui.QApplication.processEvents()

        if numpy.isnan(self.local_data['hit_rate']):
            self.hitrate_history.append(0)
            hr = 0
        else:
            self.hitrate_history.append(self.local_data['hit_rate'])
            hr = self.local_data['hit_rate']
        self.hitrate_history.pop(0)

        if numpy.isnan(self.local_data['sat_rate']):
            self.hitrate_history.append(0)
        else:
            self.satrate_history.append(self.local_data['sat_rate'])

        self.satrate_history.pop(0)

        self.hitrate_plot.setData(self.hitrate_history)
        self.satrate_plot.setData(self.satrate_history)

        QtGui.QApplication.processEvents()

        if self.local_data['optimized_geometry']:
            if not self.ui.resolutionRingsCheckBox.isEnabled():
                self.ui.resolutionRingsCheckBox.setEnabled(True)
                self.ui.resolutionRingsLineEdit.setEnabled(True)
                self.update_resolution_rings()
            self.draw_resolution_rings()
        else:
            if self.ui.resolutionRingsCheckBox.isEnabled():
                self.ui.resolutionRingsCheckBox.setEnabled(False)
                self.ui.resolutionRingsLineEdit.setEnabled(False)
            self.draw_resolution_rings()

        new_vertical_lines = []
        for vline in self.vertical_lines:
            line_pos = vline.getPos()[0]
            line_pos -= 1
            if line_pos > 0.0:
                vline.setPos(line_pos)
                new_vertical_lines.append(vline)
            else:
                self.ui.hitRatePlotWidget.removeItem(vline)
        self.ui.vertical_lines = new_vertical_lines

        QtGui.QApplication.processEvents()

        timestamp = self.local_data['timestamp']
        if timestamp is not None:
            self.ui.hitRatePlotWidget.setTitle('Hit Rate vs. Events - {0} - {1}%'.format(timestamp.strftime("%H:%M:%S"),
                                                                                         round(hr*100, 1)))
            timenow = datetime.datetime.now()
            self.ui.delayLabel.setText('Estimated delay: {0}.{1} seconds'.format((timenow - timestamp).seconds,
                                       str((timenow - timestamp).microseconds)[0:3]))
        else:
            self.ui.hitRatePlotWidget.setTitle('Hit Rate vs. Events {0}%'.format(round(hr*100, 1)))
            self.ui.delayLabel.setText('Estimated delay: -')

        QtGui.QApplication.processEvents()

        if len(self.local_data['peak_list'][0]) > 0:

            self.img = numpy.zeros(self.img_shape, dtype=numpy.float32)

            for peak_fs, peak_ss, peak_value in zip(self.local_data['peak_list'][0],
                                                    self.local_data['peak_list'][1],
                                                    self.local_data['peak_list'][2]):
                peak_in_slab = int(round(peak_ss))*self.slab_shape[1]+int(round(peak_fs))
                self.img[self.pixel_maps[0][peak_in_slab], self.pixel_maps[1][peak_in_slab]] += peak_value
                self.sum_img[self.pixel_maps[0][peak_in_slab], self.pixel_maps[1][peak_in_slab]] += peak_value

            self.toggle_acc()
            self.local_data['peak_list'] = ([], [], [])


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = QtGui.QApplication(sys.argv)
    if len(sys.argv) == 2:
        geom_filename = sys.argv[1]
        rec_ip = '127.0.0.1'
        rec_port = 12321
    elif len(sys.argv) == 4:
        geom_filename = sys.argv[1]
        rec_ip = sys.argv[2]
        rec_port = int(sys.argv[3])
    else:
        print('Usage: onda-crystallography-gui.py geometry_filename <listening ip> <listening port>')
        sys.exit()

    _ = MainFrame(geom_filename, rec_ip, rec_port)
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
