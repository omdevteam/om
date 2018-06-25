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
GUI for OnDA Crystallography.

This module contains the implementation of a GUI for OnDA
Crystallography.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import collections
import signal
import sys

import numpy
import pyqtgraph
from scipy import constants

from onda.cfelpyutils import crystfel_utils, geometry_utils
from onda.graphical_interface import gui
from onda.utils import named_tuples

try:
    from PyQt5 import QtCore, QtGui
except ImportError:
    from PyQt4 import QtCore, QtGui


class CrystallographyGui(gui.OndaGui):
    """
    GUI for OnDA crystallography.

    A GUI for OnDa Crystallography. Receive data sent by the OnDA
    monitor when they are tagged with the 'ondadata' tag. Display the
    real time hit and saturation rate information, plus a virtual
    powder pattern-style plot of the processed data.
    """

    def __init__(self,
                 geometry,
                 pub_hostname,
                 pub_port):
        """
        Initialize the CrystallographyGui class.

        Args:

            geometry (Dict): a dictionary containing CrystFEL geometry
                information (as returned by the
                `:obj:onda.cfelpyutils.crystfel_utils.load_crystfel_geometry`
                function.

            pub_hostname (str): hostname or IP address of the machine
                where the OnDA monitor is running.

            pub_port (int): port on which the the OnDA monitor is
                broadcasting information.
        """
        super(CrystallographyGui, self).__init__(
            pub_hostname=pub_hostname,
            pub_port=pub_port,
            gui_update_func=self._update_image_and_plots,
            subscription_string=u'ondadata',
        )

        # Initialize the local data dictionary with 'null' values.
        self._local_data = {
            'peak_list': named_tuples.PeakList([], [], []),
            'hit_rate': 0.0,
            'hit_flag': True,
            'saturation_rate': 0.0
        }

        pixel_maps = geometry_utils.compute_pix_maps(geometry)

        # The following information will be used later to create the
        # arrays that will store the assembled detector images.
        self._img_shape = geometry_utils.compute_min_array_size(
            pixel_maps
        )

        visual_pixel_map = geometry_utils.compute_visualization_pix_maps(
            pixel_maps
        )
        self._visual_pixel_map_x = visual_pixel_map.x.flatten()
        self._visual_pixel_map_y = visual_pixel_map.y.flatten()

        # Try to extract the coffset and res information from the
        # geometry. The geometry allows these two values to be defined
        # individually for each panel, but the GUI just needs simple
        # values for the whole detector. Just take the values from the
        # first panel.
        first_panel = list(geometry['panels'].keys())[0]
        try:
            self._coffset = geometry['panels'][first_panel]['coffset']
        except KeyError:
            self._coffset = None

        try:
            self._res = geometry['panels'][first_panel]['res']
        except KeyError:
            self._res = None

        self._img_last_peaks = numpy.zeros(
            shape=self._img_shape,
            dtype=numpy.float32  # pylint: disable=E1101
        )

        self._img_virt_powder_plot = numpy.zeros(
            shape=self._img_shape,
            dtype=numpy.float32  # pylint: disable=E1101
        )

        self._hitrate_history = collections.deque(
            iterable=10000 * [0.0],
            maxlen=10000
        )

        self._satrate_history = collections.deque(
            iterable=10000 * [0.0],
            maxlen=10000
        )

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

        self._vertical_lines = []

        # Initialize pen and canvas used to draw the resolution rings.
        self._resolution_rings_pen = pyqtgraph.mkPen('w', width=0.5)
        self._resolution_rings_canvas = pyqtgraph.ScatterPlotItem()

        # Set the PyQtGraph background color.
        pyqtgraph.setConfigOption('background', 0.2)

        # Initalize the resolution rings checkbox.
        self._resolution_rings_check_box = QtGui.QCheckBox()
        self._resolution_rings_check_box.setText("Resolution Rings")
        self._resolution_rings_check_box.setChecked(True)
        self._resolution_rings_check_box.stateChanged.connect(
            self._update_resolution_rings
        )
        self._resolution_rings_check_box.setEnabled(True)

        # Intialize the resolution rings lineedit widget.
        self._resolution_rings_lineedit = QtGui.QLineEdit()
        self._resolution_rings_lineedit.setValidator(
            self._resolution_rings_validator
        )

        self._resolution_rings_lineedit.setText(
            ','.join(
                str(x)
                for x in self._resolution_rings_in_a
            )
        )

        self._resolution_rings_lineedit.editingFinished.connect(
            self._update_resolution_rings
        )

        self._resolution_rings_lineedit.setEnabled(True)

        # Initialize the image viewer.
        self._image_view = pyqtgraph.ImageView()
        self._image_view.ui.menuBtn.hide()
        self._image_wiew.ui.roiBtn.hide()

        # Initialize the hit rate plot widget.
        self._hit_rate_plot_widget = pyqtgraph.PlotWidget()
        self._hit_rate_plot_widget.setTitle(
            'Hit Rate vs. Events'
        )

        self._hit_rate_plot_widget.setLabel(
            axis='bottom',
            text='Events'
        )

        self._hit_rate_plot_widget.setLabel(
            axis='left',
            text='Hit Rate'
        )

        self._hit_rate_plot_widget.showGrid(
            x=True,
            y=True
        )

        self._hit_rate_plot_widget.setYRange(0, 1.0)
        self._hitrate_plot = self._hit_rate_plot_widget.plot(
            self._hitrate_history
        )

        # Initialize the saturation rate plot widget.
        self._saturation_plot_widget = pyqtgraph.PlotWidget()
        self._saturation_plot_widget.setTitle(
            'Fraction of hits with too many saturated peaks'
        )

        self._saturation_plot_widget.setLabel(
            axis='bottom',
            text='Events'
        )

        self._saturation_plot_widget.setLabel(
            axis='left',
            text='Saturation rate'
        )

        self._saturation_plot_widget.showGrid(
            x=True,
            y=True

        )
        self._saturation_plot_widget.setYRange(0, 1.0)
        self._saturation_plot_widget.setXLink(
            self._hit_rate_plot_widget
        )
        self._satrate_plot = self._saturation_plot_widget.plot(
            self._satrate_history
        )

        # Initialize the 'accumulated peaks' checkbox.
        self._accumulated_peaks_check_box = QtGui.QCheckBox()
        self._accumulated_peaks_check_box.setText("Show Accumulated Peaks")
        self._accumulated_peaks_check_box.setChecked(True)
        self._accumulated_peaks_check_box.stateChanged.connect(
            self._update_virt_powder_plot
        )

        # Initialize 'reset peaks' button.
        self._reset_peaks_button = QtGui.QPushButton()
        self._reset_peaks_button.setText("Reset Plots")
        self._reset_peaks_button.clicked.connect(self._reset_virt_powder_plot)

        # Initialize 'reset plots' button.
        self._reset_plots_button = QtGui.QPushButton()
        self._reset_plots_button.clicked.connect(self._reset_plots)

        # Initialize the 'mouse clicked' signal proxy to limit the
        # accumulation of mouse events.
        self._mouse_clicked_signal_proxy = pyqtgraph.SignalProxy(
            self._ui.hitRatePlotWidget.scene().sigMouseClicked,
            rateLimit=60,
            slot=self._mouse_clicked
        )

        # Initialize and fill the layouts.
        horizontal_layout = QtGui.QHBoxLayout()
        horizontal_layout.addWidget(self._accumulated_peaks_check_box)
        horizontal_layout.addSpacerItem()
        horizontal_layout.addWidget(self._reset_peaks_button)
        horizontal_layout.addWidget(self._reset_plots_button)
        horizontal_layout.addWidget(self._resolution_rings_check_box)
        horizontal_layout.addWidget(self._resolution_rings_lineedit)
        splitter_0 = QtGui.QSplitter()
        splitter_0.addWidget(self._image_view)
        splitter_1 = QtGui.QSplitter()
        splitter_1.addWidget(self._hit_rate_plot_widget)
        splitter_1.addWidget(self._saturation_plot_widget)
        splitter_0.addWidget(splitter_1)
        vertical_layout = QtGui.QVBoxLayout()
        vertical_layout.addWidget(splitter_0)
        vertical_layout.addWidget(horizontal_layout)

        # Initialize the central widget for the main window.
        self._central_widget = QtGui.QWidget()
        self._central_widget.setLayout(self._vertical_layout)
        self.setCentralWidget(self._central_widget)

        self.show()

    def _mouse_clicked(self,
                       mouse_evt):
        # Manage mouse events.

        # Check if the click of the mouse happens in the hit rate plot
        # widget.
        mouse_pos_in_scene = mouse_evt[0].scenePos()
        if (
                self
                ._ui
                .hitRatePlotWidget
                .plotItem.sceneBoundingRect()
                .contains(mouse_pos_in_scene)
        ):
            if mouse_evt[0].button() == QtCore.Qt.MiddleButton:

                mouse_x_pos_in_data = (
                    self
                    ._ui
                    .hitRatePlotWidget
                    .plotItem
                    .vb
                    .mapSceneToView(mouse_pos_in_scene)
                    .x()
                )

                # Create the a list that will store the updated
                # vertical lines.
                new_vertical_lines = []

                for vert_line in self._vertical_lines:
                    if abs(vert_line.getPos()[0] - mouse_x_pos_in_data) < 5:

                        # Check if the current vertical line lies in
                        # the vicinity of the click location. If it
                        # does, remove it from the widget (and do not
                        # add it to the updated line list).
                        self._hit_rate_plot_widget.removeItem(vert_line)
                    else:

                        # Othewise just add the line to the updated
                        # line list.
                        new_vertical_lines.append(vert_line)

                # If the number of vertical lines changed, the user
                # removed a line. We already followed on the request,
                # so return.
                if len(new_vertical_lines) != len(self._vertical_lines):
                    self._vertical_lines = new_vertical_lines
                    return

                # If no line was removed, however, the user must be
                # trying to add one. Instantiate the new line.
                vertical_line = pyqtgraph.InfiniteLine(
                    pos=mouse_x_pos_in_data,
                    angle=90,
                    movable=False
                )

                self._vertical_lines.append(vertical_line)
                self._hit_rate_plot_widget.addItem(  # pylint: disable=E1123
                    item=vertical_line,
                    ignoreBounds=True
                )

    def _reset_plots(self):
        # Reset the plots.
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

    def _reset_virt_powder_plot(self):
        # Reset the virtual powder plot.

        # Reset virtual powder pattern.

        # Reset the attribute storing the virtual powder pattern, then
        # update the widget.
        self._img_virt_powder_plot = numpy.zeros(
            shape=self._img_shape,
            dtype=numpy.float32  # pylint: disable=E1101
        )

        self._image_view.setImage(
            self._img_virt_powder_plot.T,
            autoHistogramRange=False,
            autoLevels=False,
            autoRange=False
        )

    def _update_virt_powder_plot(self):
        # Update the virtual powder plot.

        # Change the image displayed between the last received peaks
        # and the virtual powder pattern depending on the user's
        # choice.
        if self._accumulated_peaks_check_box.isChecked():

            self._image_view.setImage(
                self._img_virt_powder_plot.T,
                autoHistogramRange=False,
                autoLevels=False,
                autoRange=False
            )
        else:
            self._image_view.setImage(
                self._img_last_peaks.T,
                autoHistogramRange=False,
                autoLevels=False,
                autoRange=False
            )

    def _update_resolution_rings(self):
        # Update the resolution rings.

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

        for text_item in self._resolution_rings_textitems:
            self._image_view.getView().removeItem(text_item)

        self._resolution_rings_textitems = [
            pyqtgraph.TextItem(text='{}A'.format(x), anchor=(0.5, 0.8))
            for x in self._resolution_rings_in_a
        ]
        for text_item in self._resolution_rings_textitems:
            self._image_view.getView().addItem(text_item)

        try:
            lambda_ = (
                constants.h * constants.c /
                self._local_data['beam_energy']
            )
            resolution_rings_in_pix = [1.0]
            resolution_rings_in_pix.extend(
                [
                    2.0 * self._res * (
                        self._local_data['detector_distance'] +
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
            print(
                "Beam energy or detector distance are not available. "
                "Resolution rings cannot be computed."
            )
            self._resolution_rings_canvas.setData([], [])
            for index, item in enumerate(self._resolution_rings_textitems):
                item.setText('')
        else:
            if (
                    self._resolution_rings_check_box.isEnabled() and
                    self._resolution_rings_check_box.isChecked()
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

                # If the relevant checkbox is not ticked, set the
                # resolution rings and the text labels to 'null'
                # content.
                self._resolution_rings_canvas.setData([], [])
                for index, item in enumerate(self._resolution_rings_textitems):
                    item.setText('')

    def _update_image_and_plots(self):
        # Update all elements in the GUI.

        if self.data:

            # Check if data has been received. If new data has been
            # received, move them to a new attribute and reset the
            # 'data' attribute. In this way, one can check if data has
            # been received simply by checking if the 'data' attribute
            # is not None.
            self._local_data = self.data
            self.data = None
        else:
            return

        QtGui.QApplication.processEvents()

        self._hitrate_history.append(self._local_data['hit_rate'])
        self._satrate_history.append(self._local_data['saturation_rate'])
        self._hitrate_plot.setData(self._hitrate_history)
        self._satrate_plot.setData(self._satrate_history)

        QtGui.QApplication.processEvents()

        if self._local_data['optimized_geometry']:
            if not self._resolution_rings_check_box.isEnabled():
                self._resolution_rings_check_box.setEnabled(True)
                self._resolution_rings_check_box.setEnabled(True)
            self._update_resolution_rings()

        else:
            if self._ui.resolutionRingsCheckBox.isEnabled():
                self._resolution_rings_line_edit.setEnabled(False)
                self._resolution_rings_line_edit.setEnabled(False)
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
                self._hit_rate_plot_widget.removeItem(vline)

        self._vertical_lines = new_vertical_lines

        QtGui.QApplication.processEvents()

        self._img_last_peaks = numpy.zeros(
            shape=self._img_shape,
            dtype=numpy.float32  # pylint: disable=E1101
        )

        # Check if some peak was received by checking if the intensity
        # list is not empty.
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

                self._img_last_peaks[
                    self._visual_pixel_map_y[peak_index_in_slab],
                    self._visual_pixel_map_x[peak_index_in_slab]
                ] += peak_value

                self._img_virt_powder_plot[
                    self._visual_pixel_map_y[peak_index_in_slab],
                    self._visual_pixel_map_x[peak_index_in_slab]
                ] += peak_value

            self._update_virt_powder_plot()

            # Reset the peak list so that the same peaks are not drawn
            # again and again.
            self._local_data['peak_list'] = named_tuples.PeakList([], [], [])


def main():
    """
    Start the GUI for OnDA Crystallography,

    Initialize and start the GUI for OnDA Crystallography. Manage
    command line arguments and instantiate the graphical interface.
    """
    signal.signal(signal.SIGINT, signal.SIG_DFL)

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

    app = QtGui.QApplication(sys.argv)
    _ = CrystallographyGui(geometry, rec_ip, rec_port)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
