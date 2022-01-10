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
Generic algorithms.

This module contains algorithms that perform generic data processing operations, not
tied to a specific experimental technique (e.g.: detector frame masking and correction,
radial averaging, data accumulation, binning, etc.).
"""
import sys
from typing import Any, Dict, List, Tuple, Union

import h5py  # type:ignore
import numpy
from numpy.typing import NDArray

from om.algorithms import crystallography as cryst_algs
from om.utils import exceptions
from om.utils import parameters as param_utils
from om.utils.crystfel_geometry import TypePixelMaps


class Correction:
    """
    See documentation of the `__init__` function.
    """

    def __init__(  # noqa: C901
        self,
        *,
        parameters: Dict[str, Any] = None,
    ) -> None:
        """
        Detector data frame correction.

        This algorithm stores a dark data frame, a bad pixel mask, and a gain map
        (all three are optionals). It can then apply a correction based on these items
        to a provided detector data frame.

        Arguments:

            parameters: A set of OM configuration parameters collected together in a
                parameter group. The parameter group should contain the following
                entries:

                * `dark_filename`: The relative or absolute path to an HDF5 file
                  containing a dark data frame. Defaults to None.

                    * If this and the `dark_hdf5_path` entry are not None, the dark
                      data is loaded and used by the algorithm.

                    * The dark data frame must be a numpy array of the same shape as
                      the data frame on which the algorithm will be applied.

                * `dark_hdf5_path`: The internal HDF5 path to the data block where
                    the dark data frame is located. Defaults to None.

                    * If the `dark_filename` entry is not None, this entry must also
                      be provided, and cannot be None. Otherwise it is ignored.

                * `mask_filename`: The relative or absolute path to an HDF5 file
                  containing a mask. Defaults to None.

                    * If this and the `mask_hdf5_path` entry are not None, the mask is
                      loaded and used by the algorithm.

                    * The mask data must be a numpy array of the same shape as the data
                      frame on which the algorithm will be applied.

                    * Each pixel in the mask must have a value of either 0, meaning
                      that the corresponding pixel in the data frame should be set to
                      0, or 1, meaning that the value of the corresponding pixel should
                      be left alone.

                * `mask_hdf5_path`: The internal HDF5 path to the data block where the
                  mask data is located. Defaults to None.

                    * If the `mask_filename` entry is not None, this entry must also be
                      provided, and cannot be None. Otherwise it is ignored.

                * `gain_filename`: The relative or absolute path to an HDF5 file
                  containing a gain map. Defaults to None.

                    * If this and the `gain_hdf5_path` entry are not None, the gain map
                      is loaded and used by the algorithm.

                    * The map must be a numpy array of the same shape as the data frame
                      on which the algorithm will be applied.

                    * Each pixel in the gain map must contain the gain factor that will
                      be applied to the corresponding pixel in the data frame.

                * `gain_hdf5_path`: The internal HDF5 path to the data block where the
                  gain map data is located. Defaults to None.

                    * If the `gain_filename` entry is not None, this entry must also be
                      provided, and cannot be None. Otherwise it is ignored.
        """

        dark_filename: Union[
            str, None
        ] = param_utils.get_parameter_from_parameter_group(
            group=parameters, parameter="dark_filename", parameter_type=str
        )
        dark_hdf5_path: Union[
            str, None
        ] = param_utils.get_parameter_from_parameter_group(
            group=parameters, parameter="dark_hdf5_path", parameter_type=str
        )
        mask_filename: Union[
            str, None
        ] = param_utils.get_parameter_from_parameter_group(
            group=parameters, parameter="mask_filename", parameter_type=str
        )
        mask_hdf5_path: Union[
            str, None
        ] = param_utils.get_parameter_from_parameter_group(
            group=parameters, parameter="mask_hdf5_path", parameter_type=str
        )
        gain_filename: Union[
            str, None
        ] = param_utils.get_parameter_from_parameter_group(
            group=parameters, parameter="gain_filename", parameter_type=str
        )
        gain_hdf5_path: Union[
            str, None
        ] = param_utils.get_parameter_from_parameter_group(
            group=parameters, parameter="gain_hdf5_path", parameter_type=str
        )

        if mask_filename is not None:
            if mask_hdf5_path is not None:
                try:
                    mask_hdf5_file_handle: Any
                    with h5py.File(mask_filename, "r") as mask_hdf5_file_handle:
                        self._mask: Union[
                            NDArray[numpy.int], None
                        ] = mask_hdf5_file_handle[mask_hdf5_path][:]
                except (IOError, OSError, KeyError) as exc:
                    exc_type, exc_value = sys.exc_info()[:2]
                    # TODO: Fix types
                    raise RuntimeError(
                        "The following error occurred while reading the "
                        f"{mask_hdf5_path} field from the {mask_filename} gain map "
                        f"HDF5 file: {exc_type.__name__}: {exc_value}"
                    ) from exc
            else:
                raise exceptions.OmHdf5PathError(
                    "Correction Algorithm: missing HDF5 path for mask."
                )
        else:
            # True here is equivalent to an all-one mask.
            self._mask = True

        if dark_filename is not None:
            if dark_hdf5_path is not None:
                try:
                    dark_hdf5_file_handle: Any
                    with h5py.File(dark_filename, "r") as dark_hdf5_file_handle:
                        self._dark: Union[NDArray[numpy.float], None] = (
                            dark_hdf5_file_handle[dark_hdf5_path][:] * self._mask
                        )
                except (IOError, OSError, KeyError) as exc:
                    exc_type, exc_value = sys.exc_info()[:2]
                    # TODO: Fix types
                    raise RuntimeError(
                        "The following error occurred while reading the "
                        f"{dark_hdf5_path} field from the {dark_filename} dark data "
                        f"HDF5 file: {exc_type.__name__}: {exc_value}"
                    ) from exc
            else:
                raise exceptions.OmHdf5PathError(
                    "Correction Algorithm: missing HDF5 path for dark frame data."
                )
        else:
            # False here is equivalent to an all-zero mask.
            self._dark = False

        if gain_filename is not None:
            if gain_hdf5_path is not None:
                try:
                    gain_hdf5_file_handle: Any
                    with h5py.File(gain_filename, "r") as gain_hdf5_file_handle:
                        self._gain: Union[NDArray[numpy.float], None] = (
                            gain_hdf5_file_handle[gain_hdf5_path][:] * self._mask
                        )
                except (IOError, OSError, KeyError) as exc:
                    exc_type, exc_value = sys.exc_info()[:2]
                    # TODO: Fix types
                    raise RuntimeError(
                        "The following error occurred while reading the "
                        f"{gain_hdf5_path} field from the {gain_filename} dark data "
                        f"HDF5 file: {exc_type.__name__}: {exc_value}"
                    ) from exc
            else:
                raise exceptions.OmHdf5PathError(
                    "Correction Algorithm: missing HDF5 path for gain map."
                )
        else:
            # True here is equivalent to an all-one map.
            self._gain_map = True

    def apply_correction(self, data: NDArray[numpy.float]) -> NDArray[numpy.float]:
        """
        Applies the correction to a detector data frame.

        This function applies the correction to a detector data frame. The operation
        is carried out in the following order: initially, the mask, if provided, is
        applied to the data frame. The dark data, if available, is then subtracted.
        Finally, the result is multiplied by the gain map, if one has been set.

        Arguments:

            data: The detector data frame to which the correction must be applied.

        Returns:

            The corrected data.
        """
        return (data * self._mask - self._dark) * self._gain_map


class RadialProfile:
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        radius_pixel_map: NDArray[numpy.float],
        parameters: Dict[str, Any],
    ) -> None:
        """
        Radial average calculation.

        This algorithm stores all the parameters needed to calculate the pixel-based
        radial profile of a detector data frame. It can then compute the profile for
        a provided frame.

        Arguments:

            parameters: A set of OM configuration parameters collected together in a
                parameter group. The parameter group must contain the following
                entries:

                * `bad_pixel_map_filename`: The relative or absolute path to an HDF5
                   file containing a bad pixel map. The map can be used to exclude
                   regions of the data frame from the calclation of the radial profile.
                   If he value of this entry is None, the full frame will be used in
                   the calculation. Defaults to None.

                    * The map must be a numpy array of the same shape as the data frame
                      on which the algorithm will be applied.

                    * Each pixel in the map must have a value of either 0, meaning that
                      the corresponding pixel in the data frame should be ignored, or
                      1, meaning that the corresponding pixel should be included in the
                      calculation of the profile.

                    * The map is only used to exclude regions from the calculation: the
                      data is not modified in any way.

                * `bad_pixel_map_hdf5_path`: The internal HDF5 path to the data block
                  where the bad pixel map data is located. Defaults to None.

                    * If the `bad_pixel_map_filename` entry is not None, this entry
                      must also be provided, and cannot be None. Otherwise it is
                      ignored.

                * `radius_step`: The width (in pixels) of each step of the radial
                  average.

            radius_pixel_map: A numpy array with radius information for the detector
                data frame.

                * The array must have the same shape as the data frame on which the
                  algorithm will be applied.

                * Each element of the array must store, for the corresponding pixel in
                  the data frame, its distance (in pixels) from the origin of the
                  detector reference system (usually the center of the detector).
        """
        bad_pixel_map_filename: Union[
            str, None
        ] = param_utils.get_parameter_from_parameter_group(
            group=parameters, parameter="bad_pixel_map_filename", parameter_type=str
        )
        if bad_pixel_map_filename is not None:
            bad_pixel_map_hdf5_path: Union[
                str, None
            ] = param_utils.get_parameter_from_parameter_group(
                group=parameters,
                parameter="bad_pixel_map_hdf5_path",
                parameter_type=str,
                required=True,
            )
        else:
            bad_pixel_map_hdf5_path = None

        if bad_pixel_map_filename is not None:
            try:
                map_hdf5_file_handle: Any
                with h5py.File(bad_pixel_map_filename, "r") as map_hdf5_file_handle:
                    bad_pixel_map: Union[
                        NDArray[numpy.float], None
                    ] = map_hdf5_file_handle[bad_pixel_map_hdf5_path][:]
            except (IOError, OSError, KeyError) as exc:
                exc_type, exc_value = sys.exc_info()[:2]
                # TODO: Fix type check
                raise RuntimeError(
                    "The following error occurred while reading the "
                    f"{bad_pixel_map_hdf5_path} field from the "
                    f"{bad_pixel_map_filename} bad pixel map HDF5 file:"
                    f"{exc_type.__name__}: {exc_value}"
                ) from exc
        else:
            bad_pixel_map = None

        if bad_pixel_map is None:
            self._mask: Union[NDArray[numpy.bool], bool] = True
        else:
            self._mask = bad_pixel_map.astype(bool)

        radius_step: float = param_utils.get_parameter_from_parameter_group(
            group=parameters,
            parameter="radius_step",
            parameter_type=float,
        )

        # Calculate radial bins
        num_bins: int = int(radius_pixel_map.max() / radius_step)
        radial_bins: NDArray[numpy.float] = numpy.linspace(
            0, num_bins * radius_step, num_bins + 1
        )

        # Create an array that labels each pixel according to the bin to which it
        # belongs.
        self._radial_bin_labels: NDArray[numpy.int] = (
            numpy.searchsorted(radial_bins, radius_pixel_map, "right") - 1
        )

    def calculate_profile(self, data: NDArray[numpy.float]) -> NDArray[numpy.float]:
        """
        Calculates the radial profile for a detector data frame.

        This function calculates the radial profile of a provided detector data frame.

        Arguments:

            data: the detector data frame for which the radial profile must be
                calculated.

        Returns:

            The radial profile.
        """

        radius_sum: NDArray[numpy.int] = numpy.bincount(
            self._radial_bin_labels[self._mask].ravel(), data[self._mask].ravel()
        )
        radius_count: NDArray[numpy.int] = numpy.bincount(
            self._radial_bin_labels[self._mask].ravel()
        )
        with numpy.errstate(divide="ignore", invalid="ignore"):
            # numpy.errstate allows to ignore the divide by zero warning
            radial_average: NDArray[numpy.float] = numpy.nan_to_num(
                radius_sum / radius_count
            )

        return radial_average


class DataAccumulation:
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        parameters: Dict[str, Any],
    ) -> None:
        """
        Data accumulation and bulk retrieval.

        This algorithm accumulates a predefined number of data entries (each data entry
        must have the format of a dictionary). When the predetermined number of entries
        has been reached, the algorithm returns the accumulated data in one go, and
        resets itself.

        Arguments:

            num_events_to_accumulate (int): the number of data entries that can be
                added to the accumulator before the collected data is returned.
        """
        self._num_events_to_accumulate: int = (
            param_utils.get_parameter_from_parameter_group(
                group=parameters,
                parameter="num_events_to_accumulate",
                parameter_type=int,
            )
        )

        self._accumulator: List[Dict[str, Any]] = []
        self._num_events_in_accumulator: int = 0

    def add_data(self, data: Dict[str, Any]) -> Union[List[Dict[str, Any]], None]:
        """
        Adds data to the accumulator.

        This function adds the provided data entry to the algorithm. If, after adding
        the data, the algorithm has reached the predefined number of entries, this
        function returns all the data collected by the algorithm, and resets it.

        Arguments:

            data: A data entry to be added to the algorithm.

        Returns:

            Either a list containing the accumulated data, if the algorithm is reset,
            or None, if more data entries can still be added to the algorithm.
        """
        self._accumulator.append(data)
        self._num_events_in_accumulator += 1

        if self._num_events_in_accumulator == self._num_events_to_accumulate:
            data_to_return: List[Dict[str, Any]] = self._accumulator
            self._accumulator = []
            self._num_events_in_accumulator = 0
            return data_to_return

        return None


class Binning:
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        parameters: Dict[str, Any],
    ) -> None:
        """
        Binning of detector data frames.

        This algorithm stores all the parameters needed to bin the data of a detector
        data frame. Starting from a provided frame, it can then generate a version with
        binned pixel values, together with binned pixel maps and masks that can be used
        with it.

        Arguments:

            parameters: A set of OM configuration parameters collected together in a
                parameter group. The parameter group must contain the following
                entries:

                * `detector_type`: The type of detector on which binning operation will
                  be performed. The following detector types are currently supported:

                    * `cspad`: The CSPAD detector used at the CXI beamline of the LCLS
                      facility before 2020.

                    * `pilatus`: The Pilatus detector used at the P11 beamline of the
                      PETRA III facility.

                    * `jungfrau1M`: The 1M version of the Jungfrau detector used at the
                      PETRA III facility.

                    * `jungfrau4M`: The 4M version of the Jungfrau detector used at the
                      CXI beamline of the LCLS facility.

                    * `epix10k2M`: The 2M version of the Epix10KA detector used at the
                      MFX beamline of the LCLS facility.

                    * `rayonix`: The Rayonix detector used at the MFX beamline of the
                      LCLS facility.

                    * `eiger16M`: The 16M version of Eiger2 detector used at the PETRA
                      III facility.

                * `bin_size`: The size of the binning area in pixels (A square of
                   pixels of size `bin_size` x `bin_size` in the original data frame
                   will be collapsed into a single binned pixel).

                * `bad_pixel_map_filename`: The absolute or relative path to an HDF5
                  file containing a pixel map which can be used to exclude regions of
                  the data frame from the binning calculation. If the value of this
                  entry is None, the full frame will be used to compute the binned
                  data. Defaults to None.

                    * If this and the `bad_pixel_map_hdf5_path` entry are not None, the
                      pixel map will be loaded and used by the algorithm.

                    * The pixel map must be a numpy array of the same shape as the data
                      frame on which the algorithm will be applied.

                    * Each pixel in the map must have a value of either 0, meaning
                      that the corresponding pixel in the data frame should be ignored
                      in the binning calculation, or 1, meaning that the pixel
                      should be included in the calculation.

                * `bad_pixel_map_hdf5_path`: The internal HDF5 path to the data block
                  where the bad pixel map is stored.

                    * If the value of the `bad_pixel_map_filename` entry is not None,
                      this parameter must also be provided, and cannot be None.
                      Otherwise it is ignored.

                * `min_good_pix_count`: The minimum number of non-excluded pixels that
                  must be present in a binning area for the generated binned pixel to
                  be considered valid (pixels of the original frame can be excluded
                  from the binning calculation. See the `bad_pixel_map_filename`
                  argument). Defaults to the same value as the `bin_size` argument.

                * `bad_pixel_value`: The value to be written in the generated binned
                  frame when a pixel is invalid (i.e.: the binning area in the original
                  frame contains too many ignored pixels, see the `min_good_pix_count`
                  argument). Defaults to `MAXINT` if the input array is of integers,
                  otherwise defaults to `numpy.nan`.
        """
        self._layout_info: cryst_algs.TypePeakfinder8Info = (
            cryst_algs.get_peakfinder8_info(
                detector_type=param_utils.get_parameter_from_parameter_group(
                    group=parameters,
                    parameter="detector_type",
                    parameter_type=str,
                    required=True,
                )
            )
        )
        self._bin_size: int = param_utils.get_parameter_from_parameter_group(
            group=parameters,
            parameter="bin_size",
            parameter_type=int,
            required=True,
        )
        min_good_pix_count: Union[
            int, None
        ] = param_utils.get_parameter_from_parameter_group(
            group=parameters,
            parameter="min_good_pix_count",
            parameter_type=int,
        )
        if min_good_pix_count is None:
            self._min_good_pix_count: int = self._bin_size ** 2
        else:
            self._min_good_pix_count = min_good_pix_count
        self._bad_pixel_value: int = param_utils.get_parameter_from_parameter_group(
            group=parameters,
            parameter="bad_pixel_value",
            parameter_type=int,
        )
        bad_pixel_map_filename: Union[
            str, None
        ] = param_utils.get_parameter_from_parameter_group(
            group=parameters,
            parameter="bad_pixel_map_filename",
            parameter_type=str,
        )
        if bad_pixel_map_filename is not None:
            bad_pixel_map_hdf5_path: Union[
                str, None
            ] = param_utils.get_parameter_from_parameter_group(
                group=parameters,
                parameter="bad_pixel_map_hdf5_path",
                parameter_type=str,
                required=True,
            )
        else:
            bad_pixel_map_hdf5_path = None

        if bad_pixel_map_filename is not None:
            try:
                map_hdf5_file_handle: Any
                with h5py.File(bad_pixel_map_filename, "r") as map_hdf5_file_handle:
                    bad_pixel_map: Union[
                        NDArray[numpy.int], None
                    ] = map_hdf5_file_handle[bad_pixel_map_hdf5_path][:]
            except (IOError, OSError, KeyError) as exc:
                exc_type, exc_value = sys.exc_info()[:2]
                # TODO: Fix type check
                raise RuntimeError(
                    "The following error occurred while reading the "
                    f"{bad_pixel_map_hdf5_path} field from the "
                    f"{bad_pixel_map_filename} bad pixel map HDF5 file:"
                    f"{exc_type.__name__}: {exc_value}"
                ) from exc
        else:
            bad_pixel_map = None
        if bad_pixel_map is None:
            self._mask: NDArray[numpy.iny] = numpy.ones(
                (self._original_nx, self._original_ny), dtype=numpy.int
            )
        else:
            self._mask = bad_pixel_map

        self._original_asic_nx: int = self._layout_info["asic_ny"]
        self._original_asic_ny: int = self._layout_info["asic_nx"]
        self._original_nx: int = (
            self._layout_info["asic_ny"] * self._layout_info["nasics_y"]
        )
        self._original_ny: int = (
            self._layout_info["asic_nx"] * self._layout_info["nasics_x"]
        )

        self._extended_asic_nx: int = (
            int(numpy.ceil(self._original_asic_nx / self._bin_size)) * self._bin_size
        )
        self._extended_asic_ny: int = (
            int(numpy.ceil(self._original_asic_ny / self._bin_size)) * self._bin_size
        )
        self._extended_nx: int = self._extended_asic_nx * self._layout_info["nasics_y"]
        self._extended_ny: int = self._extended_asic_ny * self._layout_info["nasics_x"]

        self._binned_asic_nx: int = self._extended_asic_nx // self._bin_size
        self._binned_asic_ny: int = self._extended_asic_ny // self._bin_size
        self._binned_nx: int = self._extended_nx // self._bin_size
        self._binned_ny: int = self._extended_ny // self._bin_size

        # Binned mask = num good pixels per bin
        self._binned_mask: NDArray[numpy.int] = self._bin_data_array(self._mask)

    def _extend_data_array(self, data: NDArray[numpy.float]) -> NDArray[numpy.float]:
        # Extends the original data array with zeros making the asic size divisible by
        # bin_size. Returns new array of size (self._extended_nx, self._extended_ny)
        extended_data: NDArray[numpy.float] = numpy.zeros(
            (self._extended_nx, self._extended_ny)
        )
        i: int
        j: int
        for i in range(self._layout_info["nasics_x"]):
            for j in range(self._layout_info["nasics_y"]):
                extended_data[
                    i * self._extended_asic_nx : i * self._extended_asic_nx
                    + self._original_asic_nx,
                    j * self._extended_asic_ny : j * self._extended_asic_ny
                    + self._original_asic_ny,
                ] = data[
                    i * self._original_asic_nx : (i + 1) * self._original_asic_nx,
                    j * self._original_asic_ny : (j + 1) * self._original_asic_ny,
                ]
        return extended_data

    def _bin_data_array(self, data: NDArray[numpy.float]) -> NDArray[numpy.float]:
        # Gets an extended data array with dimensions divisible by bin size and sums
        # pixel values in the bins. Returns the binned data array.
        extended_data: NDArray[numpy.float] = self._extend_data_array(data)
        binned_data: NDArray[numpy.float] = (
            extended_data.reshape(
                self._binned_nx, self._bin_size, self._binned_ny, self._bin_size
            )
            .sum(3)
            .sum(1)
        )
        return binned_data

    def get_bin_size(self) -> int:
        """
        Gets the binning area's size.

        Returns:

            The size of the binning area, in pixels, along each axis.
        """
        return self._bin_size

    def get_binned_layout_info(self) -> cryst_algs.TypePeakfinder8Info:
        """
        Gets the data layout information for the binned data frame.

        This function returns information about the internal data layout of the binned
        data frame generated by the algorithm. This is the information needed, for
        example, by the
        [Peakfinder8PeakDetection][om.algorithms.crystallography.Peakfinder8PeakDetection]
        algorithm.

        Returns:

            A dictionary with the data layout information for the binned frame.
        """
        return {
            "asic_nx": self._binned_asic_ny,
            "asic_ny": self._binned_asic_nx,
            "nasics_x": self._layout_info["nasics_x"],
            "nasics_y": self._layout_info["nasics_y"],
        }

    def get_binned_data_shape(self) -> Tuple[int, int]:
        """
        Gets the shape of the binned version of the data frame.

        This function returns the shape, in numpy format, of the binned data frame
        generated by the algorithm.

        Returns:

            A tuple storing the shape (in numpy format) of the array which contains the
            binned data frame.
        """
        return self._extended_nx // self._bin_size, self._extended_ny // self._bin_size

    def bin_detector_data(self, data: NDArray[numpy.float]) -> NDArray[numpy.float]:
        """
        Computes a binned version of the detector data frame.

        This function generates a binned version of the provided detector data frame.
        For each binning area, it initally computes the average value of all
        non-ignored pixels. The function then multiplies it by the total number of
        pixels in the area. The resulting value is finally used to fill the output
        frame pixel that corresponds to the binning area. If, however, the pixel is
        determined to be invalid (see the `min_good_pix_count` argument to the class
        constructor), a fallback value (defined by the `bad_pixel_value` constructor
        argument) is used to fill it.

        Arguments:

            data: The detector data frame on which the binning must be performed.

        Returns:

            A binned version of the detector data frame.
        """

        # Set bad pixels to zero:
        data = data * self._mask
        # Bin data and scale to the number of good pixels per bin:
        with numpy.errstate(divide="ignore", invalid="ignore"):
            binned_data = (
                self._bin_data_array(data) / self._binned_mask * self._bin_size ** 2
            )

        data_type: numpy.dtype = data.dtype
        if numpy.issubdtype(data_type, numpy.integer):
            if self._bad_pixel_value is None:
                self._bad_pixel_value = numpy.iinfo(data_type).max
            binned_data[
                numpy.where(binned_data > self._bad_pixel_value)
            ] = self._bad_pixel_value
        elif self._bad_pixel_value is None:
            self._bad_pixel_value = numpy.nan

        binned_data[
            numpy.where(self._binned_mask < self._min_good_pix_count)
        ] = self._bad_pixel_value

        return binned_data

    def bin_bad_pixel_mask(
        self, mask: Union[NDArray[numpy.int], None]
    ) -> Union[NDArray[numpy.int], None]:
        """
        Computes a bad pixel mask for the binned data frame.

        Starting from a mask designed for the original detector frame, this function
        calculates a bad pixel mask that can be used with the binned frame generated by
        the algorithm.

        In the mask computed by this function, pixels originating from binning areas
        containing only good pixels in the original mask are marked as good. However,
        even a single bad pixel in the original binning area will generate a bad pixel
        in the computed binned mask.

        Arguments:

            mask: An array storing a bad pixel map for the original data frame.

                * The map must be a numpy array of the same shape as the data frame on
                  which the binning algorithm will be applied.

                * Each pixel in the map must have a value of either 0, meaning that
                  the corresponding pixel in the data frame should be considered bad,
                  or 1, meaning that the corresponding pixel should be considered good.

                * This argument is mandatory. However, the argument can be set to None,
                  in which case the function will do nothing and return None.

        Returns:

            Either an array containing the binned mask (if the input `mask` argument is
            not None) or None.
        """
        if mask is None:
            return None
        else:
            return self._bin_data_array(mask) // self._bin_size ** 2

    def bin_pixel_maps(self, pixel_maps: TypePixelMaps) -> TypePixelMaps:
        """
        Computes pixel maps for a binned data frame.

        Starting from pixel masks designed for the original detector data frame, this
        function calculates pixel maps that can be applied to the binned data frame.
        The pixel maps can be used to determine the exact coordinates of each pixel of
        the binned data frame in the detector reference system.

        Arguments:

            pixel_maps: A dictionary storing the pixel maps for the original data frame.

        Returns:

            A dictionary storing the pixel maps for the binned frame.
        """

        binned_pixel_maps: TypePixelMaps = {
            "x": self._bin_data_array(pixel_maps["x"]) / self._bin_size ** 3,
            "y": self._bin_data_array(pixel_maps["y"]) / self._bin_size ** 3,
            "z": self._bin_data_array(pixel_maps["z"]) / self._bin_size ** 3,
            "radius": self._bin_data_array(pixel_maps["radius"]) / self._bin_size ** 3,
            "phi": self._bin_data_array(pixel_maps["phi"]) / self._bin_size ** 2,
        }

        return binned_pixel_maps
