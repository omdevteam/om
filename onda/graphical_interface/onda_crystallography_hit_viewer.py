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
HitViewer for OnDA Crystallography.

This module contains the implementation of a Hit Viewer for OnDA
Crystallography.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import collections
import copy
import signal
import sys

import numpy
import pyqtgraph

from onda.cfelpyutils import crystfel_utils, geometry_utils
from onda.graphical_interface import gui

try:
    from PyQt5 import QtGui
except ImportError:
    from PyQt4 import QtGui


class CrystallographyHitViewer(gui.OndaGui):
    """
    Hit Viewer for OnDA Crystallography.

    A Hit Viewer for OnDA Crystallography. Receive data sent by the
    OnDA monitor when they are tagged with the 'ondarawdata' tag and
    display the received detector frames along with the detected peaks.
    """
    def __init__(self,
                 geometry,
                 pub_hostname,
                 pub_port):
        """
        Initialize the CrystallographyHitViewer class.

        Args:

            geometry (Dict): a dictionary containing CrystFEL geometry
                information (as returned by the
                `:obj:onda.cfelpyutils.crystfel_utils.load_crystfel_geometry`
                function.

            pub_hostname (str): hostname or IP address of the host
                where OnDA is running.

            pub_hostname (int): port of the OnDA monitor's PUB socket.
        """
        super(CrystallographyHitViewer, self).__init__(
            pub_hostname=pub_hostname,
            pub_port=pub_port,
            gui_update_func=self._update_image,
            subscription_string=u'ondarawdata',
        )

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

        # Create the array that will store the frame to be displayed.
        # Fill it with zeros to have something to display before the
        # first data comes.
        self._img = numpy.zeros(
            shape=self._img_shape,
            dtype=numpy.float
        )

        # Initialize the buffer that will store the lastest received
        # frames, and set the current frame index to the last frame in
        # the buffer.
        self._frame_list = collections.deque(maxlen=20)
        self._current_frame_index = -1

        # Initialize the pen and the canvas used to draw the peaks.
        self._ring_pen = pyqtgraph.mkPen('r', width=2)
        self._peak_canvas = pyqtgraph.ScatterPlotItem()

        # Initialize the image view widget that will display the
        # detector image.
        self._image_view = pyqtgraph.ImageView()
        self._image_view.ui.menuBtn.hide()
        self._image_view.ui.roiBtn.hide()
        self._image_wiew.getView().addItem(self._peak_canvas)

        # Initialize the 'forward', 'back' and 'play/pause' buttons.
        self._back_button = QtGui.QPushButton()
        self._back_button.setText("Back")

        self._forward_button = QtGui.QPushButton()
        self._forward_button.setText("Forward")

        self._play_pause_button = QtGui.QPushButton()
        self._play_pause_button.setText("Pause")

        self._back_button.clicked.connect(
            self._back_button_clicked
        )
        self._forward_button.clicked.connect(
            self._forward_button_clicked
        )
        self._play_pause_button.clicked.connect(
            self._play_pause_button_clicked
        )

        # Initialize and fill the layouts.
        self._horizontal_layout = QtGui.QHBoxLayout()
        self._horizontal_layout.addWidget(self._back_button)
        self._horizontal_layout.addWidget(self._forward_button)
        self._horizontal_layout.addWidget(self._play_pause_button)
        self._vertical_layout = QtGui.QVBoxLayout()
        self._vertical_layout.addWidget(self._image_view)
        self._vertical_layout.addLayout(self._horizontal_layout)

        # Initialize the central widget for the main window.
        self._central_widget = QtGui.QWidget()
        self._central_widget.setLayout(self._vertical_layout)
        self.setCentralWidget(self._central_widget)

        self.show()

    def _update_image(self):
        # Update the frame image shown by the hit viewer.

        if self.data:

            # Check if data has been received. If new data has been
            # received, append it to the frame buffer and reset the
            # 'data' attribute. In this way, one can check if data has
            # been received simply by checking if the 'data' attribute
            # is not None.
            self._frame_list.append(copy.deepcopy(self.data))
            self.data = None
            self._current_frame_index = len(self._frame_list)-1

        try:
            data = self._frame_list[self._current_frame_index]
        except IndexError:
            # If the framebuffer is empty, return without drawing
            # anything.
            return

        self._img[
            self._pixel_map_y,
            self._pixel_map_x
        ] = data['detector_data'].ravel().astype(self._img.dtype)

        QtGui.QApplication.processEvents()

        self._image_view.setImage(
            self._img,
            autoLevels=False,
            autoRange=False,
            autoHistogramRange=False
        )

        QtGui.QApplication.processEvents()

        # Draw the detected peaks over the displayed frame.
        peak_x_list = []
        peak_y_list = []
        for peak_fs, peak_ss in zip(
                data['peak_list'].fs,
                data['peak_list'].ss,
        ):

            # Compute the array index corresponding to the peak
            # location.
            peak_index_in_slab = (
                int(round(peak_ss)) *
                self._local_data['detector_data'][1] +
                int(round(peak_fs))
            )

            # Add the coordinates of the peak to the lists of peaks to
            # display, mapping the coordinates of the peak to the
            # displayed image according to the pixel maps.
            peak_x_list.append(self._pixel_maps.x[peak_index_in_slab])
            peak_y_list.append(self._pixel_maps.y[peak_index_in_slab])

        QtGui.QApplication.processEvents()

        self._peak_canvas.setData(
            x=peak_x_list,
            y=peak_y_list,
            symbol='o',
            size=[5] * len(data['peak_list'].intensity),
            brush=(255, 255, 255, 0),
            pen=self._ring_pen,
            pxMode=False
        )

    def _back_button_clicked(self):
        # Manage clicks on the 'back' button.

        self._stop_stream()
        if self._current_frame_index > 0:
            self._current_frame_index -= 1
        print("Frame {} in buffer".format(self._current_frame_index))
        self._update_image()

    def _forward_button_clicked(self):
        # Manage clicks on the 'forward' button.

        self._stop_stream()
        if (self._current_frame_index + 1) < len(self._frame_list):
            self._current_frame_index += 1
        print("Frame {} in buffer".format(self._current_frame_index))
        self._update_image()

    def _stop_stream(self):
        # Stop reading the data stream.

        if self.listening:
            self._play_pause_button.setText('Play')
            self.stop_listening()

    def _start_stream(self):
        # Start reading the data stream.

        if not self.listening:
            self._play_pause_button.setText('Pause')
            self.start_listening()

    def _play_pause_button_clicked(self):
        # Manage clicks in the 'play/pause' button.

        if self.listening:
            self._stop_stream()
        else:
            self._start_stream()


def main():
    """
    Start the hit viewer for OnDA Fibers,

    Initialize and start the hit viewer for OnDA Fibers. Manage command
    line arguments, load the geometry and instantiate the graphical
    interface.
    """
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QtGui.QApplication(sys.argv)
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
            "Usage: fibers_hit_viewer.py geometry_filename "
            "<listening ip> <listening port>"
        )
        sys.exit()

    geometry = crystfel_utils.load_crystfel_geometry(geom_filename)

    app = QtGui.QApplication(sys.argv)
    _ = CrystallographyHitViewer(geometry, rec_ip, rec_port)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
