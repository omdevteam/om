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
GUI for OnDA SWAXS.
"""
from __future__ import absolute_import, division, print_function

import collections
import signal
import sys

import pyqtgraph
from cfelpyutils import crystfel_utils, geometry_utils

from onda.utils import gui

try:
    from PyQt5 import QtCore, QtGui
except ImportError:
    from PyQt4 import QtCore, QtGui


class SWAXSGui(gui.OndaGui):
    """
    GUI for OnDA SWAXS.
    """

    def __init__(self,
                 geometry,
                 pub_hostname,
                 pub_port):
        """
        Initializes the SwaxsGui class.
        
        Args:

            geometry (Dict): a dictionary containing CrystFEL geometry
                information (as returned by the
                :obj:`cfelpyutils.crystfel_utils.load_crystfel_geometry`
                function) from the :obj:`cfelpyutils` module.

            pub_hostname (str): hostname or IP address of the machine
                where the OnDA monitor is running.

            pub_port (int): port on which the the OnDA monitor is
                broadcasting information.
        """
        # TODO: GUI description.
        super(SWAXSGui, self).__init__(
            pub_hostname=pub_hostname,
            pub_port=pub_port,
            gui_update_func=self._update_image_and_plots,
            subscription_string=u'ondadata',
        )

        # Initializes the attribute that will store the local data.
        self._local_data = None

        # Computes the pixel maps for visualization.
        pixel_maps = geometry_utils.compute_pix_maps(geometry)

        # The following information will be used later to create the
        # arrays that will store the assembled detector images.
        self._img_shape = geometry_utils.compute_min_array_size(
            pixel_maps
        )
        self._img_center_x = int(self._img_shape[1] / 2)
        self._img_center_y = int(self._img_shape[0] / 2)

        visual_pixel_map = geometry_utils.compute_visualization_pix_maps(
            geometry
        )
        self._visual_pixel_map_x = visual_pixel_map.x.flatten()
        self._visual_pixel_map_y = visual_pixel_map.y.flatten()

        # Tries to extract the coffset and res information from the
        # geometry. The geometry allows these two values to be defined
        # individually for each panel, but the GUI just needs simple
        # values for the whole detector. This code ususe the values
        # from first panel.
        first_panel = list(geometry['panels'].keys())[0]
        try:
            self._coffset = geometry['panels'][first_panel]['coffset']
        except KeyError:
            self._coffset = None

        try:
            self._res = geometry['panels'][first_panel]['res']
        except KeyError:
            self._res = None

        self._q_bins = collections.deque(
            iterable=1000 * [0.0],
            maxlen=1000
        )

        self._unscaled_radial = collections.deque(
            iterable=1000 * [0.0],
            maxlen=1000
        )

        self._radial = collections.deque(
            iterable=1000 * [0.0],
            maxlen=1000
        )

        self._cumulative_pumped = collections.deque(
            iterable=1000 * [0.0],
            maxlen=1000
        )

        self._cumulative_dark = collections.deque(
            iterable=1000 * [0.0],
            maxlen=1000
        )

        self._diff = collections.deque(
            iterable=1000 * [0.0],
            maxlen=1000
        )

        self._recent_radial = collections.deque(
            iterable=1000 * [0.0],
            maxlen=1000
        )

        self._cumulative_radial = collections.deque(
            iterable=1000 * [0.0],
            maxlen=1000
        )

        self._hitrate_history = collections.deque(
            iterable=10000 * [0.0],
            maxlen=10000
        )

        self._pumped_hitrate_history = collections.deque(
            iterable=10000 * [0.0],
            maxlen=10000
        )

        self._dark_hitrate_history = collections.deque(
            iterable=10000 * [0.0],
            maxlen=10000
        )

        self._intensity_sums = collections.deque(
            iterable=10000 * [0.0],
            maxlen=10000
        )

        self._intensity_sum_hist = collections.deque(
            iterable=10000 * [0.0],
            maxlen=10000
        )

        self._intensity_sum_hist_bins = collections.deque(
            iterable=10000 * [0.0],
            maxlen=10000
        )

        self._digitizer_data = collections.deque(
            iterable=10000 * [0.0],
            maxlen=10000
        )

        # Set the PyQtGraph background color.
        pyqtgraph.setConfigOption('background', 1.0)

        # Initialize the radial profile plot widget.
        self._radial_plot_widget = pyqtgraph.PlotWidget()
        self._radial_plot_widget.setTitle(
            'Radial Profile'
        )

        self._radial_plot_widget.setLabel(
            axis='bottom',
            text='Radius (pixels)'
        )

        self._radial_plot_widget.setLabel(
            axis='left',
            text='Intensity (ADUs)'
        )

        self._radial_plot_widget.showGrid(
            x=True,
            y=True
        )

        self._radial_plot_widget.addLegend()

        self._unscaled_radial_plot = self._radial_plot_widget.plot(
            self._q_bins,
            self._unscaled_radial,
            name='Single Unscaled Radial'
        )

        self._radial_plot = self._radial_plot_widget.plot(
            self._q_bins,
            self._radial,
            name='Single Scaled Radial',
            pen=(0, 0, 0, 25),
            symbol='o',
            symbolPen='k',
            symbolBrush='k',
            symbolSize=2
        )

        self._cumulative_pumped_plot = self._radial_plot_widget.plot(
            self._q_bins,
            self._cumulative_pumped,
            name='Cumulative Pumped Radial',
            pen='r',
            symbol='o',
            symbolPen='r',
            symbolBrush='r',
            symbolSize=2
        )

        self._cumulative_dark_plot = self._radial_plot_widget.plot(
            self._q_bins,
            self._cumulative_dark,
            name='Cumulative Dark Radial',
            pen='b',
            symbol='o',
            symbolPen='b',
            symbolBrush='b',
            symbolSize=2
        )

        self._diff_plot = self._radial_plot_widget.plot(
            self._q_bins,
            self._diff,
            name='Single Difference',
            pen=(0, 0, 0, 20)
        )

        self._recent_radial_plot = self._radial_plot_widget.plot(
            self._recent_radial,
            name='Recent Average Difference',
            pen='r'
        )

        self._cumulative_radial_plot = self._radial_plot_widget.plot(
            self._cumulative_radial,
            name='Cumulative Average Difference',
            pen='b'
        )

        # Initialize the hit rate plot widget.
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

        self._hitrate_plot = self._hit_rate_plot_widget.plot(
            self._hitrate_history,
            pen='k'
        )

        self._pumped_hitrate_plot = self._hit_rate_plot_widget.plot(
            self._pumped_hitrate_history,
            pen=[0, 0, 0, 0],
            symbol='o',
            symbolPen='r',
            symbolBrush='r',
            symbolSize=2
        )

        self._dark_hitrate_plot = self._hit_rate_plot_widget.plot(
            self._dark_hitrate_history,
            pen=[0, 0, 0, 0],
            symbol='o',
            symbolPen='b',
            symbolBrush='b',
            symbolSize=2
        )

        # Initialize the intensity sum histogram widget.
        self._intensity_sums_plot_widget = pyqtgraph.PlotWidget()
        self._intensity_sums_plot_widget.setTitle(
            'Total unscaled radial intensity sum histogram'
        )

        self._intensity_sums_plot_widget.setLabel(
            axis='bottom',
            text='Intensity Sum (ADUs)'
        )

        self._intensity_sums_plot_widget.setLabel(
            axis='left',
            text='Counts'
        )

        self._intensity_sums_plot_widget.showGrid(
            x=True,
            y=True
        )

        self._intensity_sums_plot = self._intensity_sums_plot_widget.plot(
            self._intensity_sum_hist_bins,
            self._intensity_sum_hist,
            pen='k',
            symbol='o',
            symbolPen='k',
            symbolBrush='k',
            symbolSize=5
        )

        # Initialize 'reset plots' button.
        self._reset_plots_button = QtGui.QPushButton()
        self._reset_plots_button.setText("Reset Plots")
        self._reset_plots_button.clicked.connect(self._reset_plots)

        # Initialize and fill the layouts.
        horizontal_layout = QtGui.QHBoxLayout()
        horizontal_layout.addWidget(self._reset_plots_button)
        horizontal_layout.addStretch()
        splitter_0 = QtGui.QSplitter()
        splitter_0.addWidget(self._radial_plot_widget)
        splitter_1 = QtGui.QSplitter()
        splitter_1.setOrientation(QtCore.Qt.Vertical)
        splitter_1.addWidget(self._hit_rate_plot_widget)
        splitter_1.addWidget(self._intensity_sums_plot_widget)
        splitter_0.addWidget(splitter_1)
        vertical_layout = QtGui.QVBoxLayout()
        vertical_layout.addWidget(splitter_0)
        vertical_layout.addLayout(horizontal_layout)

        # Initialize the central widget for the main window.
        self._central_widget = QtGui.QWidget()
        self._central_widget.setLayout(vertical_layout)
        self.setCentralWidget(self._central_widget)

        self.show()

    def _reset_plots(self):
        # Reset the plots.
        self._hitrate_history = collections.deque(
            10000 * [0.0],
            maxlen=10000
        )

        self._pumped_hitrate_history = collections.deque(
            10000 * [0.0],
            maxlen=10000
        )

        self._dark_hitrate_history = collections.deque(
            10000 * [0.0],
            maxlen=10000
        )

        self._intensity_sum_hist = collections.deque(
            10000 * [0.0],
            maxlen=10000
        )

        self._radial_plot.setData(self._radial)
        self._diff_plot.setData(self._diff)
        self._cumulative_radial_plot.setData(self._cumulative_radial)
        self._recent_radial_plot.setData(self._recent_radial)
        self._hitrate_plot.setData(self._hitrate_history)
        self._pumped_hitrate_plot.setData(self._pumped_hitrate_history)
        self._dark_hitrate_plot.setData(self._dark_hitrate_history)
        self._intensity_sums_plot.setData(self._intensity_sum_hist)

    def _reset_virt_powder_plot(self):
        return

    def _update_image_and_plots(self):
        # Update all elements in the GUI.

        if self.data:
            # Check if data has been received. If new data has been
            # received, move them to a new attribute and reset the
            # 'data' attribute. In this way, one can check if data has
            # been received simply by checking if the 'data' attribute
            # is not None.
            self._local_data = self.data
            self.data = None
        else:
            return

        last_frame = self._local_data[-1]

        QtGui.QApplication.processEvents()

        # Add data from all frames accumulated in local_data to the
        # plots,but updated the displayed images and plots onley once
        # at the end.
        for frame in self._local_data:
            self._hitrate_history.append(frame[b'hit_rate'])
            phr = frame[b'pumped_hit_rate']
            dhr = frame[b'dark_hit_rate']
            self._pumped_hitrate_history.append(phr)
            self._dark_hitrate_history.append(dhr)

        QtGui.QApplication.processEvents()

        self._q_bins = last_frame[b'q_bins']
        self._unscaled_radial = last_frame[b'unscaled_radial']
        self._radial = last_frame[b'radial']
        self._cumulative_pumped = last_frame[b'cumulative_pumped_avg']
        self._cumulative_dark = last_frame[b'cumulative_dark_avg']
        self._diff = last_frame[b'diff']
        self._cumulative_radial = last_frame[b'cumulative_radial']
        self._recent_radial = last_frame[b'recent_radial']

        self._unscaled_radial_plot.setData(
            self._q_bins,
            self._unscaled_radial
        )

        self._radial_plot.setData(
            self._q,
            self._radial
        )

        self._cumulative_pumped_plot.setData(
            self._q_bins,
            self._cumulative_pumped
        )

        self._cumulative_dark_plot.setData(
            self._q_bins,
            self._cumulative_dark
        )

        self._diff_plot.setData(
            self._q_bins,
            self._diff
        )

        self._recent_radial_plot.setData(
            self._q_bins,
            self._recent_radial
        )

        self._cumulative_radial_plot.setData(
            self._q_bins,
            self._cumulative_radial
        )

        self._hitrate_plot.setData(
            self._hitrate_history
        )

        self._pumped_hitrate_plot.setData(
            self._pumped_hitrate_history
        )

        self._dark_hitrate_plot.setData(
            self._dark_hitrate_history
        )

        self._intensity_sum_hist = last_frame[b'intensity_sum_hist']
        self._intensity_sum_hist_bins = last_frame[b'intensity_sum_hist_bins']
        self._intensity_sums_plot.setData(
            self._intensity_sum_hist_bins,
            self._intensity_sum_hist
        )

        # Reset local_data so that the same data is not processed
        # multiple times.
        self._local_data = []


def main():
    """
    Start the GUI for OnDA SWAXS.

    Initialize and start the GUI for OnDA SWAXS. Manage command line
    arguments, load the geometry and instantiate the graphical
    interface.
    """
    signal.signal(signal.SIGINT, signal.SIG_DFL)

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
            "Usage: onda_swaxs_gui.py geometry_filename "
            "<listening ip> <listening port>"
        )
        sys.exit()

    geometry = crystfel_utils.load_crystfel_geometry(geom_filename)

    app = QtGui.QApplication(sys.argv)
    _ = SWAXSGui(geometry, rec_ip, rec_port)
    sys.exit(app.exec_())
