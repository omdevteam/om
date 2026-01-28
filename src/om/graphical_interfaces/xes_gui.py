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
OM's GUI for X-ray Emission Spectroscopy.

This module contains a graphical interface that displays reduced and aggregated data
in X-ray Emission Spectroscopy experiments.
"""

import signal
import sys
import time
from typing import Any

import typer
from typing_extensions import Annotated

from om.graphical_interfaces.common import OmGuiBase
from om.lib.exceptions import OmMissingDependencyError

try:
    from PyQt5 import QtWidgets  # type: ignore
except ImportError:
    raise OmMissingDependencyError(
        "The following required module cannot be imported: PyQt5"
    )

try:
    import pyqtgraph  # pyright: ignore[reportMissingTypeStubs]
except ImportError:
    raise OmMissingDependencyError(
        "The following required module cannot be imported: pyqtgraph"
    )

app: typer.Typer = typer.Typer(add_completion=False)

class XesGui(OmGuiBase):
    """
    See documentation of the `__init__` function.
    """

    def __init__(self, url: str, time_resolved: bool = False) -> None:
        """
        OM graphical user interface for XES.

        This class implements a graphical user interface for XES experiments.
        The GUI receives reduced and aggregated data from an OnDA Monitor, but only
        when it is tagged with the `omdata` label. The data must contain information
        about the collected XES spectra. The UI displays the last observed XES
        spectrum, both in raw and smoothed form, plus an average of the most recently
        collected spectra. For time resolved experiments, the graphical interface
        displays average spectra for pumped and dark events separately, and also shows
        their difference.

        Arguments:

            url: The URL where the GUI should connect and listen for data. This must
                be a string in the format used by the ZeroMQ protocol.
        """
        super(XesGui, self).__init__(
            url=url,
            tag="omdata",
        )

        self._image_view: Any = pyqtgraph.ImageView()
        self._image_view.ui.menuBtn.hide()
        self._image_view.ui.roiBtn.hide()

        self._xes_spectrum_plot_widget: Any = pyqtgraph.PlotWidget()
        self._xes_spectrum_plot_widget.setTitle("XES Spectra")
        self._xes_spectrum_plot_widget.setLabel(axis="bottom", text="Energy (Pixels)")
        self._xes_spectrum_plot_widget.setLabel(axis="left", text="Intensity")
        self._xes_spectrum_plot_widget.showGrid(x=True, y=True)
        self._xes_spectrum_plot: Any = self._xes_spectrum_plot_widget.plot(
            [0.0] * 1000,
            pen=None,
            symbol="o",
            symbolPen=pyqtgraph.mkPen(  # pyright: ignore[reportUnknownMemberType]
                "y"
            ),
            symbolBrush=pyqtgraph.mkBrush(  # pyright: ignore[reportUnknownMemberType]
                "y"
            ),
            symbolSize=3,
        )

        self._time_resolved = time_resolved
        if not self._time_resolved:
            self._xes_spectra_sum_plot: Any = self._xes_spectrum_plot_widget.plot(
                [0.0] * 1000,
                pen=pyqtgraph.mkPen(  # pyright: ignore[reportUnknownMemberType]
                    "w"
                ),
            )
            self._xes_spectra_sum_smoothed_plot: Any = (
                self._xes_spectrum_plot_widget.plot(
                    [0.0] * 1000,
                    pen=pyqtgraph.mkPen(  # pyright: ignore[reportUnknownMemberType]
                        "c", width=3
                    ),
                )
            )
        else:
            self._xes_spectra_sum_pumped_plot: Any = (
                self._xes_spectrum_plot_widget.plot(
                    [0.0] * 1000,
                    pen=pyqtgraph.mkPen(  # pyright: ignore[reportUnknownMemberType]
                        "w"
                    ),
                )
            )
            self._xes_spectra_sum_dark_plot: Any = self._xes_spectrum_plot_widget.plot(
                [0.0] * 1000,
                pen=pyqtgraph.mkPen(  # pyright: ignore[reportUnknownMemberType]
                    "c", width=3
                ),
            )
            self._xes_spectra_sum_difference_plot: Any = (
                self._xes_spectrum_plot_widget.plot(
                    [0.0] * 1000,
                    pen=pyqtgraph.mkPen(  # pyright: ignore[reportUnknownMemberType]
                        "r", width=3
                    ),
                )
            )

        pyqtgraph.setConfigOption(  # pyright: ignore[reportUnknownMemberType]
            "background", 0.2
        )

        horizontal_layout: Any = (  # pyright: ignore[reportUnknownVariableType]
            QtWidgets.QHBoxLayout()  # pyright: ignore[reportUnknownMemberType]
        )
        splitter_0: Any = (  # pyright: ignore[reportUnknownVariableType]
            QtWidgets.QSplitter()  # pyright: ignore[reportUnknownMemberType]
        )
        splitter_0.addWidget(  # pyright: ignore[reportUnknownMemberType]
            self._image_view
        )
        splitter_0.addWidget(  # pyright: ignore[reportUnknownMemberType]
            self._xes_spectrum_plot_widget
        )
        vertical_layout: Any = (  # pyright: ignore[reportUnknownVariableType]
            QtWidgets.QVBoxLayout()  # pyright: ignore[reportUnknownMemberType]
        )
        vertical_layout.addWidget(  # pyright: ignore[reportUnknownMemberType]
            splitter_0
        )
        vertical_layout.addLayout(  # pyright: ignore[reportUnknownMemberType]
            horizontal_layout
        )
        self._central_widget: Any = (
            QtWidgets.QWidget()  # pyright: ignore[reportUnknownMemberType]
        )
        self._central_widget.setLayout(  # pyright: ignore[reportUnknownMemberType]
            vertical_layout
        )
        self.setCentralWidget(  # pyright: ignore[reportUnknownMemberType]
            self._central_widget  # pyright: ignore[reportUnknownMemberType]
        )
        self.show()  # pyright: ignore[reportUnknownMemberType]

    def update_gui(self) -> None:
        """
        Updates the elements of the XES GUI.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This method, which is called at regular intervals, updates the plots showing
        the energy spectrum information.
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

        self._xes_spectrum_plot.setData(local_data["spectrum"])
        if not self._time_resolved:
            self._xes_spectra_sum_plot.setData(local_data["spectra_sum"])
            self._xes_spectra_sum_smoothed_plot.setData(
                local_data["spectra_sum_smoothed"]
            )
        else:
            self._xes_spectra_sum_pumped_plot.setData(local_data["spectra_sum_pumped"])
            self._xes_spectra_sum_dark_plot.setData(local_data["spectra_sum_dark"])
            self._xes_spectra_sum_difference_plot.setData(
                local_data["spectra_sum_difference"]
            )

        QtWidgets.QApplication.processEvents()  # pyright: ignore[reportUnknownMemberType]

        self._image_view.setImage(
            local_data["detector_data"].T,
            autoHistogramRange=False,
            autoLevels=False,
            autoRange=False,
        )

        QtWidgets.QApplication.processEvents()  # pyright: ignore[reportUnknownMemberType]

        # Computes the estimated age of the received data and prints it into the status
        # bar (a GUI is supposed to be a Qt MainWindow widget, so it is supposed to
        # have a status bar).
        time_now: float = time.time()
        estimated_delay: float = round(time_now - local_data["timestamp"], 6)
        self.statusBar().showMessage(  # pyright: ignore[reportUnknownMemberType]
            f"Estimated delay: {estimated_delay} seconds"
        )

@app.command()
def main(
    *,
    url: Annotated[
        str,
        typer.Argument(help="Experiment identifier"),
    ] = "tcp://127.0.0.1:12321",
    time_resolved: Annotated[
        bool,
        typer.Option(
            "--time-resolved",
            "-t",
            help="Whether the GUI should display time resolved data",
        ),
    ] = False,
) -> None:
    """
    OM Graphical User Interface for X-ray Emission Spectroscopy. This program must
    connect to a running OnDA Monitor for X-ray Emission Spectroscopy. If the monitor
    broadcasts the necessary information, this GUI displays the latest observed
    XES spectrum, both in raw and smoothed form, and an average of the most recently
    collected spectra. For time resolved experiments, the GUI displays separate average
    spectra for pumped and dark events, and also shows their difference.

    The graphical interface connects to and OnDA Monitor running at the IP address
    (or hostname) + port specified by the URL string. This is a string in the format
    used by the ZeroMQ protocol. The URL string is optional. If not provided, it
    defaults to "tcp://127.0.0.1:12321": the GUI connects, using the tcp protocol, to a
    monitor running on the local machine at port 12321.
    """
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app: Any = (  # pyright: ignore[reportUnknownVariableType]
        QtWidgets.QApplication(  # pyright: ignore[reportUnknownMemberType]
            sys.argv
        )
    )
    _ = XesGui(url, time_resolved)
    sys.exit(
        app.exec_()  # pyright: ignore[reportUnknownMemberType,reportUnknownArgumentType]
    )


typer_click_object = typer.main.get_command(app)

if __name__ == "__main__":
    app()
