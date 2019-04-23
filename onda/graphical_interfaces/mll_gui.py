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
GUI for OnDA Crystallography.
"""
from __future__ import absolute_import, division, print_function

import signal
import sys

import pyqtgraph

from onda.utils import gui

try:
    from PyQt5 import QtGui
except ImportError:
    from PyQt4 import QtGui


class MllGui(gui.OndaGui):
    """
    GUI for OnDA crystallography.

    This GUI receives data sent by the OnDA monitor when they are tagged with the
    'ondadata' tag. It displays the real time hit and saturation rate information,
    plus a virtual powder-pattern-style plot of the processed data.
    """

    def __init__(self, pub_hostname, pub_port):
        """
        Initializes the Crystallography GUI class.

        Args:

            geometry (Dict): a dictionary containing CrystFEL geometry information (as
                returned by the
                :obj:`cfelpyutils.crystfel_utils.load_crystfel_geometry` function)
                from the :obj:`cfelpyutils` module.

            pub_hostname (str): hostname or IP address of the machine where the OnDA
                monitor is running.

            pub_port (int): port on which the the OnDA monitor is broadcasting
                information.
        """
        super(MllGui, self).__init__(
            pub_hostname=pub_hostname,
            pub_port=pub_port,
            gui_update_func=self._update_image,
            subscription_string="ondadata",
        )

        # Initializes the local data dictionary with 'null' values.
        self._local_data = {
            "stxm": None,
            "dpc": None,
            "ss_integr": None,
            "fs_integr": None,
            "ss_start": None,
            "fs_start": None,
            "ss_end": None,
            "fs_end": None,
            "timestamp": None,
        }

        self._curr_run_num = 0
        self._curr_type = 0
        self._img = None
        self._pos = None
        self._scale = None

        # Initializes the widget that will display the image data.
        self._image_view = pyqtgraph.ImageView(view=pyqtgraph.PlotItem())
        self._image_view.ui.menuBtn.hide()
        self._image_view.ui.roiBtn.hide()
        self._image_view.scene.sigMouseClicked.connect(self._mouse_clicked)
        self._bot_axis = self._image_view.view.getAxis("bottom")
        self._lef_axis = self._image_view.view.getAxis("left")

        # Initializes the 'STXM' and 'DPC' buttons.
        self._stxm_button = QtGui.QPushButton()
        self._stxm_button.setText("STXM")
        self._stxm_button.setEnabled(False)
        self._stxm_button.clicked.connect(self._draw_image)
        self._stxm_button.setCheckable(True)
        self._stxm_button.setAutoExclusive(True)

        self._dpc_button = QtGui.QPushButton()
        self._dpc_button.setText("DPC")
        self._dpc_button.setEnabled(False)
        self._dpc_button.clicked.connect(self._draw_image)
        self._dpc_button.setCheckable(True)
        self._dpc_button.setAutoExclusive(True)

        self._stxm_dpc_button_group = QtGui.QButtonGroup()
        self._stxm_dpc_button_group.addButton(self._stxm_button)
        self._stxm_dpc_button_group.addButton(self._dpc_button)

        # Initializes the 'SS Integration' and 'FS Integration' buttons.
        self._ss_integr_button = QtGui.QPushButton()
        self._ss_integr_button.setText("SS Integration")
        self._ss_integr_button.setEnabled(False)
        self._ss_integr_button.clicked.connect(self._draw_image)
        self._ss_integr_button.setCheckable(True)
        self._ss_integr_button.setAutoExclusive(True)

        self._fs_integr_button = QtGui.QPushButton()
        self._fs_integr_button.setText("FS Integration")
        self._fs_integr_button.setEnabled(False)
        self._fs_integr_button.clicked.connect(self._draw_image)
        self._fs_integr_button.setCheckable(True)
        self._fs_integr_button.setAutoExclusive(True)

        self._ss_fs_integr_button_group = QtGui.QButtonGroup()
        self._ss_fs_integr_button_group.addButton(self._ss_integr_button)
        self._ss_fs_integr_button_group.addButton(self._fs_integr_button)

        # Initalizes restore button.
        self._rescale_button = QtGui.QPushButton()
        self._rescale_button.setText("Rescale")
        self._rescale_button.clicked.connect(self._rescale_image)

        # Initializes the 'Last Clicked Position' Label
        self._last_clicked_pos_label = QtGui.QLabel()

        # Initializes and fills the layouts.
        horizontal_layout = QtGui.QHBoxLayout()
        horizontal_layout.addWidget(self._stxm_button)
        horizontal_layout.addWidget(self._dpc_button)
        horizontal_layout.addStretch()
        horizontal_layout.addWidget(self._rescale_button)
        horizontal_layout.addStretch()
        horizontal_layout.addWidget(self._fs_integr_button)
        horizontal_layout.addWidget(self._ss_integr_button)
        vertical_layout = QtGui.QVBoxLayout()
        vertical_layout.addWidget(self._image_view)
        vertical_layout.addLayout(horizontal_layout)
        vertical_layout.addWidget(self._last_clicked_pos_label)

        # Initializes the central widget for the main window.
        self._central_widget = QtGui.QWidget()
        self._central_widget.setLayout(vertical_layout)
        self.setCentralWidget(self._central_widget)

        self.show()

    def _mouse_clicked(self, evt):
        if self._image_view.getView().sceneBoundingRect().contains(evt.scenePos()):
            mouse_point = self._image_view.getView().vb.mapSceneToView(evt.scenePos())
            self._last_clicked_pos_label.setText(
                "Last clicked position:    ss {0:.6f} / fs: {1:.6f}".format(
                    mouse_point.y(), mouse_point.x()
                )
            )

    def _rescale_image(self):
        self._image_view.setLevels(self._img.min(), self._img.max())
        self._draw_image()

    def _draw_image(self):

        if self._curr_type == 2:
            if self._stxm_button.isChecked():
                self._img = self._local_data[b"stxm"]
            else:
                self._img = self._local_data[b"dpc"]

        if self._curr_type == 1:
            if self._ss_integr_button.isChecked():
                self._img = self._local_data[b"ss_integr_image"]
            else:
                self._img = self._local_data[b"fs_integr_image"]
        self._image_view.setImage(
            self._img,
            autoRange=False,
            autoLevels=False,
            pos=self._pos,
            scale=self._scale,
        )

        print(self._img.min(), self._img.max())

        QtGui.QApplication.processEvents()

    def _update_image(self):

        if self.data:
            # Checks if data has been received. If new data has been received, moves
            # them to a new attribute and resets the 'data' attribute. In this way,
            # one can check if data has been received simply by checking if the 'data'
            # attribute is not None.
            self._local_data = self.data[-1]
            self.data = None
        else:
            return

        QtGui.QApplication.processEvents()

        autorange = False

        scan_type = self._local_data[b"scan_type"]

        # DEBUG
        import numpy

        self._local_data[b"dpc"] = 17.0 * numpy.ones_like(self._local_data[b"stxm"])
        #

        if self._local_data[b"num_run"] > self._curr_run_num:

            print("Starting new run.")

            self._bot_axis.setLabel(
                self._local_data[b"fs_name"].strip().decode("utf-8")
            )
            self._curr_run_num = self._local_data[b"num_run"]

            if self._local_data[b"scan_type"] == 2:
                self._lef_axis.setLabel(
                    self._local_data[b"ss_name"].strip().decode("utf-8")
                )
                self._pos = (
                    self._local_data[b"fs_start"],
                    self._local_data[b"ss_start"],
                )
                self._scale = (
                    (self._local_data[b"fs_end"] - self._local_data[b"fs_start"])
                    / (self._local_data[b"fs_steps"]),
                    (self._local_data[b"ss_end"] - self._local_data[b"ss_start"])
                    / (self._local_data[b"ss_steps"]),
                )
            else:
                self._lef_axis.setLabel("")
                self._pos = (self._local_data[b"fs_start"], 0)
                self._scale = (
                    (self._local_data[b"fs_end"] - self._local_data[b"fs_start"])
                    / (self._local_data[b"fs_steps"]),
                    1.0,
                )

            QtGui.QApplication.processEvents()

            if self._scale[1] > self._scale[0]:
                ratio = max(self._scale) / min(self._scale)
            else:
                ratio = min(self._scale) / max(self._scale)

            self._image_view.getView().setAspectLocked(True, ratio=ratio)

            QtGui.QApplication.processEvents()

            self._last_clicked_pos_label.setText(
                "Last clicked position:    ss: - / fs: -"
            )

            autorange = True

        if scan_type != self._curr_type:

            if scan_type == 2:
                self._stxm_button.setEnabled(True)
                self._stxm_button.setChecked(True)
                self._dpc_button.setEnabled(True)
                self._ss_integr_button.setEnabled(False)
                self._fs_integr_button.setEnabled(False)

            QtGui.QApplication.processEvents()

            if scan_type == 1:
                self._stxm_button.setEnabled(False)
                self._dpc_button.setEnabled(False)
                self._ss_integr_button.setEnabled(True)
                self._ss_integr_button.setChecked(True)
                self._fs_integr_button.setEnabled(True)

            self._curr_type = scan_type

        QtGui.QApplication.processEvents()

        self._draw_image()
        if autorange:
            self._image_view.autoRange()


def main():
    """
    Starts the GUI for OnDA MLL,

    Initializes and starts the GUI for OnDA MLL. Manages command line arguments, loads
    the geometry and instantiates the graphical interface.
    """
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    if len(sys.argv) == 1:
        rec_ip = "127.0.0.1"
        rec_port = 12321
    elif len(sys.argv) == 3:
        rec_ip = sys.argv[1]
        rec_port = int(sys.argv[2])
    else:
        print("Usage: onda-mll-gui.py <listening ip> <listening port>")
        sys.exit()

    app = QtGui.QApplication(sys.argv)
    _ = MllGui(rec_ip, rec_port)
    sys.exit(app.exec_())
