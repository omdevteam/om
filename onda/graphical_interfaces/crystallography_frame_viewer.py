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
OnDA frame viewer for crystallography.
"""
from __future__ import absolute_import, division, print_function

import collections
import copy
import sys
from typing import Any, Dict  # pylint: disable=unused-import

import cfelpyutils.crystfel_utils as cfel_crystfel
import cfelpyutils.geometry_utils as cfel_geometry
import click
import numpy
import pyqtgraph

from onda.utils import gui

try:
    import PyQt5.QtGui as QtGui
except ImportError:
    import PyQt4.QtGui as QtGui


class CrystallographyFrameViewer(gui.OndaGui):
    """
    See documentation of the __init__ function.
    """

    def __init__(self, geometry, hostname, port):
        # type: (Dict[str, Any], str, int) -> None
        """
        OnDA frame viewer for crystallography.

        This GUI receives detector data frames broadcasted from an OnDA monitor, but
        only when they are tagged with the 'ondadetectordata' label. It displays the
        detector frame, together with any detected Bragg peak (if present). A data
        buffer allows this GUI to stop receiving data from the monitor but still keep
        in memory the last 10 received data frames for inspection.

        Arguments:

            geometry (Dict[str, Any]): a dictionary containing CrystFEL detector
                geometry information (as returned by the
                :func:`~cfelpyutils.crystfel_utils.load_crystfel_geometry` function).

            hostname (str): the hostname (or IP address) of the machine where the OnDA
                monitor is broadcasting the data.

            port (int): the port where the OnDA monitor is broadcasting the data.
        """
        super(CrystallographyFrameViewer, self).__init__(
            hostname=hostname,
            port=port,
            gui_update_func=self._update_image,
            subscription_string="ondaframedata",
        )

        pixel_maps = cfel_geometry.compute_pix_maps(geometry)
        self._img_shape = cfel_geometry.compute_min_array_size(pixel_maps)
        self._img_center_x = int(self._img_shape[1] / 2)
        self._img_center_y = int(self._img_shape[0] / 2)
        visual_pixel_map = cfel_geometry.compute_visualization_pix_maps(geometry)
        self._visual_pixel_map_x = visual_pixel_map.x.flatten()
        self._visual_pixel_map_y = visual_pixel_map.y.flatten()
        self._img = numpy.zeros(shape=self._img_shape, dtype=numpy.float)

        self._frame_list = collections.deque(maxlen=20)
        self._current_frame_index = -1

        pyqtgraph.setConfigOption("background", 0.2)

        self._ring_pen = pyqtgraph.mkPen('r', width=2)
        self._peak_canvas = pyqtgraph.ScatterPlotItem()

        self._image_view = pyqtgraph.ImageView()
        self._image_view.ui.menuBtn.hide()
        self._image_view.ui.roiBtn.hide()
        self._image_view.getView().addItem(self._peak_canvas)

        self._back_button = QtGui.QPushButton(text="Back")
        self._back_button.clicked.connect(self._back_button_clicked)

        self._forward_button = QtGui.QPushButton(text="Forward")
        self._forward_button.clicked.connect(self._forward_button_clicked)

        self._play_pause_button = QtGui.QPushButton(text="Pause")
        self._play_pause_button.clicked.connect(self._play_pause_button_clicked)

        self._horizontal_layout = QtGui.QHBoxLayout()
        self._horizontal_layout.addWidget(self._back_button)
        self._horizontal_layout.addWidget(self._forward_button)
        self._horizontal_layout.addWidget(self._play_pause_button)
        self._vertical_layout = QtGui.QVBoxLayout()
        self._vertical_layout.addWidget(self._image_view)
        self._vertical_layout.addLayout(self._horizontal_layout)
        self._central_widget = QtGui.QWidget()
        self._central_widget.setLayout(self._vertical_layout)
        self.setCentralWidget(self._central_widget)

        self.show()

    def _update_image(self):
        # Type () -> None
        # Updates the frame image shown by the viewer.

        if self.aggregated_data:
            # The received aggregated data is expected to be a list of event entries
            # (each being a dictionary storing the data for an event:
            # List[Dict[str, Any], ...]). The last event in the list is extracted for
            # visualizaton.
            self._frame_list.append(copy.deepcopy(self.aggregated_data[-1]))
            self._current_frame_index = len(self._frame_list) - 1
            # Resets the 'aggregated_data' attribute to None. One can then check if
            # data has been received simply by checking wether the attribute is not
            # None.
            self.aggregated_data = None

        try:
            current_data = self._frame_list[self._current_frame_index]
        except IndexError:
            # If the framebuffer is empty, returns without drawing anything.
            return

        self._img[self._visual_pixel_map_y, self._visual_pixel_map_x] = (
            current_data[b"detector_data"].ravel().astype(self._img.dtype)
        )
        QtGui.QApplication.processEvents()
        self._image_view.setImage(
            self._img.T, autoLevels=False, autoRange=False, autoHistogramRange=False
        )

        QtGui.QApplication.processEvents()
        peak_x_list = []
        peak_y_list = []
        for peak_fs, peak_ss in zip(
            current_data[b"peak_list"][b"fs"], current_data[b"peak_list"][b"ss"]
        ):
            peak_index_in_slab = int(round(peak_ss)) * current_data[
                b"native_data_shape"
            ][1] + int(round(peak_fs))
            peak_x_list.append(self._visual_pixel_map_x[peak_index_in_slab])
            peak_y_list.append(self._visual_pixel_map_y[peak_index_in_slab])
        QtGui.QApplication.processEvents()
        self._peak_canvas.setData(
            x=peak_x_list,
            y=peak_y_list,
            symbol="o",
            size=[5] * len(current_data[b"peak_list"][b"intensity"]),
            brush=(255, 255, 255, 0),
            pen=self._ring_pen,
            pxMode=False,
        )

    def _back_button_clicked(self):
        # Type () -> None
        # Manages clicks on the 'back' button.
        self._stop_stream()
        if self._current_frame_index > 0:
            self._current_frame_index -= 1
        print("Showing frame {} in the buffer".format(self._current_frame_index))
        self._update_image()

    def _forward_button_clicked(self):
        # Type () -> None
        # Manages clicks on the 'forward' button.
        self._stop_stream()
        if (self._current_frame_index + 1) < len(self._frame_list):
            self._current_frame_index += 1
        print("Showing frame {} in the buffer".format(self._current_frame_index))
        self._update_image()

    def _stop_stream(self):
        # Type () -> None
        # Disconnects from the OnDA monitor and stops receiving data.
        if self.listening:
            self._play_pause_button.setText("Play")
            self.stop_listening()

    def _start_stream(self):
        # Type () -> None
        # Connects to the the OnDA monitor and starts receiving data.
        if not self.listening:
            self._play_pause_button.setText("Pause")
            self.start_listening()

    def _play_pause_button_clicked(self):
        # Type () -> None
        # Manages clicks on the 'play/pause' button.
        if self.listening:
            self._stop_stream()
        else:
            self._start_stream()


@click.command()
@click.argument("geometry_file", type=click.Path())
@click.argument("hostname", type=str, required=False)
@click.argument("port", type=int, required=False)
def main(geometry_file, hostname, port):
    # type: (Dict[str, Any], str, int) -> None
    """
    OnDA frame viewer for crystallography. This program must connect to a running OnDA
    monitor for crystallography. If the monitor broadcasts detector frame data, this
    viewer will display it. The viewer will also show, overlayed on the frame data,
    any found Bragg peak. The data stream from the monitor can also be temporarily
    paused, and any of the last 10 received detector frames can be recalled for
    inspection.

    GEOMETRY_FILE: the relative or absolute path to a file containing the detector
    geometry information (in CrystFEL format) to be used for visualization.

    HOSTNAME: the hostname where the OnDA monitor is broadcasting data. Optional: if
    not provided, it defaults to localhost (127.0.0.1).

    PORT: the port on HOSTNAME where the OnDA monitor is broacating data. Optional: if
    not provided, it defaults to 12321.
    """
    if hostname is None:
        hostname = "127.0.0.1"
    if port is None:
        port = 12321
    geometry = cfel_crystfel.load_crystfel_geometry(geometry_file)
    app = QtGui.QApplication(sys.argv)
    _ = CrystallographyFrameViewer(geometry, hostname, port)
    sys.exit(app.exec_())
