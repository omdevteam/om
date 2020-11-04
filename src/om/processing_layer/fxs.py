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
OM monitor for FXS.

This module contains an OM monitor for fluctuation X-ray scattering experiments.
"""
import sys
import time
from typing import Any, Dict, List, Tuple, Union

import h5py  # type: ignore
import numpy  # type: ignore

from om.algorithms import fxs_algorithms as fxs_algs
#import fxs_algorithms as fxs_algs

from om.algorithms import generic_algorithms as gen_algs
from om.processing_layer import base as process_layer_base
from om.utils import crystfel_geometry, parameters, zmq_monitor
from scipy import constants  # type: ignore


def _compute_autocorrelation(image: numpy.ndarray) -> numpy.ndarray:
    # Compute auto_correlation (img is a 2-d numpy array).

    fft_img: numpy.ndarray = numpy.fft.fft(image, axis=1)
    return numpy.fft.ifft(fft_img * fft_img.conj(), axis=1).real


def _normalize_autocorrelation(
    autocorr_image: numpy.ndarray, autocorr_mask: numpy.ndarray, npix_cutoff: int = 5
) -> numpy.ndarray:
    # Divide autocorrelation of image by the autocorrelation of the mask.
    # To avinpix_cutoff is used to decide if division should be performedi at all,
    # on a pixel-by-pixel basis (this is done to avoid division by zero).
    # For proper analysis if mask_autocorrelations at a particular q = 0, then one
    # should flag those values. Here npix_cutoff is set to 5 by default.

    ret_img: numpy.ndarray = numpy.zeros_like(autocorr_image)
    nradial: int = autocorr_image.shape[0]

    q_entry: int
    for q_entry in range(nradial):
        ind: numpy.ndarray = numpy.where(autocorr_mask[q_entry, :] > npix_cutoff)
        if numpy.size(ind) > 0:
            ret_img[q_entry, ind[0][:]] = autocorr_image[
                q_entry, ind[0][:]
            ] / autocorr_mask[q_entry, ind[0][:]].astype(float)
        else:
            ret_img[q_entry, ind[0][:]] = numpy.NaN

    return ret_img


class FxsMonitor(process_layer_base.OmMonitor):
    """
    See documentation for the '__init__' function.
    """

    def __init__(self, monitor_parameters: parameters.MonitorParams) -> None:
        """
        An OnDA real-time monitor for FXS experiments.

        TODO: Add description

        Arguments:

            monitor_params: An object storing the OM monitor parameters from the
                configuration file.
        """
        super(FxsMonitor, self).__init__(monitor_parameters=monitor_parameters)

        self._pixelmaps: Dict[str, numpy.ndarray]
        self._num_phi_steps: int
        self._num_radial_steps: int
        self._reference_detector_distance: float
        self._reference_beam_energy: float
        self._reference_wavelength: float
        self._fxs_pix_map_alg: fxs_algs.FxsPixelMaps
        self._radial_grid: numpy.ndarray = numpy.array([])
        self._q_grid: numpy.ndarray = numpy.array([])

    def initialize_processing_node(self, node_rank: int, node_pool_size: int) -> None:
        """
        Initializes the OM processing nodes for the Crystallography monitor.

        See documentation of the corresponding function in the base class.

        TODO: Add description

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        self._num_phi_steps = self._monitor_params.get_param(
            group="fxs", parameter="num_phi_steps", parameter_type=int, required=True
        )

        self._num_radial_steps = self._monitor_params.get_param(
            group="fxs",
            parameter="num_radial_steps",
            parameter_type=int,
            required=True,
        )

        geometry_filename: str = self._monitor_params.get_param(
            group="geometry",
            parameter="geometry_file",
            parameter_type=str,
            required=True,
        )
        geometry: crystfel_geometry.TypeDetector
        _: Any
        __: Any
        geometry, _, __ = crystfel_geometry.load_crystfel_geometry(geometry_filename)
        self._pixelmaps = crystfel_geometry.compute_pix_maps(geometry)

        # TODO: Will have a fixed radial grid in pixel units based on a
        # TODO: reference detector distance and beam energy. q in
        # TODO: inverse m will be calculated for these radii. If
        # TODO: detector distance or energy changes shot-to-shot, q at
        # TODO: the pixels will also change, and will be mapped onto
        # TODO: this reference grid so that SAXS and auto-correlations
        # TODO: are computed on the same resolution rings.
        self._reference_detector_distance = self._monitor_params.get_param(
            group="fxs",
            parameter="estimated_detector_distance",
            parameter_type=float,
            required=True,
        )
        self._reference_beam_energy = self._monitor_params.get_param(
            group="fxs",
            parameter="estimated_beam_energy",
            parameter_type=float,
            required=True,
        )
        self._reference_wavelength = (
            constants.h * constants.c / constants.e
        ) / self._reference_beam_energy
        self._fxs_pix_map_alg = fxs_algs.FxsPixelMaps(
            geometry=geometry, pixel_maps=self._pixelmaps
        )
        fxs_pixel_maps: Dict[
            str, numpy.ndarray
        ] = self._fxs_pix_map_alg.compute_fxs_pixel_maps(
            detector_distance=self._reference_detector_distance,
            wavelength=self._reference_wavelength,
        )
        # check if radial range for interpolation is entered
        # if not, set min and max to that from fxs_pix_map['r_corr']
        radial_range: list[float, float] = self._monitor_params.get_param(
            group="fxs", parameter="radial_range", parameter_type=list
        )
        r_min: float
        r_max: float
        if radial_range is not None:
            r_min, r_max = radial_range
        else:
            r_min, r_max = (
                fxs_pixel_maps["radius"].min(),
                fxs_pixel_maps["radius"].max(),
            )
        self._radial_grid = numpy.linspace(r_min, r_max, self._num_radial_steps)

        # TODO: Find a better place to do this
        # get the q values in inverse-metres corresponding to these radii
        idx: List[float] = [
            numpy.abs(radius - fxs_pixel_maps["radius"].flatten()).argmin()
            for radius in self._radial_grid
        ]

        self._q_grid = fxs_pixel_maps["q"].flatten()[idx]

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

        fxs_mask_fname: str = self._monitor_params.get_param(
            group="fxs", parameter="fxs_mask_filename", parameter_type=str, required=True
        )

        fxs_mask_hdf5_pth: str = self._monitor_params.get_param(
            group="fxs",
            parameter="fxs_mask_hdf5_path",
            parameter_type=str,
            required=True,
        )

        try:
            with h5py.File(name=fxs_mask_fname, mode="r") as fhandle:
                self._fxs_mask = fhandle[fxs_mask_hdf5_pth][:]
        except OSError:
            raise RuntimeError("Error reading the {} HDF5 file.".format(fxs_mask_fname))

        self._intensity_limits_for_hit: Tuple[
            float, float
        ] = self._monitor_params.get_param(
            group="fxs", parameter="intensity_limits_for_hit", parameter_type=list
        )

        # For interpolation from cartesian to polar detector.
        interpolation_method: str = self._monitor_params.get_param(
            group="fxs", parameter="interpolation_method", parameter_type=str
        )

        if interpolation_method == "nearest":
            print(
                "Interpolation method 'nearest' selected. "
                "Number of neighbors for interpolation has "
                "been set to 1."
            )
            num_neighbors: int = 1
        elif interpolation_method == "idw":
            num_neighbors = self._monitor_params.get_param(
                group="fxs",
                parameter="number_of_neighbors_for_interpolation",
                parameter_type=int,
                required=True,
            )
        else:
            print(
                "Interpolation method {} unknown. Falling back to " "'nearest' method."
            )
            interpolation_method = "nearest"
            num_neighbors = 1

        # Correct for different panel coffsets if desired, changing
        # detector distance, and energy.
        self._correct_for_coffset = self._monitor_params.get_param(
            group="fxs", parameter="correct_for_coffset", parameter_type=bool
        )

        self._interpolation_alg = fxs_algs.CartesianToPolarInterpolation(
            num_radial_steps=self._num_radial_steps,
            num_phi_steps=self._num_phi_steps,
            interpolation_method=interpolation_method,
            num_neighbors=num_neighbors,
            correct_for_coffset=self._correct_for_coffset,
            pixel_mask=self._fxs_mask
        )

        self._previous_detector_distance = None
        self._tree = None

        print("Starting worker: {0}.".format(node_rank))
        sys.stdout.flush()

    def initialize_collecting_node(self, node_rank: int, node_pool_size: int) -> None:
        """
        Initializes the OM collecting node for the Crystallography monitor.

        TODO: Add description

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        self._num_phi_steps = self._monitor_params.get_param(
            group="fxs", parameter="num_phi_steps", parameter_type=int, required=True
        )

        self._num_radial_steps = self._monitor_params.get_param(
            group="fxs",
            parameter="num_radial_steps",
            parameter_type=int,
            required=True,
        )

        geometry_filename: str = self._monitor_params.get_param(
            group="geometry",
            parameter="geometry_file",
            parameter_type=str,
            required=True,
        )
        geometry: crystfel_geometry.TypeDetector
        _: Any
        __: Any
        geometry, _, __ = crystfel_geometry.load_crystfel_geometry(geometry_filename)
        self._pixelmaps = crystfel_geometry.compute_pix_maps(geometry)

        # TODO: Will have a fixed radial grid in pixel units based on a
        # TODO: reference detector distance and beam energy. q in
        # TODO: inverse m will be calculated for these radii. If
        # TODO: detector distance or energy changes shot-to-shot, q at
        # TODO: the pixels will also change, and will be mapped onto
        # TODO: this reference grid so that SAXS and auto-correlations
        # TODO: are computed on the same resolution rings.
        self._reference_detector_distance = self._monitor_params.get_param(
            group="fxs",
            parameter="estimated_detector_distance",
            parameter_type=float,
            required=True,
        )
        self._reference_beam_energy = self._monitor_params.get_param(
            group="fxs",
            parameter="estimated_beam_energy",
            parameter_type=float,
            required=True,
        )
        self._reference_wavelength = (
            constants.h * constants.c / constants.e
        ) / self._reference_beam_energy
        self._fxs_pix_map_alg = fxs_algs.FxsPixelMaps(
            geometry=geometry, pixel_maps=self._pixelmaps
        )
        fxs_pixel_maps: Dict[
            str, numpy.ndarray
        ] = self._fxs_pix_map_alg.compute_fxs_pixel_maps(
            detector_distance=self._reference_detector_distance,
            wavelength=self._reference_wavelength,
        )
        # check if radial range for interpolation is entered
        # if not, set min and max to that from fxs_pix_map['r_corr']
        radial_range: list[float, float] = self._monitor_params.get_param(
            group="fxs", parameter="radial_range", parameter_type=list
        )
        r_min: float
        r_max: float
        if radial_range is not None:
            r_min, r_max = radial_range
        else:
            r_min, r_max = (
                fxs_pixel_maps["radius"].min(),
                fxs_pixel_maps["radius"].max(),
            )
        self._radial_grid = numpy.linspace(r_min, r_max, self._num_radial_steps)

        # TODO: FInd a better place to do this
        # get the q values in inverse-metres corresponding to these radii
        idx: List[float] = [
            numpy.abs(radius - fxs_pixel_maps["radius"].flatten()).argmin()
            for radius in self._radial_grid
        ]

        self._q_grid = fxs_pixel_maps["q"].flatten()[idx]

        self._speed_report_interval: int = self._monitor_params.get_param(
            group="fxs",
            parameter="speed_report_interval",
            parameter_type=int,
            required=True,
        )

        # Initialize arrays for average image, mask, saxs, and
        # auto-correlations.

        # This gives the SAXS profile
        self._sum_radial_average: numpy.ndarray = numpy.zeros((self._num_radial_steps,))

        # Sum auto-correlations of images
        self._sum_autocorr_image = numpy.zeros(
            (self._num_radial_steps, self._num_phi_steps)
        )

        # Sum auto-correlations of mask
        # TODO: check to see if we are computing this once or over
        # TODO: and over again
        self._sum_autocorr_mask: numpy.ndarray = numpy.zeros(
            (self._num_radial_steps, self._num_phi_steps)
        )

        self._sum_polar_image: numpy.ndarray = numpy.zeros(
            (self._num_radial_steps, self._num_phi_steps)
        )

        # TODO: same as with auto-correlation of the mask
        self._sum_polar_mask: numpy.ndarray = numpy.zeros(
            (self._num_radial_steps, self._num_phi_steps)
        )

        self._sum_image_hits: numpy.ndarray = numpy.zeros(self._pixelmaps["x"].shape)
        self._sum_image_misses: numpy.ndarray = numpy.zeros(self._pixelmaps["x"].shape)

        self._data_broadcast_interval: int = self._monitor_params.get_param(
            group="fxs",
            parameter="data_broadcast_interval",
            parameter_type=int,
            required=True,
        )

        self._num_events: int = 0
        self._old_time: float = time.time()
        self._time: Union[float, None] = None

        data_broadcast_url: Union[str, None] = self._monitor_params.get_param(
            group="fxs", parameter="data_broadcast_url", parameter_type=str
        )
        if data_broadcast_url is None:
            data_broadcast_url = "tcp://{0}:12321".format(
                zmq_monitor.get_current_machine_ip()
            )

        self._data_broadcast_socket: zmq_monitor.ZmqDataBroadcaster = (
            zmq_monitor.ZmqDataBroadcaster(url=data_broadcast_url)
        )

        self._num_hits: int = 0
        self._num_misses: int = 0
        self._sum_pix_int: List[int] = []

        print("Starting the monitor...")
        sys.stdout.flush()

    def process_data(
        self, node_rank: int, node_pool_size: int, data: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], int]:
        """
        Processes a detector data frame.

        TODO: Add description

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

            data: A dictionary containing the data retrieved by OM for the frame being
                processed.

                * The dictionary keys must match the entries in the 'required_data'
                  list found in the 'om' configuration parameter group.

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

        if not self._intensity_limits_for_hit:
            hit: bool = True
        else:
            intensity_sum: float = numpy.sum(corrected_detector_data * self._fxs_mask)
            hit = (
                self._intensity_limits_for_hit[0]
                <= intensity_sum
                <= self._intensity_limits_for_hit[1]
            )

        wavelength: float = (constants.h * constants.c / constants.e) / data[
            "beam_energy"
        ]

        # TODO: clean this up
        if not self._reference_detector_distance:
            self._reference_detector_distance = data["detector_distance"]

        if not self._reference_wavelength:
            self._reference_wavelength = wavelength

        fxs_pixel_maps: Dict[
            str, numpy.ndarray
        ] = self._fxs_pix_map_alg.compute_fxs_pixel_maps(
            detector_distance=data["detector_distance"],
            wavelength=wavelength,
            #reference_detector_distance=self._reference_detector_distance,
            #reference_wavelength=self._reference_wavelength,
        )

        interpolation_info: Dict[
            str, Any
        ] = self._interpolation_alg.compute_interpolation_info(
            radii=self._radial_grid,
            fxs_pixel_maps=fxs_pixel_maps,
            detector_distance_changed=(
                data["detector_distance"] != self._previous_detector_distance
            ),
        )
        self._previous_detector_distance = data["detector_distance"]

        polar_data: numpy.ndarray = (
            interpolation_info["weight"]
            * corrected_detector_data.ravel()[interpolation_info["index"]]
        ).reshape(self._num_radial_steps, self._num_phi_steps)

        polar_mask = numpy.floor(
            interpolation_info["weight"]
            * self._fxs_mask.ravel()[interpolation_info["index"]]
        ).reshape(self._num_radial_steps, self._num_phi_steps)

        # Compute radial average
        entry: int
        ind: List[numpy.ndarray] = [
            numpy.nonzero(polar_mask[entry, :])
            for entry in range(self._num_radial_steps)
        ]

        # TODO: what happens if we have a dynamic mask?
        radial_average: numpy.ndarray = numpy.array(
            [
                numpy.average(polar_data[q_entry, ind[q_entry][0][:]])
                if numpy.size(ind[q_entry]) > 0
                else numpy.NaN
                for q_entry in range(self._num_radial_steps)
            ]
        )

        # compute saxs profile and correlation function
        polar_corrected_image = polar_mask * (
            polar_data - radial_average[:, numpy.newaxis]
        )
        autocorrelation_image = _compute_autocorrelation(polar_corrected_image)
        autocorrelation_mask = _compute_autocorrelation(polar_mask)

        # TODO: KP will look at it (maybe)
        # HACK: assume all pixels have the same size
        theta = numpy.arctan2(
            self._radial_grid * fxs_pixel_maps["pix_size"][0, 0],
            (data["detector_distance"] + numpy.zeros((self._num_radial_steps,))),
        )

        q_values = 4.0 * numpy.pi * numpy.sin(theta / 2.0) / wavelength
        q_coords = (q_values, theta)

        processed_data["timestamp"] = data["timestamp"]
        processed_data["hit"] = hit
        processed_data["detector_distance"] = data["detector_distance"]
        processed_data["beam_energy"] = data["beam_energy"]
        processed_data["native_shape"] = corrected_detector_data.shape
        processed_data["masked_corrected_det_data"] = (
            self._fxs_mask * corrected_detector_data
        )
        processed_data["radial_average"] = radial_average
        processed_data["polar_image"] = polar_corrected_image
        processed_data["polar_mask"] = polar_mask
        processed_data["autocorrelation_image"] = autocorrelation_image
        processed_data["autocorrelation_mask"] = autocorrelation_mask
        processed_data["q_coords"] = q_coords

        return (processed_data, node_rank)

    def collect_data(
        self,
        node_rank: int,
        node_pool_size: int,
        processed_data: Tuple[Dict[str, Any], int],
    ) -> None:
        """
        Computes statistics on aggregated data and broadcasts them via a network socket.

        See documentation of the corresponding function in the base class.

        TODO: Add description

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

        if received_data["hit"]:
            self._num_hits += 1
        else:
            self._num_misses += 1

        self._sum_pix_int.append(received_data["masked_corrected_det_data"].sum())
        self._sum_radial_average += received_data["radial_average"]
        self._sum_autocorr_image += received_data["autocorrelation_image"]
        self._sum_autocorr_mask += received_data["autocorrelation_mask"]
        self._sum_polar_image += received_data["polar_image"]
        self._sum_polar_mask += received_data["polar_mask"]

        if received_data["hit"]:
            self._sum_image_hits += received_data["masked_corrected_det_data"]
        else:
            self._sum_image_misses += received_data["masked_corrected_det_data"]

        if self._num_events % self._data_broadcast_interval == 0:

            autocorr_sum_img: numpy.ndarray = _compute_autocorrelation(
                self._sum_polar_image
            )
            autocorr_sum_msk: numpy.ndarray = _compute_autocorrelation(
                self._sum_polar_mask
            )

            average_autocorr_image: numpy.ndarray = _normalize_autocorrelation(
                autocorr_image=self._sum_autocorr_image,
                autocorr_mask=self._sum_autocorr_mask,
                npix_cutoff=self._num_radial_steps,
            )

            autocorr_average_image: numpy.ndarray = _normalize_autocorrelation(
                autocorr_image=autocorr_sum_img,
                autocorr_mask=autocorr_sum_msk,
                npix_cutoff=self._num_radial_steps,
            )

            collected_data: Dict[str, Any] = {}
            if self._num_misses:
                collected_data["sum_image_misses"] = self._sum_image_misses / float(
                    self._num_misses
                )
            else:
                collected_data["sum_image_misses"] = self._sum_image_misses

            if self._num_hits:
                collected_data["sum_image_hits"] = self._sum_image_hits / float(
                    self._num_hits
                )

                collected_data["radial_average"] = self._sum_radial_average / float(
                    self._num_hits
                )
            else:
                collected_data["sum_image_hits"] = self._sum_image_hits
                collected_data["sum_radial_average"] = self._sum_radial_average

            collected_data["ac"] = average_autocorr_image - autocorr_average_image
            collected_data["timestamp"] = received_data["timestamp"]
            collected_data["detector_distance"] = received_data["detector_distance"]
            collected_data["beam_energy"] = received_data["beam_energy"]
            collected_data["native_shape"] = received_data["native_shape"]
            collected_data["sum_pix_int"] = self._sum_pix_int
            collected_data["q_coords"] = received_data["q_coords"]

            self._data_broadcast_socket.send_data(
                tag="view:omdata", message=collected_data
            )

            self._gui_sending_counter = 0
            self._sum_pix_int = []

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
    ) -> Union[Dict[str, Any], None]:
        pass

    def end_processing_on_collecting_node(
        self, node_rank: int, node_pool_size: int
    ) -> None:
        pass
