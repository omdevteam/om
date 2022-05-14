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

This module contains Cheetah, a data-processing program for serial x-ray
crystallography, based on OM but not designed to be run in real time.
"""
import collections
import pathlib
import sys
import time
from typing import Any, Deque, Dict, List, NamedTuple, TextIO, Tuple, Union, cast

import numpy
from numpy.typing import NDArray

from om.algorithms import crystallography as cryst_algs
from om.algorithms import generic as gen_algs
from om.protocols import processing_layer as pl_protocols
from om.utils import (
    crystfel_geometry,
    exceptions,
    hdf5_writers,
    parameters,
    zmq_monitor,
)
from om.utils.crystfel_geometry import TypeDetector
from om.utils.rich_console import console, get_current_timestamp

try:
    from typing import TypedDict
except ImportError:
    from mypy_extensions import TypedDict

try:
    import msgpack  # type: ignore
except ImportError:
    raise exceptions.OmMissingDependencyError(
        "The following required module cannot be imported: msgpack"
    )

try:
    import msgpack_numpy  # type: ignore
except ImportError:
    raise exceptions.OmMissingDependencyError(
        "The following required module cannot be imported: msgpack_numpy"
    )
msgpack_numpy.patch()


class _TypeClassSumData(TypedDict, total=False):
    # This typed dictionary is used internally to store the number of detector frames
    # belonging to a certain data class, their sum and, optionally, the virtual peak
    # powder.
    num_frames: int
    sum_frames: NDArray[numpy.float_]
    peak_powder: NDArray[numpy.float_]


class _TypeFrameListData(NamedTuple):
    # This named tuple is used internally to store frame data which is then written to
    # frames.txt file.
    timestamp: numpy.float64
    event_id: Union[str, None]
    frame_is_hit: int
    filename: str
    index_in_file: int
    num_peaks: int
    average_intensity: numpy.float64


class StreamingCheetahProcessing(pl_protocols.OmProcessing):
    """
    See documentation for the `__init__` function.
    """

    def __init__(self, *, monitor_parameters: parameters.MonitorParams) -> None:
        """
        Cheetah Streaming.

        This Processing class implements the Cheetah software package. Cheetah
        processes detector data frames, optionally applying detector calibration, dark
        correction and gain correction. It then detects Bragg peaks in each detector
        frame using the
        [Peakfinder8PeakDetection][om.algorithms.crystallography.Peakfinder8PeakDetection]
        algorithm, retrieving information about the location, size, intensity, SNR
        and maximum pixel value of each peak. Cheetah then saves the calibrated and
        corrected detector data, plus all the information retrieved from the facility
        or extracted from the data, in multi-event HDF5 files. In addition to saving
        individual frames, Cheetah can optionally compute separate detector frame sums
        for hit and non-hit frames. The sums are saved, together with corresponding
        virtual powder patterns, in HDF5 sum files.

        Arguments:

            monitor_parameters: An object storing OM's configuration parameters.
        """
        self._monitor_params = monitor_parameters

    def initialize_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes the processing nodes for Cheetah.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the correction, peak finding and binning algorithms,
        and some internal counters.

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
        self._data_shape: Tuple[int, ...] = self._pixelmaps["x"].shape

        self._correction = gen_algs.Correction(
            parameters=self._monitor_params.get_parameter_group(group="correction")
        )
        self._peak_detection: cryst_algs.Peakfinder8PeakDetection = (
            cryst_algs.Peakfinder8PeakDetection(
                parameters=self._monitor_params.get_parameter_group(
                    group="peakfinder8_peak_detection"
                ),
                radius_pixel_map=cast(NDArray[numpy.float_], self._pixelmaps["radius"]),
            )
        )
        binning: Union[bool, None] = self._monitor_params.get_parameter(
            group="crystallography",
            parameter="binning",
            parameter_type=bool,
            required=False,
        )
        self._binning_before_peakfinding: Union[
            bool, None
        ] = self._monitor_params.get_parameter(
            group="crystallography",
            parameter="binning_before_peakfinding",
            parameter_type=bool,
            required=False,
        )
        if self._binning_before_peakfinding is None:
            self._binning_before_peakfinding = True
        self._binning: Union[gen_algs.Binning, None]
        if binning:
            self._binning = gen_algs.Binning(
                parameters=self._monitor_params.get_parameter_group(group="binning"),
            )
            if self._binning_before_peakfinding:
                self._peak_detection.set_peakfinder8_info(
                    self._binning.get_binned_layout_info()
                )
                self._peak_detection.set_bad_pixel_map(
                    self._binning.bin_bad_pixel_map(
                        mask=self._peak_detection.get_bad_pixel_map()
                    )
                )
                self._peak_detection.set_radius_pixel_map(
                    cast(
                        NDArray[numpy.float_],
                        self._binning.bin_pixel_maps(pixel_maps=self._pixelmaps),
                    )["radius"]
                )
            self._data_shape = self._binning.get_binned_data_shape()
        else:
            self._binning = None

        class_number: int
        self._total_sums: List[_TypeClassSumData] = [
            {
                "num_frames": 0,
                "sum_frames": numpy.zeros(self._data_shape, dtype=numpy.float64),
            }
            for class_number in range(2)
        ]
        self._sum_sending_interval: Union[
            int, None
        ] = self._monitor_params.get_parameter(
            group="cheetah",
            parameter="class_sums_sending_interval",
            parameter_type=int,
        )
        self._sum_sending_counter: int = 0

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
        console.print(f"{get_current_timestamp()} Processing node {node_rank} starting")
        sys.stdout.flush()

    def _write_status_file(
        self,
        *,
        status: str = "",
        num_frames: int = 0,
        num_hits: int = 0,
    ) -> None:
        # Writes a status file that the Cheetah GUI can inspect.

        fh: TextIO
        time_string: str = time.strftime("%a %b %d %H:%M:%S %Y")
        with open(self._status_filename, "w") as fh:
            fh.write("# Cheetah status\n")
            fh.write(f"Update time: {time_string}\n")
            dt: int = int(time.time() - self._start_time)
            hours: int
            minutes: int
            hours, minutes = divmod(dt, 3600)
            seconds: int
            minutes, seconds = divmod(minutes, 60)
            fh.write(f"Elapsed time: {hours}hr {minutes}min {seconds}sec\n")
            fh.write(f"Status: {status}\n")
            fh.write(f"Frames processed: {num_frames}\n")
            fh.write(f"Number of hits: {num_hits}\n")

    def initialize_collecting_node(self, node_rank: int, node_pool_size: int) -> None:
        """
        Initializes the collecting node for Cheetah.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the data accumulation algorithms, the storage buffers
        used to compute statistics on the detected Bragg peaks and, optionally, the sum
        file writer. Additionally, it prepares the responding socket to send data to
        external programs.

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

        self._source: str = self._monitor_params.get_parameter(
            group="om",
            parameter="source",
            parameter_type=str,
            required=True,
        )

        self._configuration_file: str = self._monitor_params.get_parameter(
            group="om",
            parameter="configuration_file",
            parameter_type=str,
            required=True,
        )

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

        binning: Union[bool, None] = self._monitor_params.get_parameter(
            group="crystallography",
            parameter="binning",
            parameter_type=bool,
            required=False,
        )
        if binning:
            self._binning = gen_algs.Binning(
                parameters=self._monitor_params.get_parameter_group(group="binning"),
            )
            self._bin_size: int = self._binning.get_bin_size()
            self._pixelmaps = self._binning.bin_pixel_maps(pixel_maps=self._pixelmaps)
            self._data_shape = self._binning.get_binned_data_shape()
        else:
            self._binning = None
            self._bin_size = 1

        self._responding_socket: zmq_monitor.ZmqResponder = zmq_monitor.ZmqResponder(
            parameters=self._monitor_params.get_parameter_group(group="crystallography")
        )
        request_list_size: Union[int, None] = self._monitor_params.get_parameter(
            group="crystallography",
            parameter="external_data_request_list_size",
            parameter_type=int,
        )
        if request_list_size is None:
            request_list_size = 20
        self._request_list: Deque[Tuple[bytes, bytes]] = collections.deque(
            maxlen=request_list_size
        )

        self._num_events: int = 0
        self._num_hits: int = 0
        self._old_time: float = time.time()
        self._time: Union[float, None] = None

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
        self._frames_file: TextIO = open(self._frames_filename, "w")
        self._frames_file.write(
            "# timestamp, event_id, hit, filename, index, num_peaks, ave_intensity\n"
        )
        self._hits_file: TextIO = open(
            processed_directory_path.resolve() / "hits.lst", "w"
        )
        self._peaks_file: TextIO = open(
            processed_directory_path.resolve() / "peaks.txt", "w"
        )
        self._peaks_file.write(
            "event_id, num_peaks, fs, ss, intensity, num_pixels, "
            "max_pixel_intensity, snr\n"
        )
        self._start_time: float = time.time()
        self._status_file_update_interval: int = self._monitor_params.get_parameter(
            group="cheetah",
            parameter="status_file_update_interval",
            parameter_type=int,
        )
        if self._status_file_update_interval is not None:
            self._write_status_file(status="Not finished")

        self._frame_list: List[_TypeFrameListData] = []
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

        self._total_sums = [
            {
                "num_frames": 0,
                "sum_frames": numpy.zeros(self._data_shape, dtype=numpy.float64),
                "peak_powder": numpy.zeros(self._data_shape, dtype=numpy.float64),
            }
            for class_number in range(2)
        ]
        console.print(f"{get_current_timestamp()} Starting the monitor...")
        sys.stdout.flush()

    def process_data(  # noqa: C901
        self, *, node_rank: int, node_pool_size: int, data: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], int]:
        """
        Processes a detector data frame and saves the extracted data to HDF5 file.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function processes retrieved data events, calibrating and correcting the
        detector data frames and extracting the Bragg peak information. Finally, it
        prepares the Bragg peak data (and optionally, the detector frame data) for
        transmission to to the collecting node.

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
        corrected_detector_data: NDArray[
            numpy.float_
        ] = self._correction.apply_correction(data=data["detector_data"])
        if self._binning is not None and self._binning_before_peakfinding:
            binned_detector_data: NDArray[
                numpy.float_
            ] = self._binning.bin_detector_data(data=corrected_detector_data)
        else:
            binned_detector_data = corrected_detector_data

        peak_list: cryst_algs.TypePeakList = self._peak_detection.find_peaks(
            data=binned_detector_data
        )

        if self._binning is not None and not self._binning_before_peakfinding:
            binned_detector_data = self._binning.bin_detector_data(
                data=corrected_detector_data
            )
            i: int
            bin_size: int = self._binning.get_bin_size()
            for i in range(peak_list["num_peaks"]):
                peak_list["fs"][i] = (peak_list["fs"][i] + 0.5) / bin_size - 0.5
                peak_list["ss"][i] = (peak_list["ss"][i] + 0.5) / bin_size - 0.5

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
        processed_data["data_shape"] = binned_detector_data.shape
        if "lcls_extra" in data.keys():
            processed_data["lcls_extra"] = data["lcls_extra"]
        processed_data["peak_list"] = peak_list
        processed_data["filename"] = "---"
        processed_data["index"] = -1
        if frame_is_hit:
            processed_data["detector_data"] = binned_detector_data

        self._total_sums[frame_is_hit]["num_frames"] += 1
        self._total_sums[frame_is_hit]["sum_frames"] += binned_detector_data
        if self._sum_sending_interval is not None:
            if self._sum_sending_counter == 0:
                class_number: int
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
            self._sum_to_send[frame_is_hit]["sum_frames"] += binned_detector_data
            self._sum_sending_counter += 1
            if self._sum_sending_counter == self._sum_sending_interval:
                self._sum_sending_counter = 0
                processed_data["class_sums"] = self._sum_to_send

        return (processed_data, node_rank)

    def collect_no_data(
        self,
        *,
        node_rank: int,
        node_pool_size: int,
    ) -> None:
        """
        Receives and handles requests from external programs.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function receives requests from external programs over a network socket
        and reacts according to the nature of the request, sending data back to the
        source of the request or modifying the internal behavior of the monitor.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        """
        self._handle_external_requests()

    def collect_data(  # noqa: C901
        self,
        *,
        node_rank: int,
        node_pool_size: int,
        processed_data: Tuple[Dict[str, Any], int],
    ) -> Union[Dict[int, Dict[str, Any]], None]:
        """
        Computes statistics on aggregated data and streams hits to external programs.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function collects and accumulates frame- and peak-related information
        received from the processing nodes. Optionally, it computes the sums of hit and
        non-hit detector frames and the corresponding virtual powder patterns. If
        required, it saves the sums and virtual powder patterns to sum files.
        Additionally, this function can write information about the processing
        statistics (number of processed events, number of found hits and the elapsed
        time) in a status file at regular intervals. External programs can inspect the
        file to determine the advancement of the data processing.

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
        self._handle_external_requests()
        received_data: Dict[str, Any] = processed_data[0]

        if self._write_class_sums and "class_sums" in received_data:
            class_number: int
            for class_number in range(2):
                self._total_sums[class_number]["num_frames"] += received_data[
                    "class_sums"
                ][class_number]["num_frames"]
                self._total_sums[class_number]["sum_frames"] += received_data[
                    "class_sums"
                ][class_number]["sum_frames"]
            self._class_sum_update_counter += 1

        if "end_processing" in received_data:
            return None

        self._num_events += 1
        if received_data["frame_is_hit"]:
            self._num_hits += 1

            # Wait for a request to the responding socket.
            while len(self._request_list) == 0:
                self._handle_external_requests()
            last_request: Tuple[bytes, bytes] = self._request_list[-1]
            data_to_send: Any = msgpack.packb(
                {
                    "detector_data": received_data["detector_data"].astype(
                        numpy.float32
                    ),
                    "peak_list": received_data["peak_list"],
                    "beam_energy": received_data["beam_energy"],
                    "detector_distance": received_data["detector_distance"],
                    "event_id": received_data["event_id"],
                    "frame_id": received_data["frame_id"],
                    "timestamp": received_data["timestamp"],
                    "source": self._source,
                    "configuration_file": self._configuration_file,
                },
                use_bin_type=True,
            )
            self._responding_socket.send_data(
                identity=last_request[0], message=data_to_send
            )
            _ = self._request_list.pop()

            self._hits_file.write(f"{received_data['event_id']}\n")
            peak_list: cryst_algs.TypePeakList = received_data["peak_list"]
            self._peaks_file.writelines(
                (
                    f"{received_data['event_id']}, "
                    f"{peak_list['num_peaks']}, "
                    f"{(peak_list['fs'][i] + 0.5) * self._bin_size - 0.5}, "
                    f"{(peak_list['ss'][i] + 0.5) * self._bin_size - 0.5}, "
                    f"{peak_list['intensity'][i]}, "
                    f"{peak_list['num_pixels'][i]}, "
                    f"{peak_list['max_pixel_intensity'][i]}, "
                    f"{peak_list['snr'][i]}\n"
                    for i in range(peak_list["num_peaks"])
                )
            )

        frame_data: _TypeFrameListData = _TypeFrameListData(
            received_data["timestamp"],
            received_data["event_id"],
            int(received_data["frame_is_hit"]),
            received_data["filename"],
            received_data["index"],
            received_data["peak_list"]["num_peaks"],
            numpy.mean(received_data["peak_list"]["intensity"]),
        )
        self._frame_list.append(frame_data)
        self._frames_file.write(
            f"{frame_data.timestamp}, {frame_data.event_id}, "
            f"{frame_data.frame_is_hit}, {frame_data.filename}, "
            f"{frame_data.index_in_file}, {frame_data.num_peaks}, "
            f"{frame_data.average_intensity}\n"
        )

        peak_fs: float
        peak_ss: float
        peak_value: float
        for peak_fs, peak_ss, peak_value in zip(
            received_data["peak_list"]["fs"],
            received_data["peak_list"]["ss"],
            received_data["peak_list"]["intensity"],
        ):
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
            self._hits_file.flush()
            self._peaks_file.flush()
            self._frames_file.flush()

        if self._num_events % self._speed_report_interval == 0:
            now_time: float = time.time()
            time_diff: float = now_time - self._old_time
            events_per_second: float = float(self._speed_report_interval) / float(
                now_time - self._old_time
            )
            console.print(
                f"{get_current_timestamp()} Processed: {self._num_events} in "
                f"{time_diff:.2f} seconds ({events_per_second:.3f} Hz)"
            )
            sys.stdout.flush()
            self._old_time = now_time

        return None

    def end_processing_on_processing_node(
        self,
        *,
        node_rank: int,
        node_pool_size: int,
    ) -> Union[Dict[str, Any], None]:
        """
        Ends processing on the processing nodes.

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
        total_num_events: int = (
            self._total_sums[0]["num_frames"] + self._total_sums[1]["num_frames"]
        )
        console.print(
            f"{get_current_timestamp()} Processing finished. OM node {node_rank} has "
            f"processed {total_num_events} events in total."
        )
        sys.stdout.flush()
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
        the sum and status files, closes the files and ends the processing.

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
        frame_list: List[_TypeFrameListData] = sorted(self._frame_list)
        if self._status_file_update_interval is not None:
            self._write_status_file(
                status="Finished",
                num_frames=self._num_events,
                num_hits=self._total_sums[1]["num_frames"],
            )
        # Sort frames and write frames.txt file again
        self._frames_file.close()
        with open(self._frames_filename, "w") as self._frames_file:
            self._frames_file.write(
                "# timestamp, event_id, hit, filename, index, num_peaks, "
                "ave_intensity\n"
            )
            frame: _TypeFrameListData
            for frame in frame_list:
                self._frames_file.write(
                    f"{frame.timestamp}, {frame.event_id}, {frame.frame_is_hit}, "
                    f"{frame.filename}, {frame.index_in_file}, {frame.num_peaks}, "
                    f"{frame.average_intensity}\n"
                )
        with open(self._cleaned_filename, "w") as fh:
            fh.write(
                "# timestamp, event_id, hit, filename, index, num_peaks, "
                "ave_intensity\n"
            )
            for frame in frame_list:
                if frame.frame_is_hit:
                    fh.write(
                        f"{frame.timestamp}, {frame.event_id}, {frame.frame_is_hit}, "
                        f"{frame.filename}, {frame.index_in_file}, {frame.num_peaks}, "
                        f"{frame.average_intensity}\n"
                    )

        console.print(f"{get_current_timestamp()} Collecting node shutting down.")
        sys.stdout.flush()

    def _handle_external_requests(self) -> None:
        # This function handles external requests sent to the crystallography monitor
        # over the responding network socket.
        request: Union[
            Tuple[bytes, bytes], None
        ] = self._responding_socket.get_request()
        if request:
            if request[1] == b"next":
                self._request_list.append(request)
            else:
                console.print(
                    f"{get_current_timestamp()} OM Warning: Could not understand "
                    f"request '{str(request[1])}'.",
                    style="warning",
                )
                self._responding_socket.send_data(identity=request[0], message=b"What?")
