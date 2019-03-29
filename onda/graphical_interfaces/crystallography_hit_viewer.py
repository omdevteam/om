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
# Copyright 2014-2018 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Hit Viewer for OnDA Crystallography.
"""
from __future__ import absolute_import, division, print_function

import collections
import copy
import signal
import sys

import numpy
import pyqtgraph
from cfelpyutils import crystfel_utils, geometry_utils

from onda.utils import gui

try:
    from PyQt5 import QtGui
except ImportError:
    from PyQt4 import QtGui


class CrystallographyHitViewer(gui.OndaGui):
    """
    Hit Viewer for OnDA Crystallography.

    This GUI receives data sent by the OnDA monitor when they are tagged with the
    'ondarawdata' tag and displays the received detector frames along with the
    detected peaks. It is also possible to stop the stream and move back and forth
    between the last received frames.
    """

    def __init__(self, geometry, pub_hostname, pub_port):
        """
        Initializes the CrystallographyHitView class.

        Args:

            geometry (Dict): a dictionary containing CrystFEL geometry information (as
                returned by the
                :obj:`~onda.cfelpyutils.crystfel_utils.load_crystfel_geometry`
                function).

            pub_hostname (str): hostname or IP address of the host where OnDA is
                running.

            pub_hostname (int): port of the OnDA monitor's PUB socket.
        """
        super(CrystallographyHitViewer, self).__init__(
            pub_hostname=pub_hostname,
            pub_port=pub_port,
            gui_update_func=self._update_image,
            subscription_string="ondaframedata",
        )

        # The following information will be used later to create the arrays that will
        # store the assembled detector images.
        pixel_maps = geometry_utils.compute_pix_maps(geometry)
        self._img_shape = geometry_utils.compute_min_array_size(pixel_maps)
        self._img_center_x = int(self._img_shape[1] / 2)
        self._img_center_y = int(self._img_shape[0] / 2)

        visual_pixel_map = geometry_utils.compute_visualization_pix_maps(geometry)
        self._visual_pixel_map_x = visual_pixel_map.x.flatten()
        self._visual_pixel_map_y = visual_pixel_map.y.flatten()

        # Creates the array that will store the frame to be displayed. Fills it with
        # zeros to have something to display before the first data comes.
        self._img = numpy.zeros(shape=self._img_shape, dtype=numpy.float)

        # Initializes the buffer that will store the lastest received frames, and sets
        # the current frame index to the last frame in the buffer.
        self._frame_list = collections.deque(maxlen=20)
        self._current_frame_index = -1

        # Initializes the pen and the canvas used to draw the peaks.
        self._ring_pen = pyqtgraph.mkPen("r", width=2)
        self._peak_canvas = pyqtgraph.ScatterPlotItem()

        # Initializes the widget that will display the detector image.
        self._image_view = pyqtgraph.ImageView()
        self._image_view.ui.menuBtn.hide()
        self._image_view.ui.roiBtn.hide()
        self._image_view.getView().addItem(self._peak_canvas)

        # Initializes the 'forward', 'back' and 'play/pause' buttons.
        self._back_button = QtGui.QPushButton()
        self._back_button.setText("Back")

        self._forward_button = QtGui.QPushButton()
        self._forward_button.setText("Forward")

        self._play_pause_button = QtGui.QPushButton()
        self._play_pause_button.setText("Pause")

        self._back_button.clicked.connect(self._back_button_clicked)
        self._forward_button.clicked.connect(self._forward_button_clicked)
        self._play_pause_button.clicked.connect(self._play_pause_button_clicked)

        # Initializes and fills the layouts.
        self._horizontal_layout = QtGui.QHBoxLayout()
        self._horizontal_layout.addWidget(self._back_button)
        self._horizontal_layout.addWidget(self._forward_button)
        self._horizontal_layout.addWidget(self._play_pause_button)
        self._vertical_layout = QtGui.QVBoxLayout()
        self._vertical_layout.addWidget(self._image_view)
        self._vertical_layout.addLayout(self._horizontal_layout)

        # Initializes the central widget for the main window.
        self._central_widget = QtGui.QWidget()
        self._central_widget.setLayout(self._vertical_layout)
        self.setCentralWidget(self._central_widget)

        self.show()

    def _update_image(self):
        # Updates the frame image shown by the hit viewer.

        if self.data:
            # Checks if data has been received. If new data has been received, appends
            # it to the frame buffer. Then resets the 'data' attribute to None. In
            # this way, one can check if data has been received simply by checking if
            # the 'data' attribute is not None.
            self._frame_list.append(copy.deepcopy(self.data[0]))
            self.data = None
            self._current_frame_index = len(self._frame_list) - 1

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

        # Draws the detected peaks over the displayed frame.
        peak_x_list = []
        peak_y_list = []
        for peak_fs, peak_ss in zip(
            current_data[b"peak_list"][b"fs"], current_data[b"peak_list"][b"ss"]
        ):

            # Computes the array index corresponding to the peak location.
            peak_index_in_slab = int(round(peak_ss)) * current_data[
                b"native_data_shape"
            ][1] + int(round(peak_fs))

            # Adds the coordinates of the peak to the lists of peaks to display,
            # mapping the coordinates of the peak to the displayed image according
            # to the pixel maps.
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
        # Manages clicks on the 'back' button.

        self._stop_stream()
        if self._current_frame_index > 0:
            self._current_frame_index -= 1
        print("Showing frame {} in the buffer".format(self._current_frame_index))
        self._update_image()

    def _forward_button_clicked(self):
        # Manages clicks on the 'forward' button.

        self._stop_stream()
        if (self._current_frame_index + 1) < len(self._frame_list):
            self._current_frame_index += 1
        print("Showing frame {} in the buffer".format(self._current_frame_index))
        self._update_image()

    def _stop_stream(self):
        # Stops reading the data stream.

        if self.listening:
            self._play_pause_button.setText("Play")
            self.stop_listening()

    def _start_stream(self):
        # Starts reading the data stream.

        if not self.listening:
            self._play_pause_button.setText("Pause")
            self.start_listening()

    def _play_pause_button_clicked(self):
        # Manages clicks in the 'play/pause' button.

        if self.listening:
            self._stop_stream()
        else:
            self._start_stream()


def main():
    """
    Starts the hit viewer for OnDA Crystallography.

    Initializes and starts the Hit Viewer for OnDA Crystallography.
    Manages command line arguments, loads the geometry and instantiates
    the graphical interface.
    """
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    if len(sys.argv) == 2:
        geom_filename = sys.argv[1]
        rec_ip = "127.0.0.1"
        rec_port = 12321
    elif len(sys.argv) == 4:
        geom_filename = sys.argv[1]
        rec_ip = sys.argv[2]
        rec_port = int(sys.argv[3])
    else:
        print(
            "Usage: fibers_hit_viewer.py geometry_filename <listening ip> "
            "<listening port>"
        )
        sys.exit()

    geometry = crystfel_utils.load_crystfel_geometry(geom_filename)

    app = QtGui.QApplication(sys.argv)
    _ = CrystallographyHitViewer(geometry, rec_ip, rec_port)
    sys.exit(app.exec_())
