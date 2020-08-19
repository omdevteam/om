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
OM monitor for crystallography.

This module contains an OM monitor for serial x-ray crystallography experiments.
"""
from __future__ import absolute_import, division, print_function

import collections
import sys
import time
from typing import Any, Deque, Dict, List, Tuple, Type, Union

import h5py  # type: ignore
import numpy  # type: ignore
from future.utils import raise_from  # type: ignore

from om.algorithms import crystallography_algorithms as cryst_algs
from om.algorithms import generic_algorithms as gen_algs
from om.processing_layer import base as process_layer_base
from om.utils import crystfel_geometry, parameters, zmq_monitor
from om.utils.crystfel_geometry import TypeBeam, TypeDetector


class CrystallographyMonitor(process_layer_base.OmMonitor):
    """
    See documentation for the '__init__' function.
    """

    def __init__(self, monitor_parameters):
        # type: (parameters.MonitorParams) -> None
        """
        An OM real-time monitor for serial x-ray crystallography experiments.

        See documentation of the constructor of the base class:
        :func:`~om.processing_layer.base.OmMonitor`.

        This monitor processes detector data frames, optionally applying detector
        calibration, dark correction and gain correction. It detects Bragg peaks in
        each detector frame using the peakfinder8 algorithm from Cheetah. It provides
        information about the location and integrated intensity of each peak.
        Additionally, it calculates the evolution of the hit rate over time. It
        broadcasts all this information over a network socket for visualization by
        other programs. Optionally, it can also broadcast calibrated and corrected
        detector data frames.
        """
        super(CrystallographyMonitor, self).__init__(
            monitor_parameters=monitor_parameters
        )

    def initialize_processing_node(self, node_rank, node_pool_size):
        # type: (int, int) -> None
        """
        Initializes the OM nodes for the Crystallography monitor.

        See documentation of the function in the base class:
        :func:`~om.processing_layer.base.OmMonitor`.

        On the processing nodes, it initializes the correction and peak finding
        algorithms, plus some internal counters. On the collecting node, this function
        initializes the data accumulation algorrithms and the storage for the
        aggregated statistics.
        """

        geometry_filename = self._monitor_params.get_param(
            group="crystallography",
            parameter="geometry_file",
            parameter_type=str,
            required=True,
        )  # type: str
        geometry, _, __ = crystfel_geometry.load_crystfel_geometry(
            geometry_filename
        )  # type: Tuple[crystfel_geometry.TypeDetector, Any, Any]
        self._pixelmaps = crystfel_geometry.compute_pix_maps(
            geometry
        )  # type: Dict[str, numpy.ndarray]

        self._hit_frame_sending_counter = 0  # type: int
        self._non_hit_frame_sending_counter = 0  # type: int

        dark_data_filename = self._monitor_params.get_param(
            group="correction", parameter="dark_filename", parameter_type=str
        )  # type: str
        dark_data_hdf5_path = self._monitor_params.get_param(
            group="correction", parameter="dark_hdf5_path", parameter_type=str
        )  # type: str
        mask_filename = self._monitor_params.get_param(
            group="correction", parameter="mask_filename", parameter_type=str
        )  # type: str
        mask_hdf5_path = self._monitor_params.get_param(
            group="correction", parameter="mask_hdf5_path", parameter_type=str
        )  # type: str
        gain_map_filename = self._monitor_params.get_param(
            group="correction", parameter="gain_filename", parameter_type=str
        )  # type: str
        gain_map_hdf5_path = self._monitor_params.get_param(
            group="correction", parameter="gain_hdf5_path", parameter_type=str
        )  # type: str
        self._correction = gen_algs.Correction(
            dark_filename=dark_data_filename,
            dark_hdf5_path=dark_data_hdf5_path,
            mask_filename=mask_filename,
            mask_hdf5_path=mask_hdf5_path,
            gain_filename=gain_map_filename,
            gain_hdf5_path=gain_map_hdf5_path,
        )

        pf8_detector_info = cryst_algs.get_peakfinder8_info(
            self._monitor_params.get_param(
                group="peakfinder8_peak_detection",
                parameter="detector_type",
                parameter_type=str,
                required=True,
            )
        )
        pf8_max_num_peaks = self._monitor_params.get_param(
            group="peakfinder8_peak_detection",
            parameter="max_num_peaks",
            parameter_type=int,
            required=True,
        )  # type: int
        pf8_adc_threshold = self._monitor_params.get_param(
            group="peakfinder8_peak_detection",
            parameter="adc_threshold",
            parameter_type=float,
            required=True,
        )  # type: float
        pf8_minimum_snr = self._monitor_params.get_param(
            group="peakfinder8_peak_detection",
            parameter="minimum_snr",
            parameter_type=float,
            required=True,
        )  # type: float
        pf8_min_pixel_count = self._monitor_params.get_param(
            group="peakfinder8_peak_detection",
            parameter="min_pixel_count",
            parameter_type=int,
            required=True,
        )  # type: int
        pf8_max_pixel_count = self._monitor_params.get_param(
            group="peakfinder8_peak_detection",
            parameter="max_pixel_count",
            parameter_type=int,
            required=True,
        )  # type: int
        pf8_local_bg_radius = self._monitor_params.get_param(
            group="peakfinder8_peak_detection",
            parameter="local_bg_radius",
            parameter_type=int,
            required=True,
        )  # type: int
        pf8_min_res = self._monitor_params.get_param(
            group="peakfinder8_peak_detection",
            parameter="min_res",
            parameter_type=int,
            required=True,
        )  # type: int
        pf8_max_res = self._monitor_params.get_param(
            group="peakfinder8_peak_detection",
            parameter="max_res",
            parameter_type=int,
            required=True,
        )  # type: int
        pf8_bad_pixel_map_fname = self._monitor_params.get_param(
            group="peakfinder8_peak_detection",
            parameter="bad_pixel_map_filename",
            parameter_type=str,
        )  # type: Union[str, None]
        if pf8_bad_pixel_map_fname is not None:
            pf8_bad_pixel_map_hdf5_path = self._monitor_params.get_param(
                group="peakfinder8_peak_detection",
                parameter="bad_pixel_map_hdf5_path",
                parameter_type=str,
                required=True,
            )  # type: Union[str, None]
        else:
            pf8_bad_pixel_map_hdf5_path = None

        if pf8_bad_pixel_map_fname is not None:
            try:
                with h5py.File(pf8_bad_pixel_map_fname, "r") as hdf5_file_handle:
                    bad_pixel_map = hdf5_file_handle[pf8_bad_pixel_map_hdf5_path][
                        :
                    ]  # type: Union[numpy.ndarray, None]
            except (IOError, OSError, KeyError) as exc:
                exc_type, exc_value = sys.exc_info()[
                    :2
                ]  # type: Union[Type[BaseException], None], Union[BaseException, None]
                raise_from(
                    # TODO: Fix type check
                    exc=RuntimeError(
                        "The following error occurred while reading the {0} field"
                        "from the {1} bad pixel map HDF5 file:"
                        "{2}: {3}".format(
                            pf8_bad_pixel_map_fname,
                            pf8_bad_pixel_map_hdf5_path,
                            exc_type.__name__,  # type: ignore
                            exc_value,
                        )
                    ),
                    cause=exc,
                )
        else:
            bad_pixel_map = None

        self._peak_detection = cryst_algs.Peakfinder8PeakDetection(
            max_num_peaks=pf8_max_num_peaks,
            asic_nx=pf8_detector_info["asic_nx"],
            asic_ny=pf8_detector_info["asic_ny"],
            nasics_x=pf8_detector_info["nasics_x"],
            nasics_y=pf8_detector_info["nasics_y"],
            adc_threshold=pf8_adc_threshold,
            minimum_snr=pf8_minimum_snr,
            min_pixel_count=pf8_min_pixel_count,
            max_pixel_count=pf8_max_pixel_count,
            local_bg_radius=pf8_local_bg_radius,
            min_res=pf8_min_res,
            max_res=pf8_max_res,
            bad_pixel_map=bad_pixel_map,
            radius_pixel_map=self._pixelmaps["radius"],
        )  # type: cryst_algs.Peakfinder8PeakDetection

        self._min_num_peaks_for_hit = self._monitor_params.get_param(
            group="crystallography",
            parameter="min_num_peaks_for_hit",
            parameter_type=int,
            required=True,
        )  # type: int
        self._max_num_peaks_for_hit = self._monitor_params.get_param(
            group="crystallography",
            parameter="max_num_peaks_for_hit",
            parameter_type=int,
            required=True,
        )  # type: int
        self._hit_frame_sending_interval = self._monitor_params.get_param(
            group="crystallography",
            parameter="hit_frame_sending_interval",
            parameter_type=int,
        )  # type Union[int, None]
        self._non_hit_frame_sending_interval = self._monitor_params.get_param(
            group="crystallography",
            parameter="non_hit_frame_sending_interval",
            parameter_type=int,
        )  # type Union[int, None]

        print("Processing node {0} starting.".format(node_rank))
        sys.stdout.flush()

    def initialize_collecting_node(self, node_rank, node_pool_size):
        # type: (int, int) -> None
        """
        Initializes the OM nodes for the Crystallography monitor.

        See documentation of the function in the base class:
        :func:`~om.processing_layer.base.OmMonitor`.

        On the processing nodes, it initializes the correction and peak finding
        algorithms, plus some internal counters. On the collecting node, this function
        initializes the data accumulation algorrithms and the storage for the
        aggregated statistics.
        """
        self._speed_report_interval = self._monitor_params.get_param(
            group="crystallography",
            parameter="speed_report_interval",
            parameter_type=int,
            required=True,
        )  # type: int
        self._geometry_is_optimized = self._monitor_params.get_param(
            group="crystallography",
            parameter="geometry_is_optimized",
            parameter_type=bool,
            required=True,
        )  # type: bool

        # Theoretically, the pixel size could be different for every module of the
        # detector. The pixel size of the first module is taken as the pixel size
        # of the whole detector.
        geometry_filename = self._monitor_params.get_param(
            group="crystallography",
            parameter="geometry_file",
            parameter_type=str,
            required=True,
        )  # type: str
        geometry, _, __ = crystfel_geometry.load_crystfel_geometry(
            geometry_filename
        )  # type: Tuple[TypeDetector, TypeBeam, Union[str, None]]
        self._pixelmaps = crystfel_geometry.compute_pix_maps(geometry)
        self._pixel_size = geometry["panels"][tuple(geometry["panels"].keys())[0]][
            "res"
        ]

        self._running_average_window_size = self._monitor_params.get_param(
            group="crystallography",
            parameter="running_average_window_size",
            parameter_type=int,
            required=True,
        )  # type: int
        self._hit_rate_running_window = collections.deque(
            [0.0] * self._running_average_window_size,
            maxlen=self._running_average_window_size,
        )  # type: Deque[float]
        self._avg_hit_rate = 0  # type: int
        self._hit_rate_timestamp_history = collections.deque(
            5000 * [0.0], maxlen=5000
        )  # type: Deque[float]
        self._hit_rate_history = collections.deque(
            5000 * [0.0], maxlen=5000
        )  # type: Deque[float]

        y_minimum = (
            2
            * int(max(abs(self._pixelmaps["y"].max()), abs(self._pixelmaps["y"].min())))
            + 2
        )  # type: int
        x_minimum = (
            2
            * int(max(abs(self._pixelmaps["x"].max()), abs(self._pixelmaps["x"].min())))
            + 2
        )  # type: int
        visual_img_shape = (y_minimum, x_minimum)
        self._img_center_x = int(visual_img_shape[1] / 2)
        self._img_center_y = int(visual_img_shape[0] / 2)
        self._visual_pixelmap_x = (
            numpy.array(self._pixelmaps["x"], dtype=numpy.int)
            + visual_img_shape[1] // 2
            - 1
        ).flatten()  # type: numpy.ndarray
        self._visual_pixelmap_y = (
            numpy.array(self._pixelmaps["y"], dtype=numpy.int)
            + visual_img_shape[0] // 2
            - 1
        ).flatten()  # type: numpy.ndarray
        self._virt_powd_plot_img = numpy.zeros(
            visual_img_shape, dtype=numpy.int32
        )  # type: numpy.ndarray
        self._frame_data_img = numpy.zeros(
            visual_img_shape, dtype=numpy.float32
        )  # type: numpy.ndarray

        data_broadcast_url = self._monitor_params.get_param(
            group="crystallography", parameter="data_broadcast_url", parameter_type=str
        )  # type: Union[str, None]
        self._data_broadcast_socket = zmq_monitor.ZmqDataBroadcaster(
            url=data_broadcast_url
        )  # type: zmq_monitor.ZmqDataBroadcaster

        self._num_events = 0  # type: int
        self._old_time = time.time()  # type: float
        self._time = None  # type: Union[float, None]

        print("Starting the monitor...")
        sys.stdout.flush()

    def process_data(self, node_rank, node_pool_size, data):
        # type: (int, int, Dict[str, Any]) -> Tuple[Dict[str, Any], int]
        """
        Processes a detector data frame.

        See documentation of the function in the base class:
        :func:`~om.processing_layer.base.OmMonitor.process_data`.

        This function performs calibration and correction of a detector data frame and
        extracts Bragg peak information. Finally, it prepares the Bragg peak data (and
        optionally, the detector frame data) for transmission to to the collecting
        node.
        """
        processed_data = {}  # type: Dict[str, Any]
        corrected_detector_data = self._correction.apply_correction(
            data=data["detector_data"]
        )  # type: numpy.ndarray
        peak_list = self._peak_detection.find_peaks(
            corrected_detector_data
        )  # Tuple[List[float], ...]
        frame_is_hit = (
            self._min_num_peaks_for_hit
            < len(peak_list["intensity"])
            < self._max_num_peaks_for_hit
        )  # type: bool

        processed_data["timestamp"] = data["timestamp"]
        processed_data["frame_is_hit"] = frame_is_hit
        processed_data["detector_distance"] = data["detector_distance"]
        # processed_data["detector_distance"] = 300
        processed_data["beam_energy"] = data["beam_energy"]
        # processed_data["beam_energy"] = 10000
        processed_data["data_shape"] = data["detector_data"].shape
        if frame_is_hit:
            processed_data["peak_list"] = peak_list
            if self._hit_frame_sending_interval is not None:
                self._hit_frame_sending_counter += 1
                if self._hit_frame_sending_counter == self._hit_frame_sending_interval:
                    # If the frame is a hit, and if the 'hit_sending_interval'
                    # attribute says that the detector frame data should be sent to
                    # the collecting node, adds the data to the 'processed_data'
                    # dictionary (and resets the counter).
                    processed_data["detector_data"] = corrected_detector_data
                    self._hit_frame_sending_counter = 0
        else:
            # If the frame is not a hit, sends an empty peak list.
            processed_data["peak_list"] = {"fs": [], "ss": [], "intensity": []}
            if self._non_hit_frame_sending_interval is not None:
                self._non_hit_frame_sending_counter += 1
                if (
                    self._non_hit_frame_sending_counter
                    == self._non_hit_frame_sending_interval
                ):
                    # If the frame is a not a hit, and if the 'hit_sending_interval'
                    # attribute says that the detector frame data should be sent to
                    # the collecting node, adds the data to the 'processed_data'
                    # dictionary (and resets the counter).
                    processed_data["detector_data"] = corrected_detector_data
                    self._non_hit_frame_sending_counter = 0

        return (processed_data, node_rank)

    def collect_data(self, node_rank, node_pool_size, processed_data):
        # type: (int, int, Tuple[Dict[str, Any], int]) -> None
        """
        Computes statistics on aggregated data and broadcasts them via a network socket.

        See documentation of the function in the base class:
        :func:`~om.processing_layer.base.OmMonitor.collect_data`.

        This function computes aggregated statistics on data received from the
        processing nodes. It then broadcasts the results via a network socket (for
        visualization by other programs) using the MessagePack protocol.
        """
        received_data = processed_data[0]  # type: Dict[str, Any]
        self._num_events += 1

        self._hit_rate_running_window.append(float(received_data["frame_is_hit"]))
        avg_hit_rate = (
            sum(self._hit_rate_running_window) / self._running_average_window_size
        )  # type: float
        self._hit_rate_timestamp_history.append(received_data["timestamp"])
        self._hit_rate_history.append(avg_hit_rate * 100.0)

        peak_list_x_in_frame = []  # type: List[float]
        peak_list_y_in_frame = []  # type: List[float]

        for peak_fs, peak_ss, peak_value in zip(
            received_data["peak_list"]["fs"],
            received_data["peak_list"]["ss"],
            received_data["peak_list"]["intensity"],
        ):
            peak_index_in_slab = int(round(peak_ss)) * received_data["data_shape"][
                1
            ] + int(
                round(peak_fs)
            )  # type: int
            y_in_frame = self._visual_pixelmap_y[peak_index_in_slab]  # type: float
            x_in_frame = self._visual_pixelmap_x[peak_index_in_slab]  # type: float
            peak_list_x_in_frame.append(y_in_frame)
            peak_list_y_in_frame.append(x_in_frame)
            self._virt_powd_plot_img[y_in_frame, x_in_frame] += peak_value

        self._data_broadcast_socket.send_data(
            tag="view:omdata",
            message={
                "geometry_is_optimized": self._geometry_is_optimized,
                "timestamp": received_data["timestamp"],
                "hit_rate_timestamp_history": self._hit_rate_timestamp_history,
                "hit_rate_history": self._hit_rate_history,
                "virtual_powder_plot": self._virt_powd_plot_img,
                "beam_energy": received_data["beam_energy"],
                "detector_distance": received_data["detector_distance"],
                "pixel_size": self._pixel_size,
            },
        )

        if "detector_data" in received_data:
            # If detector frame data is found in the data received from the processing
            # node, it must be broadcasted to visualization programs. The frame is
            # wrapped into a list because the receiving programs usually expect lists
            # of aggregated events as opposed to single events.

            self._frame_data_img[self._visual_pixelmap_y, self._visual_pixelmap_x] = (
                received_data["detector_data"]
                .ravel()
                .astype(self._frame_data_img.dtype)
            )

            self._data_broadcast_socket.send_data(
                tag=u"view:omframedata",
                message={
                    "frame_data": self._frame_data_img,
                    "timestamp": received_data["timestamp"],
                    "peak_list_x_in_frame": peak_list_x_in_frame,
                    "peak_list_y_in_frame": peak_list_y_in_frame,
                },
            )
            self._data_broadcast_socket.send_data(
                tag=u"view:omtweakingdata",
                message={
                    "detector_data": received_data["detector_data"],
                    "timestamp": received_data["timestamp"],
                },
            )

        if self._num_events % self._speed_report_interval == 0:
            now_time = time.time()  # type: float
            speed_report_msg = "Processed: {0} in {1:.2f} seconds ({2:.2f} Hz)".format(
                self._num_events,
                now_time - self._old_time,
                (float(self._speed_report_interval) / float(now_time - self._old_time)),
            )  # type: str

            print(speed_report_msg)
            sys.stdout.flush()
            self._old_time = now_time

    def end_processing_on_processing_node(self, node_rank, rank_pool_size):
        # type: (int, int) -> None
        """
        Executes end-of-processing actions on the processing nodes.

        See documentation of the function in the base class:
        :func:`~om.processing_layer.base.OmMonitor.end_processing_on_processing_node`.

        Prints a message on the console and ends processing.
        """
        print("Processing node {0} shutting down.".format(node_rank))
        sys.stdout.flush()

    def end_processing_on_collecting_node(self, node_rank, rank_pool_size):
        # type: (int, int) -> None
        """
        Executes end-of-processing actions on the processing nodes.

        See documentation of the function in the base class:
        :func:`~om.processing_layer.base.OmMonitor.end_processing_on_processing_node`.

        Prints a message on the console and ends processing.
        """
        print(node_rank)
        print(
            "Processing finished. OM has processed {0} events in total.".format(
                self._num_events
            )
        )
        sys.stdout.flush()
