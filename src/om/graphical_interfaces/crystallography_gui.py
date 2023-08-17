# This file is part of OM.
#
# OM is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# OM is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with OM.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2020 -2023 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
OM's GUI for Crystallography.

This module contains a graphical interface that displays reduced and aggregated data in
Serial Crystallography experiments.
"""
import signal
import sys
import time
from typing import Any, Dict, List, Tuple, Union

import click
import numpy
from numpy.typing import NDArray
from scipy import constants  # type: ignore

from om.graphical_interfaces.common import OmGuiBase
from om.lib.exceptions import OmMissingDependencyError
from om.lib.rich_console import console, get_current_timestamp

try:
    from PyQt5 import QtCore, QtGui, QtWidgets
except ImportError:
    raise OmMissingDependencyError(
        "The following required module cannot be imported: PyQt5"
    )

try:
    import pyqtgraph  # type: ignore
except ImportError:
    raise OmMissingDependencyError(
        "The following required module cannot be imported: pyqtgraph"
    )


class CrystallographyGui(OmGuiBase):
    """
    See documentation of the `__init__` function.
    """

    def __init__(self, *, url: str) -> None:
        """
        OM graphical user interface for crystallography.

        This class implements a graphical user interface for Serial Crystallography
        experiments. The GUI receives reduced and aggregated data from an OnDA Monitor,
        but only when it is tagged with the `omdata` label. The data must contain
        information about the position of detected Bragg peaks, and about the hit rate
        of the experiment. The GUI then displays a plot showing the evolution of the
        hit rate over time, a virtual powder pattern generated using the positions of
        the detected Bragg peaks, and a peakogram plot calculated from the Bragg peak
        information.

        Arguments:

            url: The URL at which the GUI should connect and listen for data. This must
                be a string in the format used by the ZeroMQ protocol.
        """
        super(CrystallographyGui, self).__init__(
            url=url,
            tag="omdata",
        )

        self._virtual_powder_plot_img: Union[NDArray[numpy.int_], None] = None
        self._img_center_x: int = 0
        self._img_center_y: int = 0

        self._last_pixel_size: float = 0
        self._last_detector_distance: float = 0
        self._last_beam_energy: float = 0
        self._last_detector_distance_offset: float = 0
        self._resolution_rings_in_a: List[float] = [
            10.0,
            9.0,
            8.0,
            7.0,
            6.0,
            5.0,
            4.0,
            3.0,
        ]
        x: float
        self._resolution_rings_text_items: List[Any] = [
            pyqtgraph.TextItem(text=f"{x}A", anchor=(0.5, 0.8), color=(255, 0, 0))
            for x in self._resolution_rings_in_a
        ]
        self._resolution_rings_enabled: bool = False

        self._received_data: Dict[str, Any] = {}

        pyqtgraph.setConfigOption("background", 0.2)

        self._resolution_rings_pen: Any = pyqtgraph.mkPen("r", width=0.5)
        self._resolution_rings_canvas: Any = pyqtgraph.ScatterPlotItem()

        self._image_view: Any = pyqtgraph.ImageView()
        self._image_view.ui.menuBtn.hide()
        self._image_view.ui.roiBtn.hide()
        self._image_view.getView().addItem(self._resolution_rings_canvas)

        self._resolution_rings_regex: Any = QtCore.QRegExp(r"[0-9.,]+")
        self._resolution_rings_validator: Any = QtGui.QRegExpValidator()
        self._resolution_rings_validator.setRegExp(self._resolution_rings_regex)

        self._resolution_rings_check_box: Any = QtWidgets.QCheckBox(
            text="Show Resolution Rings"
        )
        self._resolution_rings_check_box.setEnabled(True)
        self._resolution_rings_line_edit: Any = QtWidgets.QLineEdit()
        self._resolution_rings_line_edit.setValidator(self._resolution_rings_validator)
        self._resolution_rings_line_edit.setText(
            ",".join(str(x) for x in self._resolution_rings_in_a)
        )
        self._resolution_rings_line_edit.editingFinished.connect(
            self._update_resolution_rings_radii
        )
        self._resolution_rings_line_edit.setEnabled(True)

        self._hit_rate_plot_widget: Any = pyqtgraph.PlotWidget()
        self._hit_rate_plot_widget.setTitle("Hit Rate vs. Events")
        self._hit_rate_plot_widget.setLabel(axis="bottom", text="Events")
        self._hit_rate_plot_widget.setLabel(axis="left", text="Hit Rate, %")
        self._hit_rate_plot_widget.showGrid(x=True, y=True)
        self._hit_rate_plot_widget.setYRange(0, 100.0)
        self._hit_rate_plot: Any = self._hit_rate_plot_widget.plot(
            tuple(range(-5000, 0)), [0.0] * 5000
        )
        self._hit_rate_plot_dark: Any = None

        self._peakogram_plot_widget = pyqtgraph.PlotWidget(
            title="Peakogram", lockAspect=False
        )
        self._peakogram_plot_widget.showGrid(x=True, y=True)
        self._peakogram_plot_widget.setLabel(
            axis="left", text="Peak maximum intensity, AU"
        )
        self._peakogram_plot_widget.setLabel(
            axis="bottom",
            text="Resolution, pixels",
        )
        self._peakogram_plot_image_view = pyqtgraph.ImageView(
            view=self._peakogram_plot_widget.getPlotItem(),
        )
        self._peakogram_plot_image_view.ui.roiBtn.hide()
        self._peakogram_plot_image_view.ui.menuBtn.hide()
        self._peakogram_plot_image_view.view.invertY(False)
        self._peakogram_plot_image_view.setColorMap(pyqtgraph.colormap.get("CET-I1"))

        self._resolution_rings_check_box.stateChanged.connect(
            self._update_resolution_rings_status
        )

        horizontal_layout: Any = QtWidgets.QHBoxLayout()
        horizontal_layout.addWidget(self._resolution_rings_check_box)
        horizontal_layout.addWidget(self._resolution_rings_line_edit)
        splitter_1: Any = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        splitter_1.addWidget(self._hit_rate_plot_widget)
        splitter_1.addWidget(self._peakogram_plot_image_view)
        splitter_0: Any = QtWidgets.QSplitter()
        splitter_0.addWidget(self._image_view)
        splitter_0.addWidget(splitter_1)
        vertical_layout: Any = QtWidgets.QVBoxLayout()
        vertical_layout.addWidget(splitter_0)
        vertical_layout.addLayout(horizontal_layout)
        self._central_widget: Any = QtWidgets.QWidget()
        self._central_widget.setLayout(vertical_layout)
        self.setCentralWidget(self._central_widget)
        self.resize(1200, 600)
        self.show()

    def _update_resolution_rings_status(self) -> None:
        if self._virtual_powder_plot_img is None:
            return
        new_state = self._resolution_rings_check_box.isChecked()
        if self._resolution_rings_enabled is True and new_state is False:
            text_item: Any
            for text_item in self._resolution_rings_text_items:
                self._image_view.scene.removeItem(text_item)
            self._resolution_rings_canvas.setData([], [])
            self._resolution_rings_enabled = False
        if self._resolution_rings_enabled is False and new_state is True:
            for text_item in self._resolution_rings_text_items:
                self._image_view.getView().addItem(text_item)
            self._resolution_rings_enabled = True
            self._draw_resolution_rings()

    def _update_resolution_rings_radii(self) -> None:
        if self._virtual_powder_plot_img is None:
            return

        was_enabled: bool = self._resolution_rings_check_box.isChecked()
        self._resolution_rings_check_box.setChecked(False)

        items: List[str] = str(self._resolution_rings_line_edit.text()).split(",")
        if items:
            item: str
            self._resolution_rings_in_a = [
                float(item) for item in items if item != "" and float(item) != 0.0
            ]
        else:
            self._resolution_rings_in_a = []

        x: float
        self._resolution_rings_text_items = [
            pyqtgraph.TextItem(text=f"{x}A", anchor=(0.5, 0.8), color=(255, 0, 0))
            for x in self._resolution_rings_in_a
        ]

        if was_enabled is True:
            self._resolution_rings_check_box.setChecked(True)

        self._draw_resolution_rings()

    def _draw_resolution_rings(self) -> None:  # noqa: C901
        # Draws the resolution rings.
        # If there is no data, returns without drawing anything.
        if self._virtual_powder_plot_img is None:
            return

        if self._resolution_rings_enabled is False:
            return

        QtWidgets.QApplication.processEvents()

        try:
            lambda_: float = (
                constants.h * constants.c / (self._last_beam_energy * constants.e)
            )
            resolution_rings_in_pix: List[float] = [1.0]
            resolution: float
            resolution_rings_in_pix.extend(
                [
                    2.0
                    * self._last_pixel_size
                    * (
                        self._last_detector_distance * 1e-3
                        + self._last_detector_distance_offset
                    )
                    * numpy.tan(
                        2.0 * numpy.arcsin(lambda_ / (2.0 * resolution * 1e-10))
                    )
                    for resolution in self._resolution_rings_in_a
                ]
            )
        except TypeError:
            console.print(
                f"{get_current_timestamp()} Beam energy or detector distance"
                "information is not available. Resolution rings cannot be drawn.",
                style="warning",
            )
            self._resolution_rings_check_box.setChecked(False)
        else:
            self._resolution_rings_canvas.setData(
                [self._img_center_x] * len(resolution_rings_in_pix),
                [self._img_center_y] * len(resolution_rings_in_pix),
                symbol="o",
                size=resolution_rings_in_pix,
                pen=self._resolution_rings_pen,
                brush=(0, 0, 0, 0),
                pxMode=False,
            )

            index: int
            item: Any
            for index, item in enumerate(self._resolution_rings_text_items):
                item.setPos(
                    (self._img_center_x + resolution_rings_in_pix[index + 1] / 2.0),
                    self._img_center_y,
                )

        QtWidgets.QApplication.processEvents()

    def update_gui(self) -> None:
        """
        Updates the elements of the Crystallography GUI.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This method, which is called at regular intervals, updates the hit rate history
        plot, the virtual powder pattern plot and the peakogram plot.
        """

        if self._received_data:
            # Resets the 'received_data' attribute to None. One can then check if
            # data has been received simply by checking wether the attribute is not
            # None.
            local_data = self._received_data
            self._received_data = {}
        else:
            # If no data has been received, returns without drawing anything.
            return

        self._last_pixel_size = local_data["pixel_size"]
        self._last_detector_distance = local_data["detector_distance"]
        self._last_beam_energy = local_data["beam_energy"]
        self._last_detector_distance_offset = local_data["detector_distance_offset"]

        virtual_powder_plot_img_shape: Tuple[int, int] = local_data[
            "virtual_powder_plot"
        ].shape

        if (
            self._virtual_powder_plot_img is None
            or self._virtual_powder_plot_img.shape != virtual_powder_plot_img_shape
        ):
            self._img_center_x = int(virtual_powder_plot_img_shape[1] / 2)
            self._img_center_y = int(virtual_powder_plot_img_shape[0] / 2)
            self._virtual_powder_plot_img = local_data["virtual_powder_plot"]
            if (
                self._resolution_rings_check_box.isEnabled()
                and self._resolution_rings_check_box.isChecked() is True
            ):
                self._update_resolution_rings_status()
        else:
            self._virtual_powder_plot_img = local_data["virtual_powder_plot"]

        QtWidgets.QApplication.processEvents()

        if local_data["geometry_is_optimized"]:
            if not self._resolution_rings_check_box.isEnabled():
                self._resolution_rings_check_box.setEnabled(True)
                self._resolution_rings_line_edit.setEnabled(True)
        else:
            if self._resolution_rings_check_box.isEnabled():
                self._resolution_rings_check_box.setEnabled(False)
                self._resolution_rings_line_edit.setEnabled(False)
            if self._resolution_rings_check_box.isChecked() is True:
                self._resolution_rings_check_box.setChecked(False)

        QtWidgets.QApplication.processEvents()

        self._hit_rate_plot.setData(
            tuple(range(-5000, 0)), local_data["hit_rate_history"]
        )

        if local_data["pump_probe_experiment"]:
            if self._hit_rate_plot_dark is None:
                self._hit_rate_plot_dark = self._hit_rate_plot_widget.plot(
                    tuple(range(-5000, 0)),
                    local_data["hit_rate_history"],
                    pen=pyqtgraph.mkPen(color="light green"),
                )
            else:
                self._hit_rate_plot_dark.setData(
                    tuple(range(-5000, 0)),
                    local_data["hit_rate_history_dark"],
                )

        QtWidgets.QApplication.processEvents()

        if self._virtual_powder_plot_img is not None:
            self._image_view.setImage(
                self._virtual_powder_plot_img.T,
                autoHistogramRange=False,
                autoLevels=False,
                autoRange=False,
            )

        self._draw_resolution_rings()

        QtWidgets.QApplication.processEvents()

        peakogram: NDArray[numpy.float_] = local_data["peakogram"]
        peakogram[numpy.where(peakogram == 0)] = numpy.nan
        self._peakogram_plot_image_view.setImage(
            numpy.log(peakogram),
            pos=(0, 0),
            scale=(
                local_data["peakogram_radius_bin_size"],
                local_data["peakogram_intensity_bin_size"],
            ),
            autoRange=False,
            autoLevels=False,
            autoHistogramRange=False,
        )
        self._peakogram_plot_widget.setAspectLocked(False)

        QtWidgets.QApplication.processEvents()

        # Computes the estimated age of the received data and prints it into the status
        # bar (a GUI is supposed to be a Qt MainWindow widget, so it is supposed to
        # have a status bar).
        time_now: float = time.time()
        estimated_delay: float = round(time_now - local_data["timestamp"], 6)
        self.statusBar().showMessage(f"Estimated delay: {estimated_delay}")


@click.command()
@click.argument("url", type=str, required=False)
def main(*, url: str) -> None:
    """
    OM Graphical User Interface for Crystallography. This program must connect to a
    running OnDA Monitor for Crystallography. If the monitor broadcasts the necessary
    information, this GUI displays the evolution of the hit rate over time, a
    real-time virtual powder pattern created using the positions of detected Bragg
    peaks, and a peakogram plot computed from the Bragg peak information.

    The GUI connects to and OnDA Monitor running at the IP address (or hostname) + port
    specified by the URL string. This is a string in the format used by the ZeroMQ
    protocol. The URL string is optional. If not provided, it defaults to
    "tcp://127.0.0.1:12321": the GUI connects, using the tcp protocol, to a monitor
    running on the local machine at port 12321.
    """
    # This function is turned into a script by the Click library. The docstring
    # above becomes the help string for the script.
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    if url is None:
        url = "tcp://127.0.0.1:12321"
    app: Any = QtWidgets.QApplication(sys.argv)
    _ = CrystallographyGui(url=url)
    sys.exit(app.exec_())
