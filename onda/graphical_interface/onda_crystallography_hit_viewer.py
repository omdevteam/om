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
Hit Viewer for OnDA Fibers.

Exports:

    Classes:

        CrystallographyHitViewer: a class implementing a hit viewer for
            OnDA Crystallography.
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

    A simple hit viewer for OnDA Fibers. Just displays on the screen
    the detector frames that it receives from the OnDA monitor, along
    with the peaks detected by the OnDA monitor. Receives data sent by
    the OnDA monitor when they are tagged with the 'ondarawdata' tag.
    """
    def __init__(self,
                 geometry,
                 pub_hostname,
                 pub_port):
        """
        Initialize the CrystallographyHitViewer class.

        Args:

            geometry (Dict): a CrystFEL geometry object.

            pub_hostname (str): hostname or IP address of the host
                where OnDA is running.

            pub_hostname (int): port of the OnDA monitor's PUB socket.
        """
        # Call the parent's constructor.
        super(CrystallographyHitViewer, self).__init__(
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

        # Initialize the pen and the canvas used to visualize the
        # peaks.
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

        # If data has been received, move them to a new attribute and
        # reset the 'data' attribute. Do this so that you know when new
        # data has been received simply by checking if the 'data'
        # attribute is not an empty dictionary. If no new data has been
        # received, just return without redrawing the plots.
        if self.data:
            self._frame_list.append(copy.deepcopy(self.data))
            self.data = None
            self._current_frame_index = len(self._frame_list)-1

        try:
            data = self._frame_list[self._current_frame_index]
        except IndexError:
            # The frame list is empty! Return without drawing anything.
            return

        # Map the received data to the displayed array, then update
        # the displayed array.
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
                data['peak_list'].ss
        ):
            peak_in_slab = (
                int(round(peak_ss)) * data['raw_data'].shape[1] +
                int(round(peak_fs))
            )
            peak_x_list.append(self._pixel_maps.x[peak_in_slab])
            peak_y_list.append(self._pixel_maps.y[peak_in_slab])

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

        # If you are not at the end of the frame buffer, move to the
        # next buffer position. Otherwide, do nothing.
        if (self._current_frame_index + 1) < len(self._frame_list):
            self._current_frame_index += 1
        print("Frame {} in buffer".format(self._current_frame_index))
        self._update_image()

    def _stop_stream(self):
        # Stop the viewer from reading the data stream.

        if self.listening:
            # Change the label of the play/pause button.
            self._play_pause_button.setText('Play')
            self.stop_listening()

    def _start_stream(self):
        # Start reading the data stream.

        if not self.listening:
            # Change the label of the 'play/pause' button.
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
    # Catch signals.
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Manage command line arguments.
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

    # Load the geometry from file.
    geometry = crystfel_utils.load_crystfel_geometry(geom_filename)

    # Instantiate the Qt application.
    app = QtGui.QApplication(sys.argv)
    _ = CrystallographyHitViewer(geometry, rec_ip, rec_port)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
