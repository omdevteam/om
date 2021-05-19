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
# Copyright 2020 -2021 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
OM's GUI for Crystallography.

This module contains the implementation of a graphical interface that displays reduced
and aggregated data in crystallography experiments.
"""
import signal
import sys
import time
from typing import Any, Dict, List, Tuple, Union

import click
import numpy  # type: ignore
from om.graphical_interfaces import base as graph_interfaces_base
from om.utils import exceptions
from scipy import constants  # type: ignore

try:
    from PyQt5 import QtCore, QtGui  # type: ignore
except ImportError:
    raise exceptions.OmMissingDependencyError(
        "The following required module cannot be imported: PyQt5"
    )

try:
    import pyqtgraph  # type: ignore
except ImportError:
    raise exceptions.OmMissingDependencyError(
        "The following required module cannot be imported: pyqtgraph"
    )


class CrystallographyGui(graph_interfaces_base.OmGui):
    """
    See documentation of the `__init__` function.

    Base class: [`OmGui`][om.graphical_interfaces.base.OmGui]
    """

    def __init__(self, url: str) -> None:
        """
        OM graphical user interface for crystallography.

        This class implements a graphical user interface for crystallography
        experiments. It is a subclass of the [OmGui]
        [om.graphical_interfaces.base.OmGui] base class.

        This GUI receives reduced and aggregated data from an OnDA Monitor for
        Crystallography when it is tagged with the 'omdata' label. The data must
        contain information about peaks detected in the frames recently processed by
        the monitor and information about the current hit rate.

        The GUI displays a plot showing the evolution of the hit rate over time, plus a
        virtual powder pattern created using the detected peaks.

        Arguments:

            url (str): the URL at which the GUI will connect and listen for data. This
                must be a string in the format used by the ZeroMQ Protocol.
        """
        super(CrystallographyGui, self).__init__(
            url=url,
            tag="view:omdata",
        )

        self._virt_powd_plot_img: Union[numpy.ndarray, None] = None
        self._img_center_x: int = 0
        self._img_center_y: int = 0

        self._last_pixel_size: float = 0
        self._last_detector_distance: float = 0
        self._last_beam_energy: float = 0
        self._last_coffset: float = 0
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
        self._resolution_rings_textitems: List[Any] = [
            pyqtgraph.TextItem(text="{0}A".format(x), anchor=(0.5, 0.8))
            for x in self._resolution_rings_in_a
        ]
        self._resolution_rings_enabled: bool = False

        self._received_data: Dict[str, Any] = {}

        pyqtgraph.setConfigOption("background", 0.2)

        self._resolution_rings_pen: Any = pyqtgraph.mkPen("w", width=0.5)
        self._resolution_rings_canvas: Any = pyqtgraph.ScatterPlotItem()

        self._image_view: Any = pyqtgraph.ImageView()
        self._image_view.ui.menuBtn.hide()
        self._image_view.ui.roiBtn.hide()
        self._image_view.getView().addItem(self._resolution_rings_canvas)

        self._resolution_rings_regex: Any = QtCore.QRegExp(r"[0-9.,]+")
        self._resolution_rings_validator: Any = QtGui.QRegExpValidator()
        self._resolution_rings_validator.setRegExp(self._resolution_rings_regex)

        self._resolution_rings_check_box: Any = QtGui.QCheckBox(
            text="Show Resolution Rings", checked=True
        )
        self._resolution_rings_check_box.setEnabled(True)
        self._resolution_rings_lineedit: Any = QtGui.QLineEdit()
        self._resolution_rings_lineedit.setValidator(self._resolution_rings_validator)
        self._resolution_rings_lineedit.setText(
            ",".join(str(x) for x in self._resolution_rings_in_a)
        )
        self._resolution_rings_lineedit.editingFinished.connect(
            self._update_resolution_rings_radii
        )
        self._resolution_rings_lineedit.setEnabled(True)

        self._hit_rate_plot_widget: Any = pyqtgraph.PlotWidget()
        self._hit_rate_plot_widget.setTitle("Hit Rate vs. Events")
        self._hit_rate_plot_widget.setLabel(axis="bottom", text="Events")
        self._hit_rate_plot_widget.setLabel(axis="left", text="Hit Rate")
        self._hit_rate_plot_widget.showGrid(x=True, y=True)
        self._hit_rate_plot_widget.setYRange(0, 100.0)
        self._hit_rate_plot: Any = self._hit_rate_plot_widget.plot(
            tuple(range(-5000, 0)), [0.0] * 5000
        )
        self._resolution_rings_check_box.stateChanged.connect(
            self._update_resolution_rings_status
        )

        horizontal_layout: Any = QtGui.QHBoxLayout()
        horizontal_layout.addWidget(self._resolution_rings_check_box)
        horizontal_layout.addWidget(self._resolution_rings_lineedit)
        splitter_0: Any = QtGui.QSplitter()
        splitter_0.addWidget(self._image_view)
        splitter_0.addWidget(self._hit_rate_plot_widget)
        vertical_layout: Any = QtGui.QVBoxLayout()
        vertical_layout.addWidget(splitter_0)
        vertical_layout.addLayout(horizontal_layout)
        self._central_widget: Any = QtGui.QWidget()
        self._central_widget.setLayout(vertical_layout)
        self.setCentralWidget(self._central_widget)
        self.show()

    def _update_resolution_rings_status(self) -> None:
        if self._virt_powd_plot_img is None:
            return
        new_state = self._resolution_rings_check_box.isChecked()
        if self._resolution_rings_enabled is True and new_state is False:
            text_item: Any
            for text_item in self._resolution_rings_textitems:
                self._image_view.scene.removeItem(text_item)
            self._resolution_rings_canvas.setData([], [])
            self._resolution_rings_enabled = False
        if self._resolution_rings_enabled is False and new_state is True:
            for text_item in self._resolution_rings_textitems:
                self._image_view.getView().addItem(text_item)
            self._resolution_rings_enabled = True
            self._draw_resolution_rings()

    def _update_resolution_rings_radii(self) -> None:
        if self._virt_powd_plot_img is None:
            return

        was_enabled: bool = self._resolution_rings_check_box.isChecked()
        self._resolution_rings_check_box.setChecked(False)

        items: List[str] = str(self._resolution_rings_lineedit.text()).split(",")
        if items:
            item: str
            self._resolution_rings_in_a = [
                float(item) for item in items if item != "" and float(item) != 0.0
            ]
        else:
            self._resolution_rings_in_a = []

        x: float
        self._resolution_rings_textitems = [
            pyqtgraph.TextItem(text="{0}A".format(x), anchor=(0.5, 0.8))
            for x in self._resolution_rings_in_a
        ]

        if was_enabled is True:
            self._resolution_rings_check_box.setChecked(True)

        self._draw_resolution_rings()

    def _draw_resolution_rings(self) -> None:  # noqa: C901
        # Draws the resolution rings.
        # If there is no data, returns without drawing anything.
        if self._virt_powd_plot_img is None:
            return

        if self._resolution_rings_enabled is False:
            return

        QtGui.QApplication.processEvents()

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
                    * (self._last_detector_distance * 1e-3 + self._last_coffset)
                    * numpy.tan(
                        2.0 * numpy.arcsin(lambda_ / (2.0 * resolution * 1e-10))
                    )
                    for resolution in self._resolution_rings_in_a
                ]
            )
        except TypeError:
            print(
                "Beam energy or detector distance information is not available. "
                "Resolution rings cannot be drawn."
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
            for index, item in enumerate(self._resolution_rings_textitems):
                item.setPos(
                    (self._img_center_x + resolution_rings_in_pix[index + 1] / 2.0),
                    self._img_center_y,
                )

        QtGui.QApplication.processEvents()

    def update_gui(self) -> None:
        """
        Updates the elements of the Crystallography GUI.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function stores the data received from OM, and calls the internal
        functions that update the hit rate history plot and the virtual power pattern.
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
        self._last_coffset = local_data["first_panel_coffset"]

        virt_powd_plot_img_shape: Tuple[int, int] = local_data[
            "virtual_powder_plot"
        ].shape

        if (
            self._virt_powd_plot_img is None
            or self._virt_powd_plot_img.shape != virt_powd_plot_img_shape
        ):

            self._img_center_x = int(virt_powd_plot_img_shape[1] / 2)
            self._img_center_y = int(virt_powd_plot_img_shape[0] / 2)
            if (
                self._resolution_rings_check_box.isEnabled()
                and self._resolution_rings_check_box.isChecked() is True
            ):
                self._virt_powd_plot_img = local_data["virtual_powder_plot"]
                self._update_resolution_rings_status()
        else:
            self._virt_powd_plot_img = local_data["virtual_powder_plot"]

        QtGui.QApplication.processEvents()

        if local_data["geometry_is_optimized"]:
            if not self._resolution_rings_check_box.isEnabled():
                self._resolution_rings_check_box.setEnabled(True)
                self._resolution_rings_lineedit.setEnabled(True)
        else:
            if self._resolution_rings_check_box.isEnabled():
                self._resolution_rings_check_box.setEnabled(False)
                self._resolution_rings_lineedit.setEnabled(False)
            if self._resolution_rings_check_box.isChecked() is True:
                self._resolution_rings_check_box.setChecked(False)

        QtGui.QApplication.processEvents()

        self._hit_rate_plot.setData(
            tuple(range(-5000, 0)), local_data["hit_rate_history"]
        )

        QtGui.QApplication.processEvents()

        if self._virt_powd_plot_img is not None:
            self._image_view.setImage(
                self._virt_powd_plot_img.T,
                autoHistogramRange=False,
                autoLevels=False,
                autoRange=False,
            )

        self._draw_resolution_rings()

        QtGui.QApplication.processEvents()

        # Computes the estimated age of the received data and prints it into the status
        # bar (a GUI is supposed to be a Qt MainWindow widget, so it is supposed to
        # have a status bar).
        timenow: float = time.time()
        self.statusBar().showMessage(
            "Estimated delay: {0} seconds".format(
                round(timenow - local_data["timestamp"], 6)
            )
        )


@click.command()
@click.argument("url", type=str, required=False)
def main(url: str) -> None:
    """
    OM Graphical User Interface for Crystallography. This program must connect to a
    running OnDA Monitor for Crystallography. If the monitor broadcasts the necessary
    information, this GUI will display the evolution of the hit rate over time, plus a
    real-time virtual powder pattern created using the peaks detected in detector
    frames processed by the monitor.

    The GUI connects to and OnDA Monitor running at the IP address (or hostname)
    specified by the URL string. This is a string in the format used by the ZeroMQ
    Protocol. The URL string is optional. If not provided, it defaults to
    "tcp://127.0.0.1:12321" and the viewer connects, using the tcp protocol, to a
    monitor running on the local machine at port 12321.
    """
    # This function is turned into a script by the Click library. The docstring
    # above becomes the help string for the script.
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    if url is None:
        url = "tcp://127.0.0.1:12321"
    app: Any = QtGui.QApplication(sys.argv)
    _ = CrystallographyGui(url)
    sys.exit(app.exec_())
