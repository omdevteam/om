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


class FibersHitViewer(gui.OndaGui):

    def __init__(self,
                 geometry,
                 pub_hostname,
                 pub_port):

        # Call the parent's constructor.
        super(FibersHitViewer, self).__init__(
            pub_hostname=pub_hostname,
            pub_port=pub_port,
            gui_update_func=self._update_image,
            subscription_string=u'ondarawdata',
        )

        # Initialize pixel maps for visualization and create the array
        # that will hold the detector image to be displayed.
        pixel_maps = geometry_utils.compute_visualization_pix_maps(
            geometry
        )
        self._pixel_map_x = pixel_maps.x.ravel()
        self._pixel_map_y = pixel_maps.y.ravel()

        self._img_shape = geometry_utils.compute_min_array_size(
            pixel_maps
        )

        self._img = numpy.zeros(
            shape=self._img_shape,
            dtype=numpy.float
        )

        # Initialize the buffer that will store the last frames
        # received and set the current image to the last in the list.
        self._frame_list = collections.deque(maxlen=20)
        self._current_frame_index = -1

        # Initialize the image view widget that will display the
        # detector image.
        self._image_view = pyqtgraph.ImageView()
        self._image_view.ui.menuBtn.hide()
        self._image_view.ui.roiBtn.hide()

        # Initialize the 'forward', 'back' and 'play/pause' buttons.
        self._back_button = QtGui.QPushButton()
        self._back_button.setText("Back")

        self._forward_button = QtGui.QPushButton()
        self._forward_button.setText("Forward")

        self._play_pause_button = QtGui.QPushButton()
        self._play_pause_button.setText("Pause")

        self._horizontal_layout = QtGui.QHBoxLayout()
        self._horizontal_layout.addWidget(self._back_button)
        self._horizontal_layout.addWidget(self._forward_button)
        self._horizontal_layout.addWidget(self._play_pause_button)

        self._back_button.clicked.connect(
            self._back_button_clicked
        )
        self._forward_button.clicked.connect(
            self._forward_button_clicked
        )
        self._play_pause_button.clicked.connect(
            self._play_pause_button_clicked
        )

        # Assemble the image view and the buttons in a vertical layout.
        self._vertical_layout = QtGui.QVBoxLayout()
        self._vertical_layout.addWidget(self._image_view)
        self._vertical_layout.addLayout(self._horizontal_layout)

        # Initialize the central widget for the main window.
        self._central_widget = QtGui.QWidget()
        self._central_widget.setLayout(self._vertical_layout)
        self.setCentralWidget(self._central_widget)

        self.show()

    def _update_image(self):
        if self.data:
            self._frame_list.append(copy.deepcopy(self.data))
            self.data = None
            self._current_frame_index = len(self._frame_list)-1

        data = self._frame_list[self._current_frame_index]

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

    def _back_button_clicked(self):
        self._stop_stream()
        if self._current_frame_index > 0:
            self._current_frame_index -= 1
        print("Frame {} in buffer".format(self._current_frame_index))
        self._update_image()

    def _forward_button_clicked(self):
        self._stop_stream()
        if (self._current_frame_index + 1) < len(self._frame_list):
            self._current_frame_index += 1
        print("Frame {} in buffer".format(self._current_frame_index))
        self._update_image()

    def _stop_stream(self):
        if self.listening:
            self._play_pause_button.setText('Play')
            self.stop_listening()

    def _start_stream(self):
        if not self.listening:
            self._play_pause_button.setText('Pause')
            self.start_listening()

    def _play_pause_button_clicked(self):
        if self.listening:
            self._stop_stream()
        else:
            self._start_stream()


def main():
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
    _ = FibersHitViewer(geometry, rec_ip, rec_port)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
