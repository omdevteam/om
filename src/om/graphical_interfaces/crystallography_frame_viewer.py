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
OM's Frame Viewer for Crystallography.

This module contains a graphical interface that displays detector data frames and
detected Bragg peaks in crystallography experiments.
"""
import collections
import copy
import signal
import sys
import time
from typing import Any, Deque, Dict, Union

import click
import numpy
from numpy.typing import NDArray

from om.graphical_interfaces import common as graph_interfaces_common
from om.utils import exceptions
from om.utils.rich_console import console, get_current_timestamp

try:
    from PyQt5 import QtWidgets
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


class CrystallographyFrameViewer(graph_interfaces_common.OmGuiBase):
    """
    See documentation of the `__init__` function.
    """

    def __init__(self, *, url: str):
        """
        OM frame viewer for crystallography.

        This class implements a frame viewer for serial crystallography experiments.
        The viewer receives data frames from an OnDA Monitor, but only when the data is
        tagged with the `view:omframedata` label. The data must contain processed
        detector frames, and information on any detected Bragg peak. The viewer will
        then display the frame images, and the position of each peak. A data storage
        buffer allows the viewer to stop receiving data from the OnDA Monitor, but
        still keep in memory the last 10 displayed frames for re-inspection.

        Arguments:

            url: The URL at which the GUI will connect and listen for data. This must
                be a string in the format used by the ZeroMQ protocol.
        """
        super(CrystallographyFrameViewer, self).__init__(
            url=url,
            tag="omframedata",
        )

        self._img: Union[NDArray[numpy.float_], None] = None
        self._frame_list: Deque[Dict[str, Any]] = collections.deque(maxlen=20)
        self._current_frame_index: int = -1

        self._received_data: Dict[str, Any] = {}

        pyqtgraph.setConfigOption("background", 0.2)

        self._ring_pen: Any = pyqtgraph.mkPen("r", width=2)
        self._peak_canvas: Any = pyqtgraph.ScatterPlotItem()

        self._image_view: Any = pyqtgraph.ImageView()
        self._image_view.ui.menuBtn.hide()
        self._image_view.ui.roiBtn.hide()
        self._image_view.getView().addItem(self._peak_canvas)

        self._back_button: Any = QtWidgets.QPushButton(text="Back")
        self._back_button.clicked.connect(self._back_button_clicked)

        self._forward_button: Any = QtWidgets.QPushButton(text="Forward")
        self._forward_button.clicked.connect(self._forward_button_clicked)

        self._play_pause_button: Any = QtWidgets.QPushButton(text="Pause")
        self._play_pause_button.clicked.connect(self._play_pause_button_clicked)

        self._horizontal_layout: Any = QtWidgets.QHBoxLayout()
        self._horizontal_layout.addWidget(self._back_button)
        self._horizontal_layout.addWidget(self._forward_button)
        self._horizontal_layout.addWidget(self._play_pause_button)
        self._vertical_layout: Any = QtWidgets.QVBoxLayout()
        self._vertical_layout.addWidget(self._image_view)
        self._vertical_layout.addLayout(self._horizontal_layout)
        self._central_widget: Any = QtWidgets.QWidget()
        self._central_widget.setLayout(self._vertical_layout)
        self.setCentralWidget(self._central_widget)

        self.show()

    def _update_peaks(
        self,
        *,
        peak_list_x_in_frame: NDArray[numpy.float_],
        peak_list_y_in_frame: NDArray[numpy.float_],
    ) -> None:
        # Updates the Bragg peaks shown by the viewer.
        QtWidgets.QApplication.processEvents()

        self._peak_canvas.setData(
            x=peak_list_x_in_frame,
            y=peak_list_y_in_frame,
            symbol="o",
            size=[5] * len(peak_list_x_in_frame),
            brush=(255, 255, 255, 0),
            pen=self._ring_pen,
            pxMode=False,
        )

    def _update_image_and_peaks(self) -> None:
        # Updates the image and Bragg peaks shown by the viewer.

        try:
            current_data: Dict[str, Any] = self._frame_list[self._current_frame_index]
        except IndexError:
            # If the framebuffer is empty, returns without drawing anything.
            return

        QtWidgets.QApplication.processEvents()

        self._image_view.setImage(
            current_data["frame_data"].T,
            autoLevels=False,
            autoRange=False,
            autoHistogramRange=False,
        )

        QtWidgets.QApplication.processEvents()

        self._update_peaks(
            peak_list_x_in_frame=current_data["peak_list_x_in_frame"],
            peak_list_y_in_frame=current_data["peak_list_y_in_frame"],
        )

        QtWidgets.QApplication.processEvents()

        # Computes the estimated age of the received data and prints it into the status
        # bar (a GUI is supposed to be a Qt MainWindow widget, so it is supposed to
        # have a status bar).
        timenow: float = time.time()
        estimated_delay: float = round(timenow - current_data["timestamp"], 6)
        self.statusBar().showMessage(f"Estimated delay: {estimated_delay} seconds")

    def update_gui(self) -> None:
        """
        Updates the elements of the Crystallography Frame Viewer.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This method, which is executed at regular intervals, calls the internal
        functions that update the displayed detector frame and Bragg peaks.
        Additionally, this function manages the data storage buffer that allows the
        last received frames to be re-inspected.
        """
        # Makes sure that the data shown by the viewer is updated if data is
        # received.

        if self._received_data:
            # Resets the 'received_data' attribute to None. One can then check if
            # data has been received simply by checking wether the attribute is not
            # False.
            local_data = self._received_data
            self._received_data = {}
        else:
            # If no data has been received, returns without drawing anything.
            return

        self._frame_list.append(copy.deepcopy(local_data))
        self._current_frame_index = len(self._frame_list) - 1

        self._update_image_and_peaks()

    def _back_button_clicked(self) -> None:
        # Manages clicks on the 'back' button.
        self._stop_stream()
        if self._current_frame_index > 0:
            self._current_frame_index -= 1
        console.print(
            f"{get_current_timestamp()} Showing frame "
            f"{self._current_frame_index} in the buffer"
        )
        self._update_image_and_peaks()

    def _forward_button_clicked(self) -> None:
        # Manages clicks on the 'forward' button.
        self._stop_stream()
        if (self._current_frame_index + 1) < len(self._frame_list):
            self._current_frame_index += 1
        console.print(f"Showing frame {self._current_frame_index} in the buffer")
        self._update_image_and_peaks()

    def _stop_stream(self) -> None:
        # Disconnects from the OM monitor and stops receiving data.
        if self.listening:
            self._play_pause_button.setText("Play")
            self.stop_listening()

    def _start_stream(self) -> None:
        # Connects to the the OM monitor and starts receiving data.
        if not self.listening:
            self._play_pause_button.setText("Pause")
            self.start_listening()

    def _play_pause_button_clicked(self) -> None:
        # Manages clicks on the 'play/pause' button.
        if self.listening:
            self._stop_stream()
        else:
            self._start_stream()


@click.command()
@click.argument("url", type=str, required=False)
def main(*, url: str) -> None:
    """
    OM Frame Viewer for Crystallography. This program must connect to a running OnDA
    Monitor for Crystallography. If the monitor broadcasts detector data frames, this
    viewer will display them. The viewer will also show, overlayed on each frame,
    any detected Bragg peak. The data stream from the monitor can also be temporarily
    paused, and any of 10 most recently displayed detector frames can be recalled for
    re-inspection.

    The viewer connects to and OnDA Monitor running at the IP address (or hostname)
    specified by the URL string. This is a string in the format used by the ZeroMQ
    protocol. The URL string is optional. If not provided, it defaults to
    "tcp://127.0.0.1:12321": the viewer will connect, using the tcp protocol, to a
    monitor running on the local machine at port 12321.
    """
    # This function is turned into a script by the Click library. The docstring
    # above becomes the help string for the script.
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    if url is None:
        url = "tcp://127.0.0.1:12321"
    app: Any = QtWidgets.QApplication(sys.argv)
    _ = CrystallographyFrameViewer(url=url)
    sys.exit(app.exec_())
