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
OnDA Monitor for Crystallography.

This module contains an OnDA Monitor for serial x-ray crystallography experiments.
"""
import collections
import sys
import time
from random import random
from typing import Any, Deque, Dict, List, Tuple, Union

import h5py  # type: ignore
import numpy  # type: ignore
from scipy import constants

from om.algorithms import crystallography as cryst_algs
from om.algorithms import generic as gen_algs
from om.algorithms.crystallography import TypePeakfinder8Info
from om.processing_layer import base as process_layer_base
from om.utils import (
    crystfel_geometry,
    exceptions,
    hdf5_writers,
    parameters,
    zmq_monitor,
)
from om.utils.crystfel_geometry import TypeDetector, TypePixelMaps

try:
    import msgpack  # type: ignore
except ImportError:
    raise exceptions.OmMissingDependencyError(
        "The following required module cannot be imported: msgpack"
    )


# TODO: Fix documentation for this file


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

        self._droplet_detection_enabled: Union[
            bool, None
        ] = self._monitor_params.get_param(
            group="droplet_detection",
            parameter="droplet_detection_enabled",
            parameter_type=bool,
        )
        if self._droplet_detection_enabled is None:
            self._droplet_detection_enabled = False

        if self._droplet_detection_enabled is True:
            dd_oil_peak_min_i: int = self._monitor_params.get_param(
                group="droplet_detection",
                parameter="oil_peak_min_i",
                parameter_type=int,
                required=True,
            )
            dd_oil_peak_max_i: int = self._monitor_params.get_param(
                group="droplet_detection",
                parameter="oil_peak_max_i",
                parameter_type=int,
                required=True,
            )
            dd_water_peak_min_i: int = self._monitor_params.get_param(
                group="droplet_detection",
                parameter="water_peak_min_i",
                parameter_type=int,
                required=True,
            )
            dd_water_peak_max_i: int = self._monitor_params.get_param(
                group="droplet_detection",
                parameter="water_peak_max_i",
                parameter_type=int,
                required=True,
            )
            dd_threshold_min: float = self._monitor_params.get_param(
                group="droplet_detection",
                parameter="minimum_threshold_for_droplet_hit",
                parameter_type=float,
                required=True,
            )
            dd_threshold_max: float = self._monitor_params.get_param(
                group="droplet_detection",
                parameter="maximum_threshold_for_droplet_hit",
                parameter_type=float,
                required=True,
            )
            dd_oil_profile_fname: str = self._monitor_params.get_param(
                group="droplet_detection",
                parameter="oil_profile_filename",
                parameter_type=str,
            )
            dd_water_profile_fname: str = self._monitor_params.get_param(
                group="droplet_detection",
                parameter="water_profile_filename",
                parameter_type=str,
            )

            if dd_oil_profile_fname is not None:
                try:
                    dd_oil_profile: numpy.ndarray = numpy.loadtxt(dd_oil_profile_fname)
                except (IOError, OSError, KeyError) as exc:
                    # TODO: type this
                    exc_type, exc_value = sys.exc_info()[:2]
                    raise RuntimeError(
                        "The following error occurred while reading the {0} oil profile "
                        " file: {1}: {2}".format(
                            dd_oil_profile_fname,
                            exc_type.__name__,  # type: ignore
                            exc_value,
                        )
                    ) from exc
            else:
                dd_oil_profile = None

            if dd_water_profile_fname is not None:
                try:
                    dd_water_profile: numpy.ndarray = numpy.loadtxt(
                        dd_water_profile_fname
                    )
                except (IOError, OSError, KeyError) as exc:
                    # TODO: type this
                    exc_type, exc_value = sys.exc_info()[:2]
                    raise RuntimeError(
                        "The following error occurred while reading the {0} water profile "
                        "file: {1}: {2}".format(
                            dd_water_profile_fname,
                            exc_type.__name__,  # type: ignore
                            exc_value,
                        )
                    ) from exc
            else:
                dd_water_profile = None

            self._droplet_detection: cryst_algs.DropletDetection = (
                cryst_algs.DropletDetection(
                    oil_peak_min_i=dd_oil_peak_min_i,
                    oil_peak_max_i=dd_oil_peak_max_i,
                    water_peak_min_i=dd_water_peak_min_i,
                    water_peak_max_i=dd_water_peak_max_i,
                    oil_profile=dd_oil_profile,
                    water_profile=dd_water_profile,
                    threshold_min=dd_threshold_min,
                    threshold_max=dd_threshold_max,
                    radius_pixel_map=self._pixelmaps["radius"],
                    bad_pixel_map=bad_pixel_map,
                )
            )

            self._dd_jet_threshold: Union[bool, None] = self._monitor_params.get_param(
                group="droplet_detection",
                parameter="threshold_for_jet_hit",
                parameter_type=float,
            )

            self._swaxs_subtract_background: bool = self._monitor_params.get_param(
                group="droplet_detection",
                parameter="subtract_background",
                parameter_type=bool,
                required=True,
            )
            swaxs_bg_vectors_fname: str = self._monitor_params.get_param(
                group="droplet_detection",
                parameter="background_vectors_npy_filename",
                parameter_type=str,
            )

            if self._swaxs_subtract_background:
                if swaxs_bg_vectors_fname is not None:
                    try:
                        self._swaxs_bg_vectors: numpy.ndarray = numpy.atleast_2d(
                            numpy.load(swaxs_bg_vectors_fname)
                        )
                    except (IOError, OSError, KeyError) as exc:
                        # TODO: type this
                        exc_type, exc_value = sys.exc_info()[:2]
                        raise RuntimeError(
                            "The following error occurred while reading the {0} water profile "
                            "file: {1}: {2}".format(
                                swaxs_bg_vectors_fname,
                                exc_type.__name__,  # type: ignore
                                exc_value,
                            )
                        ) from exc
                else:
                    self._swaxs_bg_vectors = None
                    self._swaxs_subtract_background = False

            # Acqiris
            self._integrate_digitizer: Union[
                bool, None
            ] = self._monitor_params.get_param(
                group="droplet_detection",
                parameter="integrate_digitizer",
                parameter_type=bool,
            )

            if self._integrate_digitizer is None:
                self._integrate_digitizer = False
            else:
                offset = numpy.array(
                    [
                        -0.00842321,
                        -0.00538909,
                        -0.00853421,
                        -0.0058195,
                        -0.00840969,
                        -0.00561713,
                        -0.00844767,
                        -0.00562044,
                        -0.00838569,
                        -0.00528033,
                        -0.008455,
                        -0.00522185,
                        -0.00864199,
                        -0.0056621,
                        -0.00876859,
                        -0.0058492,
                    ]
                )
                self._75xoffset = numpy.tile(offset, 75)

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

        self._droplet_detection_enabled: Union[
            bool, None
        ] = self._monitor_params.get_param(
            group="droplet_detection",
            parameter="droplet_detection_enabled",
            parameter_type=bool,
        )
        if self._droplet_detection_enabled is None:
            self._droplet_detection_enabled = False

        if self._droplet_detection_enabled:
            self._save_radials: bool = self._monitor_params.get_param(
                group="droplet_detection",
                parameter="save_radials",
                parameter_type=bool,
                required=True,
            )

            if self._save_radials:
                self._radials_filename: str = self._monitor_params.get_param(
                    group="droplet_detection",
                    parameter="radials_filename",
                    parameter_type=str,
                    required=True,
                )

            # droplet hitrate
            self._droplet_hit_rate_running_window: Deque[float] = collections.deque(
                [0.0] * self._running_average_window_size,
                maxlen=self._running_average_window_size,
            )
            self._avg_droplet_hit_rate: int = 0
            self._droplet_hit_rate_timestamp_history: Deque[float] = collections.deque(
                5000 * [0.0], maxlen=5000
            )
            self._droplet_hit_rate_history: Deque[float] = collections.deque(
                5000 * [0.0], maxlen=5000
            )

            self._q_tosave: List[numpy.ndarray] = []
            self._image_sum_tosave: List[float] = []
            self._radials_tosave: List[numpy.ndarray] = []
            self._errors_tosave: List[numpy.ndarray] = []
            self._frame_is_droplet: List[bool] = []
            self._frame_is_crystal: List[bool] = []
            self._frame_is_jet: List[bool] = []
            self._q: List[numpy.ndarrray] = None

            self._roi1_qmin: float = self._monitor_params.get_param(
                group="droplet_detection",
                parameter="roi1_qmin",
                parameter_type=float,
                required=True,
            )
            self._roi1_qmax: float = self._monitor_params.get_param(
                group="droplet_detection",
                parameter="roi1_qmax",
                parameter_type=float,
                required=True,
            )
            self._roi2_qmin: float = self._monitor_params.get_param(
                group="droplet_detection",
                parameter="roi2_qmin",
                parameter_type=float,
                required=True,
            )
            self._roi2_qmax: float = self._monitor_params.get_param(
                group="droplet_detection",
                parameter="roi2_qmax",
                parameter_type=float,
                required=True,
            )
            self._estimate_particle_size: float = self._monitor_params.get_param(
                group="droplet_detection",
                parameter="estimate_particle_size",
                parameter_type=bool,
                required=True,
            )
            self._use_guinier_peak: float = self._monitor_params.get_param(
                group="droplet_detection",
                parameter="use_guinier_peak",
                parameter_type=bool,
                required=False,
            )
            self._guinier_qmin: float = self._monitor_params.get_param(
                group="droplet_detection",
                parameter="guinier_qmin",
                parameter_type=float,
                required=False,
            )
            self._guinier_qmax: float = self._monitor_params.get_param(
                group="droplet_detection",
                parameter="guinier_qmax",
                parameter_type=float,
                required=False,
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

        self._cheetah_enabled: str = self._monitor_params.get_param(
            group="cheetah",
            parameter="cheetah_enabled",
            parameter_type=bool,
        )
        if self._cheetah_enabled:
            processed_directory: str = self._monitor_params.get_param(
                group="cheetah",
                parameter="processed_directory",
                parameter_type=str,
            )
            processed_filename_prefix: Union[
                str, None
            ] = self._monitor_params.get_param(
                group="cheetah",
                parameter="processed_filename_prefix",
                parameter_type=str,
            )
            processed_filename_extension: Union[
                str, None
            ] = self._monitor_params.get_param(
                group="cheetah",
                parameter="processed_filename_extension",
                parameter_type=str,
            )
            data_type: Union[str, None] = self._monitor_params.get_param(
                group="cheetah",
                parameter="hdf5_file_data_type",
                parameter_type=str,
            )
            compression: Union[str, None] = self._monitor_params.get_param(
                group="cheetah",
                parameter="hdf5_file_compression",
                parameter_type=str,
            )
            compression_opts: Union[int, None] = self._monitor_params.get_param(
                group="cheetah",
                parameter="hdf5_file_compression_opts",
                parameter_type=int,
            )
            compression_shuffle: Union[bool, None] = self._monitor_params.get_param(
                group="cheetah",
                parameter="hdf5_file_compression_shuffle",
                parameter_type=bool,
            )
            hdf5_file_max_num_peaks: Union[int, None] = self._monitor_params.get_param(
                group="cheetah",
                parameter="hdf5_file_max_num_peaks",
                parameter_type=int,
            )
            hdf5_fields: Dict[str, str] = self._monitor_params.get_all_parameters()[
                "cheetah"
            ]["hdf5_fields"]

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

        self._data_shape: Tuple[int, int] = self._pixelmaps["x"].shape

        if bad_pixel_map is None:
            mask = numpy.ones(self._data_shape, dtype=bool)
        else:
            mask = bad_pixel_map.astype(bool)

        # Calculate radial bins to get shape for hdf5 creation
        r: numpy.ndarray = self._pixelmaps["radius"]
        rstep: float = 1.0
        nbins: int = int((r.max() - r.min()) / rstep)
        # rbins = numpy.linspace(0, nbins * rstep, nbins + 1)
        rbins = numpy.linspace(r.min(), r.max(), nbins + 1)
        rbin_labels: numpy.ndarray = numpy.searchsorted(rbins, r, "right")
        rbin_labels -= 1
        # get average r value in each bin for q calculation
        rsum: numpy.ndarray = numpy.bincount(rbin_labels[mask].ravel(), r[mask].ravel())
        rcount: numpy.ndarray = numpy.bincount(rbin_labels[mask].ravel())
        with numpy.errstate(divide="ignore", invalid="ignore"):
            # numpy.errstate just allows us to ignore the divide by zero warning
            self._ravg = numpy.nan_to_num(rsum / rcount)
        radial_shape = (len(self._ravg),)

        if self._cheetah_enabled:
            self._file_writer: hdf5_writers.HDF5Writer = hdf5_writers.HDF5Writer(
                directory_for_processed_data=processed_directory,
                node_rank=node_rank,
                geometry=self._geometry,
                compression=compression,
                detector_data_type=data_type,
                detector_data_shape=self._data_shape,
                radial_shape=radial_shape,
                hdf5_fields=hdf5_fields,
                processed_filename_prefix=processed_filename_prefix,
                processed_filename_extension=processed_filename_extension,
                compression_opts=compression_opts,
                compression_shuffle=compression_shuffle,
                max_num_peaks=hdf5_file_max_num_peaks,
            )

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

        # peak_list: cryst_algs.TypePeakList = self._peak_detection.find_peaks(
        #     corrected_detector_data
        # )
        # frame_is_hit: bool = (
        #     self._min_num_peaks_for_hit
        #     < len(peak_list["intensity"])
        #     < self._max_num_peaks_for_hit
        # )
        frame_is_hit: bool = False

        processed_data["timestamp"] = data["timestamp"]
        processed_data["frame_is_hit"] = frame_is_hit
        processed_data["detector_distance"] = data["detector_distance"]
        processed_data["beam_energy"] = data["beam_energy"]
        processed_data["event_id"] = data["event_id"]
        processed_data["data_shape"] = data["detector_data"].shape
        processed_data["lcls_extra"] = data["lcls_extra"]

        # for testing to plot an image and the q values
        # it would be great if I could do this assembled somehow.
        # rbins = self._droplet_detection._rbin_labels
        # nominal_energy = data["beam_energy"]
        # wavelen = constants.c * constants.h / (nominal_energy * constants.electron_volt )
        # detdist = 2.5908 #data["detector_distance"]*1e-3 + self._first_panel_coffset
        # pixsize = 0.000110 #self._pixel_size #pixel size is actual res from crystfel, which is 1/pixsize
        # theta =  numpy.arctan( pixsize*rbins / detdist ) *.5
        # q = numpy.sin( theta ) * 4 * numpy.pi / wavelen
        # q *= 1e-10
        # import matplotlib.pyplot as plt
        # fig, (ax1, ax2) = plt.subplots(1,2)
        # print(q.min(),q.max())
        # print(corrected_detector_data.min(),corrected_detector_data.max())
        # ax1.imshow(q)
        # ax2.imshow(corrected_detector_data,vmin=0,vmax=100.0)
        # plt.show()
        # exit()

        # if frame_is_hit:
        #     processed_data["peak_list"] = peak_list
        #     if self._hit_frame_sending_interval is not None:
        #         self._hit_frame_sending_counter += 1
        #         if self._hit_frame_sending_counter == self._hit_frame_sending_interval:
        #             # If the frame is a hit, and if the 'hit_sending_interval'
        #             # attribute says that the detector frame data should be sent to
        #             # the collecting node, adds the data to the 'processed_data'
        #             # dictionary (and resets the counter).
        #             processed_data["detector_data"] = corrected_detector_data
        #             self._hit_frame_sending_counter = 0
        # else:
        #     # If the frame is not a hit, sends an empty peak list.
        #     processed_data["peak_list"] = {"fs": [], "ss": [], "intensity": []}
        #     if self._non_hit_frame_sending_interval is not None:
        #         self._non_hit_frame_sending_counter += 1
        #         if (
        #             self._non_hit_frame_sending_counter
        #             == self._non_hit_frame_sending_interval
        #         ):
        #             # If the frame is a not a hit, and if the 'hit_sending_interval'
        #             # attribute says that the detector frame data should be sent to
        #             # the collecting node, adds the data to the 'processed_data'
        #             # dictionary (and resets the counter).
        #             processed_data["detector_data"] = corrected_detector_data
        #             self._non_hit_frame_sending_counter = 0

        # TODO: This part we need to merge

        if self._droplet_detection_enabled:
            self._dd_median_filter = False
            # Solution/radial profile-based droplet hit finding
            radial, errors = self._droplet_detection.radial_profile(
                corrected_detector_data,
                medfilter=self._dd_median_filter,
                return_errors=True,
            )
            frame_is_jet: bool = corrected_detector_data.sum() > self._dd_jet_threshold
            frame_is_droplet, waterp_oilp_ratio = self._droplet_detection.is_droplet(
                radial
            )
            if not frame_is_jet:
                frame_is_droplet = False

        else:
            radial = numpy.zeros(1)
            errors = numpy.zeros(1)
            frame_is_droplet = False
            frame_is_jet = False

        processed_data["radial"] = radial
        processed_data["errors"] = errors
        processed_data["image_sum"] = corrected_detector_data.sum()

        if self._swaxs_subtract_background:
            # vectors=numpy.vstack((self._oil_profile, self._water_profile))
            coefficients = cryst_algs._fit_by_least_squares(
                radial=radial, vectors=self._swaxs_bg_vectors, nmin=800, nmax=1000
            )
            bgfit = radial * 0
            for i in range(len(coefficients)):
                bgfit += coefficients[i] * self._swaxs_bg_vectors[i]
            subtracted_radial = radial - bgfit
            processed_data["subtracted_radial"] = subtracted_radial
        else:
            processed_data["subtracted_radial"] = radial

        # get acqiris trace for photodiode reading if desired (simple sum):
        if self._integrate_digitizer:
            # we noticed a periodic systematic signal after averaging over a run
            # it appears to be consistent, every 16 points (75 periods over 1200 points)
            # so for now, let's manually correct for this:
            dd = data["lcls_extra"]["digitizer_data"][0]
            dd -= self._75xoffset
            # sum from indices 200 to 500 to focus on just the region with signal (out of 1200 total).
            # the range on the diode is 0e-7 to 6e-7. We want 1e-7 to 2.5e-7, so 200 to 500 index
            # will make this a config parameter in the future
            i0, i1 = (200, 500)
            processed_data["digitizer_sum"] = numpy.sum(dd[i0:i1])
            # reset digitizer signal for convenience in h5 saving when analyzing offline
            data["lcls_extra"]["digitizer_data"] = dd
        else:
            processed_data["digitizer_sum"] = 0

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

        request: Union[str, None] = self._responding_socket.get_request()
        if request is not None:
            if request == "next":
                message: Any = msgpack.packb(
                    {
                        "beam_energy": received_data["beam_energy"],
                        "detector_distance": received_data["detector_distance"],
                        "event_id": received_data["event_id"],
                        "timestamp": received_data["timestamp"],
                    },
                    use_bin_type=True,
                )
                self._responding_socket.send_data(message)
            else:
                print("OM Warning: Could not understand request '{}'.")

        # rbins = numpy.arange(len(received_data["radial"]))
        rbins = self._ravg
        nominal_energy = received_data["beam_energy"]
        wavelen = constants.c * constants.h / (nominal_energy * constants.electron_volt)
        detdist = received_data["detector_distance"] * 1e-3 + self._first_panel_coffset
        # XXXXXXXXXXXXXXX
        # detdist = 2.100 #hard code for a moment
        # XXXXXXXXXXXXXXXX
        pixsize = (
            1 / self._pixel_size
        )  # pixel size is actual res from crystfel, which is 1/pixsize
        theta = numpy.arctan(pixsize * rbins / detdist) * 0.5
        q = numpy.sin(theta) * 4 * numpy.pi / wavelen
        q *= 1e-10

        if self._q is None:
            self._q = numpy.zeros((self._running_average_window_size, len(rbins)))
            self._radials = numpy.zeros((self._running_average_window_size, len(rbins)))
            self._errors = numpy.zeros((self._running_average_window_size, len(rbins)))
            self._image_sum = numpy.zeros(
                (self._running_average_window_size, len(rbins))
            )
            self._upstream_monitor = numpy.zeros((5000))
            self._downstream_monitor = numpy.zeros((5000))
            self._roi1_int = numpy.zeros((5000))
            self._roi2_int = numpy.zeros((5000))
            self._rg = numpy.zeros((5000))
            self._digitizer_sum = numpy.zeros((5000))

        # wp = numpy.mean(received_data["subtracted_radial"][360:390])
        # hp = numpy.mean(received_data["subtracted_radial"][100:150])
        # ratio = wp/hp
        # if ratio > 1.0:
        self._q = numpy.roll(self._q, -1, axis=0)
        self._q[-1] = q
        self._radials = numpy.roll(self._radials, -1, axis=0)
        self._radials[-1] = received_data["subtracted_radial"]
        self._errors = numpy.roll(self._errors, -1, axis=0)
        self._errors[-1] = received_data["errors"]
        self._image_sum = numpy.roll(self._image_sum, -1, axis=0)
        self._image_sum[-1] = received_data["image_sum"]
        self._upstream_monitor = numpy.roll(self._upstream_monitor, -1)
        self._upstream_monitor[-1] = received_data["lcls_extra"]["before_sample"]
        self._downstream_monitor = numpy.roll(self._downstream_monitor, -1)
        self._downstream_monitor[-1] = received_data["lcls_extra"]["after_sample"]
        self._digitizer_sum = numpy.roll(self._digitizer_sum, -1)
        self._digitizer_sum[-1] = received_data["digitizer_sum"]

        # grab the intensities from the regions of interest, e.g. water ring and low q ring
        # normalize by the downstream monitor
        radial = received_data["subtracted_radial"]
        roi1_idx = numpy.where((q >= self._roi1_qmin) & (q <= self._roi1_qmax))
        roi1_int = numpy.mean(radial[roi1_idx])
        roi2_idx = numpy.where((q >= self._roi2_qmin) & (q <= self._roi2_qmax))
        roi2_int = numpy.mean(radial[roi2_idx])
        self._roi1_int = numpy.roll(self._roi1_int, -1)
        self._roi1_int[-1] = roi1_int / received_data["lcls_extra"]["before_sample"]
        self._roi2_int = numpy.roll(self._roi2_int, -1)
        self._roi2_int[-1] = roi2_int / received_data["lcls_extra"]["before_sample"]

        if self._estimate_particle_size:
            qidx = numpy.where((q >= self._guinier_qmin) & (q <= self._guinier_qmax))
            qmini = numpy.min(qidx)
            qmaxi = numpy.max(qidx)
            if self._use_guinier_peak:
                # try to estimate Rg using Guinier Peak method
                rg = cryst_algs.calc_rg_by_guinier_peak(q, radial, nb=qmini, ne=qmaxi)
            else:
                # try to estimate Rg using standard Guinier plot
                rg = cryst_algs.calc_rg_by_guinier(q, radial, nb=qmini, ne=qmaxi)
        else:
            rg = 0.0

        self._rg = numpy.roll(self._rg, -1)
        self._rg[-1] = rg

        if self._cheetah_enabled:
            data_to_write = {
                "q": q,
                "radial": received_data["radial"],
                "errors": received_data["errors"],
                "image_sum": received_data["image_sum"],
            }
            data_to_write.update(received_data)
            self._file_writer.write_frame(data_to_write)
            received_data["filename"] = self._file_writer.get_current_filename()
            received_data["index"] = self._file_writer.get_num_written_frames()

        if self._num_events % self._data_broadcast_interval == 0:
            message = {
                "geometry_is_optimized": self._geometry_is_optimized,
                "timestamp": received_data["timestamp"],
                "beam_energy": received_data["beam_energy"],
                "detector_distance": received_data["detector_distance"],
                "first_panel_coffset": self._first_panel_coffset,
                "pixel_size": self._pixel_size,
            }

            stack = self._radials
            message["q"] = q
            message["radial"] = received_data["subtracted_radial"]
            message["radial_stack"] = stack[-self._running_average_window_size :]
            message["recent_radial_average"] = numpy.mean(
                stack[-self._running_average_window_size :], 0
            )
            # message["cumulative_radial_average"] = numpy.mean(stack,0)

            message["upstream_monitor_history"] = self._upstream_monitor
            message["downstream_monitor_history"] = self._downstream_monitor
            message["roi1_int_history"] = self._roi1_int
            message["roi2_int_history"] = self._roi2_int
            message["digitizer_sum_history"] = self._digitizer_sum
            message["rg"] = self._rg

            # if self._num_events % self._data_broadcast_interval == 0:
            #     svd = True
            #     if svd:
            #         n0 = 60
            #         n1 = -30
            #         svd_stack = stack[-self._running_average_window_size:]
            #         svd_stack[:,:n0] = 0
            #         svd_stack[:,n1:] = 0
            #         u, s, vt = numpy.linalg.svd(svd_stack, full_matrices=False)
            #         self._svd_nvecs_to_keep = 5
            #         message["svd_vectors"] = vt[:self._svd_nvecs_to_keep]
            #     else:
            #         message["svd_vectors"] = numpy.zeros((2,len(q)))

            self._data_broadcast_socket.send_data(tag="view:omdata", message=message)

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
        # if self._save_radials:
        #     print("Saving radial data to the radials.h5 file.")
        #     radials_file = h5py.File(self._radials_filename, "w")
        #     radials_file.create_dataset("q", data=self._q_tosave)
        #     radials_file.create_dataset("radials", data=self._radials_tosave)
        #     radials_file.create_dataset("errors", data=self._errors_tosave)
        #     radials_file.create_dataset("image_sum", data=self._image_sum_tosave)
        #     radials_file.close()

        print(
            "Processing finished. OM has processed {0} events in total.".format(
                self._num_events
            )
        )
        sys.stdout.flush()
