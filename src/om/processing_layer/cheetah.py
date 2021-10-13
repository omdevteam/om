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
Cheetah

This module contains the implementation of Cheetah, a data processing program for
serial x-ray crystallography experiments based on OM.
"""
import collections
import pathlib
import sys
import time
from typing import Any, Deque, Dict, List, TextIO, Tuple, Union

import h5py  # type: ignore
import numpy  # type: ignore

from om.algorithms import crystallography as cryst_algs
from om.algorithms import generic as gen_algs
from om.algorithms.crystallography import TypePeakfinder8Info
from om.processing_layer import base as process_layer_base
from om.utils import crystfel_geometry, hdf5_writers, parameters, zmq_monitor
from om.utils.crystfel_geometry import TypePixelMaps


class CheetahProcessing(process_layer_base.OmProcessing):
    """
    See documentation for the `__init__` function.

    Base class: [`OmProcessing`][om.processing_layer.base.OmProcessing]
    """

    def __init__(self, *, monitor_parameters: parameters.MonitorParams) -> None:
        """
        Cheetah processing layer for serial crystallography experiments.

        This class contains the implementation of the Cheetah software package. Cheetah
        processes detector data frames, optionally applying detector calibration, dark
        correction and gain correction. It then detects Bragg peaks in each detector
        frame using the 'peakfinder8' peak detection algorithm. It retrieves
        information about the location, size, intensity, SNR and the maximum pixel
        value of each peak. Cheetah then saves the calibrated and corrected detector
        data, plus all the experiment-related information retrieved from the facility
        or extracted from the data in multi-event HDF5 files. In addition to saving
        individual frames, Cheetah can write compute and save sums of frames identified
        as hits and non-hits, together with virtual powder patterns,  into separate
        HDF5 "sum files".

        Cheetah can also optionally broadcast detector data, Bragg peaks and hit-rate
        information over a network socket for monitoring and visualization by other
        programs, mimicking the functionality of a regular real-time OnDA Monitor.

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
        Initializes the OM processing nodes for Cheetah.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the correction and peak finding algorithms, the HDF5
        file writer plus some internal counters.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        self._geometry: TypeDetector
        self._geometry, _, __ = crystfel_geometry.load_crystfel_geometry(
            filename=self._monitor_params.get_parameter(
                group="crystallography",
                parameter="geometry_file",
                parameter_type=str,
                required=True,
            )
        )
        self._pixelmaps = crystfel_geometry.compute_pix_maps(geometry=self._geometry)
        self._data_shape: Tuple[int, int] = self._pixelmaps["x"].shape

        # TODO: Type this dictionary
        self._total_sums: List[Dict[str, Any]] = [
            {
                "num_frames": 0,
                "sum_frames": numpy.zeros(self._data_shape, dtype=numpy.float64),
            }
            for class_number in range(2)
        ]
        self._sum_sending_interval: Union[int, None] = self._monitor_params.get_parameter(
            group="cheetah",
            parameter="class_sums_sending_interval",
            parameter_type=int,
        )
        self._sum_sending_counter: int = 0

        self._hit_frame_sending_counter: int = 0
        self._non_hit_frame_sending_counter: int = 0

        self._correction = gen_algs.Correction(
            parameters=self._monitor_params.get_parameter_group(group="correction")
        )

        self._peak_detection: cryst_algs.Peakfinder8PeakDetection = (
            cryst_algs.Peakfinder8PeakDetection(
                parameters=self._monitor_params.get_parameter_group(
                    group="peakfinder8_peak_detection"
                ),
                radius_pixel_map=self._pixelmaps["radius"],
            )
        )

        self._min_num_peaks_for_hit: int = self._monitor_params.get_parameter(
            group="crystallography",
            parameter="min_num_peaks_for_hit",
            parameter_type=int,
            required=True,
        )
        self._max_num_peaks_for_hit: int = self._monitor_params.get_parameter(
            group="crystallography",
            parameter="max_num_peaks_for_hit",
            parameter_type=int,
            required=True,
        )
        self._hit_frame_sending_interval: Union[
            int, None
        ] = self._monitor_params.get_parameter(
            group="crystallography",
            parameter="hit_frame_sending_interval",
            parameter_type=int,
        )
        self._non_hit_frame_sending_interval: Union[
            int, None
        ] = self._monitor_params.get_parameter(
            group="crystallography",
            parameter="non_hit_frame_sending_interval",
            parameter_type=int,
        )

        processed_directory: str = self._monitor_params.get_parameter(
            group="cheetah",
            parameter="processed_directory",
            parameter_type=str,
            required=True,
        )
        processed_filename_prefix: Union[str, None] = self._monitor_params.get_parameter(
            group="cheetah",
            parameter="processed_filename_prefix",
            parameter_type=str,
        )
        processed_filename_extension: Union[str, None] = self._monitor_params.get_parameter(
            group="cheetah",
            parameter="processed_filename_extension",
            parameter_type=str,
        )
        data_type: Union[str, None] = self._monitor_params.get_parameter(
            group="cheetah",
            parameter="hdf5_file_data_type",
            parameter_type=str,
        )
        compression: Union[str, None] = self._monitor_params.get_parameter(
            group="cheetah",
            parameter="hdf5_file_compression",
            parameter_type=str,
        )
        compression_opts: Union[int, None] = self._monitor_params.get_parameter(
            group="cheetah",
            parameter="hdf5_file_compression_opts",
            parameter_type=int,
        )
        compression_shuffle: Union[bool, None] = self._monitor_params.get_parameter(
            group="cheetah",
            parameter="hdf5_file_compression_shuffle",
            parameter_type=bool,
        )
        hdf5_file_max_num_peaks: Union[int, None] = self._monitor_params.get_parameter(
            group="cheetah",
            parameter="hdf5_file_max_num_peaks",
            parameter_type=int,
        )
        hdf5_fields: Dict[str, str] = self._monitor_params.get_parameter(
            group="cheetah",
            parameter="hdf5_fields",
            parameter_type=dict,
            required=True,
        )
        self._file_writer: hdf5_writers.HDF5Writer = hdf5_writers.HDF5Writer(
            parameters=self._monitor_params.get_parameter_group(
                group="cheetah"
            ),
            detector_data_shape=self._data_shape,
            node_rank=node_rank,
            geometry=self._geometry,
        )

        print("Processing node {0} starting.".format(node_rank))
        sys.stdout.flush()

    def _write_status_file(
        self,
        *,
        status: str = "",
        num_frames: int = 0,
        num_hits: int = 0,
    ) -> None:
        # Writes a status file that the Cheetah GUI from Anton Barty can inspect.

        fh: TextIO
        with open(self._status_filename, "w") as fh:
            fh.write("# Cheetah status\n")
            fh.write("Update time: {}\n".format(time.strftime("%a %b %d %H:%M:%S %Y")))
            dt: int = int(time.time() - self._start_time)
            hours: int
            minutes: int
            hours, minutes = divmod(dt, 3600)
            seconds: int
            minutes, seconds = divmod(minutes, 60)
            fh.write("Elapsed time: {}hr {}min {}sec\n".format(hours, minutes, seconds))
            fh.write("Status: {}\n".format(status))
            fh.write("Frames processed: {}\n".format(num_frames))
            fh.write("Number of hits: {}\n".format(num_hits))
            if status == "Not finished":
                fh.write("ZMQ broadcast URL: {}\n".format(self._data_broadcast_url))

    def initialize_collecting_node(self, node_rank: int, node_pool_size: int) -> None:
        """
        Initializes the OM collecting node for Cheetah.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the data accumulation algorithms, the storage buffers
        used to compute statistics on the detected Bragg peaks and, optionally, the sum
        file writers. Additionally, it prepares the data broadcasting socket to send
        data to external programs.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        self._speed_report_interval: int = self._monitor_params.get_parameter(
            group="crystallography",
            parameter="speed_report_interval",
            parameter_type=int,
            required=True,
        )
        self._data_broadcast_interval: int = self._monitor_params.get_parameter(
            group="crystallography",
            parameter="data_broadcast_interval",
            parameter_type=int,
            required=True,
        )
        self._geometry_is_optimized: bool = self._monitor_params.get_parameter(
            group="crystallography",
            parameter="geometry_is_optimized",
            parameter_type=bool,
            required=True,
        )

        self._geometry: TypeDetector
        self._geometry, _, __ = crystfel_geometry.load_crystfel_geometry(
            filename=self._monitor_params.get_parameter(
                group="crystallography",
                parameter="geometry_file",
                parameter_type=str,
                required=True,
            )
        )
        self._pixelmaps = crystfel_geometry.compute_pix_maps(geometry=self._geometry)
        self._data_shape = self._pixelmaps["x"].shape

        # Theoretically, the pixel size could be different for every module of the
        # detector. The pixel size of the first module is taken as the pixel size
        # of the whole detector.
        self._pixel_size: float = self._geometry["panels"][
            tuple(self._geometry["panels"].keys())[0]
        ]["res"]
        self._first_panel_coffset: float = self._geometry["panels"][
            list(self._geometry["panels"].keys())[0]
        ]["coffset"]

        self._running_average_window_size: int = self._monitor_params.get_parameter(
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

        self._data_broadcast_socket: zmq_monitor.ZmqDataBroadcaster = (
            zmq_monitor.ZmqDataBroadcaster(
                parameters=self._monitor_params.get_parameter_group(
                    group="crystallography"
                )
            )
        )
        # temporary fix because of missing get_broadcast_url() method in ZmqDataBroadcaster
        self._data_broadcast_url = None

        self._num_events = 0  # type: int
        self._num_hits = 0  # type: int
        self._old_time = time.time()  # type: float
        self._time = None  # type: Union[float, None]

        processed_directory: str = self._monitor_params.get_parameter(
            group="cheetah",
            parameter="processed_directory",
            parameter_type=str,
            required=True,
        )
        processed_directory_path: pathlib.Path = pathlib.Path(processed_directory)
        if not processed_directory_path.exists():
            processed_directory_path.mkdir()
        self._frames_filename: pathlib.Path = (
            processed_directory_path.resolve() / "frames.txt"
        )
        self._cleaned_filename: pathlib.Path = (
            processed_directory_path.resolve() / "cleaned.txt"
        )
        self._status_filename: pathlib.Path = (
            processed_directory_path.resolve() / "status.txt"
        )
        self._start_time: float = time.time()
        self._status_file_update_interval: int = self._monitor_params.get_parameter(
            group="cheetah",
            parameter="status_file_update_interval",
            parameter_type=int,
        )
        if self._status_file_update_interval is not None:
            self._write_status_file(status="Not finished")

        self._frame_list: List[Tuple[Any, ...]] = []
        self._write_class_sums: bool = self._monitor_params.get_parameter(
            group="cheetah",
            parameter="write_class_sums",
            parameter_type=bool,
            required=True,
        )
        if self._write_class_sums is True:
            sum_filename_prefix: Union[str, None] = self._monitor_params.get_parameter(
                group="cheetah",
                parameter="class_sum_filename_prefix",
                parameter_type=str,
            )

            class_number: int
            self._sum_writers = [
                hdf5_writers.SumHDF5Writer(
                    directory_for_processed_data=processed_directory,
                    powder_class=class_number,
                    detector_data_shape=self._data_shape,
                    sum_filename_prefix=sum_filename_prefix,
                )
                for class_number in range(2)
            ]
            self._class_sum_update_interval: int = self._monitor_params.get_parameter(
                group="cheetah",
                parameter="class_sums_update_interval",
                parameter_type=int,
                required=True,
            )
            self._class_sum_update_counter: int = 0

        # TODO: Type this dictionary
        self._total_sums = [
            {
                "num_frames": 0,
                "sum_frames": numpy.zeros(self._data_shape, dtype=numpy.float64),
                "peak_powder": numpy.zeros(self._data_shape, dtype=numpy.float64),
            }
            for class_number in range(2)
        ]
        print("Starting the monitor...")
        sys.stdout.flush()

    def process_data(  # noqa: C901
        self, *, node_rank: int, node_pool_size: int, data: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], int]:
        """
        Processes a detector data frame and saves the extracted data to HDF5 file.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function performs calibration and correction of a detector data frame and
        extracts Bragg peak information. It then saves the frame in the output HDF5
        file if it is identified as hit. Finally, it prepares the Bragg peak data (and
        optionally, the detector frame data and accumulated sums of hits and non-hits)
        for transmission to the collecting node.

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
            data=corrected_detector_data
        )
        frame_is_hit: bool = (
            self._min_num_peaks_for_hit
            < len(peak_list["intensity"])
            < self._max_num_peaks_for_hit
        )

        processed_data["timestamp"] = data["timestamp"]
        processed_data["frame_is_hit"] = frame_is_hit
        if "detector_distance" in data.keys():
            processed_data["detector_distance"] = data["detector_distance"]
        else:
            processed_data["detector_distance"] = 300
        if "beam_energy" in data.keys():
            processed_data["beam_energy"] = data["beam_energy"]
        else:
            processed_data["beam_energy"] = 10000
        processed_data["data_shape"] = data["detector_data"].shape
        if "event_id" in data.keys():
            processed_data["event_id"] = data["event_id"]
        else:
            processed_data["event_id"] = None
        if "optical_laser_active" in data.keys():
            processed_data["optical_laser_active"] = data["optical_laser_active"]
        else:
            processed_data["optical_laser_active"] = None
        if "lcls_extra" in data.keys():
            processed_data["lcls_extra"] = data["lcls_extra"]
        processed_data["peak_list"] = peak_list
        processed_data["filename"] = "---"
        processed_data["index"] = -1
        if frame_is_hit:
            data_to_write = {"detector_data": corrected_detector_data}
            data_to_write.update(processed_data)
            self._file_writer.write_frame(processed_data=data_to_write)
            processed_data["filename"] = self._file_writer.get_current_filename()
            processed_data["index"] = self._file_writer.get_num_written_frames()

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

        self._total_sums[frame_is_hit]["num_frames"] += 1
        self._total_sums[frame_is_hit]["sum_frames"] += corrected_detector_data
        if self._sum_sending_interval is not None:
            if self._sum_sending_counter == 0:
                self._sum_to_send: List[Dict[str, Any]] = [
                    {
                        "num_frames": 0,
                        "sum_frames": numpy.zeros(
                            self._data_shape, dtype=numpy.float64
                        ),
                    }
                    for class_number in range(2)
                ]
            self._sum_to_send[frame_is_hit]["num_frames"] += 1
            self._sum_to_send[frame_is_hit]["sum_frames"] += corrected_detector_data
            self._sum_sending_counter += 1
            if self._sum_sending_counter == self._sum_sending_interval:
                self._sum_sending_counter = 0
                processed_data["class_sums"] = self._sum_to_send

        return (processed_data, node_rank)

    def collect_data(  # noqa: C901
        self,
        *,
        node_rank: int,
        node_pool_size: int,
        processed_data: Tuple[Dict[str, Any], int],
    ) -> None:
        """
        Computes aggregated Bragg peak data and broadcasts it over the network.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function collects the Bragg peak information and accumulated sums of
        frames from the processing nodes. It then computes the total sums of hits and
        non-hits detector frames as well as the corresponding virtual powder patterns,
        saving them to HDF5 files. It also optionally writes the number of
        processed events, number of found hits and the elapsed time in a status file.
        External programs can inspect the status file to determine the advancement of
        the processing work.

        This method additionally broadcasts the information about the average hit rate
        and accumulated virtual powder pattern over a network socket for visualization
        by external programs.

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
        if self._write_class_sums and "class_sums" in received_data:
            class_number: int
            for class_number in range(2):
                key: str
                for key in ("num_frames", "sum_frames"):
                    self._total_sums[class_number][key] += received_data["class_sums"][
                        class_number
                    ][key]
            self._class_sum_update_counter += 1

        if "end_processing" in received_data:
            return

        self._num_events += 1
        if received_data["frame_is_hit"]:
            self._num_hits += 1

        self._frame_list.append(
            (
                received_data["timestamp"],
                received_data["event_id"],
                received_data["frame_is_hit"],
                received_data["filename"],
                received_data["index"],
                received_data["peak_list"]["num_peaks"],
                numpy.mean(received_data["peak_list"]["intensity"]),
            )
        )

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

            self._total_sums[received_data["frame_is_hit"]]["peak_powder"][
                int(round(peak_ss))
            ][int(round(peak_fs))] += peak_value

        if (
            self._write_class_sums is True
            and self._class_sum_update_counter == self._class_sum_update_interval
        ):
            self._class_sum_update_counter = 0
            for class_number in range(2):
                self._sum_writers[class_number].write_sums(
                    num_frames=self._total_sums[class_number]["num_frames"],
                    sum_frames=self._total_sums[class_number]["sum_frames"],
                    virtual_powder_pattern=self._total_sums[class_number][
                        "peak_powder"
                    ],
                )
        if (
            self._status_file_update_interval is not None
            and self._num_events % self._status_file_update_interval == 0
        ):
            self._write_status_file(
                status="Not finished",
                num_frames=self._num_events,
                num_hits=self._num_hits,
            )

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
                    tag="view:omframedata",
                    message={
                        "frame_data": self._frame_data_img,
                        "timestamp": received_data["timestamp"],
                        "peak_list_x_in_frame": peak_list_x_in_frame,
                        "peak_list_y_in_frame": peak_list_y_in_frame,
                    },
                )
                self._data_broadcast_socket.send_data(
                    tag="view:omtweakingdata",
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
        self,
        *,
        node_rank: int,
        node_pool_size: int,
    ) -> Union[Dict[str, Any], None]:
        """
        Ends processing actions on the processing nodes.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function prints a message on the console, closes output HDF5 file and ends
        the processing.

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
        print(
            "Processing finished. OM node {0} has processed {1} events in "
            "total.".format(
                node_rank,
                self._total_sums[0]["num_frames"] + self._total_sums[1]["num_frames"],
            )
        )
        sys.stdout.flush()
        if self._file_writer is not None:
            # self._file_writer.write_sums(self._total_sums)
            self._file_writer.close()
        if self._sum_sending_interval is not None and self._sum_sending_counter > 0:
            return {"class_sums": self._sum_to_send, "end_processing": True}
        else:
            return None

    def end_processing_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Ends processing on the collecting node.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function prints a message on the console, writes the final information in
        the status and sums HDF5 files, closes the files and ends the processing.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        if self._write_class_sums:
            class_number: int
            for class_number in range(2):
                self._sum_writers[class_number].write_sums(
                    num_frames=self._total_sums[class_number]["num_frames"],
                    sum_frames=self._total_sums[class_number]["sum_frames"],
                    virtual_powder_pattern=self._total_sums[class_number][
                        "peak_powder"
                    ],
                )
        # TODO: Type this tuple
        frame_list: List[Tuple[Any, ...]] = sorted(self._frame_list)
        if self._status_file_update_interval is not None:
            self._write_status_file(
                status="Finished",
                num_frames=self._num_events,
                num_hits=self._total_sums[1]["num_frames"],
            )
        fh: TextIO
        with open(self._frames_filename, "w") as fh:
            fh.write(
                "# timestamp, event_id, hit, filename, index, num_peaks, "
                "ave_intensity\n"
            )
            frame: Tuple[Any, ...]
            for frame in frame_list:
                fh.write("{}, {}, {}, {}, {}, {}, {}\n".format(*frame))
        with open(self._cleaned_filename, "w") as fh:
            fh.write(
                "# timestamp, event_id, hit, filename, index, num_peaks, "
                "ave_intensity\n"
            )
            for frame in frame_list:
                if frame[2] is True:
                    fh.write("{}, {}, {}, {}, {}, {}, {}\n".format(*frame))
        print("Collecting node shutting down.")
        sys.stdout.flush()
