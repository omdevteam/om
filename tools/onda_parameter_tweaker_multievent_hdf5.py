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


import argparse
import h5py
import numpy
import random
import signal
import sys

from configparser import ConfigParser

try:
    from PyQt5 import QtCore, QtGui
except ImportError:
    from PyQt4 import QtCore, QtGui
import pyqtgraph as pg

try:
    from GUI.UI.onda_crystallography_parameter_tweaker_ui_qt5 import Ui_MainWindow
except ImportError:
    from GUI.UI.onda_crystallography_parameter_tweaker_ui_qt4 import Ui_MainWindow
import cfelpyutils.cfel_optarg as coa
import cfelpyutils.cfel_hdf5 as ch5
import cfelpyutils.cfel_geom as cgm
import python_extensions.peakfinder8_extension as pf8


def load_file(filename, hdf5_path, index):
    hdf5_fh = h5py.File(filename, 'r')
    data = hdf5_fh[hdf5_path][index, :, :]
    hdf5_fh.close()
    return data, filename


def check_changed_parameter(param, param_conv_vers, lineedit_element):
    try:
        new_param = param_conv_vers(lineedit_element.text())
        if new_param != param:
            return new_param, True
        else:
            return param, False
    except ValueError:
        lineedit_element.setText(str(param))
        return param, False


class MainFrame(QtGui.QMainWindow):
    """
    The main frame of the application
    """

    def draw_things(self):
        img, title = load_file(self.filename, self.data_path, self.file_index)
        img = img.astype(numpy.float64)

        if self.apply_darkcal is True:
            img -= self.darkcal

        self.img_to_draw[self.pixel_maps[0], self.pixel_maps[1]] = img.ravel()
        self.ui.imageView.setImage(self.img_to_draw.T, autoLevels=False, autoRange=False, autoHistogramRange=False)
        self.mask_image_view.setImage(numpy.transpose(self.mask_to_draw, axes=(1, 0, 2)), autoLevels=False,
                                      autoRange=False, opacity=0.1)

        peak_list = pf8.peakfinder_8(
            self.max_num_peaks,
            img.astype(numpy.float32),
            self.mask.astype(numpy.int8),
            self.pixelmap_radius,
            self.asic_nx,
            self.asic_ny,
            self.nasics_x,
            self.nasics_y,
            self.adc_thresh,
            self.minimum_snr,
            self.min_pixel_count,
            self.max_pixel_count,
            self.local_bg_radius)

        if self.ui.showHidePeaksCheckBox.isChecked():

            peak_x = []
            peak_y = []
            for peak_fs, peak_ss in zip(peak_list[0], peak_list[1]):
                peak_in_slab = int(round(peak_ss)) * self.slab_shape[1] + int(round(peak_fs))
                try:
                    peak_x.append(self.pixel_maps[0][peak_in_slab])
                    peak_y.append(self.pixel_maps[1][peak_in_slab])
                except IndexError:
                    pass
            self.peak_canvas.setData(peak_y, peak_x, symbol='o', size=15, pen=self.ring_pen, brush=(0, 0, 0, 0),
                                     pxMode=False)

            hit = self.min_num_peaks_for_hit < len(peak_list[2]) < self.max_num_peaks_for_hit

            if hit:
                self.ui.hitLabel.setText('Hit [{0}-{1} peaks]: <b>Yes</b> ({2} peaks)'.format(
                    self.min_num_peaks_for_hit, self.max_num_peaks_for_hit, len(peak_list[2])))
            else:
                self.ui.hitLabel.setText('Hit [{0}-{1} peaks]: No ({2} peaks)'.format(
                    self.min_num_peaks_for_hit, self.max_num_peaks_for_hit, len(peak_list[2])))

        else:

            self.ui.hitLabel.setText('Hit [{0}-{1} peaks]: - (- peaks)'.format(self.min_num_peaks_for_hit,
                                                                               self.max_num_peaks_for_hit))
            self.peak_canvas.setData([])

        if self.ui.resolutionRingsCheckBox.isChecked():
            self.circle_canvas.setData([self.img_shape[1] / 2, self.img_shape[1] / 2],
                                       [self.img_shape[0] / 2, self.img_shape[0] / 2],
                                       symbol='o', size=[2 * self.min_res, 2 * self.max_res],
                                       pen=self.circle_pen, brush=(0, 0, 0, 0), pxMode=False)

        else:

            self.circle_canvas.setData([])

        self.setWindowTitle('%g - %s' % (self.file_index, title))

    def update_peaks(self):

        something_changed = False
        self.adc_thresh, changed = check_changed_parameter(self.adc_thresh, float, self.adc_threshold_lineedit)
        if changed:
            something_changed = True
        self.minimum_snr, changed = check_changed_parameter(self.minimum_snr, float, self.min_snr_lineedit)
        if changed:
            something_changed = True
        self.min_pixel_count, changed = check_changed_parameter(self.min_pixel_count, int,
                                                                self.min_pixel_count_lineedit)
        if changed:
            something_changed = True
        self.max_pixel_count, changed = check_changed_parameter(self.max_pixel_count, int,
                                                                self.max_pixel_count_lineedit)
        if changed:
            something_changed = True
        self.local_bg_radius, changed = check_changed_parameter(self.local_bg_radius, int,
                                                                self.local_bg_radius_lineedit)
        if changed:
            something_changed = True
        self.min_res, changed = check_changed_parameter(self.min_res, int, self.min_res_lineedit)
        if changed:
            something_changed = True
        self.max_res, changed = check_changed_parameter(self.max_res, int, self.max_res_lineedit)
        if changed:
            something_changed = True

        self.res_mask = numpy.ones(self.slab_shape, dtype=numpy.int8)
        self.res_mask[numpy.where(self.pixelmap_radius < self.min_res)] = 0
        self.res_mask[numpy.where(self.pixelmap_radius > self.max_res)] = 0
        self.mask = self.loaded_mask * self.res_mask

        if something_changed:
            self.draw_things()

    def previous_event(self):

        if self.file_index == 0:
            self.file_index = self.num_events - 1
        else:
            self.file_index -= 1
        self.draw_things()

    def next_event(self):

        if self.file_index == self.num_events - 1:
            self.file_index = 0
        else:
            self.file_index += 1
        self.draw_things()

    def random_event(self):
        self.file_index = random.randrange(0, self.num_events)
        self.draw_things()

    def mouse_clicked(self, event):
        pos = event[0].scenePos()
        if self.ui.imageView.getView().sceneBoundingRect().contains(pos):
            mouse_point = self.ui.imageView.getView().mapSceneToView(pos)
            x_mouse = int(mouse_point.x())
            y_mouse = int(mouse_point.y())
            if 0 < x_mouse < self.img_to_draw.shape[1] and 0 < y_mouse < self.img_to_draw.shape[0]:
                self.ui.lastClickedPositionLabel.setText('Last clicked position: (%g,%g)' % (x_mouse, y_mouse))
                self.ui.lastClickedPixelValueLabel.setText('Pixel Value: %5.1f' % (self.img_to_draw[y_mouse,
                                                                                                    x_mouse]))

    def __init__(self, input_file, data_path, apply_darkcal, monitor_params, ):

        QtCore.QObject.__init__(self)

        self.filename = input_file
        self.data_path = data_path
        self.apply_darkcal = apply_darkcal
        fh = h5py.File(self.filename, 'r')
        self.num_events = fh[self.data_path].shape[0]
        fh.close()

        self.file_index = 0

        self.monitor_params = monitor_params

        gen_params = monitor_params['General']
        p8pd_params = monitor_params['Peakfinder8PeakDetection']
        dkc_params = monitor_params['DarkCalCorrection']

        self.ring_pen = pg.mkPen('r', width=2)
        self.circle_pen = pg.mkPen('b', width=2)

        pix_maps = cgm.pixel_maps_from_geometry_file(gen_params['geometry_file'])
        self.pixelmap_radius = pix_maps[2]

        if apply_darkcal is True:
            self.darkcal = ch5.load_nparray_from_hdf5_file(dkc_params['filename'], dkc_params['hdf5_group'])

        self.pixel_maps, self.slab_shape, self.img_shape = cgm.pixel_maps_for_image_view(gen_params['geometry_file'])
        self.img_to_draw = numpy.zeros(self.img_shape, dtype=numpy.float32)
        self.mask_to_draw = numpy.zeros(self.img_shape + (3,), dtype=numpy.int16)
        self.max_num_peaks = int(p8pd_params['max_num_peaks'])
        self.asic_nx = int(p8pd_params['asics_nx'])
        self.asic_ny = int(p8pd_params['asics_ny'])
        self.nasics_x = int(p8pd_params['nasics_x'])
        self.nasics_y = int(p8pd_params['nasics_y'])
        self.adc_thresh = float(p8pd_params['adc_threshold'])
        self.minimum_snr = float(p8pd_params['minimum_snr'])
        self.min_pixel_count = int(p8pd_params['min_pixel_count'])
        self.max_pixel_count = int(p8pd_params['max_pixel_count'])
        self.local_bg_radius = int(p8pd_params['local_bg_radius'])
        self.mask_filename = p8pd_params['mask_filename']
        self.mask_hdf5_path = p8pd_params['mask_hdf5_path']
        self.min_res = int(p8pd_params['min_res'])
        self.max_res = int(p8pd_params['max_res'])
        self.loaded_mask = ch5.load_nparray_from_hdf5_file(self.mask_filename, self.mask_hdf5_path)
        self.min_num_peaks_for_hit = int(monitor_params['General']['min_num_peaks_for_hit'])
        self.max_num_peaks_for_hit = int(monitor_params['General']['max_num_peaks_for_hit'])

        self.res_mask = numpy.ones(self.slab_shape, dtype=numpy.int8)
        self.res_mask[numpy.where(self.pixelmap_radius < self.min_res)] = 0
        self.res_mask[numpy.where(self.pixelmap_radius > self.max_res)] = 0
        self.mask = self.loaded_mask * self.res_mask

        mask = self.loaded_mask.copy().astype(numpy.float)
        mask = mask * 255. / mask.max()
        mask = 255. - mask
        self.mask_to_draw[self.pixel_maps[0], self.pixel_maps[1], 1] = mask.ravel()

        self.mask_image_view = pg.ImageItem()
        self.peak_canvas = pg.ScatterPlotItem()
        self.circle_canvas = pg.ScatterPlotItem()

        self.adc_threshold_label = QtGui.QLabel(self)
        self.adc_threshold_label.setText('adc_threshold')
        self.adc_threshold_lineedit = QtGui.QLineEdit(self)
        self.adc_threshold_lineedit.setText(str(p8pd_params['adc_threshold']))
        self.adc_threshold_lineedit.editingFinished.connect(self.update_peaks)
        self.hlayout0 = QtGui.QHBoxLayout()
        self.hlayout0.addWidget(self.adc_threshold_label)
        self.hlayout0.addWidget(self.adc_threshold_lineedit)

        self.min_snr_label = QtGui.QLabel(self)
        self.min_snr_label.setText('minmum_snr')
        self.min_snr_lineedit = QtGui.QLineEdit(self)
        self.min_snr_lineedit.setText(str(p8pd_params['minimum_snr']))
        self.min_snr_lineedit.editingFinished.connect(self.update_peaks)
        self.hlayout1 = QtGui.QHBoxLayout()
        self.hlayout1.addWidget(self.min_snr_label)
        self.hlayout1.addWidget(self.min_snr_lineedit)

        self.min_pixel_count_label = QtGui.QLabel(self)
        self.min_pixel_count_label.setText('min_pixel_count')
        self.min_pixel_count_lineedit = QtGui.QLineEdit(self)
        self.min_pixel_count_lineedit.setText(str(p8pd_params['min_pixel_count']))
        self.min_pixel_count_lineedit.editingFinished.connect(self.update_peaks)
        self.hlayout2 = QtGui.QHBoxLayout()
        self.hlayout2.addWidget(self.min_pixel_count_label)
        self.hlayout2.addWidget(self.min_pixel_count_lineedit)

        self.max_pixel_count_label = QtGui.QLabel(self)
        self.max_pixel_count_label.setText('max_pixel_count')
        self.max_pixel_count_lineedit = QtGui.QLineEdit(self)
        self.max_pixel_count_lineedit.setText(str(p8pd_params['max_pixel_count']))
        self.max_pixel_count_lineedit.editingFinished.connect(self.update_peaks)
        self.hlayout3 = QtGui.QHBoxLayout()
        self.hlayout3.addWidget(self.max_pixel_count_label)
        self.hlayout3.addWidget(self.max_pixel_count_lineedit)

        self.local_bg_radius_label = QtGui.QLabel(self)
        self.local_bg_radius_label.setText('local_bg_raidus')
        self.local_bg_radius_lineedit = QtGui.QLineEdit(self)
        self.local_bg_radius_lineedit.setText(str(p8pd_params['local_bg_radius']))
        self.local_bg_radius_lineedit.editingFinished.connect(self.update_peaks)
        self.hlayout4 = QtGui.QHBoxLayout()
        self.hlayout4.addWidget(self.local_bg_radius_label)
        self.hlayout4.addWidget(self.local_bg_radius_lineedit)

        self.min_res_label = QtGui.QLabel(self)
        self.min_res_label.setText('min_res')
        self.min_res_lineedit = QtGui.QLineEdit(self)
        self.min_res_lineedit.setText(str(self.min_res))
        self.min_res_lineedit.editingFinished.connect(self.update_peaks)
        self.hlayout5 = QtGui.QHBoxLayout()
        self.hlayout5.addWidget(self.min_res_label)
        self.hlayout5.addWidget(self.min_res_lineedit)

        self.max_res_label = QtGui.QLabel(self)
        self.max_res_label.setText('max_res')
        self.max_res_lineedit = QtGui.QLineEdit(self)
        self.max_res_lineedit.setText(str(self.max_res))
        self.max_res_lineedit.editingFinished.connect(self.update_peaks)
        self.hlayout6 = QtGui.QHBoxLayout()
        self.hlayout6.addWidget(self.max_res_label)
        self.hlayout6.addWidget(self.max_res_lineedit)

        self.param_label = QtGui.QLabel(self)
        self.param_label.setText('<b>Peakfinder Parameters:</b>')

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.init_ui()

        self.proxy = pg.SignalProxy(self.ui.imageView.getView().scene().sigMouseClicked,
                                    slot=self.mouse_clicked)

        self.update_peaks()
        self.draw_things()
        self.show()

    def init_ui(self):

        self.ui.imageView.ui.menuBtn.hide()
        self.ui.imageView.ui.roiBtn.hide()

        self.ui.imageView.getView().addItem(self.mask_image_view)
        self.ui.imageView.getView().addItem(self.peak_canvas)
        self.ui.imageView.getView().addItem(self.circle_canvas)
        self.ui.forwardButton.clicked.connect(self.next_event)
        self.ui.backButton.clicked.connect(self.previous_event)
        self.ui.randomButton.clicked.connect(self.random_event)

        self.ui.verticalLayout1.insertLayout(0, self.hlayout6)
        self.ui.verticalLayout1.insertLayout(0, self.hlayout5)
        self.ui.verticalLayout1.insertLayout(0, self.hlayout4)
        self.ui.verticalLayout1.insertLayout(0, self.hlayout3)
        self.ui.verticalLayout1.insertLayout(0, self.hlayout2)
        self.ui.verticalLayout1.insertLayout(0, self.hlayout1)
        self.ui.verticalLayout1.insertLayout(0, self.hlayout0)
        self.ui.verticalLayout1.insertWidget(0, self.param_label)
        self.ui.splitter.setStretchFactor(0, 1)
        self.ui.splitter.setStretchFactor(1, 0)

        self.ui.showHidePeaksCheckBox.stateChanged.connect(self.draw_things)
        self.ui.resolutionRingsCheckBox.stateChanged.connect(self.draw_things)


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    config = ConfigParser()

    parser = argparse.ArgumentParser(prog='mpirun [MPI OPTIONS] onda.py', description='OnDA - Online Data Analysis')
    parser.add_argument('hdf5_file_name', type=str, help='multievent hdf5 file name')
    parser.add_argument('hdf5_data_path', type=str, help='internal path to data (in the hdf5 file structure)')
    parser.add_argument('-d', '--darkcal', action='store_true', default=False,
                        help='subtract darkcal (file name taken from monitor.ini file)')
    args = parser.parse_args()

    input_file = args.hdf5_file_name
    data_path = args.hdf5_data_path
    apply_darkcal = args.darkcal

    config.read('monitor.ini')
    monitor_params = coa.parse_parameters(config)

    app = QtGui.QApplication(sys.argv)
    _ = MainFrame(input_file, data_path, apply_darkcal, monitor_params)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
