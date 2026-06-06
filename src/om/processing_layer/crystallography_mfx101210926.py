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

This module contains an OnDA Monitor for the MFX101210926 Serial Crystallography
experiment. It replaces Bragg peak detection with diffraction streak (line) detection
via cbclib_v2.
"""

from collections import deque
from typing import Any, cast

import numpy
from numpy.typing import NDArray
from scipy.ndimage import maximum_position

from om.algorithms.common import PeakList
from om.algorithms.generic import Binning, BinningPassthrough
from om.lib.crystallography import CrystallographyPlots
from om.lib.files import load_hdf5_data
from om.lib.event_management import EventCounter
from om.lib.exceptions import OmMissingDependencyError
from om.lib.geometry import DataVisualizer, GeometryInformation, PixelMaps
from om.lib.logging import log_error_and_exit, log_info
from om.lib.parameters import CrystallographyParameters, MonitorParameters
from om.lib.protocols import OmProcessingProtocol
from om.lib.zmq import ZmqDataBroadcaster

try:
    import msgpack  # noqa: F401
except ImportError:
    raise OmMissingDependencyError(
        "The following required module cannot be imported: msgpack"
    )

try:
    from cbclib_v2.label import Structure, index, label, labels, line_fit
except ImportError:
    raise OmMissingDependencyError(
        "The following required module cannot be imported: cbclib_v2"
    )


def _detect_lines(
    image: NDArray[numpy.floating[Any] | numpy.signedinteger[Any]],
    radii: list[int],
    connectivity: int,
    vmin: float,
    npts: int,
) -> tuple[Any, list[tuple[int, ...]]]:
    # Detects diffraction streaks in a detector frame using cbclib_v2.
    # Returns the fitted line parameters and the list of per-line peak positions
    # (row, col) as reported by scipy.ndimage.maximum_position.
    structure: Structure = Structure(radii, connectivity)
    regions: Any = label(image > vmin, structure=structure, npts=npts)
    lines: Any = line_fit(regions, image)
    peaks: list[tuple[int, ...]] = cast(
        list[tuple[int, ...]],
        maximum_position(image, labels(regions), index(regions)),
    )
    return lines, peaks


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

        self._line_detection_radii: list[int] = (
            self._monitor_parameters.line_detection.radii
        )
        self._line_detection_connectivity: int = (
            self._monitor_parameters.line_detection.connectivity
        )
        self._line_detection_vmin: float = self._monitor_parameters.line_detection.vmin
        self._line_detection_npts: int = self._monitor_parameters.line_detection.npts

        # Mask (always loaded)
        self._mask: NDArray[numpy.floating[Any]] = load_hdf5_data(
            hdf5_filename=self._monitor_parameters.line_detection.mask_filename,
            hdf5_path="/data/data",
        ).astype(numpy.float64)

        # Background (loaded only when background subtraction is enabled)
        self._background_subtraction: bool = (
            self._monitor_parameters.line_detection.background_subtraction
        )
        self._background: NDArray[numpy.floating[Any]] | None = None
        if self._background_subtraction:
            self._background = load_hdf5_data(
                hdf5_filename=self._monitor_parameters.line_detection.background_filename,  # type: ignore[arg-type]
                hdf5_path="/data/data",
            ).astype(numpy.float64)

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
        masked_data: NDArray[numpy.floating[Any]] = (
            data["detector_data"].astype(numpy.float64) * self._mask
        )

        # OLS background subtraction (optional)
        if self._background_subtraction and self._background is not None:
            masked_bg: NDArray[numpy.floating[Any]] = self._background * self._mask
            bg_norm: float = float(numpy.sum(masked_bg**2))
            scale: float = (
                float(numpy.sum(masked_data * masked_bg)) / bg_norm
                if bg_norm > 0.0
                else 0.0
            )
            preprocessed: NDArray[numpy.floating[Any]] = masked_data - scale * masked_bg
        else:
            preprocessed = masked_data

        # Line detection
        _, peaks = _detect_lines(
            preprocessed,
            self._line_detection_radii,
            self._line_detection_connectivity,
            self._line_detection_vmin,
            self._line_detection_npts,
        )
        peak_list: PeakList = _peaks_to_peak_list(peaks, preprocessed)

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
                preprocessed
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
