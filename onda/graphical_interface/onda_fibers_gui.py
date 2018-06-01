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
GUI for OnDA Crystallography.

Exports:

    Classes:

        FibersGui: a class implementing the OnDA Fibers GUI.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import collections
import signal
import sys

import pyqtgraph as pyqtgraph

from onda.graphical_interface import gui

try:
    from PyQt5 import QtCore, QtGui
except ImportError:
    from PyQt4 import QtCore, QtGui


class FibersGui(gui.OndaGui):
    """
    GUI for OnDA Fibers.

    A GUI for OnDA Fibers. Displays real-time hit rate information plus
    information on the total intensity recorded on the x-ray detector.
    Receives data sent by the OnDA monitor when they are tagged with
    the 'ondadata' tag.
    """

    def __init__(self,
                 pub_hostname,
                 pub_port):
        """
        Initialize the OnDAFIbers class.

        Args:

            pub_hostname (str): hostname or IP address of the host
                where OnDA is running.

            pub_hostname (int): port of the OnDA monitor's PUB socket.
        """
        # Call the parent's constructor.
        super(FibersGui, self).__init__(
            pub_hostname=pub_hostname,
            pub_port=pub_port,
            gui_update_func=self._update_plots,
            subscription_string=u'ondadata',
        )

        # Initialize the dictionary with the data to be displayed with
        # default values.
        self._local_data = {
            'accumulated_sum_detector': [],
            'accumulated_hit_rate': []
        }

        # Create the attributes that will store the detector intensity
        # and hit rate history
        self._hit_rate_history = collections.deque(
            10000 * [0.0],
            maxlen=10000
        )

        self._sum_detector_history = collections.deque(
            10000 * [0.0],
            maxlen=10000
        )

        # Set the PyQtGraph background color.
        pyqtgraph.setConfigOption('background', 0.2)

        # Create an attribute that stores the vertical lines that the
        # users can put on the plot widgets.
        self._vertical_lines = []

        # Initialize the hit rate plot widget
        self._hit_rate_plot_widget = pyqtgraph.PlotWidget()
        self._hit_rate_plot_widget.setTitle(
            'Hit Rate vs. Events'
        )

        self._hit_rate_plot_widget.setLabel(
            axis='bottom',
            text='Events'
        )

        self._hit_rate_plot_widget.setLabel(
            axis='left',
            text='Hit Rate'
        )

        self._hit_rate_plot_widget.showGrid(
            x=True,
            y=True
        )

        self._hit_rate_plot_widget.setYRange(0, 1.0)
        self._hit_rate_plot = self._hit_rate_plot_widget.plot(
            self._hit_rate_history
        )

        # Initialize the detector intensity plot widget
        self._sum_detector_plot_widget = pyqtgraph.PlotWidget()
        self._sum_detector_plot_widget.setTitle(
            'Intensity On Detector vs. Events'
        )

        self._sum_detector_plot_widget.setLabel(
            axis='bottom',
            text='Events'
        )

        self._sum_detector_plot_widget.setLabel(
            axis='left',
            text='Num pixels above threshold'
        )

        self._sum_detector_plot_widget.showGrid(
            x=True,
            y=True

        )
        self._sum_detector_plot_widget.setXLink(
            self._hit_rate_plot_widget
        )

        self._sum_detector_plot = self._sum_detector_plot_widget.plot(
            self._sum_detector_history
        )

        # Initialize the 'Reset Plots' button.
        self._reset_plots_button = QtGui.QPushButton()
        self._reset_plots_button.setText("Reset Plots")

        # Connect signals for the 'peaks' and 'plots' buttons.
        self._reset_plots_button.clicked.connect(self._reset_plots)

        # Initialize the 'mouse clicked' signal proxy to limit the
        # accumulation of mouse events.
        self._mouse_clicked_signal_proxy = pyqtgraph.SignalProxy(
            self._hit_rate_plot_widget.scene().sigMouseClicked,
            rateLimit=60,
            slot=self._mouse_clicked
        )

        # Initialize and fill the layouts.
        self._vertical_layout = QtGui.QVBoxLayout()
        self._vertical_layout.addWidget(self._hit_rate_plot_widget)
        self._vertical_layout.addWidget(self._sum_detector_plot_widget)
        self._vertical_layout.addWidget(self._reset_plots_button)

        # Initialize the central widget for the main window.
        self._central_widget = QtGui.QWidget()
        self._central_widget.setLayout(self._vertical_layout)
        self.setCentralWidget(self._central_widget)

        self.show()

    def _mouse_clicked(self,
                       mouse_evt):
        # Manage mouse events.

        # Check if the click of the mouse happens in the hit rate plot
        # widget
        mouse_pos_in_scene = mouse_evt[0].scenePos()
        if (
                self
                ._hit_rate_plot_widget
                .plotItem.sceneBoundingRect()
                .contains(mouse_pos_in_scene)
        ):
            if mouse_evt[0].button() == QtCore.Qt.MiddleButton:
                # If the mouse click takes place in the hit rate plot
                # widget and the middle button was clicked, check if a
                # vertical line exists already in the vicinity of the
                # click. If it does, remove it. If it does not, add the
                # vertical line to the plot in the place where the user
                # clicked.
                mouse_x_pos_in_data = (
                    self
                    ._hit_rate_plot_widget
                    .plotItem
                    .vb
                    .mapSceneToView(mouse_pos_in_scene)
                    .x()
                )
                new_vertical_lines = []
                for vert_line in self._vertical_lines:
                    if abs(vert_line.getPos()[0] - mouse_x_pos_in_data) < 5:
                        self._hit_rate_plot_widget.removeItem(vert_line)
                    else:
                        new_vertical_lines.append(vert_line)

                if len(new_vertical_lines) != len(self._vertical_lines):
                    self._vertical_lines = new_vertical_lines
                    return

                vertical_line = pyqtgraph.InfiniteLine(
                    pos=mouse_x_pos_in_data,
                    angle=90,
                    movable=False
                )
                self._vertical_lines.append(vertical_line)
                self._hit_rate_plot_widget.addItem(  # pylint: disable=E1123
                    item=vertical_line,
                    ignoreBounds=True
                )

    def _reset_plots(self):
        # Reset the plots.

        # Reset the hit and saturation data history and plot widgets.
        self._hit_rate_history = collections.deque(
            10000 * [0.0],
            maxlen=10000
        )
        self._sum_detector_history = collections.deque(
            10000 * [0.0],
            maxlen=10000
        )
        self._hitrate_plot.setData(self._hitrate_history)
        self._sum_detector_plot.setData(self._satrate_history)

    def _update_plots(self):
        # Update the elements of the GUI.

        # If data has been received, move them to a new attribute and
        # reset the 'data' attribute. Do this so that you know when new
        # data has been received simply by checking if the 'data'
        # attribute is not an empty dictionary. If no new data has been
        # received, just return without redrawing the plots.
        if self.data:
            self._local_data = self.data
            self.data = None
        else:
            return

        QtGui.QApplication.processEvents()

        # Update the hit rate and detector intensity histories and
        # plots.
        for hit_rate_entry in self._local_data['accumulated_hit_rate']:
            self._hit_rate_history.append(hit_rate_entry)
        for sum_detector_entry in self._local_data['accumulated_sum_detector']:
            self._sum_detector_history.append(sum_detector_entry)
        self._hit_rate_plot.setData(self._hit_rate_history)
        self._sum_detector_plot.setData(self._sum_detector_history)

        QtGui.QApplication.processEvents()

        # Draw the vertical lines on the hit rate plot widget.
        new_vertical_lines = []
        for vline in self._vertical_lines:
            line_pos = vline.getPos()[0]
            line_pos -= 1
            if line_pos > 0.0:
                vline.setPos(line_pos)
                new_vertical_lines.append(vline)
            else:
                self._ui.hit_rate_plot_widget.removeItem(vline)

        self._vertical_lines = new_vertical_lines


def main():
    """
    Start the GUI for OnDA Fibers,

    Initialize and start the GUI for OnDA Fibers. Manage command line
    arguments and instantiate the graphical interface.
    """
    # Catch signals.
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Manage command line arguments.
    if len(sys.argv) == 1:
        rec_ip = '127.0.0.1'
        rec_port = 12321
    elif len(sys.argv) == 3:
        rec_ip = sys.argv[1]
        rec_port = int(sys.argv[2])
    else:
        print(
            "Usage: onda-fibers-gui.py <listening ip> <listening port>"
        )
        sys.exit()

    # Instantiate the Qt application.
    app = QtGui.QApplication(sys.argv)
    _ = FibersGui(rec_ip, rec_port)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
