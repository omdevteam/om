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
# Copyright 2020 -2023 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
OnDA Monitor for CBC Crystallography at MFX experiment mfx101210926.

This module contains an OnDA Monitor for Convergent Beam Crystallography experiments.
It replaces Bragg peak detection with diffraction streak (line) detection via cbclib_v2.
"""

from collections import deque
from typing import Any, cast
from pathlib import Path

import numpy
from numpy.typing import NDArray
from scipy.ndimage import generate_binary_structure, label, sum_labels

from om.algorithms.common import PeakList
from om.algorithms.generic import Binning, BinningPassthrough
from om.lib.crystallography import CrystallographyPlots
from om.lib.files import load_hdf5_data
from om.lib.event_management import EventCounter
from om.lib.exceptions import OmMissingDependencyError
from om.lib.geometry import (
    DataVisualizer,
    GeometryInformation,
    PixelMaps,
    DetectorLayoutInformation,
)
from om.lib.cheetah import (
    CheetahClassSumsAccumulator,
    CheetahClassSumsCollector,
    CheetahlistFilesWriter,
    CheetahStatusFileWriter,
    FramelistData,
    HDF5Writer,
    write_VDS_master_file,
)
from om.lib.logging import log_error_and_exit, log_info
from om.lib.parameters import (
    BinningParameters,
    CheetahParameters,
    CrystallographyParameters,
    LineDetectionParameters,
    MonitorParameters,
)
from om.lib.protocols import OmProcessingProtocol
from om.lib.zmq import ZmqDataBroadcaster

try:
    import msgpack  # noqa: F401
except ImportError:
    raise OmMissingDependencyError(
        "The following required module cannot be imported: msgpack"
    )

# try:
#     from cbclib_v2.label import Structure, index, label, labels, line_fit
# except ImportError:
#     raise OmMissingDependencyError(
#         "The following required module cannot be imported: cbclib_v2"
#     )


def _maximum_positions(
    image: NDArray[numpy.floating[Any] | numpy.signedinteger[Any]],
    regions: NDArray[numpy.signedinteger[Any]],
    index: NDArray[numpy.integer[Any]],
    num_labels: int,
) -> list[tuple[int, ...]]:
    if index.size == 0:
        return []

    flat_regions = regions.ravel()
    flat_image = image.ravel()
    max_values = numpy.full(num_labels + 1, -numpy.inf, dtype=float)
    numpy.maximum.at(max_values, flat_regions, flat_image)

    selected = numpy.zeros(num_labels + 1, dtype=bool)
    selected[index] = True
    candidate_positions = numpy.flatnonzero(selected[flat_regions])
    candidate_regions = flat_regions[candidate_positions]
    candidate_positions = candidate_positions[
        flat_image[candidate_positions] == max_values[candidate_regions]
    ]

    peak_positions = numpy.full(num_labels + 1, flat_image.size, dtype=numpy.intp)
    numpy.minimum.at(
        peak_positions, flat_regions[candidate_positions], candidate_positions
    )

    coords = numpy.unravel_index(peak_positions[index], image.shape)
    return [tuple(int(coord) for coord in point) for point in zip(*coords)]


def _detect_lines(
    image: NDArray[numpy.floating[Any] | numpy.signedinteger[Any]],
    radius: int,
    connectivity: int,
    vmin: float,
    npts: int,
) -> list[tuple[int, ...]]:
    # Detects diffraction streaks in a detector frame using scipy.ndimage.
    # Returns the list of per-line peak positions (row, col).

    if radius != 1:
        raise ValueError("scipy.ndimage.label only supports radius=1 connectivity.")
    structure = generate_binary_structure(image.ndim, connectivity)
    regions, num_labels = label(image > vmin, structure=structure)
    all_index = numpy.arange(1, num_labels + 1)
    sizes = numpy.asarray(
        sum_labels(numpy.ones(image.shape, dtype=int), regions, index=all_index)
    )
    index = all_index[sizes >= npts]
    return _maximum_positions(image, regions, index, num_labels)


def _peaks_to_peak_list(
    peaks: list[tuple[int, ...]],
    image: NDArray[numpy.floating[Any] | numpy.signedinteger[Any]],
) -> PeakList:
    # Converts the list of (row, col) peak positions returned by _detect_lines
    # into a PeakList compatible with the rest of the crystallography pipeline.
    # ss = slow-scan (row), fs = fast-scan (column).
    # Intensity and max_pixel_intensity are set to the image value at the peak
    # position; snr and num_pixels are not computed by the line detector and are
    # set to 0.0 and 1.0 respectively.
    ss_list: list[float] = [float(p[0]) for p in peaks]
    fs_list: list[float] = [float(p[1]) for p in peaks]
    intensity_list: list[float] = [float(image[int(p[0]), int(p[1])]) for p in peaks]
    return PeakList(
        num_peaks=len(peaks),
        ss=ss_list,
        fs=fs_list,
        intensity=intensity_list,
        num_pixels=[1.0] * len(peaks),
        max_pixel_intensity=intensity_list,
        snr=[0.0] * len(peaks),
    )


class CbCrystallographyProcessing(OmProcessingProtocol):
    """
    See documentation for the `__init__` function.
    """

    def __init__(self, *, parameters: MonitorParameters) -> None:
        """
        OnDA Monitor for CBC Crystallography.

        This Processing class implements an OnDA Monitor for Serial CBC Crystallography
        experiments. The monitor processes detector data frames, detecting diffraction
        streaks in each frame using the cbclib_v2 line-detection algorithm. It
        retrieves the location and intensity of the brightest pixel in each detected
        streak. The monitor also calculates the evolution of the hit rate over time.
        All the information is streamed to external programs for visualization.

        Arguments:

            parameters: An object storing OM's configuration parameters.
        """
        if parameters.crystallography is None:
            log_error_and_exit(
                "'crystallography' section is not present in the configuration file"
            )
            return  # For the type checker
        self._crystallography_parameters: CrystallographyParameters = (
            parameters.crystallography
        )
        self._monitor_parameters: MonitorParameters = parameters

        # Geometry
        self._geometry_information: GeometryInformation = GeometryInformation.from_file(
            geometry_filename=self._crystallography_parameters.geometry_file
        )

        # Post-processing binning
        if parameters.crystallography.post_processing_binning:
            if parameters.binning is None:
                log_error_and_exit(
                    "'binning' section is not present in the configuration file"
                )
                return  # For the type checker
            self._post_processing_binning: Binning | BinningPassthrough = Binning(
                parameters=parameters.binning,
                layout_info=self._geometry_information.get_layout_info(),
            )
        else:
            self._post_processing_binning = BinningPassthrough(
                layout_info=self._geometry_information.get_layout_info()
            )

    def initialize_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes the processing nodes for the CBC Crystallography Monitor.

        This function reads the line-detection parameters from the ``line_detection``
        configuration section, and initializes the hit-counting thresholds.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        if self._monitor_parameters.line_detection is None:
            log_error_and_exit(
                "'line_detection' section is not present in the configuration file"
            )
            return  # For the type checker

        self._line_detection_parameters: LineDetectionParameters = (
            self._monitor_parameters.line_detection
        )

        # Mask (loaded if a mask filename is provided in the configuration)
        if self._line_detection_parameters.bad_pixel_map_filename is not None:
            mask_data: NDArray[numpy.floating[Any]] = load_hdf5_data(
                hdf5_filename=self._line_detection_parameters.bad_pixel_map_filename,  # type: ignore[arg-type]
                hdf5_path=self._line_detection_parameters.bad_pixel_map_hdf5_path,  # type: ignore[arg-type]
            )
            self._mask: NDArray[numpy.int8] | None = mask_data.astype(numpy.int8)
        else:
            self._mask = None

        # Background (loaded only when background subtraction is enabled)
        self._background_subtraction: bool = (
            self._line_detection_parameters.background_subtraction
        )
        self._background: NDArray[numpy.floating[Any]] | None = None
        if self._background_subtraction:
            self._background = load_hdf5_data(
                hdf5_filename=self._line_detection_parameters.background_filename,  # type: ignore[arg-type]
                hdf5_path=self._line_detection_parameters.background_hdf5_path,  # type: ignore[arg-type]
            ).astype(numpy.float64)
            if self._mask is not None:
                self._background *= self._mask
            self._background_norm: float = float(numpy.sum(self._background**2))

        self._min_num_peaks_for_hit = (
            self._crystallography_parameters.min_num_peaks_for_hit
        )
        self._max_num_peaks_for_hit = (
            self._crystallography_parameters.max_num_peaks_for_hit
        )

        # Frame sending
        self._send_hit_frame: bool = False
        self._send_non_hit_frame: bool = False

        # Console
        log_info(f"Processing node {node_rank} starting")

    def initialize_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes the collecting node for the CBC Crystallography Monitor.

        This function initializes the data accumulation algorithms, storage buffers,
        and network sockets needed on the collecting node.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """

        # Geometry
        self._detector_distance_offset: float = (
            self._geometry_information.get_detector_distance_offset()
        )

        self._pixel_size = self._geometry_information.get_pixel_size()
        pixel_maps: PixelMaps = self._geometry_information.get_pixel_maps()

        self._pixel_size *= self._post_processing_binning.get_bin_size()
        binned_pixel_maps = self._post_processing_binning.bin_pixel_maps(
            pixel_maps=pixel_maps
        )

        # Data visualizer
        self._data_visualizer: DataVisualizer = DataVisualizer(
            pixel_maps=binned_pixel_maps
        )

        # Data broadcast
        self._data_broadcast_socket: ZmqDataBroadcaster = ZmqDataBroadcaster(
            data_broadcast_url=self._crystallography_parameters.data_broadcast_url
        )

        # Plots
        self._plots: CrystallographyPlots = CrystallographyPlots(
            parameters=self._monitor_parameters,
            data_visualizer=self._data_visualizer,
            pump_probe_experiment=(
                self._crystallography_parameters.pump_probe_experiment
            ),
            bin_size=self._post_processing_binning.get_bin_size(),
        )

        self._geometry_is_optimized: bool = (
            self._crystallography_parameters.geometry_is_optimized
        )

        # Event counting
        self._event_counter: EventCounter = EventCounter(
            speed_report_interval=(
                self._crystallography_parameters.speed_report_interval
            ),
            data_broadcast_interval=(
                self._crystallography_parameters.data_broadcast_interval
            ),
            hit_frame_sending_interval=(
                self._crystallography_parameters.hit_frame_sending_interval
            ),
            non_hit_frame_sending_interval=(
                self._crystallography_parameters.non_hit_frame_sending_interval
            ),
            node_pool_size=node_pool_size,
        )

        # Console
        log_info("Starting the monitor...")

    def process_data(
        self, *, node_rank: int, node_pool_size: int, data: dict[str, Any]
    ) -> tuple[dict[str, Any], int]:
        """
        Processes a detector data frame using streak (line) detection.

        This function replaces the Bragg peak detection of the standard Crystallography
        monitor with diffraction streak detection via cbclib_v2. The detected streak
        positions are converted into a
        [`PeakList`][om.algorithms.common.PeakList] so that the rest of the
        pipeline (binning, hit classification, broadcasting) is unchanged.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

            data: A dictionary containing the data that OM retrieved for the detector
                data frame being processed.

        Returns:

            A tuple with two entries. The first entry is a dictionary storing the
                processed data that should be sent to the collecting node. The second
                entry is the OM rank number of the node that processed the information.
        """
        processed_data: dict[str, Any] = {}

        # Pre-processing: apply mask
        data["detector_data"] *= self._mask if self._mask is not None else 1

        # OLS background subtraction (optional)
        if self._background_subtraction and self._background is not None:
            scale: float = (
                float(numpy.sum(data["detector_data"] * self._background))
                / self._background_norm
                if self._background_norm > 0.0
                else 0.0
            )
            data["detector_data"] -= scale * self._background

        # Line detection
        peaks = _detect_lines(
            data["detector_data"],
            self._line_detection_parameters.structure_radius,
            self._line_detection_parameters.structure_connectivity,
            self._line_detection_parameters.threshold,
            self._line_detection_parameters.min_pixel_count,
        )
        peak_list: PeakList = _peaks_to_peak_list(peaks, data["detector_data"])

        peak_list = self._post_processing_binning.bin_peak_positions(
            peak_list=peak_list
        )

        frame_is_hit: bool = (
            self._min_num_peaks_for_hit
            < len(peak_list.intensity)
            < self._max_num_peaks_for_hit
        )

        # Data to send
        processed_data["timestamp"] = data["timestamp"]
        processed_data["frame_is_hit"] = frame_is_hit
        processed_data["detector_distance"] = data["detector_distance"]
        processed_data["beam_energy"] = data["beam_energy"]
        processed_data["event_id"] = data["event_id"]
        processed_data["peak_list"] = peak_list
        if self._crystallography_parameters.pump_probe_experiment:
            processed_data["optical_laser_active"] = data["optical_laser_active"]

        # Frame sending
        if "requests" in data:
            if data["requests"] == "hit_frame":
                self._send_hit_frame = True
            if data["requests"] == "non_hit_frame":
                self._send_non_hit_frame = True

        send_detector_data: bool = (frame_is_hit and self._send_hit_frame) or (
            not frame_is_hit and self._send_non_hit_frame
        )

        if send_detector_data:
            data_to_send: NDArray[numpy.floating[Any] | numpy.signedinteger[Any]] = (
                data["detector_data"]
            )
            data_to_send = self._post_processing_binning.bin_detector_data(
                data=data_to_send
            )
            processed_data["detector_data"] = data_to_send
            if frame_is_hit:
                self._send_hit_frame = False
            else:
                self._send_non_hit_frame = False

        return (processed_data, node_rank)

    def wait_for_data(
        self,
        *,
        node_rank: int,
        node_pool_size: int,
    ) -> None:
        """
        No-op: this monitor does not handle external requests.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        pass

    def collect_data(
        self,
        *,
        node_rank: int,
        node_pool_size: int,
        processed_data: tuple[dict[str, Any], int],
    ) -> dict[str, dict[str, Any]] | None:
        """
        Computes statistics on aggregated data and broadcasts data to external programs.

        This function collects and accumulates frame- and peak-related information
        received from the processing nodes. It also computes a rolling average
        estimation of the hit rate evolution over time. Additionally, it uses the
        streak information to compute a virtual powder pattern and a peakogram plot.
        All the aggregated information is then broadcast to external programs for
        visualization.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

            processed_data (tuple[dict, int]): A tuple whose first entry is a
                dictionary storing the data received from a processing node, and whose
                second entry is the OM rank number of the node that processed the
                information.
        """
        received_data: dict[str, Any] = processed_data[0]

        # Event counting
        if received_data["frame_is_hit"] is True:
            self._event_counter.add_hit_event()
        else:
            self._event_counter.add_non_hit_event()

        if self._crystallography_parameters.pump_probe_experiment:
            optical_laser_active: bool = received_data["optical_laser_active"]
        else:
            optical_laser_active = False

        # Plots
        curr_hit_rate_timestamp_history: deque[float]
        curr_hit_rate_history: deque[float]
        curr_hit_rate_timestamp_history_dark: deque[float] | None
        curr_hit_rate_history_dark: deque[float] | None
        curr_virt_powd_plot_img: NDArray[numpy.signedinteger[Any]]
        curr_peakogram: NDArray[numpy.floating[Any]]
        peakogram_radius_bin_size: float
        peakogram_intensity_bin_size: float
        peak_list_x_in_frame: list[float]
        peak_list_y_in_frame: list[float]
        (
            curr_hit_rate_timestamp_history,
            curr_hit_rate_history,
            curr_hit_rate_timestamp_history_dark,
            curr_hit_rate_history_dark,
            curr_virt_powd_plot_img,
            curr_peakogram,
            peakogram_radius_bin_size,
            peakogram_intensity_bin_size,
            peak_list_x_in_frame,
            peak_list_y_in_frame,
        ) = self._plots.update_plots(
            timestamp=received_data["timestamp"],
            peak_list=received_data["peak_list"],
            frame_is_hit=received_data["frame_is_hit"],
            optical_laser_active=optical_laser_active,
        )

        if self._event_counter.should_broadcast_data():
            omdata_message: dict[str, Any] = {
                "geometry_is_optimized": self._geometry_is_optimized,
                "timestamp": received_data["timestamp"],
                "hit_rate_timestamp_history": curr_hit_rate_timestamp_history,
                "hit_rate_history": curr_hit_rate_history,
                "virtual_powder_plot": curr_virt_powd_plot_img,
                "beam_energy": received_data["beam_energy"],
                "detector_distance": received_data["detector_distance"],
                "detector_distance_offset": self._detector_distance_offset,
                "pixel_size": self._pixel_size,
                "pump_probe_experiment": (
                    self._crystallography_parameters.pump_probe_experiment
                ),
                "start_timestamp": self._event_counter.get_start_timestamp(),
                "peakogram": curr_peakogram,
                "peakogram_radius_bin_size": peakogram_radius_bin_size,
                "peakogram_intensity_bin_size": peakogram_intensity_bin_size,
            }
            if self._crystallography_parameters.pump_probe_experiment:
                omdata_message["hit_rate_timestamp_history_dark"] = (
                    curr_hit_rate_timestamp_history_dark
                )
                omdata_message["hit_rate_history_dark"] = curr_hit_rate_history_dark

            self._data_broadcast_socket.send_data(
                tag="omdata",
                message=omdata_message,
            )

        # Frame viewer broadcast
        if "detector_data" in received_data:
            self._frame_data_img = self._data_visualizer.visualize_data(
                data=received_data["detector_data"],
            )
            self._data_broadcast_socket.send_data(
                tag="omframedata",
                message={
                    "frame_data": self._frame_data_img,
                    "timestamp": received_data["timestamp"],
                    "peak_list_x_in_frame": peak_list_x_in_frame,
                    "peak_list_y_in_frame": peak_list_y_in_frame,
                },
            )
            if self._post_processing_binning.is_passthrough():
                self._data_broadcast_socket.send_data(
                    tag="omtweakingdata",
                    message={
                        "detector_data": received_data["detector_data"],
                        "timestamp": received_data["timestamp"],
                    },
                )

        return_dict: dict[str, dict[str, Any]] = {}
        if self._event_counter.should_send_hit_frame():
            return_dict["random"] = {"requests": "hit_frame"}
        if self._event_counter.should_send_non_hit_frame():
            return_dict["random"] = {"requests": "non_hit_frame"}

        self._event_counter.report_speed()

        if return_dict:
            return return_dict
        return None

    def end_processing_on_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> dict[str, Any] | None:
        """
        Ends processing on the processing nodes for the CBC Crystallography Monitor.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        Returns:

            Usually nothing. Optionally, a dictionary storing information to be sent to
                the processing node.
        """
        log_info(f"Processing node {node_rank} shutting down.")
        return None

    def end_processing_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Ends processing on the collecting node for the CBC Crystallography Monitor.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        log_info(
            "Processing finished. OM has processed "
            f"{self._event_counter.get_num_events()} events in total."
        )


class CbCheetahProcessing(OmProcessingProtocol):
    """
    See documentation for the `__init__` function.
    """

    def __init__(self, *, parameters: MonitorParameters) -> None:
        """
        Cheetah Processing class for Convergent Beam Crystallography.

        Arguments:

            parameters: An object storing OM's configuration parameters.
        """
        if parameters.cheetah is None:
            log_error_and_exit(
                "'cheetah' section is not present in the configuration file"
            )
            return  # For the type checker
        if parameters.crystallography is None:
            log_error_and_exit(
                "'crystallography' section is not present in the configuration file"
            )
            return  # For the type checker
        if parameters.line_detection is None:
            log_error_and_exit(
                "'line_detection' section is not present in the configuration file"
            )
            return  # For the type checker

        self._line_detection_parameters: LineDetectionParameters = (
            parameters.line_detection
        )
        self._cheetah_parameters: CheetahParameters = parameters.cheetah
        self._crystallography_parameters: CrystallographyParameters = (
            parameters.crystallography
        )
        self._monitor_parameters: MonitorParameters = parameters

        # Processed data directory
        Path(parameters.cheetah.processed_directory).mkdir(exist_ok=True)

        # Geometry
        self._geometry_information: GeometryInformation = GeometryInformation.from_file(
            geometry_filename=self._crystallography_parameters.geometry_file
        )

        self._post_processing_binning_enabled: bool = (
            self._crystallography_parameters.post_processing_binning
        )
        if self._post_processing_binning_enabled:
            if parameters.binning is None:
                log_error_and_exit(
                    "'binning' section is not present in the configuration file"
                )
                return  # For the type checker
            self._monitor_parameters_binning: BinningParameters = parameters.binning

    def initialize_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes the collecting node for the CBC Cheetah.

        This function initializes the data accumulation algorithms, the storage buffers
        used to compute statistics on the processed data, and some internal counters.
        Additionally, it prepares all the file writers.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """

        # Status file
        self._status_file_writer: CheetahStatusFileWriter = CheetahStatusFileWriter(
            parameters=self._cheetah_parameters
        )
        self._status_file_writer.update_status(status="Not finished")

        # Event counting
        self._event_counter: EventCounter = EventCounter(
            speed_report_interval=(
                self._crystallography_parameters.speed_report_interval
            ),
            node_pool_size=node_pool_size,
        )

        # list files
        self._list_files_writer: CheetahlistFilesWriter = CheetahlistFilesWriter(
            parameters=self._cheetah_parameters,
        )

        # Class sums collection
        self._class_sum_collector: CheetahClassSumsCollector = (
            CheetahClassSumsCollector(
                parameters=self._cheetah_parameters, num_classes=2
            )
        )

        # Console
        log_info("Starting the monitor...")

    def initialize_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes the processing nodes for the CBC Cheetah.

        This function initializes all the required algorithms (peak finding, binning,
        etc.), plus some internal counters.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """

        # Mask (loaded if a mask filename is provided in the configuration)
        if self._line_detection_parameters.bad_pixel_map_filename is not None:
            mask_data: NDArray[numpy.floating[Any]] = load_hdf5_data(
                hdf5_filename=self._line_detection_parameters.bad_pixel_map_filename,  # type: ignore[arg-type]
                hdf5_path=self._line_detection_parameters.bad_pixel_map_hdf5_path,  # type: ignore[arg-type]
            )
            self._mask: NDArray[numpy.int8] | None = mask_data.astype(numpy.int8)
        else:
            self._mask = None

        # Background (loaded only when background subtraction is enabled)
        self._background_subtraction: bool = (
            self._line_detection_parameters.background_subtraction
        )
        self._background: NDArray[numpy.floating[Any]] | None = None
        if self._background_subtraction:
            self._background = load_hdf5_data(
                hdf5_filename=self._line_detection_parameters.background_filename,  # type: ignore[arg-type]
                hdf5_path=self._line_detection_parameters.background_hdf5_path,  # type: ignore[arg-type]
            ).astype(numpy.float64)
            if self._mask is not None:
                self._background *= self._mask
            self._background_norm: float = float(numpy.sum(self._background**2))

        self._min_num_peaks_for_hit = (
            self._crystallography_parameters.min_num_peaks_for_hit
        )
        self._max_num_peaks_for_hit = (
            self._crystallography_parameters.max_num_peaks_for_hit
        )

        # Post-processing binning
        if self._post_processing_binning_enabled:
            if self._monitor_parameters.binning is None:
                log_error_and_exit(
                    "'binning' section is not present in the configuration file"
                )
                return  # For the type checker
            self._post_processing_binning: Binning | BinningPassthrough = Binning(
                parameters=self._monitor_parameters_binning,
                layout_info=self._geometry_information.get_layout_info(),
            )
        else:
            self._post_processing_binning = BinningPassthrough(
                layout_info=self._geometry_information.get_layout_info()
            )

        # Processed data shape
        layout_info: DetectorLayoutInformation = (
            self._post_processing_binning.get_binned_layout_info()
        )
        self._processed_data_shape: tuple[int, int] = (
            layout_info.asic_ny * layout_info.nasics_y,
            layout_info.asic_nx * layout_info.nasics_x,
        )

        # Class sums accumulation
        self._class_sum_accumulator: CheetahClassSumsAccumulator = (
            CheetahClassSumsAccumulator(
                parameters=self._cheetah_parameters,
                num_classes=2,
            )
        )

        # HDF5 file writer
        self._file_writer: HDF5Writer = HDF5Writer(
            parameters=self._cheetah_parameters,
            node_rank=node_rank,
        )

        log_info(f"Processing node {node_rank} starting")

    def process_data(
        self, *, node_rank: int, node_pool_size: int, data: dict[str, Any]
    ) -> tuple[dict[str, Any], int]:
        """
        Processes a detector data frame.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

            data: A dictionary containing the data that OM retrieved for the detector
                data frame being processed.

        Returns:

            A tuple with two entries. The first entry is a dictionary storing the
                processed data that should be sent to the collecting node. The second
                entry is the OM rank number of the node that processed the information.
        """
        processed_data: dict[str, Any] = {}

        # Pre-processing: apply mask
        preprocessed_data: NDArray[numpy.floating[Any]] = (
            data["detector_data"] * self._mask
        )

        # OLS background subtraction (optional)
        if self._background_subtraction and self._background is not None:
            scale: float = (
                float(numpy.sum(preprocessed_data * self._background))
                / self._background_norm
                if self._background_norm > 0.0
                else 0.0
            )
            preprocessed_data -= scale * self._background

        # Line detection
        peaks = _detect_lines(
            preprocessed_data,
            self._line_detection_parameters.structure_radius,
            self._line_detection_parameters.structure_connectivity,
            self._line_detection_parameters.threshold,
            self._line_detection_parameters.min_pixel_count,
        )
        peak_list: PeakList = _peaks_to_peak_list(peaks, preprocessed_data)

        peak_list = self._post_processing_binning.bin_peak_positions(
            peak_list=peak_list
        )

        frame_is_hit: bool = (
            self._min_num_peaks_for_hit
            < len(peak_list.intensity)
            < self._max_num_peaks_for_hit
        )

        binned_detector_data: NDArray[
            numpy.floating[Any] | numpy.signedinteger[Any]
        ] = self._post_processing_binning.bin_detector_data(data=data["detector_data"])

        # Add data to the class sums
        self._class_sum_accumulator.add_frame(
            class_number=int(frame_is_hit),
            frame_data=binned_detector_data,
            peak_list=peak_list,
        )

        # Saving data to HDF5 file
        if frame_is_hit:
            data_to_write: dict[str, Any] = {
                "detector_data": binned_detector_data,
                "event_id": data["event_id"],
                "timestamp": data["timestamp"],
                "beam_energy": data["beam_energy"],
                "detector_distance": data["detector_distance"],
                "peak_list": peak_list,
            }
            if "optical_laser_active" in data.keys():
                data_to_write["optical_laser_active"] = int(
                    data["optical_laser_active"]
                )
            if "lcls_extra" in data.keys():
                data_to_write["lcls_extra"] = data["lcls_extra"]
            self._file_writer.write_frame(processed_data=data_to_write)

        # Data to send to the collecting node
        processed_data = {
            "timestamp": data["timestamp"],
            "frame_is_hit": frame_is_hit,
            "event_id": data["event_id"],
            "peak_list": peak_list,
            "class_sums": self._class_sum_accumulator.get_sums_for_sending(),
        }
        if frame_is_hit:
            processed_data["filename"] = self._file_writer.get_current_filename()
            processed_data["index"] = self._file_writer.get_num_written_frames()
        else:
            processed_data["filename"] = "---"
            processed_data["index"] = -1

        return (processed_data, node_rank)

    def wait_for_data(
        self,
        *,
        node_rank: int,
        node_pool_size: int,
    ) -> None:
        """
        Receives and handles requests from external programs.

        This function is not used in Cheetah, and therefore does nothing.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        """
        pass

    def collect_data(  # noqa: C901
        self,
        *,
        node_rank: int,
        node_pool_size: int,
        processed_data: tuple[dict[str, Any], int],
    ) -> dict[str, dict[str, Any]] | None:
        """
        Computes statistics on aggregated data and saves them to files.

        This function collects and accumulates frame- and peak-related information
        received from the processing nodes.  Optionally, it computes the sums of hit
        and non-hit detector frames and the corresponding virtual powder patterns, and
        saves them to file. Additionally, this function writes information about the
        processing statistics (number of processed events, number of found hits and the
        elapsed time) to a status file at regular intervals. External programs can
        inspect the file to determine the advancement of the data processing.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

            processed_data (tuple[dict, int]): A tuple whose first entry is a
                dictionary storing the data received from a processing node, and whose
                second entry is the OM rank number of the node that processed the
                information.
        """

        received_data: dict[str, Any] = processed_data[0]

        # Collect class sums
        if received_data["class_sums"] is not None:
            self._class_sum_collector.add_sums(class_sums=received_data["class_sums"])

        # End processing
        if "end_processing" in received_data:
            return None

        # Event counting
        if received_data["frame_is_hit"] is True:
            self._event_counter.add_hit_event()
        else:
            self._event_counter.add_non_hit_event()

        if received_data is None:
            return None

        # Write frame and peaks data to list files
        frame_data: FramelistData = FramelistData(
            received_data["timestamp"],
            received_data["event_id"],
            int(received_data["frame_is_hit"]),
            received_data["filename"],
            received_data["index"],
            received_data["peak_list"].num_peaks,
            numpy.mean(cast(numpy.floating[Any], received_data["peak_list"].intensity)),
        )
        self._list_files_writer.add_frame(
            frame_data=frame_data, peak_list=received_data["peak_list"]
        )

        # Update status file
        num_events: int = self._event_counter.get_num_events()
        if num_events % self._cheetah_parameters.status_file_update_interval == 0:
            self._status_file_writer.update_status(
                status="Not finished",
                num_frames=num_events,
                num_hits=self._event_counter.get_num_hits(),
            )
            self._list_files_writer.flush_files()

        self._event_counter.report_speed()

        return None

    def end_processing_on_processing_node(
        self,
        *,
        node_rank: int,
        node_pool_size: int,
    ) -> dict[str, Any] | None:
        """
        Ends processing on the processing nodes for Cheetah.

        This function prints a message on the console, closes the output HDF5 files
        and ends the processing.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        Returns:

            Usually nothing. Optionally, a dictionary storing information to be sent to
                the processing node.
        """
        log_info(f"Processing node {node_rank} shutting down.")
        self._file_writer.close()
        return {
            "class_sums": self._class_sum_accumulator.get_sums_for_sending(
                disregard_counter=True
            ),
            "end_processing": True,
        }

    def end_processing_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Ends processing on the collecting node for Cheetah.

        This function prints a message on the console, writes the final information in
        the sum and status files, closes the files and ends the processing.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        # Save final accumulated class sums
        self._class_sum_collector.save_sums()

        # Sort frames and write final list files
        self._list_files_writer.sort_frames_and_close_files()

        # Write master file with sorted frames
        write_VDS_master_file(
            parameters=self._cheetah_parameters,
        )

        # Write final status
        self._status_file_writer.update_status(
            status="Finished",
            num_frames=self._event_counter.get_num_events(),
            num_hits=self._event_counter.get_num_hits(),
        )

        log_info(
            "Processing finished. OM has processed "
            f"{self._event_counter.get_num_events()} events in total."
        )
