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
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import collections
import os
import os.path
import signal
import sys

import numpy
import pyqtgraph as pg
from scipy import constants

from onda.algorithms import crystallography_algorithms as crystalgs
from onda.cfelpyutils import geometry_utils, crystfel_utils
from onda.graphical_interface import gui

try:
    from PyQt5 import QtCore, QtGui, uic
except ImportError:
    from PyQt4 import QtCore, QtGui, uic


class CrystallographyGui(gui.OndaGui):

    def __init__(self,
                 geometry,
                 pub_hostname,
                 pub_port):

        # Initialize the dictionary with the data to be displayed with
        # default values.
        self._local_data = {
            'peak_list': crystalgs.PeakList([], [], []),
            'hit_rate': 0.0,
            'hit_flag': True,
            'saturation_rate': 0.0
        }

        # Load the geometry from the geometry file. Compute the pixel
        # maps and the minimum shape of an array that contains the
        # layout described by the geometry, to be used when creating
        # the image widget. Compute then the indexes of the center of
        # the image in this array.
        pixel_maps = geometry_utils.compute_pixel_maps(geometry)

        self._img_shape = geometry_utils.compute_minimum_array_size(
            pixel_maps
        )

        ImageCenter = collections.namedtuple(  # pylint: disable=C0103
            typename='ImageCenter',
            field_names=['y', 'x']
        )
        self._image_center = ImageCenter(
            self._img_shape[0] / 2,
            self._img_shape[1] / 2
        )

        pg_pixel_maps = geometry_utils.adjust_pixel_maps_for_pyqtgraph(
            pixel_maps
        )
        self._pg_pixel_map_x = pg_pixel_maps.x.flatten()
        self._pg_pixel_map_y = pg_pixel_maps.y.flatten()

        # Try to extract the coffset and res information from the
        # geometry (since the geometry allows these two values to be
        # defined individually for each panel, but we need just two
        # simple values, use the ones from the first panel)
        first_panel = list(geometry['panels'].keys())[0]
        try:
            self._coffset = geometry['panels'][first_panel]['coffset']
        except KeyError:
            self._coffset = None

        try:
            self._res = geometry['panels'][first_panel]['res']
        except KeyError:
            self._res = None

        # Create the two arrays that will hold the virtual powder
        # pattern and the last received peaks.
        self._img_last_peaks = numpy.zeros(
            shape=self._img_shape,
            dtype=numpy.float32  # pylint: disable=E1101
        )
        self._img_vpp = numpy.zeros(
            shape=self._img_shape,
            dtype=numpy.float32  # pylint: disable=E1101
        )

        # Create the attributesthat will store the hit and
        # saturation rate history.
        self._hitrate_history = collections.deque(
            10000 * [0.0],
            maxlen=10000
        )
        self._satrate_history = collections.deque(
            10000 * [0.0],
            maxlen=10000
        )

        # Create the attributes that will hold the resolution rings
        # data and be used for the GUI widgets related to the
        # resolution rings.
        self._resolution_rings_regex = QtCore.QRegExp(r'[0-9.,]+')
        self._resolution_rings_validator = QtGui.QRegExpValidator()
        self._resolution_rings_validator.setRegExp(
            self._resolution_rings_regex
        )
        self._resolution_rings_in_a = [
            10.0,
            9.0,
            8.0,
            7.0,
            6.0,
            5.0,
            4.0,
            3.0
        ]
        self._resolution_rings_textitems = []

        # Create attributes that will be used to draw the GUI
        self._ui = None
        self._vertical_lines = None
        self._hitrate_plot = None
        self._satrate_plot = None
        self._resolution_rings_pen = None
        self._resolution_rings_canvas = None
        super(CrystallographyGui, self).__init__(
            pub_hostname=pub_hostname,
            pub_port=pub_port,
            gui_init_func=self._init_ui,
            gui_update_func=self._update_image_and_plots,
            subscription_string=u'ondadata',
        )
        self.show()

    def _init_ui(self):

        # Set the PyQtGraph background color.
        pg.setConfigOption('background', 0.2)

        # Create an attribute that stores the vertical lines that the
        # users can put on the plot widgets.
        self._vertical_lines = []

        # Load the GUI file and instantiate the GUI.
        ui_mainwindow, _ = uic.loadUiType(
            os.path.join(
                os.environ['ONDA_INSTALLATION_DIR'],
                'onda',
                'graphical_interface',
                'ui_files',
                'OndaCrystallographyGUI.ui'
            )
        )
        self._ui = ui_mainwindow()
        self._ui.setupUi(self)

        # Adjust some UI elements.
        # Add the menu buttons from the image viewer.
        self._ui.imageView.ui.menuBtn.hide()
        self._ui.imageView.ui.roiBtn.hide()

        # Add labels to the hit rate plot widget and initialize it.status
        self._ui.hitRatePlotWidget.setTitle(
            'Hit Rate vs. Events'
        )

        self._ui.hitRatePlotWidget.setLabel(
            axis='bottom',
            text='Events'
        )

        self._ui.hitRatePlotWidget.setLabel(
            axis='left',
            text='Hit Rate'
        )

        self._ui.hitRatePlotWidget.showGrid(
            x=True,
            y=True
        )

        self._ui.hitRatePlotWidget.setYRange(0, 1.0)
        self._hitrate_plot = self._ui.hitRatePlotWidget.plot(
            self._hitrate_history
        )

        # Add labels to the saturation rate plot widget.
        self._ui.saturationPlotViewer.setTitle(
            'Fraction of hits with too many saturated peaks'
        )

        self._ui.saturationPlotViewer.setLabel(
            axis='bottom',
            text='Events'
        )

        self._ui.saturationPlotViewer.setLabel(
            axis='left',
            text='Saturation rate'
        )

        self._ui.saturationPlotViewer.showGrid(
            x=True,
            y=True

        )
        self._ui.saturationPlotViewer.setYRange(0, 1.0)
        self._ui.saturationPlotViewer.setXLink(
            self._ui.hitRatePlotWidget
        )
        self._satrate_plot = self._ui.saturationPlotViewer.plot(
            self._satrate_history
        )

        # Connect signals for the 'accumulated peaks' checkbox.
        self._ui.accumulatedPeaksCheckBox.setChecked(True)
        self._ui.accumulatedPeaksCheckBox.stateChanged.connect(
            self._update_image_view_content
        )

        # Connect signals for the 'peaks' and 'plots' buttons.
        self._ui.resetPeaksButton.clicked.connect(self._reset_vpp)
        self._ui.resetPlotsButton.clicked.connect(self._reset_plots)
        self._ui.accumulatedPeaksCheckBox.stateChanged.connect(
            self._update_image_view_content
        )

        # Connect signals, add validators and set labels for the
        # resolution rings.
        self._resolution_rings_pen = pg.mkPen('w', width=0.5)
        self._resolution_rings_canvas = pg.ScatterPlotItem()
        self._ui.resolutionRingsCheckBox.setChecked(True)
        self._ui.resolutionRingsCheckBox.stateChanged.connect(
            self._update_resolution_rings
        )

        self._ui.resolutionRingsLineEdit.setValidator(
            self._resolution_rings_validator
        )

        self._ui.resolutionRingsLineEdit.setText(
            ','.join(
                str(x)
                for x in self._resolution_rings_in_a
            )
        )

        self._ui.resolutionRingsLineEdit.editingFinished.connect(
            self._update_resolution_rings
        )

        self._ui.resolutionRingsCheckBox.setEnabled(False)
        self._ui.resolutionRingsLineEdit.setEnabled(False)
        # for text_item in self._resolution_rings_textitems:
        #     self._ui.imageView.getView().addItem(text_item)
        # self._ui.imageView.getView().addItem(self._resolution_rings_canvas)

        # Initialize the 'mouse clicked' signal proxy to limit the
        # accumulation of mouse events.
        self._mouse_clicked_signal_proxy = pg.SignalProxy(
            self._ui.hitRatePlotWidget.scene().sigMouseClicked,
            rateLimit=60,
            slot=self._mouse_clicked
        )

    def _mouse_clicked(self,
                       mouse_evt):
        mouse_pos_in_scene = mouse_evt[0].scenePos()

        # Check if the click of the mouse happens in one of the plot
        # widgets
        if (
                self
                ._ui
                .hitRatePlotWidget
                .plotItem.sceneBoundingRect()
                .contains(mouse_pos_in_scene)
        ):
            if mouse_evt[0].button() == QtCore.Qt.MiddleButton:
                # If the mouse click takes place in a plot widgets and
                # the middle button was clicked, check if a vertical
                # line exists already in the vicinity of the click. If
                # it does, remove it. If it does not, add the vertical
                # line to the plot in the place where the user clicked.
                mouse_x_pos_in_data = (
                    self
                    ._ui
                    .hitRatePlotWidget
                    .plotItem
                    .vb
                    .mapSceneToView(mouse_pos_in_scene)
                    .x()
                )
                new_vertical_lines = []
                for vert_line in self._vertical_lines:
                    if abs(vert_line.getPos()[0] - mouse_x_pos_in_data) < 5:
                        self._ui.hitRatePlotWidget.removeItem(vert_line)
                    else:
                        new_vertical_lines.append(vert_line)

                if len(new_vertical_lines) != len(self._vertical_lines):
                    self._vertical_lines = new_vertical_lines
                    return

                vertical_line = pg.InfiniteLine(
                    pos=mouse_x_pos_in_data,
                    angle=90,
                    movable=False
                )
                self._vertical_lines.append(vertical_line)
                self._ui.hitRatePlotWidget.addItem(
                    item=vertical_line,
                    ignoreBounds=True
                )

    def _reset_plots(self):
        # Reset the hit and saturation data history and plot widgets.
        self._hitrate_history = collections.deque(
            10000 * [0.0],
            maxlen=10000
        )
        self._satrate_history = collections.deque(
            10000 * [0.0],
            maxlen=10000
        )
        self._hitrate_plot.setData(self._hitrate_history)
        self._satrate_plot.setData(self._satrate_history)

    def _reset_vpp(self):
        # Reset virtual powder pattern.
        self._img_vpp = numpy.zeros(
            shape=self._img_shape,
            dtype=numpy.float32  # pylint: disable=E1101
        )
        self._ui.imageView.setImage(
            self._img_vpp.T,
            autoHistogramRange=False,
            autoLevels=False,
            autoRange=False
        )

    def _update_image_view_content(self):
        # Change the image view between last received peaks and virtual
        # powder pattern.
        if self._ui.accumulatedPeaksCheckBox.isChecked():
            self._ui.imageView.setImage(
                self._img_vpp.T,
                autoHistogramRange=False,
                autoLevels=False,
                autoRange=False
            )
        else:
            self._ui.imageView.setImage(
                self._img_last_peaks.T,
                autoHistogramRange=False,
                autoLevels=False,
                autoRange=False
            )

    def _update_resolution_rings(self):
        # Get the list of new resolutions for the rings from the
        # relevant widget.
        items = str(
            self
            ._ui
            .resolutionRingsLineEdit
            .text()
        ).split(',')
        if items:
            self._resolution_rings_in_a = [
                float(item)
                for item in items
                if item != '' and float(item) != 0.0
            ]
        else:
            self._resolution_rings_in_a = []

        # Remove the old text items from the resolution rings label
        # list, then add the new ones.
        for text_item in self._resolution_rings_textitems:
            self._ui.imageView.getView().removeItem(text_item)

        self._resolution_rings_textitems = [
            pg.TextItem(text='{}A'.format(x), anchor=(0.5, 0.8))
            for x in self._resolution_rings_in_a
        ]
        for text_item in self._resolution_rings_textitems:
            self._ui.imageView.getView().addItem(text_item)

        # Create list containing the radii of the resolution rings in
        # pixels.
        try:
            lambda_ = (
                constants.h * constants.c /
                (constants.e * self._local_data['beam_energy'])
            )
            resolution_rings_in_pix = [1.0]
            resolution_rings_in_pix.extend(
                [
                    2.0 * self._res * (
                        self._local_data['detector_distance'] * 10e-4 +
                        self._coffset
                    ) * numpy.tan(
                        2.0 * numpy.arcsin(
                            lambda_ / (2.0 * resolution * 10e-11)
                        )
                    )
                    for resolution in self._resolution_rings_in_a
                ]
            )
        except TypeError:
            # If the calculation fails, draw no rings.
            print(
                "Beam energy or detector distance are not available. "
                "Resolution rings cannot be computed."
            )
            self._resolution_rings_canvas.setData([], [])
            for index, item in enumerate(self._resolution_rings_textitems):
                item.setText('')
        else:
            # Otherwise, if the relevant checkbox is ticked, draw the
            # resution rings and their labels.
            if (
                    self._ui.resolutionRingsCheckBox.isEnabled() and
                    self._ui.resolutionRingsCheckBox.isChecked()
            ):
                self._resolution_rings_canvas.setData(
                    [self._image_center.y] * len(resolution_rings_in_pix),
                    [self._image_center.x] * len(resolution_rings_in_pix),
                    symbol='o',
                    size=resolution_rings_in_pix,
                    pen=self._resolution_rings_pen,
                    brush=(0, 0, 0, 0),
                    pxMode=False
                )
                for index, item in enumerate(self._resolution_rings_textitems):
                    item.setText(
                        '{}A'.format(self._resolution_rings_in_a[index])
                    )
                    item.setPos(
                        self._image_center.y,
                        (
                            self._image_center.x +
                            resolution_rings_in_pix[index + 1] / 2.0
                        )
                    )
            else:
                self._resolution_rings_canvas.setData([], [])
                for index, item in enumerate(self._resolution_rings_textitems):
                    item.setText('')

    def _update_image_and_plots(self):
        # If data has been received, move them to a new attribute and
        # reset the 'data' attribute. Do this so that you know when new
        # data has been received simply by checking if the 'data'
        # attribute is not an empty dictionary. If no new data has been
        # received, just return without redrawing the plots.
        if self.data:
            self._local_data = self.data
            self.data = None
        else:
            return

        QtGui.QApplication.processEvents()

        # Update the hit and saturation rate histories and the plots.
        self._hitrate_history.append(self._local_data['hit_rate'])
        self._satrate_history.append(self._local_data['saturation_rate'])
        self._hitrate_plot.setData(self._hitrate_history)
        self._satrate_plot.setData(self._satrate_history)
        QtGui.QApplication.processEvents()

        # If the geometry is optimixed, activate the resolution ring
        # widgets. Otherwise, disable the. Then call the function to
        # update the resolution rings.
        if self._local_data['optimized_geometry']:
            if not self._ui.resolutionRingsCheckBox.isEnabled():
                self._ui.resolutionRingsCheckBox.setEnabled(True)
                self._ui.resolutionRingsLineEdit.setEnabled(True)
            self._update_resolution_rings()
        else:
            if self._ui.resolutionRingsCheckBox.isEnabled():
                self._ui.resolutionRingsCheckBox.setEnabled(False)
                self._ui.resolutionRingsLineEdit.setEnabled(False)
            self._update_resolution_rings()

        # Draw the vertical lines on the plot widgets.
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

        # Update the images with the last received peaks and the
        # virtual powder pattern.
        QtGui.QApplication.processEvents()
        if self._local_data['peak_list'].intensity:
            for peak_fs, peak_ss, peak_value in zip(
                    self._local_data['peak_list'].fs,
                    self._local_data['peak_list'].ss,
                    self._local_data['peak_list'].intensity
            ):
                peak_index_in_slab = (
                    int(round(peak_ss)) *
                    self._local_data['native_data_shape'][1] +
                    int(round(peak_fs))
                )

                self._img_last_peaks = numpy.zeros(
                    shape=self._img_shape,
                    dtype=numpy.float32  # pylint: disable=E1101
                )

                self._img_last_peaks[
                    self._pg_pixel_map_y[peak_index_in_slab],
                    self._pg_pixel_map_x[peak_index_in_slab]
                ] += peak_value

                self._img_vpp[
                    self._pg_pixel_map_y[peak_index_in_slab],
                    self._pg_pixel_map_x[peak_index_in_slab]
                ] += peak_value

            self._update_image_view_content()

            # Reset the list so that the same peaks are not drawn again
            # and again.
            self._local_data['peak_list'] = crystalgs.PeakList([], [], [])


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
        print(
            "Usage: onda-crystallography-gui.py geometry_filename "
            "<listening ip> <listening port>"
        )
        sys.exit()

    geometry = crystfel_utils.load_crystfel_geometry(geom_filename)
    _ = CrystallographyGui(geometry, rec_ip, rec_port)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
