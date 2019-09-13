# This file is part of OnDA.
#
# OnDA is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# OnDA is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with OnDA.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
OnDA GUI for cystallography.

This module contains a graphical interface that displays reduced and aggregated data
for crystallography experiments.
"""
from __future__ import absolute_import, division, print_function

import collections
import sys
from typing import Any, Dict  # pylint: disable=unused-import

import cfelpyutils.crystfel_utils as cfel_crystfel
import cfelpyutils.geometry_utils as cfel_geometry
import click
import numpy
import pyqtgraph
from scipy import constants

from onda.utils import gui

try:
    import PyQt5.QtCore as QtCore
    import PyQt5.QtGui as QtGui
except ImportError:
    import PyQt4.QtCore as QtCore
    import PyQt4.QtGui as QtGui


class CrystallographyGui(gui.OndaGui):
    """
    See documentation of the __init__ function.
    """

    def __init__(self, geometry, hostname, port):
        # type: (Dict[str, Any], str, int) -> None
        """
        OnDA graphical user interface for crystallography.

        This graphical user interface receives reduced and aggregated data from an OnDA
        crystallography monitor, when it is tagged with the 'ondadata' label. It
        displays some plots showing the evolution of the hit and saturation rates over
        time, plus a real-time virtual powder pattern created using the detected Bragg
        peaks.

        Arguments:

            geometry (Dict[str, Any]): a dictionary containing CrystFEL detector
                geometry information (as returned by the 'load_crystfel_geometry`
                function in the 'cfelpyutils' module).

            hostname (str): the hostname or IP address where the GUI will listen for
                data.

            port(int): the port at which the GUI will listen for data.
        """
        super(CrystallographyGui, self).__init__(
            hostname=hostname,
            port=port,
            gui_update_func=self._update_image_and_plots,
            tag="ondadata",
        )
        pixel_maps = cfel_geometry.compute_pix_maps(geometry)
        x_map, y_map = pixel_maps.x, pixel_maps.y
        y_minimum = 2 * int(max(abs(y_map.max()), abs(y_map.min()))) + 2
        x_minimum = 2 * int(max(abs(x_map.max()), abs(x_map.min()))) + 2
        self._img_shape = (y_minimum, x_minimum)
        self._img_center_x = int(self._img_shape[1] / 2)
        self._img_center_y = int(self._img_shape[0] / 2)
        visual_pixel_map = cfel_geometry.compute_visualization_pix_maps(geometry)
        self._visual_pixel_map_x = visual_pixel_map.x.flatten()
        self._visual_pixel_map_y = visual_pixel_map.y.flatten()
        self._img_virt_powder_plot = numpy.zeros(
            shape=self._img_shape, dtype=numpy.float32
        )

        # Tries to extract the coffset and res information from the geometry. The
        # CrystFEL geometry format allows these two values to be defined individually
        # for each detector panel, but this GUI needs just a single value for the whole
        # detector. The values from the first panel are taken.
        first_panel = list(geometry["panels"].keys())[0]
        try:
            self._coffset = geometry["panels"][first_panel]["coffset"]
        except KeyError:
            self._coffset = None

        try:
            self._res = geometry["panels"][first_panel]["res"]
        except KeyError:
            self._res = None

        self._local_data = None
        self._last_beam_energy = None
        self._last_detector_distance = None
        self._hit_rate_history = collections.deque(iterable=10000 * [0.0], maxlen=10000)
        self._saturation_rate_history = collections.deque(
            iterable=10000 * [0.0], maxlen=10000
        )

        pyqtgraph.setConfigOption("background", 0.2)

        self._resolution_rings_pen = pyqtgraph.mkPen("w", width=0.5)
        self._resolution_rings_canvas = pyqtgraph.ScatterPlotItem()

        self._image_view = pyqtgraph.ImageView()
        self._image_view.ui.menuBtn.hide()
        self._image_view.ui.roiBtn.hide()
        self._image_view.getView().addItem(self._resolution_rings_canvas)

        self._resolution_rings_regex = QtCore.QRegExp(r"[0-9.,]+")
        self._resolution_rings_validator = QtGui.QRegExpValidator()
        self._resolution_rings_validator.setRegExp(self._resolution_rings_regex)
        self._resolution_rings_in_a = [10.0, 9.0, 8.0, 7.0, 6.0, 5.0, 4.0, 3.0]
        self._resolution_rings_textitems = []
        self._resolution_rings_check_box = QtGui.QCheckBox(
            text="Show Resolution Rings", checked=True
        )
        self._resolution_rings_check_box.stateChanged.connect(
            self._update_resolution_rings
        )
        self._resolution_rings_check_box.setEnabled(True)
        self._resolution_rings_lineedit = QtGui.QLineEdit()
        self._resolution_rings_lineedit.setValidator(self._resolution_rings_validator)
        self._resolution_rings_lineedit.setText(
            ",".join(str(x) for x in self._resolution_rings_in_a)
        )
        self._resolution_rings_lineedit.editingFinished.connect(
            self._update_resolution_rings
        )
        self._resolution_rings_lineedit.setEnabled(True)

        self._hit_rate_plot_widget = pyqtgraph.PlotWidget()
        self._hit_rate_plot_widget.setTitle("Hit Rate vs. Events")
        self._hit_rate_plot_widget.setLabel(axis="bottom", text="Events")
        self._hit_rate_plot_widget.setLabel(axis="left", text="Hit Rate")
        self._hit_rate_plot_widget.showGrid(x=True, y=True)
        self._hit_rate_plot_widget.setYRange(0, 1.0)
        self._hit_rate_plot = self._hit_rate_plot_widget.plot(self._hit_rate_history)

        self._saturation_plot_widget = pyqtgraph.PlotWidget()
        self._saturation_plot_widget.setTitle(
            "Fraction of hits with too many saturated peaks"
        )
        self._saturation_plot_widget.setLabel(axis="bottom", text="Events")
        self._saturation_plot_widget.setLabel(axis="left", text="Saturation rate")
        self._saturation_plot_widget.showGrid(x=True, y=True)
        self._saturation_plot_widget.setYRange(0, 1.0)
        self._saturation_plot_widget.setXLink(self._hit_rate_plot_widget)
        self._saturation_rate_plot = self._saturation_plot_widget.plot(
            self._saturation_rate_history
        )

        self._reset_peaks_button = QtGui.QPushButton(text="Reset Peaks")
        self._reset_peaks_button.clicked.connect(self._reset_virt_powder_plot)

        self._reset_plots_button = QtGui.QPushButton(text="Reset Plots")
        self._reset_plots_button.clicked.connect(self._reset_plots)

        self._citation_label = QtGui.QLabel(
            "You are using an <b>OnDA</b> real-time monitor. Please cite: "
            "Mariani et al., J Appl Crystallogr. 2016 May 23;49(Pt 3):1073-1080"
        )
        self._citation_label.setSizePolicy(
            QtGui.QSizePolicy(
                QtGui.QSizePolicy.Expanding,
                QtGui.QSizePolicy.Fixed,
            )
        )

        horizontal_layout = QtGui.QHBoxLayout()
        horizontal_layout.addWidget(self._reset_peaks_button)
        horizontal_layout.addWidget(self._reset_plots_button)
        horizontal_layout.addStretch()
        horizontal_layout.addWidget(self._resolution_rings_check_box)
        horizontal_layout.addWidget(self._resolution_rings_lineedit)
        splitter_0 = QtGui.QSplitter()
        splitter_0.addWidget(self._image_view)
        splitter_1 = QtGui.QSplitter()
        splitter_1.setOrientation(QtCore.Qt.Vertical)
        splitter_1.addWidget(self._hit_rate_plot_widget)
        splitter_1.addWidget(self._saturation_plot_widget)
        splitter_0.addWidget(splitter_1)
        vertical_layout = QtGui.QVBoxLayout()
        vertical_layout.addWidget(self._citation_label)
        vertical_layout.addWidget(splitter_0)
        vertical_layout.addLayout(horizontal_layout)
        self._central_widget = QtGui.QWidget()
        self._central_widget.setLayout(vertical_layout)
        self.setCentralWidget(self._central_widget)
        self.show()

    def _reset_plots(self):
        # type () -> None
        # Resets the hit and saturation rate plots.
        self._hit_rate_history = collections.deque(10000 * [0.0], maxlen=10000)
        self._saturation_rate_history = collections.deque(10000 * [0.0], maxlen=10000)
        self._hit_rate_plot.setData(self._hit_rate_history)
        self._saturation_rate_plot.setData(self._saturation_rate_history)

    def _reset_virt_powder_plot(self):
        # type: () -> None
        # Resets the virtual powder plot.
        self._img_virt_powder_plot = numpy.zeros(
            shape=self._img_shape, dtype=numpy.float32
        )
        self._image_view.setImage(
            self._img_virt_powder_plot.T,
            autoHistogramRange=False,
            autoLevels=False,
            autoRange=False,
        )

    def _update_resolution_rings(self):
        # type: () -> None
        # Updates the resolution rings.
        # If there is no data, returns without drawing anything.
        if self._local_data is None:
            return
        items = str(self._resolution_rings_lineedit.text()).split(",")
        if items:
            self._resolution_rings_in_a = [
                float(item) for item in items if item != "" and float(item) != 0.0
            ]
        else:
            self._resolution_rings_in_a = []

        for text_item in self._resolution_rings_textitems:
            self._image_view.getView().removeItem(text_item)
        self._resolution_rings_textitems = [
            pyqtgraph.TextItem(text="{0}A".format(x), anchor=(0.5, 0.8))
            for x in self._resolution_rings_in_a
        ]
        for text_item in self._resolution_rings_textitems:
            self._image_view.getView().addItem(text_item)
        try:
            lambda_ = (
                constants.h
                * constants.c
                / (self._local_data[-1][b"beam_energy"] * constants.e)
            )
            resolution_rings_in_pix = [1.0]
            resolution_rings_in_pix.extend(
                [
                    2.0
                    * self._res
                    * (
                        self._local_data[-1][b"detector_distance"] * 1e-3
                        + self._coffset
                    )
                    * numpy.tan(
                        2.0 * numpy.arcsin(lambda_ / (2.0 * resolution * 1e-10))
                    )
                    for resolution in self._resolution_rings_in_a
                ]
            )
        except TypeError:
            print(
                "Beam energy or detector distance are not available. Resolution "
                "rings cannot be computed."
            )
            self._resolution_rings_canvas.setData([], [])
            for index, item in enumerate(self._resolution_rings_textitems):
                item.setText("")
        else:
            if (
                self._resolution_rings_check_box.isEnabled()
                and self._resolution_rings_check_box.isChecked()
            ):
                self._resolution_rings_canvas.setData(
                    [self._img_center_x] * len(resolution_rings_in_pix),
                    [self._img_center_y] * len(resolution_rings_in_pix),
                    symbol="o",
                    size=resolution_rings_in_pix,
                    pen=self._resolution_rings_pen,
                    brush=(0, 0, 0, 0),
                    pxMode=False,
                )

                for index, item in enumerate(self._resolution_rings_textitems):
                    item.setText("{0}A".format(self._resolution_rings_in_a[index]))
                    item.setPos(
                        (self._img_center_x + resolution_rings_in_pix[index + 1] / 2.0),
                        self._img_center_y,
                    )
            else:
                self._resolution_rings_canvas.setData([], [])
                for index, item in enumerate(self._resolution_rings_textitems):
                    item.setText("")

    def _update_image_and_plots(self):
        # type: () -> None
        # Updates all elements in the GUI.
        if self.received_data is not None:
            # Resets the 'received_data' attribute to None. One can then check if
            # data has been received simply by checking wether the attribute is not
            # None.
            self._local_data = self.received_data
            self.received_data = None
        else:
            # If no data has been received, returns without drawing anything.
            return

        QtGui.QApplication.processEvents()
        last_frame = self._local_data[-1]
        if last_frame[b"geometry_is_optimized"]:
            if not self._resolution_rings_check_box.isEnabled():
                self._resolution_rings_check_box.setEnabled(True)
                self._resolution_rings_lineedit.setEnabled(True)
            self._update_resolution_rings()
        else:
            if self._resolution_rings_check_box.isEnabled():
                self._resolution_rings_check_box.setEnabled(False)
                self._resolution_rings_lineedit.setEnabled(False)
            self._update_resolution_rings()
        QtGui.QApplication.processEvents()
        for frame in self._local_data:
            for peak_fs, peak_ss, peak_value in zip(
                frame[b"peak_list"][b"fs"],
                frame[b"peak_list"][b"ss"],
                frame[b"peak_list"][b"intensity"],
            ):
                peak_index_in_slab = int(round(peak_ss)) * frame[b"native_data_shape"][
                    1
                ] + int(round(peak_fs))
                self._img_virt_powder_plot[
                    self._visual_pixel_map_y[peak_index_in_slab],
                    self._visual_pixel_map_x[peak_index_in_slab],
                ] += peak_value
            self._hit_rate_history.append(frame[b"hit_rate"])
            self._saturation_rate_history.append(frame[b"saturation_rate"])
        QtGui.QApplication.processEvents()
        self._hit_rate_plot.setData(self._hit_rate_history)
        self._saturation_rate_plot.setData(self._saturation_rate_history)
        self._image_view.setImage(
            self._img_virt_powder_plot.T,
            autoHistogramRange=False,
            autoLevels=False,
            autoRange=False,
        )
        # Resets local_data so that the same data is not processed multiple times.
        self._local_data = []


@click.command()
@click.argument("geometry_file", type=click.Path())
@click.argument("hostname", type=str, required=False)
@click.argument("port", type=int, required=False)
def main(geometry_file, hostname, port):
    """
    OnDA graphical user interface for crystallography. This program must connect to a
    running OnDA monitor for crystallography. If the monitor broacasts information on
    Bragg peaks and hit and saturation rates, this GUI will display their evolution
    over time, plus a real-time virtual powder pattern created using the
    detected peaks.

    GEOMETRY_FILE: the relative or absolute path to a file containing the detector
    geometry information (in CrystFEL format) to be used for visualization.

    HOSTNAME: the hostname where the GUI will listen for data. Optional: if not
    provided, it defaults to localhost (127.0.0.1).

    PORT: the port at which the GUI will listen for data. Optional: if not provided, it
    defaults to 12321.
    """
    if hostname is None:
        hostname = "127.0.0.1"
    if port is None:
        port = 12321
    geometry = cfel_crystfel.load_crystfel_geometry(geometry_file)
    app = QtGui.QApplication(sys.argv)
    _ = CrystallographyGui(geometry, hostname, port)
    sys.exit(app.exec_())
