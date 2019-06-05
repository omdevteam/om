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
GUI for OnDA Crystallography.
"""
from __future__ import absolute_import, division, print_function

import collections
import signal
import sys

import cfelpyutils.crystfel_utils as cfel_crystfel
import cfelpyutils.geometry_utils as cfel_geometry
import click
import numpy
import pyqtgraph
import scipy.constants

import onda.utils.gui as onda_gui

try:
    import PyQt5.QtCore as QtCore
    import PyQt5.QtGui as QtGui
except ImportError:
    import PyQt4.QtCore as QtCore
    import PyQt4.QtGui as QtGui


class CrystallographyGui(onda_gui.OndaGui):
    """
    GUI for OnDA crystallography.

    This GUI receives data sent by the OnDA monitor when they are tagged with the
    'ondadata' tag. It displays the real time hit and saturation rate information,
    plus a virtual powder-pattern-style plot of the processed data.
    """

    def __init__(self, geometry, pub_hostname, pub_port):
        """
        Initializes the Crystallography GUI class.

        Args:

            geometry (Dict): a dictionary containing CrystFEL geometry information (as
                returned by the
                :obj:`cfelpyutils.crystfel_utils.load_crystfel_geometry` function)
                from the :obj:`cfelpyutils` module.

            pub_hostname (str): hostname or IP address of the machine where the OnDA
                monitor is running.

            pub_port (int): port on which the the OnDA monitor is broadcasting
                information.
        """
        super(CrystallographyGui, self).__init__(
            pub_hostname=pub_hostname,
            pub_port=pub_port,
            gui_update_func=self._update_image_and_plots,
            subscription_string="ondadata",
        )

        # Initializes the local data dictionary with 'null' values.
        # self._local_data = {
        #     "peak_list": named_tuples.PeakList(fs=[], ss=[], intensity=[]),
        #     "hit_rate": 0.0,
        #     "hit_flag": True,
        #     "saturation_rate": 0.0,
        # }

        self._local_data = None

        pixel_maps = cfel_geometry.compute_pix_maps(geometry)

        # The following information will be used later to create the arrays that will
        # store the assembled detector images.
        self._img_shape = cfel_geometry.compute_min_array_size(pixel_maps)
        self._img_center_x = int(self._img_shape[1] / 2)
        self._img_center_y = int(self._img_shape[0] / 2)

        visual_pixel_map = cfel_geometry.compute_visualization_pix_maps(geometry)
        self._visual_pixel_map_x = visual_pixel_map.x.flatten()
        self._visual_pixel_map_y = visual_pixel_map.y.flatten()

        # Tries to extract the coffset and res information from the geometry. The
        # geometry allows these two values to be defined individually for each panel,
        # but the GUI just needs simple values for the whole detector. The GUI just
        # takes the values from the first panel.
        first_panel = list(geometry["panels"].keys())[0]
        try:
            self._coffset = geometry["panels"][first_panel]["coffset"]
        except KeyError:
            self._coffset = None

        try:
            self._res = geometry["panels"][first_panel]["res"]
        except KeyError:
            self._res = None

        self._img_virt_powder_plot = numpy.zeros(
            shape=self._img_shape, dtype=numpy.float32
        )

        self._hitrate_history = collections.deque(iterable=10000 * [0.0], maxlen=10000)
        self._satrate_history = collections.deque(iterable=10000 * [0.0], maxlen=10000)

        # Sets the PyQtGraph background color.
        pyqtgraph.setConfigOption("background", 0.2)

        # Initializes all that is needed to draw resolution rings.
        self._resolution_rings_regex = QtCore.QRegExp(r"[0-9.,]+")
        self._resolution_rings_validator = QtGui.QRegExpValidator()
        self._resolution_rings_validator.setRegExp(self._resolution_rings_regex)
        self._resolution_rings_in_a = [10.0, 9.0, 8.0, 7.0, 6.0, 5.0, 4.0, 3.0]

        self._resolution_rings_check_box = QtGui.QCheckBox(
            text="Show Resolution Rings", checked=True
        )
        self._resolution_rings_check_box.stateChanged.connect(
            self._update_resolution_rings_to_display
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

        self._resolution_rings_widget = onda_gui.OndaScatterPlotWidget(
            symbol="o",
            color="w"
        )

        self._last_beam_energy = None
        self._last_detector_distance = None

        # Initializes the image viewer.
        self._image_widget = onda_gui.OndaImageWidget(axes_visible=True)
        self._image_widget.set_scatter_plot_overlays(self._resolution_rings_widget)

        # Initializes the hit rate plot widget.
        self._hit_rate_widget = onda_gui.OndaPlotWidget(
            data=(range(-10000, 0), self._hitrate_history),
            grid_shown=True,
            plot_title="Hit Rate vs. Events",
            x_axis_label="Events",
            y_axis_label="Hit Rate",
            x_axis_range=(-10000, 0),
            y_axis_range=(0, 100),
        )

        # Initializes the saturation rate plot widget.
        self._saturation_widget = onda_gui.OndaPlotWidget(
            data=(range(-10000, 0), self._satrate_history),
            grid_shown=True,
            plot_title="Fraction of hits with too many saturated peaks",
            x_axis_label="Events",
            y_axis_label="Saturation Rate",
            x_axis_range=(-10000, 0),
            y_axis_range=(0, 100),
        )
        self._saturation_widget.link_x_axis(self._hit_rate_widget)

        # Initializes the 'reset peaks' button.
        self._reset_peaks_button = QtGui.QPushButton(text="Reset Peaks")
        self._reset_peaks_button.clicked.connect(self._reset_virt_powder_plot)

        # Initializes the 'reset plots' button.
        self._reset_plots_button = QtGui.QPushButton(text="Reset Plots")
        self._reset_plots_button.clicked.connect(self._reset_plots)

        # Initializes and fills the layouts.
        horizontal_layout = QtGui.QHBoxLayout()
        horizontal_layout.addWidget(self._reset_peaks_button)
        horizontal_layout.addWidget(self._reset_plots_button)
        horizontal_layout.addStretch()
        horizontal_layout.addWidget(self._resolution_rings_check_box)
        horizontal_layout.addWidget(self._resolution_rings_lineedit)
        splitter_0 = QtGui.QSplitter()
        splitter_0.addWidget(self._image_widget.widget)
        splitter_1 = QtGui.QSplitter()
        splitter_1.setOrientation(QtCore.Qt.Vertical)
        splitter_1.addWidget(self._hit_rate_widget.widget)
        splitter_1.addWidget(self._saturation_widget.widget)
        splitter_0.addWidget(splitter_1)
        vertical_layout = QtGui.QVBoxLayout()
        vertical_layout.addWidget(splitter_0)
        vertical_layout.addLayout(horizontal_layout)

        # Initializes the central widget for the main window.
        self._central_widget = QtGui.QWidget()
        self._central_widget.setLayout(vertical_layout)
        self.setCentralWidget(self._central_widget)

        self.show()

    def _reset_plots(self):
        # Resetsthe plots.
        self._hitrate_history = collections.deque(10000 * [0.0], maxlen=10000)
        self._satrate_history = collections.deque(10000 * [0.0], maxlen=10000)
        self._hit_rate_widget.update(data=(range(-10000, 0), self._hitrate_history))
        self._saturation_widget.update(data=(range(-10000, 0), self._satrate_history))

    def _reset_virt_powder_plot(self):
        # Resets the virtual powder plot.
        self._img_virt_powder_plot = numpy.zeros(
            shape=self._img_shape, dtype=numpy.float32
        )
        self._image_widget.update(data=self._img_virt_powder_plot.T)

    def _update_resolution_rings_to_display(self):
        items = str(self._resolution_rings_lineedit.text()).split(",")
        if items:
            self._resolution_rings_in_a = [
                float(item) for item in items if item != "" and float(item) != 0.0
            ]
        else:
            self._resolution_rings_in_a = []
        self._update_resolution_rings()

    def _update_resolution_rings(self):
        # Updates the resolution rings.

        if self._local_data:
            last_frame = self._local_data[-1]
            curr_beam_energy = last_frame[b"beam_energy"]
            curr_detector_distance = last_frame[b"detector_distance"]
            self._last_beam_energy = curr_beam_energy
            self._last_detector_distance = curr_detector_distance
        else:
            if self._last_beam_energy:
                curr_beam_energy = self._last_beam_energy
                curr_detector_distance = self._last_detector_distance
            else:
                return

        try:
            lambda_ = scipy.constants.h * scipy.constants.c / curr_beam_energy
            resolution_rings_in_pix = [1.0]
            resolution_rings_in_pix.extend(
                [
                    2.0
                    * self._res
                    * (curr_detector_distance + self._coffset)
                    * numpy.tan(2.0 * numpy.arcsin(lambda_ / (2.0 * resolution)))
                    for resolution in self._resolution_rings_in_a
                ]
            )
        except TypeError:
            print(
                "Beam energy or detector distance are not available. Resolution"
                "rings cannot be computed."
            )
            self._resolution_rings_widget.update(data=([], []), size=[])
            self._image_widget.set_text()
        else:
            if (
                self._resolution_rings_check_box.isEnabled()
                and self._resolution_rings_check_box.isChecked()
            ):
                num_rings = len(resolution_rings_in_pix)
                self._resolution_rings_widget.update(
                    data=(
                        [self._img_center_y] * num_rings,
                        [self._img_center_x] * num_rings,
                    ),
                    size=resolution_rings_in_pix,
                )

                resolution_rings_text = [
                    "{}A".format(ring) for ring in self._resolution_rings_in_a
                ]

                self._image_widget.set_text(
                    text=resolution_rings_text,
                    text_coordinates=(
                        [self._img_center_y] * num_rings,
                        [
                            self._img_center_x + resolution_rings_in_pix[index] / 2.0
                            for index in range(0, num_rings)
                        ],
                    ),
                )
            else:
                # If the relevant checkbox is not ticked, sets the resolution rings
                # and the text labels to 'null' content.
                self._resolution_rings_widget.update(data=([], []), size=[])
                self._image_widget.set_text()

    def _update_image_and_plots(self):
        # Updates all elements in the GUI.

        if self.data:

            # Checks if data has been received. If new data has been received, moves
            # them to a new attribute and resets the 'data' attribute. In this way,
            # one can check if data has been received simply by checking if the 'data'
            # attribute is not None.
            self._local_data = self.data
            self.data = None
        else:
            return

        last_frame = self._local_data[-1]

        QtGui.QApplication.processEvents()

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

        # Adds data from all frames accumulated in local_data to the plots, but updates
        # the displayed images and plots only once at the end.
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

            self._hitrate_history.append(100.0 * frame[b"hit_rate"])
            self._satrate_history.append(100.0 * frame[b"saturation_rate"])

        QtGui.QApplication.processEvents()

        self._hit_rate_widget.update((range(-10000, 0), self._hitrate_history))
        self._saturation_widget.update((range(-10000, 0), self._satrate_history))
        self._image_widget.update(self._img_virt_powder_plot.T)

        # Resets local_data so that the same data is not processed multiple times.
        self._local_data = []

@click.command()
@click.argument("geometry_file", type=click.Path())
@click.argument("hostname", type=str, required=False)
@click.argument("port", type=int, required=False)
def main(geometry_file, hostname, port):
    """
    OnDA GUI for crystallography. This script starts a GUI and tries to connect to a
    running OnDA monitor. The script accepts the following arguments:

    GEOMETRY_FILE:  the full path to a file containing the geometry information to be
    used for data visualization.

    HOSTNAME: the hostname where the monitor is running. Optional: if not provided,
    it defaults to localhost (127.0.0.1).

    PORT: the port on HOSTNAME where the monitor is running. Optional: if not
    provided, it defaults to 12321.
    """
    if hostname is None:
        hostname = "127.0.0.1"
    if port is None:
        port = 12321

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    geometry = cfel_crystfel.load_crystfel_geometry(geometry_file)

    app = QtGui.QApplication(sys.argv)
    _ = CrystallographyGui(geometry, hostname, port)
    sys.exit(app.exec_())
