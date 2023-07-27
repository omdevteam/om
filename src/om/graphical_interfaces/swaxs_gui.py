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
# Copyright 2020 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
OM's GUI for Crystallography.

This module contains the implementation of a graphical interface that displays reduced
and aggregated data in crystallography experiments.
"""

# TODO: Documentation of this whole file.

import signal
import sys
import time
from typing import Any, Dict

import click
import numpy
from numpy.typing import NDArray

from om.graphical_interfaces.common import OmGuiBase
from om.lib.exceptions import OmMissingDependencyError

try:
    from PyQt5 import QtCore, QtWidgets  # type: ignore
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


class SwaxsGui(OmGuiBase):
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
        super(SwaxsGui, self).__init__(
            url=url,
            tag="omdata",
        )

        self._received_data: Dict[str, Any] = {}

        pyqtgraph.setConfigOption("background", 0.2)

        # radial profiles
        self._radial_widget: Any = pyqtgraph.PlotWidget()
        self._radial_widget.addLegend(offset=(0, 100))
        self._radial_widget.setLabel(axis="left", text="I(q)")
        self._radial_widget.setLabel(axis="bottom", text="q (1/angstrom)")
        self._radial_plot: Any = self._radial_widget.plot(
            tuple(range(1000, 0)), [0.0] * 1000, name="frame"
        )
        self._recent_avg_plot: Any = self._radial_widget.plot(
            tuple(range(1000, 0)), [0.0] * 1000, pen=pyqtgraph.mkPen("y"), name="recent"
        )

        self._roi_widget: Any = pyqtgraph.PlotWidget()
        self._roi_widget.addLegend()
        self._roi_widget.setTitle("Intensity of ROI vs. Events")
        self._roi_widget.setLabel(axis="bottom", text="Events")
        self._roi_widget.setLabel(axis="left", text="ROI Intensity")
        self._roi_widget.showGrid(x=True, y=True)
        self._roi_widget.setYRange(-1e-3, 1.0e-2)

        self._roi1_plot: Any = self._roi_widget.plot(
            tuple(range(-5000, 0)),
            [0.0] * 5000,
            pen=None,
            symbol="o",
            symbolPen=pyqtgraph.mkPen("y"),
            symbolSize=3,
            name="ROI1",
        )
        self._roi2_plot: Any = self._roi_widget.plot(
            tuple(range(-5000, 0)),
            [0.0] * 5000,
            pen=None,
            symbol="o",
            symbolPen=pyqtgraph.mkPen("c"),
            symbolSize=3,
            name="ROI2",
        )

        # self._int_widget: Any = pyqtgraph.PlotWidget()
        # self._int_widget.addLegend()
        # self._int_widget.setTitle("Intensity Monitor vs. Events")
        # self._int_widget.setLabel(axis="bottom", text="Events")
        # self._int_widget.setLabel(
        #     axis="left", text="Ratio of Transmitted/Incident Intensity"
        # )
        # self._int_widget.showGrid(x=True, y=True)
        # self._int_widget.setYRange(0, 1.0)

        # self._int_monitor_ratio_plot: Any = self._int_widget.plot(
        #     pen=None,
        #     symbol="o",
        #     symbolPen=pyqtgraph.mkPen("y"),
        #     symbolSize=3,
        #     name="Int Ratio",
        # )

        # self._digitizer_sum_plot: Any = self._int_widget.plot(
        #     pen=None,
        #     symbol="o",
        #     symbolPen=pyqtgraph.mkPen("c"),
        #     symbolSize=3,
        #     name="Digitizer Sum",
        # )

        #
        self._radial_stack_view: Any = pyqtgraph.ImageView()
        self._radial_stack_view.view.setAspectLocked(False)
        self._radial_stack_view.setLevels(0, 12.0)
        self._radial_stack_view.ui.histogram.gradient.loadPreset("flame")

        pos = numpy.linspace(0, 1.0, 5)
        colors = [(0, 0, 0), (0, 0, 255), (0, 255, 0), (255, 255, 0), (255, 0, 0)]
        colormap = pyqtgraph.ColorMap(pos, colors)
        self._radial_stack_view.setColorMap(colormap)

        horizontal_layout: Any = QtWidgets.QHBoxLayout()

        splitter_0: Any = QtWidgets.QSplitter()
        splitter_0.addWidget(self._radial_stack_view)

        vertical_splitter: Any = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        vertical_splitter.addWidget(self._radial_widget)
        vertical_splitter.addWidget(self._roi_widget)
        # vertical_splitter.addWidget(self._int_widget)
        splitter_0.addWidget(vertical_splitter)
        horizontal_layout.addWidget(splitter_0)
        self._central_widget: Any = QtWidgets.QWidget()
        self._central_widget.setLayout(horizontal_layout)
        self.setCentralWidget(self._central_widget)
        self.show()

        QtWidgets.QApplication.processEvents()

    def update_gui(self) -> None:
        """
        Updates the elements of the Swaxs GUI.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function stores the data received from OM, and calls the internal
        functions that update the hit rate history plot and the virtual power pattern.
        """
        if self._received_data:
            # Resets the 'received_data' attribute to None. One can then check if
            # data has been received simply by checking wether the attribute is not
            # None.
            local_data: Dict[str, Any] = self._received_data
            self._received_data = {}
        else:
            # If no data has been received, returns without drawing anything.
            return

        # self._last_pixel_size: float = local_data["pixel_size"]
        # self._last_detector_distance: float = local_data["detector_distance"]
        # self._last_beam_energy: float = local_data["beam_energy"]
        # self._last_coffset: float = local_data["first_panel_coffset"]

        radial: NDArray[numpy.float_] = local_data["radial"]
        q: NDArray[numpy.float_] = local_data["q"]
        self._radial_plot.setData(q, radial)

        recent_avg: NDArray[numpy.float_] = local_data["recent_radial_average"]
        self._recent_avg_plot.setData(q, recent_avg)
        self._radial_stack_view.setImage(
            local_data["radial_stack"].T,
            autoHistogramRange=False,
            autoLevels=False,
            autoRange=False,
        )

        self._roi1_plot.setData(tuple(range(-5000, 0)), local_data["roi1_int_history"])
        self._roi2_plot.setData(tuple(range(-5000, 0)), local_data["roi2_int_history"])

        QtWidgets.QApplication.processEvents()

        # Computes the estimated age of the received data and prints it into the status
        # bar (a GUI is supposed to be a Qt MainWindow widget, so it is supposed to
        # have a status bar).
        time_now: float = time.time()
        estimated_delay: float = round(time_now - local_data["timestamp"], 6)
        self.statusBar().showMessage(f"Estimated delay: {estimated_delay} seconds")


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
    app: Any = QtWidgets.QApplication(sys.argv)
    _ = SwaxsGui(url)
    sys.exit(app.exec_())
