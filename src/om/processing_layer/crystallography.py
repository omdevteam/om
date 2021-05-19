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
OnDA Monitor for Crystallography.

This module contains an OnDA Monitor for serial x-ray crystallography experiments.
"""
import collections
import sys
import time
from typing import Any, Deque, Dict, List, Tuple, Union

import h5py  # type: ignore
import numpy  # type: ignore

from om.algorithms import crystallography as cryst_algs
from om.algorithms import generic as gen_algs
from om.processing_layer import base as process_layer_base
from om.utils import crystfel_geometry, exceptions, parameters, zmq_monitor
from om.utils.crystfel_geometry import TypeDetector, TypePixelMaps
from om.algorithms.crystallography import TypePeakfinder8Info

try:
    import msgpack  # type: ignore
except ImportError:
    raise exceptions.OmMissingDependencyError(
        "The following required module cannot be imported: msgpack"
    )


class CrystallographyMonitor(process_layer_base.OmMonitor):
    """
    See documentation for the `__init__` function.

    Base class: [`OmMonitor`][om.processing_layer.base.OmMonitor]
    """

    def __init__(self, monitor_parameters: parameters.MonitorParams) -> None:
        """
        OnDA real-time Monitor for serial x-ray crystallography experiments.

        This class contains an OnDA Monitor that processes detector data frames,
        optionally applying detector calibration, dark correction and gain correction.
        The Monitor then detects Bragg peaks in each detector frame using the
        'peakfinder8' peak detection algorithm from the Cheetah software package. It
        retrieves information about the location, size and intensity of each peak.
        Additionally, it calculates the evolution of the hit rate over time. It
        broadcasts all this information over a network socket for visualization by
        other programs. This OnDA Monitor can also optionally broadcast calibrated and
        corrected detector data frames to be displayed by an external program.

        This class is a subclass of the [OmMonitor][om.processing_layer.base.OmMonitor]
        base class.

        Arguments:

          monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.
        """
        super(CrystallographyMonitor, self).__init__(
            monitor_parameters=monitor_parameters
        )

    def initialize_processing_node(self, node_rank: int, node_pool_size: int) -> None:
        """
        Initializes the OM processing nodes for the Crystallography Monitor.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the correction and peak finding algorithms, plus some
        internal counters.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        geometry_filename: str = self._monitor_params.get_param(
            group="crystallography",
            parameter="geometry_file",
            parameter_type=str,
            required=True,
        )
        geometry: crystfel_geometry.TypeDetector
        _: Any
        __: Any
        geometry, _, __ = crystfel_geometry.load_crystfel_geometry(geometry_filename)
        self._pixelmaps: TypePixelMaps = crystfel_geometry.compute_pix_maps(geometry)

        self._hit_frame_sending_counter: int = 0
        self._non_hit_frame_sending_counter: int = 0

        dark_data_filename: str = self._monitor_params.get_param(
            group="correction", parameter="dark_filename", parameter_type=str
        )
        dark_data_hdf5_path: str = self._monitor_params.get_param(
            group="correction", parameter="dark_hdf5_path", parameter_type=str
        )
        mask_filename: str = self._monitor_params.get_param(
            group="correction", parameter="mask_filename", parameter_type=str
        )
        mask_hdf5_path: str = self._monitor_params.get_param(
            group="correction", parameter="mask_hdf5_path", parameter_type=str
        )
        gain_map_filename: str = self._monitor_params.get_param(
            group="correction", parameter="gain_filename", parameter_type=str
        )
        gain_map_hdf5_path: str = self._monitor_params.get_param(
            group="correction", parameter="gain_hdf5_path", parameter_type=str
        )
        self._correction = gen_algs.Correction(
            dark_filename=dark_data_filename,
            dark_hdf5_path=dark_data_hdf5_path,
            mask_filename=mask_filename,
            mask_hdf5_path=mask_hdf5_path,
            gain_filename=gain_map_filename,
            gain_hdf5_path=gain_map_hdf5_path,
        )

        pf8_detector_info: TypePeakfinder8Info = cryst_algs.get_peakfinder8_info(
            self._monitor_params.get_param(
                group="peakfinder8_peak_detection",
                parameter="detector_type",
                parameter_type=str,
                required=True,
            )
        )
        pf8_max_num_peaks: int = self._monitor_params.get_param(
            group="peakfinder8_peak_detection",
            parameter="max_num_peaks",
            parameter_type=int,
            required=True,
        )
        pf8_adc_threshold: float = self._monitor_params.get_param(
            group="peakfinder8_peak_detection",
            parameter="adc_threshold",
            parameter_type=float,
            required=True,
        )
        pf8_minimum_snr: float = self._monitor_params.get_param(
            group="peakfinder8_peak_detection",
            parameter="minimum_snr",
            parameter_type=float,
            required=True,
        )
        pf8_min_pixel_count: int = self._monitor_params.get_param(
            group="peakfinder8_peak_detection",
            parameter="min_pixel_count",
            parameter_type=int,
            required=True,
        )
        pf8_max_pixel_count: int = self._monitor_params.get_param(
            group="peakfinder8_peak_detection",
            parameter="max_pixel_count",
            parameter_type=int,
            required=True,
        )
        pf8_local_bg_radius: int = self._monitor_params.get_param(
            group="peakfinder8_peak_detection",
            parameter="local_bg_radius",
            parameter_type=int,
            required=True,
        )
        pf8_min_res: int = self._monitor_params.get_param(
            group="peakfinder8_peak_detection",
            parameter="min_res",
            parameter_type=int,
            required=True,
        )
        pf8_max_res: int = self._monitor_params.get_param(
            group="peakfinder8_peak_detection",
            parameter="max_res",
            parameter_type=int,
            required=True,
        )
        pf8_bad_pixel_map_fname: Union[str, None] = self._monitor_params.get_param(
            group="peakfinder8_peak_detection",
            parameter="bad_pixel_map_filename",
            parameter_type=str,
        )
        if pf8_bad_pixel_map_fname is not None:
            pf8_bad_pixel_map_hdf5_path: Union[
                str, None
            ] = self._monitor_params.get_param(
                group="peakfinder8_peak_detection",
                parameter="bad_pixel_map_hdf5_path",
                parameter_type=str,
                required=True,
            )
        else:
            pf8_bad_pixel_map_hdf5_path = None

        if pf8_bad_pixel_map_fname is not None:
            try:
                map_hdf5_file_handle: Any
                with h5py.File(pf8_bad_pixel_map_fname, "r") as map_hdf5_file_handle:
                    bad_pixel_map: Union[numpy.ndarray, None] = map_hdf5_file_handle[
                        pf8_bad_pixel_map_hdf5_path
                    ][:]
            except (IOError, OSError, KeyError) as exc:
                exc_type, exc_value = sys.exc_info()[:2]
                # TODO: Fix type check
                raise RuntimeError(
                    "The following error occurred while reading the {0} field from"
                    "the {1} bad pixel map HDF5 file:"
                    "{2}: {3}".format(
                        pf8_bad_pixel_map_fname,
                        pf8_bad_pixel_map_hdf5_path,
                        exc_type.__name__,  # type: ignore
                        exc_value,
                    )
                ) from exc
        else:
            bad_pixel_map = None

        self._peak_detection: cryst_algs.Peakfinder8PeakDetection = (
            cryst_algs.Peakfinder8PeakDetection(
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
            )
        )

        self._min_num_peaks_for_hit: int = self._monitor_params.get_param(
            group="crystallography",
            parameter="min_num_peaks_for_hit",
            parameter_type=int,
            required=True,
        )
        self._max_num_peaks_for_hit: int = self._monitor_params.get_param(
            group="crystallography",
            parameter="max_num_peaks_for_hit",
            parameter_type=int,
            required=True,
        )
        self._hit_frame_sending_interval: Union[
            int, None
        ] = self._monitor_params.get_param(
            group="crystallography",
            parameter="hit_frame_sending_interval",
            parameter_type=int,
        )
        self._non_hit_frame_sending_interval: Union[
            int, None
        ] = self._monitor_params.get_param(
            group="crystallography",
            parameter="non_hit_frame_sending_interval",
            parameter_type=int,
        )

        print("Processing node {0} starting.".format(node_rank))
        sys.stdout.flush()

    def initialize_collecting_node(self, node_rank: int, node_pool_size: int) -> None:
        """
        Initializes the OM collecting node for the Crystallography Monitor.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the data accumulation algorithms and the storage
        buffers used to compute statistics on the detected Bragg peaks. Additionally,
        it prepares the data broadcasting socket to send data to external programs.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        self._speed_report_interval: int = self._monitor_params.get_param(
            group="crystallography",
            parameter="speed_report_interval",
            parameter_type=int,
            required=True,
        )

        self._data_broadcast_interval: int = self._monitor_params.get_param(
            group="crystallography",
            parameter="data_broadcast_interval",
            parameter_type=int,
            required=True,
        )

        self._geometry_is_optimized: bool = self._monitor_params.get_param(
            group="crystallography",
            parameter="geometry_is_optimized",
            parameter_type=bool,
            required=True,
        )

        geometry_filename: str = self._monitor_params.get_param(
            group="crystallography",
            parameter="geometry_file",
            parameter_type=str,
            required=True,
        )
        geometry: TypeDetector
        self._geometry, _, __ = crystfel_geometry.load_crystfel_geometry(
            geometry_filename
        )
        self._pixelmaps = crystfel_geometry.compute_pix_maps(self._geometry)

        # Theoretically, the pixel size could be different for every module of the
        # detector. The pixel size of the first module is taken as the pixel size
        # of the whole detector.
        self._pixel_size: float = self._geometry["panels"][
            tuple(self._geometry["panels"].keys())[0]
        ]["res"]

        self._running_average_window_size: int = self._monitor_params.get_param(
            group="crystallography",
            parameter="running_average_window_size",
            parameter_type=int,
            required=True,
        )
        self._hit_rate_running_window: Deque[float] = collections.deque(
            [0.0] * self._running_average_window_size,
            maxlen=self._running_average_window_size,
        )
        self._avg_hit_rate: int = 0
        self._hit_rate_timestamp_history: Deque[float] = collections.deque(
            5000 * [0.0], maxlen=5000
        )
        self._hit_rate_history: Deque[float] = collections.deque(
            5000 * [0.0], maxlen=5000
        )

        y_minimum: int = (
            2
            * int(max(abs(self._pixelmaps["y"].max()), abs(self._pixelmaps["y"].min())))
            + 2
        )
        x_minimum: int = (
            2
            * int(max(abs(self._pixelmaps["x"].max()), abs(self._pixelmaps["x"].min())))
            + 2
        )
        visual_img_shape: Tuple[int, int] = (y_minimum, x_minimum)
        self._img_center_x: int = int(visual_img_shape[1] / 2)
        self._img_center_y: int = int(visual_img_shape[0] / 2)
        self._visual_pixelmap_x: numpy.ndarray = (
            numpy.array(self._pixelmaps["x"], dtype=numpy.int)
            + visual_img_shape[1] // 2
            - 1
        ).flatten()
        self._visual_pixelmap_y: numpy.ndarray = (
            numpy.array(self._pixelmaps["y"], dtype=numpy.int)
            + visual_img_shape[0] // 2
            - 1
        ).flatten()
        self._virt_powd_plot_img: numpy.ndarray = numpy.zeros(
            visual_img_shape, dtype=numpy.int32
        )
        self._frame_data_img: numpy.ndarray = numpy.zeros(
            visual_img_shape, dtype=numpy.float32
        )

        first_panel: str = list(self._geometry["panels"].keys())[0]
        self._first_panel_coffset: float = self._geometry["panels"][first_panel][
            "coffset"
        ]

        data_broadcast_url: Union[str, None] = self._monitor_params.get_param(
            group="crystallography", parameter="data_broadcast_url", parameter_type=str
        )
        if data_broadcast_url is None:
            data_broadcast_url = "tcp://{0}:12321".format(
                zmq_monitor.get_current_machine_ip()
            )
        responding_url: Union[str, None] = self._monitor_params.get_param(
            group="crystallography", parameter="responding_url", parameter_type=str
        )
        if responding_url is None:
            responding_url = "tcp://{0}:12322".format(
                zmq_monitor.get_current_machine_ip()
            )

        self._data_broadcast_socket: zmq_monitor.ZmqDataBroadcaster = (
            zmq_monitor.ZmqDataBroadcaster(url=data_broadcast_url)
        )

        self._responding_socket: zmq_monitor.ZmqResponder = zmq_monitor.ZmqResponder(
            url=responding_url
        )

        self._num_events: int = 0
        self._old_time: float = time.time()
        self._time: Union[float, None] = None

        print("Starting the monitor...")
        sys.stdout.flush()

    def process_data(
        self, node_rank: int, node_pool_size: int, data: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], int]:
        """
        Processes a detector data frame and extracts Bragg peak information.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function performs calibration and correction of a detector data frame and
        extracts Bragg peak information. Finally, it prepares the Bragg peak data (and
        optionally, the detector frame data) for transmission to to the collecting
        node.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

            data: A dictionary containing the data retrieved by OM for the frame being
                processed.

                * The dictionary keys must match the entries in the 'required_data'
                  list found in the 'om' parameter group in the configuration file.

                * The corresponding dictionary values must store the retrieved data.

        Returns:

            A tuple whose first entry is a dictionary storing the data that should be
            sent to the collecting node, and whose second entry is the OM rank number
            of the node that processed the information.
        """
        processed_data: Dict[str, Any] = {}
        corrected_detector_data: numpy.ndarray = self._correction.apply_correction(
            data=data["detector_data"]
        )
        peak_list: cryst_algs.TypePeakList = self._peak_detection.find_peaks(
            corrected_detector_data
        )
        frame_is_hit: bool = (
            self._min_num_peaks_for_hit
            < len(peak_list["intensity"])
            < self._max_num_peaks_for_hit
        )

        processed_data["timestamp"] = data["timestamp"]
        processed_data["frame_is_hit"] = frame_is_hit
        processed_data["detector_distance"] = data["detector_distance"]
        processed_data["beam_energy"] = data["beam_energy"]
        processed_data["event_id"] = data["event_id"]
        processed_data["frame_id"] = data["frame_id"]
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

    def collect_data(
        self,
        node_rank: int,
        node_pool_size: int,
        processed_data: Tuple[Dict[str, Any], int],
    ) -> None:
        """
        Computes aggregated Bragg peak data and broadcasts it over the network.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function collects the Bragg peak information from the processing nodes and
        computes the average hit rate and a virtual powder pattern. It then broadcasts
        this information over a network socket for visualization by external programs.
        This function also broadcasts any detector frame data received from the
        processing nodes.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

            processed_data (Tuple[Dict, int]): a tuple whose first entry is a
                dictionary storing the data received from a processing node, and whose
                second entry is the OM rank number of the node that processed the
                information.
        """
        received_data: Dict[str, Any] = processed_data[0]
        self._num_events += 1

        if received_data["frame_is_hit"] is True:
            request: Union[str, None] = self._responding_socket.get_request()
            if request is not None:
                if request == "next":
                    message: Any = msgpack.packb(
                        {
                            "peak_list": received_data["peak_list"],
                            "beam_energy": received_data["beam_energy"],
                            "detector_distance": received_data["detector_distance"],
                            "event_id": received_data["event_id"],
                            "frame_id": received_data["frame_id"],
                            "timestamp": received_data["timestamp"],
                        },
                        use_bin_type=True,
                    )
                    self._responding_socket.send_data(message)
                else:
                    print("OM Warning: Could not understand request '{}'.")

        self._hit_rate_running_window.append(float(received_data["frame_is_hit"]))
        avg_hit_rate: float = (
            sum(self._hit_rate_running_window) / self._running_average_window_size
        )
        self._hit_rate_timestamp_history.append(received_data["timestamp"])
        self._hit_rate_history.append(avg_hit_rate * 100.0)

        peak_list_x_in_frame: List[float] = []
        peak_list_y_in_frame: List[float] = []
        peak_fs: float
        peak_ss: float
        peak_value: float
        for peak_fs, peak_ss, peak_value in zip(
            received_data["peak_list"]["fs"],
            received_data["peak_list"]["ss"],
            received_data["peak_list"]["intensity"],
        ):
            peak_index_in_slab: int = int(round(peak_ss)) * received_data["data_shape"][
                1
            ] + int(round(peak_fs))
            y_in_frame: float = self._visual_pixelmap_y[peak_index_in_slab]
            x_in_frame: float = self._visual_pixelmap_x[peak_index_in_slab]
            peak_list_x_in_frame.append(y_in_frame)
            peak_list_y_in_frame.append(x_in_frame)
            self._virt_powd_plot_img[y_in_frame, x_in_frame] += peak_value

        if self._num_events % self._data_broadcast_interval == 0:
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
                    "first_panel_coffset": self._first_panel_coffset,
                    "pixel_size": self._pixel_size,
                },
            )

            if "detector_data" in received_data:
                # If detector frame data is found in the data received from the
                # processing node, it must be broadcasted to visualization programs.

                self._frame_data_img[
                    self._visual_pixelmap_y, self._visual_pixelmap_x
                ] = (
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
        self, node_rank: int, node_pool_size: int
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
        self, node_rank: int, node_pool_size: int
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
