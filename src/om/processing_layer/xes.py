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
# Copyright 2020 -2021 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
OM monitor for x-ray emission spectroscopy.
This module contains an OM monitor for x-ray emission spectroscopy experiments.
"""
from __future__ import absolute_import, division, print_function

import sys
import time
from typing import Any, Dict, Tuple, Union

import numpy  # type: ignore

from om.algorithms import generic as gen_algs
from om.algorithms import xes as xes_algs
from om.processing_layer import base as pl_base
from om.utils import crystfel_geometry, parameters, zmq_monitor
from om.utils.crystfel_geometry import TypePixelMaps


class XESProcessing(pl_base.OmProcessing):
    """
    See documentation for the `__init__` function.

    Base class: [`OmProcessing`][om.processing_layer.base.OmProcessing]
    """

    def __init__(self, *, monitor_parameters: parameters.MonitorParams) -> None:
        """
        An OM real-time monitor for x-ray emission spectroscopy experiments.

        This monitor contains an Onda Monitor that processes detector data frames,
        optionally applying detector calibration, dark correction and gain correction.
        and extracts 1D spectral information. It also calculates the evolution of the
        hit rate over time and broadcasts all this information over a network socket
        for visualization by other programs. This OnDA Monitor can also optionally
        broadcast calibrated and corrected detector data frames to be displayed by
        external programs. This monitor is designed to work with cameras or
        simple single-module detectors. It will not work with a segmented detector.

        This class is a subclass of the
        [OmProcessing][om.processing_layer.base.OmProcessing] base class.

        Arguments:

          monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.
        """
        self._monitor_params = monitor_parameters

    def initialize_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes the OM processing nodes for the XES monitor.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the correction and spectrum extraction algorithms,
        plus some internal counters.
        """

        self._pixelmaps: TypePixelMaps = (
            crystfel_geometry.pixel_maps_from_geometry_file(
                filename=self._monitor_params.get_parameter(
                    group="xes",
                    parameter="geometry_file",
                    parameter_type=str,
                    required=True,
                )
            )
        )

        self._correction = gen_algs.Correction(
            parameters=self._monitor_params.get_parameter_group(group="correction")
        )

        self._xes_analysis = xes_algs.XESAnalysis(
            parameters=self._monitor_params.get_parameter_group(group="xes")
        )

        self._time_resolved: bool = self._monitor_params.get_param(
            group="xes",
            parameter="time_resolved",
            parameter_type=bool,
            required=True,
        )

        self._hit_frame_sending_interval: Union[
            int, None
        ] = self._monitor_params.get_parameter(
            group="xes",
            parameter="hit_frame_sending_interval",
            parameter_type=int,
        )
        self._non_hit_frame_sending_interval: Union[
            int, None
        ] = self._monitor_params.get_parameter(
            group="xes",
            parameter="non_hit_frame_sending_interval",
        )

        self._hit_frame_sending_counter: int = 0
        self._non_hit_frame_sending_counter: int = 0

        print("Processing node {0} starting.".format(node_rank))
        sys.stdout.flush()

    def initialize_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes the OM collecting node for the XES monitor.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the data accumulation algorithms and the storage
        buffers used to compute statistics on aggregated spectrum data. Additionally,
        it prepares the data broadcasting socket to send data to external programs.
        """
        self._speed_report_interval: int = self._monitor_params.get_parameter(
            group="xes",
            parameter="speed_report_interval",
            parameter_type=int,
            required=True,
        )

        self._data_broadcast_interval: int = self._monitor_params.get_parameter(
            group="xes",
            parameter="data_broadcast_interval",
            parameter_type=int,
            required=True,
        )

        self._time_resolved = self._monitor_params.get_param(
            group="xes",
            parameter="time_resolved",
            parameter_type=bool,
            required=True,
        )

        self._xes_analysis = xes_algs.XESAnalysis(
            parameters=self._monitor_params.get_parameter_group(group="xes")
        )

        self._spectra_cumulative_sum: Union[numpy.ndarray, None] = None
        self._spectra_cumulative_sum_smoothed: Union[numpy.ndarray, None] = None

        self._cumulative_2d = None
        self._cumulative_2d_pumped: Union[numpy.ndarray, None] = None
        self._cumulative_2d_dark: Union[numpy.ndarray, None] = None

        self._num_events_pumped: int = 0
        self._num_events_dark: int = 0

        self._data_broadcast_socket: zmq_monitor.ZmqDataBroadcaster = (
            zmq_monitor.ZmqDataBroadcaster(
                parameters=self._monitor_params.get_parameter_group(group="xes")
            )
        )

        self._responding_socket: zmq_monitor.ZmqResponder = zmq_monitor.ZmqResponder(
            parameters=self._monitor_params.get_parameter_group(group="xes")
        )

        self._num_events: int = 0
        self._old_time: float = time.time()
        self._time: Union[float, None] = None

        print("Starting the monitor...")
        sys.stdout.flush()

    def process_data(
        self, *, node_rank: int, node_pool_size: int, data: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], int]:
        """
        Processes a detector data frame and extracts spectrum information.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function performs calibration and correction of a detector data frame and
        extracts spectrum information. Finally, it prepares the spectrum data for
        transmission to to the collecting node.
        """
        processed_data: Dict[str, Any] = {}
        corrected_camera_data: numpy.ndarray = self._correction.apply_correction(
            data=data["detector_data"]
        )

        # Mask the camera edges
        corrected_camera_data[
            corrected_camera_data.shape[0] // 2
            - 1 : corrected_camera_data.shape[0] // 2
            + 1
        ] = 0
        corrected_camera_data[
            :,
            corrected_camera_data.shape[1] // 2
            - 1 : corrected_camera_data.shape[1] // 2
            + 1,
        ] = 0

        xes: Dict[str, numpy.ndarray] = self._xes_analysis.generate_spectrum(
            corrected_camera_data
        )

        processed_data["timestamp"] = data["timestamp"]
        processed_data["spectrum"] = xes["spectrum"]
        processed_data["beam_energy"] = data["beam_energy"]
        processed_data["data_shape"] = data["detector_data"].shape
        processed_data["detector_data"] = corrected_camera_data
        if self._time_resolved:
            processed_data["optical_laser_active"] = data["optical_laser_active"]

        return (processed_data, node_rank)

    def collect_data(
        self,
        *,
        node_rank: int,
        node_pool_size: int,
        processed_data: Tuple[Dict[str, Any], int],
    ) -> None:
        """
        Computes statistics on aggregated spectrum data and broadcasts them.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function computes aggregated statistics on spectrum data received from the
        processing nodes. It then broadcasts the results via a network socket (for
        visualization by other programs) using the MessagePack protocol.
        """
        received_data: Dict[str, Any] = processed_data[0]
        self._num_events += 1

        if self._time_resolved:
            if received_data["optical_laser_active"]:
                self._num_events_pumped += 1
            else:
                self._num_events_dark += 1

        if self._cumulative_2d is None:
            self._cumulative_2d = received_data["detector_data"]
        else:
            self._cumulative_2d += (
                (received_data["detector_data"] - self._cumulative_2d * 1.0)
                / self._num_events
                * 1.0
            )

        # Calculate normalized spectrum from cumulative 2D images.
        cumulative_xes: Dict[str, numpy.ndarray] = self._xes_analysis.generate_spectrum(
            self._cumulative_2d
        )
        self._spectra_cumulative_sum = cumulative_xes["spectrum"]
        self._spectra_cumulative_sum_smoothed = cumulative_xes["spectrum_smoothed"]

        if numpy.mean(numpy.abs(self._spectra_cumulative_sum)) > 0:
            self._spectra_cumulative_sum /= numpy.mean(
                numpy.abs(self._spectra_cumulative_sum)
            )
        if numpy.mean(numpy.abs(self._spectra_cumulative_sum_smoothed)) > 0:
            self._spectra_cumulative_sum_smoothed /= numpy.mean(
                numpy.abs(self._spectra_cumulative_sum_smoothed)
            )

        spectrum_for_gui = received_data["spectrum"]

        if self._time_resolved:
            # Sum the spectra for pumped (optical_laser_active) and dark
            if self._cumulative_2d_pumped is None:
                self._cumulative_2d_pumped = received_data["detector_data"] * 0
            if self._cumulative_2d_dark is None:
                self._cumulative_2d_dark = received_data["detector_data"] * 0

            # Need to calculate a running average
            if received_data["optical_laser_active"]:
                self._cumulative_2d_pumped += (
                    (received_data["detector_data"] - self._cumulative_2d_pumped * 1.0)
                    / self._num_events_pumped
                    * 1.0
                )
            else:
                self._cumulative_2d_dark += (
                    (received_data["detector_data"] - self._cumulative_2d_dark * 1.0)
                    / self._num_events_dark
                    * 1.0
                )

            # Calculate spectrum from cumulative 2D images
            cumulative_xes_pumped: Dict[
                str, numpy.ndarray
            ] = self._xes_analysis.generate_spectrum(self._cumulative_2d_pumped)
            spectra_cumulative_sum_pumped: numpy.ndarray = cumulative_xes_pumped[
                "spectrum"
            ]

            # calculate spectrum from cumulative 2D images
            cumulative_xes_dark: Dict[
                str, numpy.ndarray
            ] = self._xes_analysis.generate_spectrum(self._cumulative_2d_dark)
            spectra_cumulative_sum_dark: numpy.ndarray = cumulative_xes_dark["spectrum"]

            # normalize spectra
            if numpy.mean(numpy.abs(spectra_cumulative_sum_pumped)) > 0:
                spectra_cumulative_sum_pumped /= numpy.mean(
                    numpy.abs(spectra_cumulative_sum_pumped)
                )
            if numpy.mean(numpy.abs(spectra_cumulative_sum_dark)) > 0:
                spectra_cumulative_sum_dark /= numpy.mean(
                    numpy.abs(spectra_cumulative_sum_dark)
                )

            spectra_cumulative_sum_difference = (
                spectra_cumulative_sum_pumped - spectra_cumulative_sum_dark
            )

        message: Dict[str, Any] = {
            "timestamp": received_data["timestamp"],
            "detector_data": self._cumulative_2d,
            "spectrum": spectrum_for_gui,
            "spectra_sum": self._spectra_cumulative_sum,
            "spectra_sum_smoothed": self._spectra_cumulative_sum_smoothed,
            "beam_energy": received_data["beam_energy"],
        }
        if self._time_resolved:
            message["spectra_sum_pumped"] = spectra_cumulative_sum_pumped
            message["spectra_sum_dark"] = spectra_cumulative_sum_dark
            message["spectra_sum_difference"] = spectra_cumulative_sum_difference

        if self._num_events % self._data_broadcast_interval == 0:
            self._data_broadcast_socket.send_data(
                tag="view:omdata",
                message=message,
            )

        if self._num_events % self._speed_report_interval == 0:
            now_time: float = time.time()
            speed_report_msg: str = (
                "Processed: {0} in {1:.2f} seconds "
                "({2:.2f} Hz)".format(
                    self._num_events,
                    now_time - self._old_time,
                    (
                        float(self._speed_report_interval)
                        / float(now_time - self._old_time)
                    ),
                )
            )
            print(speed_report_msg)
            sys.stdout.flush()
            self._old_time = now_time

    def end_processing_on_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Ends processing actions on the processing nodes.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function prints a message on the console and ends the processing.

        Arguments:
            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.
            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        Returns:
            A dictionary storing information to be sent to the processing node
            (Optional: if this function returns nothing, no information is transferred
            to the processing node.
        """
        print("Processing node {0} shutting down.".format(node_rank))
        sys.stdout.flush()

    def end_processing_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Ends processing on the collecting node.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function prints a message on the console and ends the processing.

        Arguments:
            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.
            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        print(
            "Processing finished. OM has processed {0} events in total.".format(
                self._num_events
            )
        )
        sys.stdout.flush()
