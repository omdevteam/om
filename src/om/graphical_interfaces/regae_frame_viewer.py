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
# Copyright 2020 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
OM frame viewer for REGAE.

This module contains a graphical interface that displays detector data frames in
crystallography experiments.
"""
import collections
import copy
import signal
import sys
import time
from typing import Any, Deque, Dict, Union, List

import click
import numpy  # type: ignore
import pyqtgraph  # type: ignore

from om_gui_desktop.graphical_interfaces import base as graph_interfaces_base

from PyQt5 import QtGui, QtCore  # type: ignore

from scipy.optimize import curve_fit

from sortedcontainers import SortedDict

def rotate(x, y, theta): 
    return (x * numpy.cos(theta) - y * numpy.sin(theta), x * numpy.sin(theta) + y * numpy.cos(theta)) 


def gaussian2D(coord, a, cx, cy, sx, sy, theta): 
    x, y = coord
    cx, cy = rotate(cx, cy, theta) 
    x, y = rotate(x, y, theta)
    return a * numpy.exp(-(((x - cx) / sx)**2 + ((y - cy) / sy)**2) / 2) 


class RegaeFrameViewer(graph_interfaces_base.OmGui):  # type: ignore
    """
    See documentation of the __init__ function.
    """

    def __init__(self, url: str):
        """
        OM frame viewer for crystallography.

        This viewer receives detector frame data from an OM crystallography monitor,
        when it is tagged with the 'omdetectordata' label. It displays the received
        detector frames, together with any detected Bragg peak (if present). A data
        buffer allows the viewer to stop receiving data from the monitor but still keep
        in memory the last 10 displayed frames for inspection.

        Arguments:

            url (str): the URL at which the GUI will connect and listen for data. This
                must be a string in the format used by the ZeroMQ Protocol.
        """
        super(RegaeFrameViewer, self).__init__(
            url=url, tag=u"view:omframedata",
        )

        self._img: Union[numpy.array, None] = None
        self._frame_list: Deque[Dict[str, Any]] = collections.deque(maxlen=20)
        self._current_frame_index: int = -1

        self._received_data: Dict[str, Any] = {}

        pyqtgraph.setConfigOption("background", 0.2)

        self._ring_pen: Any = pyqtgraph.mkPen("r", width=2)
        self._peak_canvas: Any = pyqtgraph.ScatterPlotItem()

        self._roi = pyqtgraph.RectROI([100, 100], [50, 50], pen=pyqtgraph.mkPen('b', width=2))
        self._roi.sigRegionChanged.connect(self._update_roi)

        self._image_view: Any = pyqtgraph.ImageView()
        self._image_view.ui.menuBtn.hide()
        self._image_view.ui.roiBtn.hide()
        self._image_view.getView().addItem(self._peak_canvas)
        self._image_view.getView().addItem(self._roi)
        self._image_hist = self._image_view.getHistogramWidget()
        self._image_hist.sigLevelsChanged.connect(self._update_roi)

        self._roi_view: Any = pyqtgraph.GraphicsView()
        roi_layout: Any = pyqtgraph.GraphicsLayout(border=(100,100,100))

        self._roi_view.setCentralItem(roi_layout)
        self._vert_ave_roi_plot: Any = roi_layout.addPlot(title="AveX")
        self._vert_ave_roi_line: Any = self._vert_ave_roi_plot.plot()
        self._roi_label: Any = roi_layout.addLabel("")
        roi_layout.nextRow()
        self._roi_image: Any = pyqtgraph.ImageItem()
        self._roi_image_view: Any = roi_layout.addPlot(title="ROI")
        self._roi_image_view.getViewBox().setAspectLocked()
        self._roi_image_view.addItem(self._roi_image)
        self._horiz_ave_roi_plot: Any = roi_layout.addPlot(title="AveY", angle=-90)
        self._horiz_ave_roi_line: Any = self._horiz_ave_roi_plot.plot()
        
        self._peak_roi = pyqtgraph.EllipseROI([0, 0], [0.1, 0.1], pen=pyqtgraph.mkPen('r', width=1))
        self._roi_image_view.addItem(self._peak_roi)
        self._peak_roi.sigRegionChanged.connect(self._update_peak_info)

        self._vert_ave_roi_plot.setXLink(self._roi_image_view)
        self._horiz_ave_roi_plot.setYLink(self._roi_image_view)

        roi_layout.layout.setColumnStretchFactor(0, 2)
        roi_layout.layout.setRowStretchFactor(1, 2)
        # self._roi_view: Any = pyqtgraph.ImageView()
        # self._roi_view.ui.menuBtn.hide()
        # self._roi_view.ui.roiBtn.hide()

        self._time_plot_list = QtGui.QListWidget()
        self._time_plot_list.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        
        self._time_plot_options: List[str] = [
            "peakTotalIntensity", 
            "peakSNR", 
            "peakWidth", 
            "peakLength", 
            "peakPositionX", 
            "peakPositionY"
        ]

        self._time_plot_data: Dict[str, Any] = {}
        for option in self._time_plot_options:
            self._time_plot_list.addItem(QtGui.QListWidgetItem(option))
            self._time_plot_data[option] = SortedDict()

        self._time_plot_list.itemSelectionChanged.connect(self._time_plots_selection_changed)
        self._time_plot_widget: Any = pyqtgraph.PlotWidget()
        self._time_plot_widget.setXRange(-50, 0)
        self._time_plot_widget.getPlotItem().setClipToView(True)
        self._time_plot_widget.getPlotItem().setLabel("bottom", "Time", "s")
        self._time_plot_widget.getPlotItem().addLegend()
        self._time_plots = {}

        self._back_button: Any = QtGui.QPushButton(text="Back")
        self._back_button.clicked.connect(self._back_button_clicked)

        self._forward_button: Any = QtGui.QPushButton(text="Forward")
        self._forward_button.clicked.connect(self._forward_button_clicked)

        self._play_pause_button: Any = QtGui.QPushButton(text="Pause")
        self._play_pause_button.clicked.connect(self._play_pause_button_clicked)

        self._fit_peak_check_box: Any = QtGui.QCheckBox(
            text="Fit peak ", checked=True
        )
        self._fit_peak_check_box.setEnabled(True)

        self._roi_widget: Any = QtGui.QWidget()
        self._roi_layout: Any = QtGui.QVBoxLayout()
        self._roi_layout.addWidget(self._fit_peak_check_box)
        self._roi_layout.addWidget(self._roi_view)
        self._roi_widget.setLayout(self._roi_layout)

        self._time_plot_view: Any = QtGui.QWidget()
        self._time_plot_layout: Any = QtGui.QHBoxLayout()
        self._time_plot_layout.addWidget(self._time_plot_widget)
        self._time_plot_layout.addWidget(self._time_plot_list)
        self._time_plot_view.setLayout(self._time_plot_layout)
        
        self._horizontal_layout: Any = QtGui.QHBoxLayout()
        self._horizontal_layout.addWidget(self._back_button)
        self._horizontal_layout.addWidget(self._forward_button)
        self._horizontal_layout.addWidget(self._play_pause_button)
        splitter_1 = QtGui.QSplitter(QtCore.Qt.Vertical)
        splitter_1.addWidget(self._roi_widget)
        splitter_1.addWidget(self._time_plot_view)
        splitter_0: Any = QtGui.QSplitter()
        splitter_0.addWidget(self._image_view)
        splitter_0.addWidget(splitter_1)
        self._vertical_layout: Any = QtGui.QVBoxLayout()
        self._vertical_layout.addWidget(splitter_0)
        self._vertical_layout.addLayout(self._horizontal_layout)
        self._central_widget: Any = QtGui.QWidget()
        self._central_widget.setLayout(self._vertical_layout)
        self.setCentralWidget(self._central_widget)
        self._current_image_timestamp = None
        self.show()

    def _update_time_plots(self):
        if len(self._time_plot_list.selectedItems()) == 0:
            return
        timenow: float = time.time()
        timestamps: List[float] = [t - timenow for t in self._time_plot_data["peakTotalIntensity"].keys()]
        self._time_plot_widget.enableAutoRange("y")
        for item in self._time_plot_list.selectedItems():
            prop = item.text()
            self._time_plots[prop].setData(
                timestamps,
                list(self._time_plot_data[prop].values())
            )

    def _time_plots_selection_changed(self):
        self._time_plot_widget.clear()
        self._time_plots = {}
        for (i, item) in enumerate(self._time_plot_list.selectedItems()):
            prop = item.text()
            self._time_plots[prop] = self._time_plot_widget.plot(pen=(i, 6), name=prop)
        self._update_time_plots()

    def _update_roi(self):
        self._roi_region: Any = self._roi.getArrayRegion(self._current_image, self._image_view.getImageItem())[:, ::-1]
        cmap: Any = self._image_view.ui.histogram.gradient.colorMap()
        self._roi_image.setImage(
            self._roi_region,
            levels=self._image_hist.getLevels(),
            lut=cmap.getLookupTable()
        )
        self._vert_ave_roi_line.setData(numpy.mean(self._roi_region, axis=1))
        self._horiz_ave_roi_line.setData(numpy.mean(self._roi_region, axis=0), numpy.arange(self._roi_region.shape[1]))
        if self._fit_peak_check_box.isChecked():
            self._fit_roi_peak()
        else:
            self._update_peak_info()

    def _fit_roi_peak(self):
        ny: int
        nx: int
        ny, nx = self._roi_region.shape
        x: numpy.ndarray
        y: numpy.ndarray
        x, y = numpy.meshgrid(numpy.linspace(0, nx - 1, nx), numpy.linspace(0, ny - 1, ny))
        popt: numpy.ndarray
        pcov: numpy.ndarray

        ampl: float
        cx: float
        cy: float
        sigma_x: float
        sigma_y: float
        theta: float
        try:
            popt, pcov = curve_fit(gaussian2D, (x.ravel(), y.ravel()), self._roi_region.ravel(), p0=(1000, nx/2, ny/2, nx/4, ny/4, 1.))
            ampl, cx, cy, sigma_x, sigma_y, theta = popt
        except RuntimeError:
            ampl, cx, cy, sigma_x, sigma_y, theta = 0, 0, 0.1, 0.1, 0, 0

        sigma_x = abs(sigma_x)
        sigma_y = abs(sigma_y)
        pos_x: float = cy - 3 * sigma_y + 1
        pos_y: float = cx - 3 * sigma_x + 1
        size_x: float = 6 * sigma_y
        size_y: float = 6 * sigma_x

        self._peak_roi.setAngle(0, update=False)
        self._peak_roi.setPos([pos_x, pos_y], update=False)
        self._peak_roi.setSize([size_x, size_y], update=False)
        self._peak_roi.setAngle(180 / numpy.pi * theta, center=[0.5, 0.5], update=True)
        
    def _update_peak_info(self):
        peak_region = self._peak_roi.getArrayRegion(self._roi_region, self._roi_image)

        sl: Tuple[Tuple, Tuple]
        sl, *_ = self._peak_roi.getArraySlice(self._roi_region, self._roi_image, returnSlice=False)

        background: Any = self._roi_region.copy()
        background[sl[0][0]:sl[0][1], sl[1][0]:sl[1][1]] = numpy.nan
        background_mean: float = numpy.nanmean(background)
        background_sigma: float = numpy.nanstd(background)

        peak_num_pix: int = len(numpy.where(peak_region != 0)[0])
        peak_max_value: float = peak_region.max()
        peak_total_intensity: float = peak_region.sum() - peak_num_pix * background_mean
        peak_snr: float = peak_total_intensity / background_sigma
        size: Tuple[float, float] = self._peak_roi.size()

        width: float
        length: float
        width, length = sorted((abs(i) for i in size))
        
        ellipse_pos: Tuple[float, float] = self._peak_roi.pos()

        self._roi_label.setText("peakMaximumValue = %.2f <br> \
                                 peakTotalIntensity = %.2f <br> \
                                 peakSNR = %.2f <br> <br> \
                                 backgroundMean = %.2f <br> \
                                 backgroundSigma = %.2f <br> <br>\
                                 peakEllipseSize: %.1f %.1f pixels"%(
                                    peak_max_value, 
                                    peak_total_intensity,
                                    peak_snr,
                                    background_mean,
                                    background_sigma,
                                    width, length,
                                    )
                                 )
        if self._current_image_timestamp is None:
            return
        if numpy.isnan(peak_total_intensity) or numpy.isnan(peak_snr):
            return
            
        self._time_plot_data["peakTotalIntensity"][self._current_image_timestamp] = peak_total_intensity
        self._time_plot_data["peakSNR"][self._current_image_timestamp] = peak_snr
        self._time_plot_data["peakWidth"][self._current_image_timestamp] = width
        self._time_plot_data["peakLength"][self._current_image_timestamp] = length
        #TODO: get real peak position from fitting
        self._time_plot_data["peakPositionX"][self._current_image_timestamp] = ellipse_pos[0]
        self._time_plot_data["peakPositionY"][self._current_image_timestamp] = ellipse_pos[1]
        self._update_time_plots()

    def _update_peaks(
        self, peak_list_x_in_frame: numpy.ndarray, peak_list_y_in_frame: numpy.ndarray,
    ) -> None:
        # Updates the Bragg peaks shown by the viewer.
        QtGui.QApplication.processEvents()

        self._peak_canvas.setData(
            x=peak_list_y_in_frame,
            y=peak_list_x_in_frame,
            symbol="o",
            size=[5] * len(peak_list_x_in_frame),
            brush=(255, 255, 255, 0),
            pen=self._ring_pen,
            pxMode=False,
        )

    def _update_image_and_peaks(self) -> None:
        # Updates the image and Bragg peaks shown by the viewer.

        try:
            current_data: numpy.ndarray = self._frame_list[self._current_frame_index]
        except IndexError:
            # If the framebuffer is empty, returns without drawing anything.
            return

        QtGui.QApplication.processEvents()

        self._current_image: Any = current_data["frame_data"].T

        self._image_view.setImage(
            self._current_image,
            autoLevels=False,
            autoRange=False,
            autoHistogramRange=False,
        )

        QtGui.QApplication.processEvents()

        # self._update_peaks(
        #     peak_list_x_in_frame=current_data["peak_list_x_in_frame"],
        #     peak_list_y_in_frame=current_data["peak_list_y_in_frame"],
        # )

        self._update_roi()

        QtGui.QApplication.processEvents()

        # Computes the estimated age of the received data and prints it into the status
        # bar (a GUI is supposed to be a Qt MainWindow widget, so it is supposed to
        # have a status bar).
        timenow: float = time.time()
        self.statusBar().showMessage(
            "Estimated delay: {0} seconds".format(
                round(timenow - current_data["timestamp"], 6)
            )
        )
        self._current_image_timestamp = current_data["timestamp"]

    def update_gui(self) -> None:
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
        print("Showing frame {0} in the buffer".format(self._current_frame_index))
        self._update_image_and_peaks()

    def _forward_button_clicked(self) -> None:
        # Manages clicks on the 'forward' button.
        self._stop_stream()
        if (self._current_frame_index + 1) < len(self._frame_list):
            self._current_frame_index += 1
        print("Showing frame {0} in the buffer".format(self._current_frame_index))
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
def main(url: str) -> None:
    """
    OM frame viewer for crystallography. This program must connect to a running OM
    monitor for crystallography. If the monitor broadcasts detector frame data, this
    viewer will display it. The viewer will also show, overlayed on the frame data,
    any found Bragg peak. The data stream from the monitor can also be temporarily
    paused, and any of the last 10 displayed detector frames can be recalled for
    inspection.

    URL: the URL at which the GUI will connect and listen for data. This is a string in
    the format used by the ZeroMQ Protocol. Optional: if not provided, it defaults to
    tcp://127.0.0.1:12321
    """
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    if url is None:
        url = "tcp://127.0.0.1:12321"
    app: Any = QtGui.QApplication(sys.argv)
    _ = RegaeFrameViewer(url)
    sys.exit(app.exec_())
