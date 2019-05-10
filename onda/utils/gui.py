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
Base OnDA GUI class.
"""
from __future__ import absolute_import, division, print_function

import copy
import time

import numpy
import pyqtgraph

from onda.utils import zmq

try:
    from PyQt5 import QtCore, QtGui
except ImportError:
    from PyQt4 import QtCore, QtGui


class OndaGui(QtGui.QMainWindow):
    """
    Main GUI class.

    A class implementing the common GUI elements. It is designed to be subclassed to
    implement an OnDA GUI. It lets the user set up the GUI in the constructor method
    of the derived class. It then makes sure that the 'gui_update_func' function is
    called at regular intervals to update the GUI. Furthermore, it instantiates a
    listening thread to receive data from an OnDA monitor and make the data available
    to the derived class as soon as it isreceived.
    """

    _listening_thread_start_processing = QtCore.pyqtSignal()
    _listening_thread_stop_processing = QtCore.pyqtSignal()

    def __init__(self, pub_hostname, pub_port, subscription_string, gui_update_func):
        """
        Initializes the OndaGui class.

        Attributes:

            data (Dict): dictionary containing the last data received from the OnDA
                monitor.

            listening (bool): the state of the listening thread. True if the thread is
                listening for data from the OnDA monitor, False if it is not.

        Args:

            pub_hostname (str): hostname or IP address of the machine where the OnDA
                monitor is running.

            pub_port (int): port on which the the OnDA monitor is broadcasting
                information.

            subscription_string (str): the subscription string used to filter the data
                received from the OnDA monitor.

            gui_update_func (Callable): function that updates the GUI, to be called at
                regular intervals.
        """
        super(OndaGui, self).__init__()

        self._gui_update_func = gui_update_func
        self.data = None
        self.listening = False

        # Initializes an empty status bar
        self.statusBar().showMessage("")

        # Creates and initializes the ZMQ listening thread.
        self._data_listener_thread = QtCore.QThread()
        self._data_listener = zmq.DataListener(
            pub_hostname=pub_hostname,
            pub_port=pub_port,
            subscription_string=subscription_string,
        )
        self._data_listener.zmqmessage.connect(self._data_received)
        self._listening_thread_start_processing.connect(
            self._data_listener.start_listening
        )
        self._listening_thread_stop_processing.connect(
            self._data_listener.stop_listening
        )
        self._data_listener.moveToThread(self._data_listener_thread)
        self._data_listener_thread.start()
        self.start_listening()

        # Sets up and starts the timer that will call the GUI update function at
        # regular intervals (hardcoded to 500ms).
        self._refresh_timer = QtCore.QTimer()
        self._refresh_timer.timeout.connect(self._gui_update_func)
        self._refresh_timer.start(500)

    def start_listening(self):
        """
        Starts listening for data from the OnDA monitor.
        """
        if not self.listening:
            self.listening = True
            self._listening_thread_start_processing.emit()

    def stop_listening(self):
        """
        Stops listening for data from the OnDA monitor.
        """
        if self.listening:
            self.listening = False
            self._listening_thread_stop_processing.emit()

    def _data_received(self, data_dictionary):
        # This function is called every time thath listening thread receives data from
        # the OnDA monitor.

        # Stores the received dictionary as an attribute.
        self.data = copy.deepcopy(data_dictionary)

        # Computes the esimated delay and prints it into the status bar. (The GUI is
        # supposed to be a Qt MainWindow widget, so it is supposed to have a status
        # bar. This function expects the GUI to have it). The timestamp of the last
        # event in the received list of accumulated events is used to compute the
        # estimated delay.
        timestamp = self.data[-1][b"timestamp"]
        timenow = time.time()
        self.statusBar().showMessage(
            "Estimated delay: {} seconds".format(round(timenow - timestamp, 6))
        )


class OndaImageWidget(object):
    """
    OnDA widget to display images.

    An image widget with a histogram plot. Optionally, it can show axes labels and
    ticks. (It wraps a PyQtGraph's ImageView widget, with some tweaks).
    """

    def __init__(
        self,
        data=None,
        axes_visible=False,
        x_axis_range=None,
        y_axis_range=None,
        x_axis_label=None,
        y_axis_label=None,
    ):
        """
        Initializes the OndaImageWidget class.

        Attributes:

            widget (ImageView): the underlying PyQtGraph widget exposed.

        Args:

            image (ndarray): image data to be shown by the widget at startup.

            axes_visible (bool): flag that determines if the axes of the image should
                be visible or not.

            x_axis_range (Tuple): a tuple with the coordinates for the beginning and
                the end of the x-axis of the image in the widget data reference
                system.

            y_axis_range (Tuple): a tuple with the coordinates for the beginning and
                the end of the y-axis of the image in the widget data reference
                system.

            x_axis_label (str): x-axis label.

            y_axis_label (str): y-axis label.

        """
        self._axes_visible = axes_visible
        if self._axes_visible:
            self.widget = pyqtgraph.ImageView(view=pyqtgraph.PlotItem())
            self._bottom_axis = self.widget.view.getAxis("bottom")
            self._left_axis = self.widget.view.getAxis("left")
            self._image_item = self.widget.getImageItem()
        else:
            self.widget = pyqtgraph.ImageView()
        self._view = self.widget.getView()

        self.widget.ui.menuBtn.hide()
        self.widget.ui.roiBtn.hide()

        self._text = []
        self._scatter_plots = []

        self.update(
            data=data,
            x_axis_label=x_axis_label,
            x_axis_range=x_axis_range,
            y_axis_label=y_axis_label,
            y_axis_range=y_axis_range,
        )

    def update(
        self,
        data=None,
        x_axis_label=None,
        x_axis_range=None,
        y_axis_label=None,
        y_axis_range=None,
    ):
        """
        Updates the OnDA Image With Axes widget.

        Updates the image shown by the widget, or any of the axis labels or ticks.

        Args:

            image (ndarray): image data for the updated widget.

            x_axis_label (str): new X-axis label.

            x_axis_range (Tuple): A tuple with the new minimum and maximum values to be
                used for the x-axis ticks.

            y_axis_label (str): Y-axis label.

            y_axis_range (Tuple): A tuple with the new minimum and maximum values to be
                used for the y-axis ticks.
        """
        if data is not None:
            self.widget.setImage(
                data.T, autoHistogramRange=False, autoLevels=False, autoRange=False
            )

        if self._axes_visible and x_axis_label is not None:
            self._bottom_axis.setLabel(x_axis_label)

        if self._axes_visible and y_axis_label is not None:
            self._left_axis.setLabel(y_axis_label)

        if x_axis_range is not None or y_axis_range is not None:
            current_pos = self._image_item.pos()
            current_scale = self._image_item.scale()
            current_image = self._image_item.image

            new_pos = current_pos
            new_scale = current_scale

            if not y_axis_range is None:
                new_pos[0] = y_axis_range[0]
                new_scale[0] = (
                    y_axis_range[1] - y_axis_range[0]
                ) / current_image.shape[0]

            if not x_axis_range is None:
                new_pos[1] = x_axis_range[0]
                new_scale[1] = (
                    x_axis_range[1] - x_axis_range[0]
                ) / current_image.shape[1]

            self.widget.setImage(
                current_image,
                pos=new_pos,
                scale=new_scale,
                autoHistogramRange=False,
                autoLevels=False,
                autoRange=True,
            )

    def rescale(self, rescale_range=None):
        """
        Rescales the displayed image.

        The levels of displayed image are rescaled within the specified range, or
        between the minimum and the maximum pixel value in the image, if no range is
        specified.

        Args:

            rescale_range (Tuple[float, float]): Tuple with the minimum and the
                maximum values between which the image should be rescaled.
        """
        if rescale_range is None:
            current_image = self._image_item.image
            self.widget.setLevels(
                numpy.nanmin(current_image), numpy.nanmax(current_image)
            )
        else:
            self.widget.setLevels(rescale_range[0], rescale_range[1])

    def set_text(self, text=None, text_coordinates=None):
        """
        Adds or updates text displayed on an OnDA Image widget.

        The text is displayed on top of the image. Each text entry is rendered on the
        image in close proximity to the coordinates (in the widget data reference
        system) assigned to it. If called without arguments, this function removes the
        text currently displayed on the image (if any text is present)

        Arguments:

            text (List[str]): a list of text items to be displayed.

            text_coordinates (Tuple[List(float), List(float)]): a tuple of two lists
                storing the coordinates at which the text items should be displayed (in
                the widget data reference system). Each list must have the same length
                as the the list of text entries in the 'text' parameter. The first
                list should store the set of y_coordinates for the text entries, while
                the secondo should store the set of x_coordinates.
        """

        for text_entry in self._text:
            self._view.removeItem(text_entry)

        if text is not None and text_coordinates is not None:
            text_items = [
                pyqtgraph.TextItem(text=text_entry, anchor=(0.5, 0.8))
                for text_entry in text
            ]
            for text_item, y_coord, x_coord in zip(
                text_items, text_coordinates[0], text_coordinates[1]
            ):
                text_item.setPos(y_coord, x_coord)
                self._text.append(text_item)
                self._view.addItem(text_item)

    def set_scatter_plot_overlays(self, scatter_plots=None):
        """
        Adds or updates OnDA Scatter Plot Widget overlays on an OnDA Image widget.

        The scatter plots are displayed on top of the image. If called without
        arguments, this function all scatter plots currently displayed on top of the
        image (if any are present).

        Arguments:

            scatter_plots (Union[OndaScatterPlot, List[OndaScatterPlot]): an
                OnDAScatterPlotWidget or a list of OndaScatterPlotWidget objects to be
                displayed on top of the image.
        """
        for scatter_plot_entry in self._scatter_plots:
            self._view.removeItem(scatter_plot_entry)

        if scatter_plots is not None:
            if not isinstance(scatter_plots, list) or not isinstance(
                scatter_plots, tuple
            ):
                scatter_plot_tuple = (scatter_plots,)

            for scatter_plot in scatter_plot_tuple:
                scatter_plot.widget.getPlotItem().hideAxis(axis="bottom")
                scatter_plot.widget.getPlotItem().hideAxis(axis="left")
                self._view.addItem(scatter_plot.widget.getPlotItem().listDataItems()[0])

    def click_in_widget(self, mouse_click_event):
        """
        Returns position of a mouse click event in the widget data space.

        If a mouse click event happened within the widget, it returns the coordinates
        of the mouse event within the the dataset displayed by the widget.

        Args:

            mouse_click_event (MouseClickEvent): a MouseClickEvent object generated by
                the PyQtGraph library.

        Returns:

            Union[QPoint, None]: a QPoint object with the coordinates of the mouse
            click event in the widget data space if the event happened within the
            widget. None otherwise.
        """
        if self._view.sceneBoundingRect().contains(mouse_click_event.scenePos()):
            return self._view.vb.mapSceneToView(mouse_click_event.scenePos())
        else:
            return None


class OndaPlotWidget(object):
    """
    OnDA widget to display line plots.

    A widget that displays a line plot (wrapping a basic PyQtGraph's PlotWidget widget,
    with some tweaks).
    """

    def __init__(
        self,
        data=None,
        grid_shown=True,
        plot_title=None,
        x_axis_label=None,
        x_axis_range=None,
        y_axis_label=None,
        y_axis_range=None,
    ):
        """
        Initializes the OndaPlotWidget class.

        Attributes:

            widget (PlotWidget): the underlying PyQtGraph widget exposed.

        Args:

            data (Union[List], Tuple[List, List]): data to be plotted. If a
                tuple is provided, the first element of the tuple will be used for the
                x axis and the second for the second. If a single ndarray is provided,
                this will be used for the y axis, and a list of ints of the same length
                as the dataset will be used for the x axis.

            grid_shown (bool): flag to show or hide a coordinate grid on the plot.

            plot_title (str): a title for the plot.

            x_axis_label (str): x-axis label.

            x_axis_range (Tuple): a tuple with the minimum and maximum values to be
                be displayed on the x-axis.

            y_axis_label (str): y-axis label.

            y_axis_range (Tuple): a tuple with the minimum and maximum values to be
                be displayed on the y-axis ticks.
        """
        self.widget = pyqtgraph.PlotWidget()
        if grid_shown:
            self.widget.showGrid(x=True, y=True)
        else:
            self.widget.showGrid(x=False, y=False)
        self._plot = self.widget.plot([], [])

        self.update(
            data=data,
            plot_title=plot_title,
            x_axis_label=x_axis_label,
            x_axis_range=x_axis_range,
            y_axis_label=y_axis_label,
            y_axis_range=y_axis_range,
        )

    def update(
        self,
        data=None,
        plot_title=None,
        x_axis_label=None,
        x_axis_range=None,
        y_axis_label=None,
        y_axis_range=None,
    ):
        """
        Updates the OnDA Simple Plot widget.

        Updates the plot shown by the widget, or any of the axis labels or displayed
        ranges.

        Args:

            data (Union[List], Tuple[List, List]): image data for the updated
                widget.

            plot_title (str): new plot title.

            x_axis_label (str): new X-axis label.

            x_axis_range (Tuple): A tuple with the new minimum and maximum values to be
                be displayed on the x-axis.

            y_axis_label (str): Y-axis label.

            y_axis_range (Tuple): A tuple with the new minimum and maximum values to be
                to be displayed on the y-axis ticks.
        """
        if data is not None:
            if isinstance(data, tuple) or isinstance(data, list):
                self._plot.setData(data[0], data[1])
            else:
                self._plot.setData(range(0, len(data)), data)

        if plot_title is not None:
            self.widget.setTitle(plot_title)

        if x_axis_label is not None:
            self.widget.setLabel(axis="bottom", text=x_axis_label)

        if y_axis_label is not None:
            self.widget.setLabel(axis="left", text=y_axis_label)

        if x_axis_range is not None:
            self.widget.setXRange(x_axis_range[0], x_axis_range[1])

        if y_axis_range is not None:
            self.widget.setYRange(y_axis_range[0], y_axis_range[1])

    def link_x_axis(self, onda_plot_widget):
        """
        Links the x axis of the widget to the x axis of another plot widget.

        The x axes of the linked widgets react to mouse events (zooming, padding) in a
        coordinated way.

        Arguments:

            onda_plot_widget (class): an OnDA Plot Widget (OndaSimplePlotWidget,
                OndaPlotWithVerticalBarsWidget, etc.).
        """
        self.widget.setXLink(onda_plot_widget.widget)

    def link_y_axis(self, onda_plot_widget):
        """
        Links the y axis of the widget to the y axis of another plot widget.

        The y axes of the linked widgets react to mouse events (zooming, padding) in a
        coordinated way.

        Arguments:

            onda_plot_widget (class): an OnDA Plot Widget (OndaSimplePlotWidget,
                OndaPlotWithVerticalBarsWidget, etc.).
        """
        self.widget.setYLink(onda_plot_widget.widget)


class OndaScatterPlotWidget(object):
    """
    OnDA widget to display scatter plots.

    The scatter plot can also be drawn over an image displayed by an image widget. This
    widget wraps a basic PyQtGraph's ScatterPlotItem widget, with some tweaks.
    """

    def __init__(
        self,
        symbol,
        color,
        data=None,
        size=None,
        plot_title=None,
        x_axis_label=None,
        x_axis_range=None,
        y_axis_label=None,
        y_axis_range=None,
    ):
        """
        Initializes the OndaScatterPlotWidget class.

        Attributes:

            widget (PlotWidget): the underlying PyQtGraph widget exposed.

        Args:

            data (Tuple[List, List]): data to be plotted. The first element of the
                tuple is taken as the list of x coordinates of all points to be drawn
                in the scatterplot, the second element of the tuple is taken as the
                list of y coordinates of the points.

            symbol (str): The shape with which points in the scatter plot should be
                drawn (See PyQtGraphDocumentation).

            size (Union[List, int): the size of the symbols of the scatter plot. If a
                single number is provided, all symbols will be drawn with the specified
                size. If a list of sizes with a length equal to the numbers of points
                to plot is provided, each size in the list is used to draw the symbol
                of the corresponding data point.

            color (Union[Tuple, int, float, str): the color to be used to draw the
                symbols. The color can be specified in any of the formats accepted
                by PyQtGraph's mkColor function.

            plot_title (str): a title for the plot.

            x_axis_label (str): x-axis label.

            x_axis_range (Tuple): a tuple with the minimum and maximum values to be
                be displayed on the x-axis.

            y_axis_label (str): y-axis label.

            y_axis_range (Tuple): a tuple with the minimum and maximum values to be
                be displayed on the y-axis ticks.
        """
        pen = pyqtgraph.mkPen(color, width=1.0)
        self.widget = pyqtgraph.PlotWidget()
        self.widget.showGrid(x=True, y=True)
        self._plot = self.widget.plot(
            [],
            [],
            symbol=symbol,
            symbolColor=color,
            pen=None,
            symbolPen=pen,
            symbolBrush=(0, 0, 0, 0),
            pxMode=False,
        )

        self.widget.addItem(self._plot)
        self.update(
            data=data,
            size=size,
            plot_title=plot_title,
            x_axis_label=x_axis_label,
            x_axis_range=x_axis_range,
            y_axis_label=y_axis_label,
            y_axis_range=y_axis_range,
        )

    def update(
        self,
        data=None,
        size=None,
        plot_title=None,
        x_axis_label=None,
        x_axis_range=None,
        y_axis_label=None,
        y_axis_range=None,
    ):
        """
        Updates the OnDA Scatter Plot overlay.

        Updates the data shown by the overlay, without changing the shape and color of
        the symbols. If called without arguments, makes the widget display no data

        Args:

            data (Tuple[ndarray, ndarray]): data to be plotted. The first element of
                the tuple is taken as the list of x coordinates of all points to be
                drawn in the scatterplot, the second element of the tuple is taken as
                the list of y coordinates of the points.

            size (Union[List, int): the size of the symbols of the scatter plot. If a
                single number is provided, all symbols will be drawn with the specified
                size. If a list of sizes with a length equal to the numbers of points
                to plot is provided, each size in the list is used to draw the symbol
                of the corresponding data point.

            plot_title (str): new plot title.

            x_axis_label (str): new X-axis label.

            x_axis_range (Tuple): A tuple with the new minimum and maximum values to be
                be displayed on the x-axis.

            y_axis_label (str): Y-axis label.

            y_axis_range (Tuple): A tuple with the new minimum and maximum values to be
                to be displayed on the y-axis ticks.
        """
        if data is not None:
            if size is not None:
                self._plot.setData(data[0], data[1], symbolSize=size)
            else:
                self._plot.setData(data[0], data[1])
        else:
            if size is not None:
                curr_data = self._plot.getData()[1]
                self._plot.setData(curr_data[0], curr_data[1], symbolSize=size)

        if plot_title is not None:
            self.widget.setTitle(plot_title)

        if x_axis_label is not None:
            self.widget.setLabel(axis="bottom", text=x_axis_label)

        if y_axis_label is not None:
            self.widget.setLabel(axis="left", text=y_axis_label)

        if x_axis_range is not None:
            self.widget.setXRange(x_axis_range[0], x_axis_range[1])

        if y_axis_range is not None:
            self.widget.setYRange(y_axis_range[0], y_axis_range[1])
