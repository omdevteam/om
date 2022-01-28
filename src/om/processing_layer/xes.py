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
OnDA Monitor for X-ray Emission Spectroscopy.

This module contains an OnDA Monitor for x-ray emission spectroscopy experiments.
"""
from __future__ import absolute_import, division, print_function

import sys
import time
from typing import Any, Dict, Tuple, Union, cast

import numpy
from numpy.typing import NDArray

from om.algorithms import generic as gen_algs
from om.algorithms import xes as xes_algs
from om.processing_layer import base as pl_base
from om.utils import crystfel_geometry, parameters, zmq_monitor
from om.utils.crystfel_geometry import TypePixelMaps


class XESProcessing(pl_base.OmProcessing):
    """
    See documentation for the `__init__` function.
    """

    def __init__(self, *, monitor_parameters: parameters.MonitorParams) -> None:
        """
        OnDA Monitor for X-ray Emission Spectroscopy.

        This Processing class implements and OnDA Monitor for x-ray emission
        spectroscopy experiments. The monitor processes detector data frames,
        optionally applying detector calibration, dark correction and gain correction.
        It then extracts a 1D XES spectrum from each of the data frames. The monitor
        computes smoothed and averaged spectral data information and broadcasts it to
        external programs, like
        [OM's XES GUI][om.graphical_interfaces.xes_gui.XesGui], for visualization. In
        time resolved experiments, the monitor can process spectra for pumped and dark
        events separately, and compute their difference.

        This monitor is designed to work with cameras or simple single-module
        detectors. It will not work with a segmented detector.

        Arguments:

            monitor_parameters: An object storing OM's configuration parameters.
        """
        self._monitor_params = monitor_parameters

    def initialize_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes the processing nodes for the XES Monitor.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the correction algorithm and the spectrum extraction
        algorithm, plus some internal counters.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
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

        self._time_resolved: bool = self._monitor_params.get_parameter(
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

        print(f"Processing node {node_rank} starting")
        sys.stdout.flush()

    def initialize_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes the collecting node for the XES Monitor.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the data accumulation algorithms and the storage
        buffers used to compute statistics on the aggregated spectral data.
        Additionally, it prepares the data broadcasting socket to send data to
        external programs.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
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

        self._time_resolved = self._monitor_params.get_parameter(
            group="xes",
            parameter="time_resolved",
            parameter_type=bool,
            required=True,
        )

        self._xes_analysis = xes_algs.XESAnalysis(
            parameters=self._monitor_params.get_parameter_group(group="xes")
        )

        self._spectra_cumulative_sum: Union[NDArray[numpy.float_], None] = None
        self._spectra_cumulative_sum_smoothed: Union[NDArray[numpy.float_], None] = None

        self._cumulative_2d: Union[NDArray[numpy.float_], None] = None
        self._cumulative_2d_pumped: Union[NDArray[numpy.float_], None] = None
        self._cumulative_2d_dark: Union[NDArray[numpy.float_], None] = None

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

        This function processes retrieved data events, calibrating and correcting
        the detector data frames and extracting a XES spectrum from each of them. It
        additionally prepares the spectral data for transmission to to the collecting
        node.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

            data: A dictionary containing the data that OM retrieved for the detector
                data frame being processed.

                * The dictionary keys describe the Data Sources for which OM has
                  retrieved data. The keys must match the source names listed in the
                  `required_data` entry of OM's `om` configuration parameter group.

                * The corresponding dictionary values must store the the data that OM
                  retrieved for each of the Data Sources.

        Returns:

            A tuple with two entries. The first entry is a dictionary storing the
            processed data that should be sent to the collecting node. The second entry
            is the OM rank number of the node that processed the information.
        """
        processed_data: Dict[str, Any] = {}
        corrected_camera_data: NDArray[
            numpy.float_
        ] = self._correction.apply_correction(data=data["detector_data"])

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

        xes: Dict[str, NDArray[numpy.float_]] = self._xes_analysis.generate_spectrum(
            data=corrected_camera_data
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

        This function computes aggregated statistics on spectral data received from the
        processing nodes. It then broadcasts the results via a ZMQ socket for
        visualization by external programs.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

            processed_data (Tuple[Dict, int]): A tuple whose first entry is a
                dictionary storing the data received from a processing node, and whose
                second entry is the OM rank number of the node that processed the
                information.
        """
        received_data: Dict[str, Any] = processed_data[0]
        self._num_events += 1

        if self._time_resolved:
            if received_data["optical_laser_active"]:
                self._num_events_pumped += 1
            else:
                self._num_events_dark += 1

        if self._cumulative_2d is None:
            self._cumulative_2d = cast(
                NDArray[numpy.float_], received_data["detector_data"]
            )
        else:
            self._cumulative_2d += (
                (
                    cast(NDArray[numpy.float_], received_data["detector_data"])
                    - self._cumulative_2d * 1.0
                )
                / self._num_events
                * 1.0
            )

        # Calculate normalized spectrum from cumulative 2D images.
        cumulative_xes: Dict[
            str, NDArray[numpy.float_]
        ] = self._xes_analysis.generate_spectrum(data=self._cumulative_2d)
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
                    (
                        cast(NDArray[numpy.float_], received_data["detector_data"])
                        - self._cumulative_2d_pumped * 1.0
                    )
                    / self._num_events_pumped
                    * 1.0
                )
            else:
                self._cumulative_2d_dark += (
                    (
                        cast(NDArray[numpy.float_], received_data["detector_data"])
                        - self._cumulative_2d_dark * 1.0
                    )
                    / self._num_events_dark
                    * 1.0
                )

            # Calculate spectrum from cumulative 2D images
            cumulative_xes_pumped: Dict[
                str, NDArray[numpy.float_]
            ] = self._xes_analysis.generate_spectrum(data=self._cumulative_2d_pumped)
            spectra_cumulative_sum_pumped: NDArray[
                numpy.float_
            ] = cumulative_xes_pumped["spectrum"]

            # calculate spectrum from cumulative 2D images
            cumulative_xes_dark: Dict[
                str, NDArray[numpy.float_]
            ] = self._xes_analysis.generate_spectrum(data=self._cumulative_2d_dark)
            spectra_cumulative_sum_dark: NDArray[numpy.float_] = cumulative_xes_dark[
                "spectrum"
            ]

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
                tag="omdata",
                message=message,
            )

        if self._num_events % self._speed_report_interval == 0:
            now_time: float = time.time()
            time_diff: float = now_time - self._old_time
            events_per_second: float = float(self._speed_report_interval) / float(
                now_time - self._old_time
            )
            print(
                f"Processed: {self._num_events} in {time_diff:.2f} seconds "
                f"({events_per_second} Hz)"
            )
            sys.stdout.flush()
            self._old_time = now_time

    def end_processing_on_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> Union[Dict[str, Any], None]:
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

            Usually nothing. Optionally, a dictionary storing information to be sent to
            the processing node.
        """
        print(f"Processing node {node_rank} shutting down.")
        sys.stdout.flush()
        return None

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
            f"Processing finished. OM has processed {self._num_events} events "
            "in total."
        )
        sys.stdout.flush()
