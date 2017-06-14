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
import time
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
import cfelpyutils.cfel_crystfel as cfl
import ondautils.onda_zmq_gui_utils as zgut

_ImageCenter = namedtuple('ImageCenter', ['y', 'x'])

class MainFrame(QtGui.QMainWindow):

    _listening_thread_start_processing = QtCore.pyqtSignal()
    _listening_thread_stop_processing = QtCore.pyqtSignal()

    def __init__(self, geom_filename, rec_ip, rec_port):
        super(MainFrame, self).__init__()

        self._data = {}
        self._local_data = {'peak_list': ([], [], []), 'hit_rate': 0, 'hit_flag': True, 'sat_rate': 0,
                            'time_string': None}
        self._pixel_maps = cgm.pixel_maps_for_image_view(geom_filename)
        self._img_shape = cgm.get_image_shape(geom_filename)

        detector = cfl.load_crystfel_geometry(geom_filename)
        try:
            self._coffset = detector['coffset']
        except KeyError:
            self._coffset = None
        try:
            self._res = detector['res']
        except KeyError:
            self._res = None

        self._image_center = _ImageCenter(self._img_shape[0] / 2, self._img_shape[1] / 2)
        self._img = numpy.zeros(self._img_shape, dtype=numpy.float32)
        self._sum_img = numpy.zeros(self._img_shape, dtype=numpy.float32)
        self._hitrate_history_size = 10000
        self._hitrate_history = self._hitrate_history_size * [0.0]
        self._satrate_history_size = 10000
        self._satrate_history = self._satrate_history_size * [0.0]
        self._resolution_rings_in_A = [10.0, 9.0, 8.0, 7.0, 6.0, 5.0, 4.0, 3.0]
        self._resolution_rings_textitems = []

        self._init_listening_thread(rec_ip, rec_port)

        self._resolution_rings_pen = pg.mkPen('w', width=0.5)
        self._resolution_rings_canvas = pg.ScatterPlotItem()
        self._vertical_lines = []
        self._resolution_rings_regex = QtCore.QRegExp('[0-9\.\,]+')
        self._resolution_rings_validator = QtGui.QRegExpValidator()
        self._resolution_rings_validator.setRegExp(self._resolution_rings_regex)
        pg.setConfigOption('background', 0.2)
        self._ui = Ui_MainWindow()
        self._ui.setupUi(self)
        self._init_ui()

        self._proxy = pg.SignalProxy(self._ui.hitRatePlotWidget.scene().sigMouseClicked,
                                     rateLimit=60, slot=self._mouse_clicked)
        self._hitrate_plot = self._ui.hitRatePlotWidget.plot(self._hitrate_history)
        self._satrate_plot = self._ui.saturationPlotViewer.plot(self._satrate_history)
        for ti in self._resolution_rings_textitems:
            self._ui.imageView.getView().addItem(ti)

        self._refresh_timer = QtCore.QTimer()
        self._init_timer()
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

    def _init_timer(self):
        self._refresh_timer.timeout.connect(self._update_image_plot)
        self._refresh_timer.start(500)

    def _init_ui(self):

        self._ui.imageView.ui.menuBtn.hide()
        self._ui.imageView.ui.roiBtn.hide()

        self._ui.imageView.getView().addItem(self._resolution_rings_canvas)

        self._ui.hitRatePlotWidget.setTitle('Hit Rate vs. Events')
        self._ui.hitRatePlotWidget.setLabel('bottom', text='Events')
        self._ui.hitRatePlotWidget.setLabel('left', text='Hit Rate')
        self._ui.hitRatePlotWidget.showGrid(True, True)
        self._ui.hitRatePlotWidget.setYRange(0, 1.0)

        self._ui.saturationPlotViewer.setTitle('Fraction of hits with too many saturated peaks')
        self._ui.saturationPlotViewer.setLabel('bottom', text='Events')
        self._ui.saturationPlotViewer.setLabel('left', text='Saturation rate')
        self._ui.saturationPlotViewer.showGrid(True, True)
        self._ui.saturationPlotViewer.setYRange(0, 1.0)
        self._ui.saturationPlotViewer.setXLink(self._ui.hitRatePlotWidget)

        self._ui.accumulatedPeaksCheckBox.setChecked(True)
        self._ui.accumulatedPeaksCheckBox.stateChanged.connect(self._toggle_acc)
        self._ui.resetPeaksButton.clicked.connect(self._reset_peaks)
        self._ui.resetPlotsButton.clicked.connect(self._reset_plots)

        self._ui.accumulatedPeaksCheckBox.stateChanged.connect(self._toggle_acc)

        self._ui.resolutionRingsCheckBox.setChecked(True)
        self._ui.resolutionRingsCheckBox.stateChanged.connect(self._draw_resolution_rings)

        self._ui.resolutionRingsLineEdit.setValidator(self._resolution_rings_validator)
        self._ui.resolutionRingsLineEdit.setText(','.join(str(x) for x in self._resolution_rings_in_A))
        self._ui.resolutionRingsLineEdit.editingFinished.connect(self._update_resolution_rings)

        self._ui.resolutionRingsCheckBox.setEnabled(False)
        self._ui.resolutionRingsLineEdit.setEnabled(False)

    def _mouse_clicked(self, mouse_evt):
        mouse_pos_in_scene = mouse_evt[0].scenePos()
        if self._ui.hitRatePlotWidget.plotItem.sceneBoundingRect().contains(mouse_pos_in_scene):
            if mouse_evt[0].button() == QtCore.Qt.MiddleButton:
                mouse_x_pos_in_data = self._ui.hitRatePlotWidget.plotItem.vb.mapSceneToView(mouse_pos_in_scene).x()
                new_vertical_lines = []
                for vert_line in self._vertical_lines:
                    if abs(vert_line.getPos()[0] - mouse_x_pos_in_data) < 5:
                        self._ui.hitRatePlotWidget.removeItem(vert_line)
                    else:
                        new_vertical_lines.append(vert_line)
                if len(new_vertical_lines) != len(self._vertical_lines):
                    self._vertical_lines = new_vertical_lines
                    return
                vertical_line = pg.InfiniteLine(mouse_x_pos_in_data, angle=90, movable=False)
                self._vertical_lines.append(vertical_line)
                self._ui.hitRatePlotWidget.addItem(vertical_line, ignoreBounds=True)

    def _data_received(self, datdict):
        self._data = copy.deepcopy(datdict)

    def _update_resolution_rings(self):
        items = str(self._ui.resolutionRingsLineEdit.text()).split(',')
        for ti in self._resolution_rings_textitems:
            self._ui.imageView.getView().removeItem(ti)
        if len(items) == 0:
            self._resolution_rings_in_A = []
        self._resolution_rings_in_A = [float(item) for item in items if item != '' and float(item) != 0.0]
        self._resolution_rings_textitems = [pg.TextItem(str(x) + 'A',
                                                        anchor=(0.5, 0.8)) for x in self._resolution_rings_in_A]
        for ti in self._resolution_rings_textitems:
            self._ui.imageView.getView().addItem(ti)
        self._draw_resolution_rings()

    def _reset_plots(self):
        self._hitrate_history = self._hitrate_history_size * [0.0]
        self._satrate_history = self._satrate_history_size * [0.0]
        self._hitrate_plot.setData(self._hitrate_history)
        self._satrate_plot.setData(self._satrate_history)

    def _reset_peaks(self):
        self._sum_img = numpy.zeros(self._img_shape, dtype=numpy.float32)
        self._ui.imageView.setImage(self._sum_img.T, autoHistogramRange=False, autoLevels=False, autoRange=False)

    def _toggle_acc(self):
        if self._ui.accumulatedPeaksCheckBox.isChecked():
            self._ui.imageView.setImage(self._sum_img.T, autoHistogramRange=False, autoLevels=False, autoRange=False)
        else:
            self._ui.imageView.setImage(self._img.T, autoHistogramRange=False, autoLevels=False, autoRange=False)

    def _draw_resolution_rings(self):

        try:

            lambd = scipy.constants.h * scipy.constants.c / (scipy.constants.e * self._local_data['beam_energy'])
            resolution_rings_in_pix = [1.0]

            resolution_rings_in_pix.extend([2.0 * self._res *
                                            (self._local_data['detector_distance'] * 10e-4 + self._coffset) *
                                            numpy.tan(2.0*numpy.arcsin(lambd/(2.0*resolution*10e-11)))
                                            for resolution in self._resolution_rings_in_A])

        except TypeError:

            print('Beam energy or detector distance are not available. Resolution rings cannot be computed.')
            self._resolution_rings_canvas.setData([], [])
            for index, item in enumerate(self._resolution_rings_textitems):
                item.setText('')

        else:

            if self._ui.resolutionRingsCheckBox.isEnabled() and self._ui.resolutionRingsCheckBox.isChecked():

                self._resolution_rings_canvas.setData(
                    [self._image_center.y] * len(resolution_rings_in_pix),
                    [self._image_center.x] * len(resolution_rings_in_pix),
                    symbol='o',
                    size=resolution_rings_in_pix,
                    pen=self._resolution_rings_pen,
                    brush=(0, 0, 0, 0), pxMode=False)
                for index, item in enumerate(self._resolution_rings_textitems):
                    item.setText(str(self._resolution_rings_in_A[index]) + 'A')
                    item.setPos(self._image_center.y, self._image_center.x + resolution_rings_in_pix[index + 1] / 2.0)

            else:
                self._resolution_rings_canvas.setData([], [])
                for index, item in enumerate(self._resolution_rings_textitems):
                    item.setText('')

    def _update_image_plot(self):

        if len(self._data) != 0:
            self._local_data = self._data
            self._data = {}
        else:
            return

        QtGui.QApplication.processEvents()

        if numpy.isnan(self._local_data['hit_rate']):
            self._hitrate_history.append(0)
            hr = 0
        else:
            self._hitrate_history.append(self._local_data['hit_rate'])
            hr = self._local_data['hit_rate']
        self._hitrate_history.pop(0)

        if numpy.isnan(self._local_data['sat_rate']):
            self._hitrate_history.append(0)
        else:
            self._satrate_history.append(self._local_data['sat_rate'])

        self._satrate_history.pop(0)

        self._hitrate_plot.setData(self._hitrate_history)
        self._satrate_plot.setData(self._satrate_history)

        QtGui.QApplication.processEvents()

        if self._local_data['optimized_geometry']:
            if not self._ui.resolutionRingsCheckBox.isEnabled():
                self._ui.resolutionRingsCheckBox.setEnabled(True)
                self._ui.resolutionRingsLineEdit.setEnabled(True)
                self._update_resolution_rings()
            self._draw_resolution_rings()
        else:
            if self._ui.resolutionRingsCheckBox.isEnabled():
                self._ui.resolutionRingsCheckBox.setEnabled(False)
                self._ui.resolutionRingsLineEdit.setEnabled(False)
            self._draw_resolution_rings()

        new_vertical_lines = []
        for vline in self._vertical_lines:
            line_pos = vline.getPos()[0]
            line_pos -= 1
            if line_pos > 0.0:
                vline.setPos(line_pos)
                new_vertical_lines.append(vline)
            else:
                self._ui.hitRatePlotWidget.removeItem(vline)
        self._ui.vertical_lines = new_vertical_lines

        QtGui.QApplication.processEvents()

        timestamp = self._local_data['timestamp']
        if timestamp is not None:
            self._ui.hitRatePlotWidget.setTitle('Hit Rate vs. Events - {0} - {1}%'.format(time.strftime('%H:%M:%S'),
                                                                                          timestamp))
            timenow = time.time()
            self._ui.delayLabel.setText('Estimated delay: {0} seconds'.format(round(timenow - timestamp, 6)))
        else:
            self._ui.hitRatePlotWidget.setTitle('Hit Rate vs. Events {0}%'.format(round(hr * 100, 1)))
            self._ui.delayLabel.setText('Estimated delay: -')

        QtGui.QApplication.processEvents()

        if len(self._local_data['peak_list'][0]) > 0:

            self._img = numpy.zeros(self._img_shape, dtype=numpy.float32)

            for peak_fs, peak_ss, peak_value in zip(self._local_data['peak_list'].fs,
                                                    self._local_data['peak_list'].ss,
                                                    self._local_data['peak_list'].intensity):
                peak_in_slab = int(round(peak_ss))*self._local_data['native_shape'][1]+int(round(peak_fs))
                self._img[self._pixel_maps.y[peak_in_slab], self._pixel_maps.x[peak_in_slab]] += peak_value
                self._sum_img[self._pixel_maps.y[peak_in_slab], self._pixel_maps.x[peak_in_slab]] += peak_value

            self._toggle_acc()
            self._local_data['peak_list'] = ([], [], [])


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
