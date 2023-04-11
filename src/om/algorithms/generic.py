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
from typing import Any, Dict, List, Tuple, TypeVar, Union, cast

import numpy
from numpy.typing import DTypeLike, NDArray

from om.algorithms import crystallography as cryst_algs
from om.lib.geometry import GeometryInformation, TypePixelMaps
from om.lib.hdf5 import parse_parameters_and_load_hdf5_data
from om.lib.parameters import get_parameter_from_parameter_group

from ._generic import bin_detector_data  # type: ignore

A = TypeVar("A", numpy.float_, numpy.int_)


class Correction:
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        parameters: Dict[str, Any],
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

        dark_data: Union[NDArray[numpy.float_], None] = cast(
            Union[NDArray[numpy.float_], None],
            parse_parameters_and_load_hdf5_data(
                parameters=parameters,
                hdf5_filename_parameter="dark_filename",
                hdf5_path_parameter="dark_hdf5_path",
            ),
        )

        if dark_data is not None:
            self._dark: Union[NDArray[numpy.float_], int] = dark_data
        else:
            self._dark = 0

        mask_data: Union[NDArray[numpy.int_], None] = cast(
            Union[NDArray[numpy.int_], None],
            parse_parameters_and_load_hdf5_data(
                parameters=parameters,
                hdf5_filename_parameter="mask_filename",
                hdf5_path_parameter="mask_hdf5_path",
            ),
        )

        if mask_data is not None:
            self._mask: Union[NDArray[numpy.int_], int] = mask_data
        else:
            self._mask = 1

        gain_data: Union[NDArray[numpy.float_], None] = cast(
            Union[NDArray[numpy.float_], None],
            parse_parameters_and_load_hdf5_data(
                parameters=parameters,
                hdf5_filename_parameter="gain_filename",
                hdf5_path_parameter="gain_hdf5_path",
            ),
        )

        if gain_data is not None:
            self._gain_map: Union[NDArray[numpy.float_], float] = gain_data
        else:
            self._gain_map = 1.0

    def apply_correction(self, data: NDArray[numpy.float_]) -> NDArray[numpy.float_]:
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
        radius_pixel_map: NDArray[numpy.float_],
        parameters: Dict[str, Any],
        bad_pixel_map: Union[NDArray[numpy.int_], None],
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
                   regions of the data frame from the calculation of the radial profile.
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
        if bad_pixel_map is None:
            self._mask: Union[NDArray[numpy.bool_], bool] = True
        else:
            self._mask = bad_pixel_map.astype(bool)

        radius_step: float = get_parameter_from_parameter_group(
            group=parameters,
            parameter="radius_step",
            parameter_type=float,
        )

        # Calculate radial bins
        num_bins: int = int(radius_pixel_map.max() / radius_step)
        radial_bins: NDArray[numpy.float_] = numpy.linspace(
            0, num_bins * radius_step, num_bins + 1
        )

        # Create an array that labels each pixel according to the bin to which it
        # belongs.
        self._radial_bin_labels: NDArray[numpy.int_] = (
            numpy.searchsorted(radial_bins, radius_pixel_map, "right") - 1
        )

    def calculate_profile(self, data: NDArray[numpy.float_]) -> NDArray[numpy.float_]:
        """
        Calculates the radial profile for a detector data frame.

        This function calculates the radial profile of a provided detector data frame.

        Arguments:

            data: the detector data frame for which the radial profile must be
                calculated.

        Returns:

            The radial profile.
        """

        radius_sum: NDArray[numpy.int_] = numpy.bincount(
            self._radial_bin_labels[self._mask].ravel(), data[self._mask].ravel()
        )
        radius_count: NDArray[numpy.int_] = numpy.bincount(
            self._radial_bin_labels[self._mask].ravel()
        )
        with numpy.errstate(divide="ignore", invalid="ignore"):
            # numpy.errstate allows to ignore the divide by zero warning
            radial_average: NDArray[numpy.float_] = numpy.nan_to_num(
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

            parameters: A set of OM configuration parameters collected together in a
                parameter group. The parameter group must contain the following
                entries:

                * `num_events_to_accumulate`: the number of data entries that can be
                   added to the accumulator before the collected data is returned.
        """
        self._num_events_to_accumulate: int = get_parameter_from_parameter_group(
            group=parameters,
            parameter="num_events_to_accumulate",
            parameter_type=int,
        )

        self._accumulator: List[Dict[str, Any]] = []
        self._num_events_in_accumulator: int = 0

    def add_data(self, *, data: Dict[str, Any]) -> Union[List[Dict[str, Any]], None]:
        """
        Adds data to the accumulator.

        This function adds the provided data entry to the algorithm. If, after adding
        the data, the algorithm has reached its maximum predefined number of
        accumulated entries, the function returns all the accumulated data and resets
        the algorithm. Otherwise, the function returns None.

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
        geometry_information: GeometryInformation,
        bad_pixel_map: Union[NDArray[numpy.int_], None],
    ) -> None:
        """
        Binning of detector data frames.

        This algorithm stores all the parameters needed to bin the data of a detector
        data frame. Starting from a provided frame, it can then generate a version of
        the frame with binned pixel values, and additionally provide pixel maps and
        masks that can be used with it.

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

                * `geometry information`: TODO

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
                  argument). Defaults to `MAXINT` if the input array is an array of
                  integers, otherwise defaults to `numpy.nan`.
        """

        self._geometry_information = geometry_information

        self._layout_info: cryst_algs.TypePeakfinder8Info = (
            cryst_algs.get_peakfinder8_info(
                detector_type=get_parameter_from_parameter_group(
                    group=parameters,
                    parameter="detector_type",
                    parameter_type=str,
                    required=True,
                )
            )
        )
        self._bin_size: int = get_parameter_from_parameter_group(
            group=parameters,
            parameter="bin_size",
            parameter_type=int,
            required=True,
        )
        min_good_pix_count: Union[int, None] = get_parameter_from_parameter_group(
            group=parameters,
            parameter="min_good_pix_count",
            parameter_type=int,
        )
        if min_good_pix_count is None:
            self._min_good_pix_count: int = self._bin_size**2
        else:
            self._min_good_pix_count = min_good_pix_count

        self._bad_pixel_value: Union[int, float] = get_parameter_from_parameter_group(
            group=parameters,
            parameter="bad_pixel_value",
            parameter_type=int,
        )

        self._original_asic_nx: int = self._layout_info["asic_ny"]
        self._original_asic_ny: int = self._layout_info["asic_nx"]
        self._original_nx: int = (
            self._layout_info["asic_ny"] * self._layout_info["nasics_y"]
        )
        self._original_ny: int = (
            self._layout_info["asic_nx"] * self._layout_info["nasics_x"]
        )

        if bad_pixel_map is None:
            self._mask: NDArray[numpy.int_] = numpy.ones(
                (self._original_nx, self._original_ny), dtype=numpy.int8
            )
        else:
            self._mask = bad_pixel_map.astype(numpy.int8)

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
        self._binned_mask: NDArray[numpy.int_] = self._bin_data_array(
            data=cast(NDArray[numpy.int_], self._mask)
        )

        self._float_data_array: NDArray[numpy.float_] = numpy.zeros(
            (self._original_nx, self._original_ny), dtype=numpy.float64
        )
        self._binned_data_array: NDArray[numpy.float_] = numpy.zeros(
            (self._binned_nx, self._binned_ny), dtype=numpy.float64
        )

        # TODO: What is the following?
        self._saturation_value: float = -1.0

        self._binned_pixel_maps: TypePixelMaps = self._bin_pixel_maps(
            pixel_maps=self._geometry_information.get_pixel_maps()
        )

        self._binned_visual_pixel_maps: TypePixelMaps = self._bin_pixel_maps(
            pixel_maps=self._geometry_information.get_visualization_pixel_maps()
        )

        geometry_information.get_pixel_maps()
        self._binned_visual_pixel_maps = geometry_information.get_pixel_maps()

    def _extend_data_array(self, *, data: NDArray[A]) -> NDArray[A]:
        # Extends the original data array with zeros making the asic size divisible by
        # bin_size. Returns new array of size (self._extended_nx, self._extended_ny)
        extended_data: NDArray[A] = numpy.zeros(
            (self._extended_nx, self._extended_ny), dtype=data.dtype
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

    def _bin_data_array(self, *, data: NDArray[A]) -> NDArray[A]:
        # Gets an extended data array with dimensions divisible by bin size and sums
        # pixel values in the bins. Returns the binned data array.
        extended_data: NDArray[A] = self._extend_data_array(data=data)
        binned_data: NDArray[A] = (
            extended_data.reshape(
                self._binned_nx, self._bin_size, self._binned_ny, self._bin_size
            )
            .sum(3)
            .sum(1)
        )
        return binned_data

    def _bin_pixel_maps(self, *, pixel_maps: TypePixelMaps) -> TypePixelMaps:
        # TODO

        binned_pixel_maps: TypePixelMaps = {
            "x": self._bin_data_array(data=cast(NDArray[numpy.float_], pixel_maps["x"]))
            / self._bin_size**3,
            "y": self._bin_data_array(data=cast(NDArray[numpy.float_], pixel_maps["y"]))
            / self._bin_size**3,
            "z": self._bin_data_array(data=cast(NDArray[numpy.float_], pixel_maps["z"]))
            / self._bin_size**3,
            "radius": self._bin_data_array(
                data=cast(NDArray[numpy.float_], pixel_maps["radius"])
            )
            / self._bin_size**3,
            "phi": self._bin_data_array(
                data=cast(NDArray[numpy.float_], pixel_maps["phi"])
            )
            / self._bin_size**2,
        }

        return binned_pixel_maps

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

    def get_binned_min_array_shape_for_visualization(self) -> Tuple[int, int]:
        """
        Gets the shape of the binned version of the data frame.

        This function returns the shape, in numpy format, of the binned data frame
        generated by the algorithm.

        Returns:

            A tuple storing the shape (in numpy format) of the array which contains the
                binned data frame.
        """
        return self._extended_nx // self._bin_size, self._extended_ny // self._bin_size

    def get_binned_pixel_maps(self) -> TypePixelMaps:
        """
        TODO
        """
        return self._binned_pixel_maps

    def get_binned_visualization_pixel_maps(self) -> TypePixelMaps:
        """
        TODO
        """
        return self._binned_visual_pixel_maps

    def get_binned_bad_pixel_map(self) -> NDArray[numpy.int_]:
        """
        TODO
        """
        return self._binned_mask

    def bin_detector_data(
        self, *, data: NDArray[numpy.float_]
    ) -> NDArray[numpy.float_]:
        """
        Computes a binned version of the detector data frame.

        This function generates a binned version of the provided detector data frame.
        For each binning area, it initially computes the average value of all
        non-ignored pixels. The function then multiplies it by the total number of
        pixels in the area. The resulting value is finally used to fill the output
        frame pixel that corresponds to the binning area. If, however, the pixel is
        determined to be invalid (see the `min_good_pix_count` argument of the class's
        constructor), a fallback value (defined by the `bad_pixel_value` argument of
        the constructor) is used to fill it.

        Arguments:

            data: The detector data frame on which the binning must be performed.

        Returns:

            A binned version of the detector data frame.
        """

        data_type: DTypeLike = data.dtype
        if self._bad_pixel_value is None:
            if numpy.issubdtype(data_type, numpy.integer):
                # TODO: is self._bad_pixel_value int or float?
                self._bad_pixel_value = numpy.iinfo(data_type).max
            else:
                self._bad_pixel_value = -1.0e10
        if numpy.issubdtype(data_type, numpy.integer):
            self._saturation_value = float(numpy.iinfo(data_type).max)

        self._float_data_array[:] = data
        bin_detector_data(
            self._float_data_array,
            self._binned_data_array,
            self._mask,
            self._bin_size,
            self._min_good_pix_count,
            self._bad_pixel_value,
            self._saturation_value,
            self._original_asic_ny,
            self._original_asic_nx,
            self._layout_info["nasics_y"],
            self._layout_info["nasics_x"],
        )
        return self._binned_data_array
