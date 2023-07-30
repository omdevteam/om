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
tied to a specific experimental technique (e.g.: data accumulation, binning, etc.).
"""
from typing import Any, Dict, List, TypeVar, Union, cast

import numpy
from numpy.typing import DTypeLike, NDArray

from om.algorithms.crystallography import TypePeakList
from om.lib.geometry import TypeDetectorLayoutInformation, TypePixelMaps
from om.lib.hdf5 import parse_parameters_and_load_hdf5_data
from om.lib.parameters import get_parameter_from_parameter_group

from ._generic import bin_detector_data  # type: ignore

A = TypeVar("A", numpy.float_, numpy.int_)


class RadialProfile:
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        radius_pixel_map: NDArray[numpy.float_],
        radial_parameters: Dict[str, Any],
    ) -> None:
        """
        Radial average calculation.

        This algorithm stores all the parameters needed to calculate the pixel-based
        radial profile of a detector data frame. After the algorithm has been
        initialized, it can be invoked to compute the radial profile of a provided
        detector frame.

        Arguments:

            radius_pixel_map: A pixel map storing radius information for the detector
                data frame on which the algorithm will be applied.


                * The array must have the same shape as the data frame on which the
                  algorithm will be applied.

                * Each element of the array must store, for the corresponding pixel in
                  the data frame, its distance (in pixels) from the origin of the
                  detector reference system (usually the center of the detector).

            radial_parameters: A set of OM configuration parameters collected together
                in a parameter group. The parameter group must contain the following
                entries:

                * `radius_bin_size`: The width (in pixels) of each radius bin in the
                  radial profile.

                * `bad_pixel_map_filename`: The relative or absolute path to an HDF5
                   file containing a bad pixel map. The map can be used to exclude
                   regions of the data frame from the calculation of the radial
                   profile. If the value of this entry is None, the calculation will
                   include the full frame. Defaults to None.

                    - The map must be a numpy array with the same shape as the data
                      frame on which the algorithm will be applied.

                    - Each pixel in the map must have a value of either 0, meaning that
                      the corresponding pixel in the data frame should be ignored, or
                      1, meaning that the corresponding pixel should be included in the
                      calculation of the profile.

                    - The map is only used to exclude regions from the calculation: the
                      data is not modified in any way.

                * `bad_pixel_map_hdf5_path`: The internal HDF5 path to the data block
                  where the bad pixel map data is located. Defaults to None.

                    - If the `bad_pixel_map_filename` entry is not None, this entry
                      must also be provided, and cannot be None. Otherwise it is
                      ignored.

        """

        bad_pixel_map: Union[NDArray[numpy.int_], None] = cast(
            Union[NDArray[numpy.int_], None],
            parse_parameters_and_load_hdf5_data(
                parameters=radial_parameters,
                hdf5_filename_parameter="bad_pixel_map_filename",
                hdf5_path_parameter="bad_pixel_map_hdf5_path",
            ),
        )

        if bad_pixel_map is None:
            self._mask: Union[NDArray[numpy.bool_], bool] = True
        else:
            self._mask = bad_pixel_map.astype(bool)

        radius_step: float = get_parameter_from_parameter_group(
            group=radial_parameters,
            parameter="radius_bin_size",
            parameter_type=float,
            required=True,
        )

        # Calculate radial bins
        self._num_bins: int = int(radius_pixel_map.max() / radius_step)
        radial_bins: NDArray[numpy.float_] = numpy.linspace(
            0, self._num_bins * radius_step, self._num_bins + 1
        )

        # Create an array that labels each pixel according to the bin to which it
        # belongs.
        self._radial_bin_labels: NDArray[numpy.int_] = (
            numpy.searchsorted(radial_bins, radius_pixel_map, "right") - 1
        )

        # TODO: Make r not the r at the center of the bin, but the average of the
        # rs all pixels in the bin. Call radial profile with r values rather than
        # intensity to calculate it. We need to return it for further calculation.

    def get_radial_bin_labels(self) -> NDArray[numpy.int_]:
        """
        # TODO: Documentation
        """
        return self._radial_bin_labels

    def get_mask(self) -> Union[NDArray[numpy.bool_], bool]:
        return self._mask

    def calculate_profile(
        self,
        data: Union[NDArray[numpy.float_], NDArray[numpy.int_]],
    ) -> NDArray[numpy.float_]:
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
                   added to the accumulation algorithm before the collected data is
                   returned.
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
        Adds data to the accumulation algorithm.

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
        layout_info: TypeDetectorLayoutInformation,
        parameters: Dict[str, Any],
    ) -> None:
        """
        Binning of detector data frames.

        This algorithm stores all the parameters needed to bin the data in a detector
        data frame. After the algorithm has been initialized, it can be invoked to bin
        the data in a provided data frame, or to generate pixel maps and masks that are
        compatible with the binned data.

        Arguments:

            layout_info: An object storing information about the internal layout of the
                detector data frame on which the algorithm will be applied (number and
                size of ASICs, etc.).

            parameters: A set of OM configuration parameters collected together in a
                parameter group. The parameter group must contain the following
                entries:

                * `bin_size`: The size of the binning area in pixels (A square of
                   pixels of size `bin_size` x `bin_size` in the original data frame
                   will be collapsed into a single binned pixel).

                * `bad_pixel_map_filename`: The absolute or relative path to an HDF5
                  file containing a pixel map with information on the regions of the
                  the detector data frame that must be excluded from the binning
                  calculation. If the value of this entry is None, the full frame will
                  be used to compute the binned data. Defaults to None.

                    * If this and the `bad_pixel_map_hdf5_path` entry are not None, the
                      pixel map will be loaded and used by the algorithm.

                    * The pixel map must be a numpy array of the same shape as the data
                      frame on which the algorithm will be applied.

                    * Each pixel in the map must have a value of either 0, meaning
                      that the corresponding pixel in the data frame must be ignored
                      in the binning calculation, or 1, meaning that the pixel
                      must be included in the calculation.

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
        self._layout_info: TypeDetectorLayoutInformation = layout_info
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
        bad_pixel_map: Union[NDArray[numpy.int_], None] = cast(
            Union[NDArray[numpy.int_], None],
            parse_parameters_and_load_hdf5_data(
                parameters=parameters,
                hdf5_filename_parameter="bad_pixel_map_filename",
                hdf5_path_parameter="bad_pixel_map_hdf5_path",
            ),
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

        # # Binned mask = num good pixels per bin
        self._binned_mask: NDArray[numpy.int_] = self._bin_data_array(data=self._mask)

        self._float_data_array: NDArray[numpy.float_] = numpy.zeros(
            (self._original_nx, self._original_ny), dtype=numpy.float64
        )
        self._binned_data_array: NDArray[numpy.float_] = numpy.zeros(
            (self._binned_nx, self._binned_ny), dtype=numpy.float64
        )

        # TODO: What is the following?
        self._saturation_value: float = -1.0

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

    def is_passthrough(self) -> bool:
        return False

    def get_bin_size(self) -> int:
        """
        Gets the size of the binning area.

        This value represents the size of the area in the original data that will end
        up in the same pixel in the binned data. Specifically, an area of size
        `bin size x bin size` ends up in a single binned pixel.

        Returns:

            The size of the edge of binning area.
        """
        return self._bin_size

    def get_binned_layout_info(self) -> TypeDetectorLayoutInformation:
        """
        Gets the data layout information for the binned data frame.

        This function returns information about the internal data layout of the binned
        data frame generated by the algorithm.

        Returns:

            A dictionary with the data layout information for the binned frame.
        """
        return {
            "asic_nx": self._binned_asic_ny,
            "asic_ny": self._binned_asic_nx,
            "nasics_x": self._layout_info["nasics_x"],
            "nasics_y": self._layout_info["nasics_y"],
        }

    def bin_detector_data(
        self, *, data: Union[NDArray[numpy.float_], NDArray[numpy.int_]]
    ) -> NDArray[numpy.float_]:
        """
        Computes a binned version of the detector data frame.

        This function generates a binned version of the provided detector data frame.
        For each source region in the original data, the function initially computes
        the average value of all pixels, excluding the ones that are marked to be
        ignored. It then multiplies the average value by the total number of
        pixels in the region, and uses the result to fill, in the binned frame, the
        corresponding binned pixel. If, however, the binned pixel is determined to be
        invalid (based on the `min_good_pix_count` argument provided when the algorithm
        is initialized), a fallback value is used to fill it.

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

        self._float_data_array[:] = data.astype(numpy.float_)
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

    def bin_bad_pixel_map(
        self, *, mask: Union[NDArray[numpy.int_], None]
    ) -> Union[NDArray[numpy.int_], None]:
        """
        Computes a bad pixel map for the binned data frame.

        Starting from a map designed for the original detector frame, this function
        calculates a bad pixel map that can be used with the binned data frame
        generated by the algorithm.

        In the binned map computed by this function, only pixels originating from
        good pixels in the original map are marked as good. If even a single bad pixel
        in the original map ends up contributing to a pixel in the binned map, the
        pixel n the binned map is marked as bad.

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

            Either an array containing the binned map (if the input `mask` argument is
                not None) or None.
        """
        if mask is None:
            return None
        else:
            return self._bin_data_array(data=mask) // self._bin_size**2

    def bin_pixel_maps(self, *, pixel_maps: TypePixelMaps) -> TypePixelMaps:
        """
        Computes pixel maps for a binned data frame.

        Starting from pixel maps designed for the original detector frame, this
        function bad calculates pixel maps that can be used with the binned data frame
        generated by the algorithm.

        Arguments:

            pixel_maps: A dictionary storing the pixel maps for the original data frame.

        Returns:

            A dictionary storing the pixel maps for the binned frame.
        """

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

    def bin_peak_positions(self, peak_list: TypePeakList) -> TypePeakList:
        """
        Computes peaks positions for a binned data frame.

        Starting from a list of peaks detected in the original data frame, this
        function calculates the coordinates of the same peaks in the binned data frame
        generated by the algorithm.

        Arguments:

            peak_list: An dictionary storing information about a set of peaks detected
                in the original data frame.

        Returns:

            A dictionary which stores the information about the detected peaks and can
                be used with the binned frame.
        """
        peak_index: int
        for peak_index in range(peak_list["num_peaks"]):
            peak_list["fs"][peak_index] = (
                peak_list["fs"][peak_index] + 0.5
            ) / self._bin_size - 0.5
            peak_list["ss"][peak_index] = (
                peak_list["ss"][peak_index] + 0.5
            ) / self._bin_size - 0.5
        return peak_list


class BinningPassthrough:
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        layout_info: TypeDetectorLayoutInformation,
    ) -> None:
        """
        Binning of detector data frames.

        This algorithm has the same methods as the
        [Binning][om.algorithms.generic.Binning] algorithm. The methods, however,
        perform no operation at all, simply returning the original detector layout
        information, detector data frame, bad pixel map, or pixel maps.

        This algorithm exists to avoid littering the code base with if statements that
        just check if binning is required and call the Binning algorithm accordingly.
        With a single initial check of the form:

        ```
        if binning_required:
            binning = Binning(...)
        else:
            binning = BinningPassthrough(...)
        ```

        The rest of the code can avoid performing checks and simply call the methods of
        the `binning` instance, expecting the correct behavior.

        Arguments:

            layout_info: An object storing information about the internal layout of the
                detector data frame on which the algorithm will be applied (number and
                size of ASICs, etc.).
        """
        self._layout_info: TypeDetectorLayoutInformation = layout_info

    def is_passthrough(self) -> bool:
        return True

    def get_bin_size(self) -> int:
        """
        Gets the size of the binning area.

        This value represents the size of the area in the original data that will end
        up in the same pixel in the binned data. Specifically, an area of size
        `bin size x bin size` ends up in a single binned pixel.

        Since the `BinningPassthrough` algorithm performs no binning operation at all,
        this function always returns 1.

        Returns:

            The size of the edge of binning area.
        """
        return 1

    def get_binned_layout_info(self) -> TypeDetectorLayoutInformation:
        """
        Gets the data layout information for the binned data frame.

        This function returns information about the internal data layout of the binned
        data frame generated by the algorithm.

        Since the `BinningPassthrough` algorithm performs no binning operation at all,
        this function always returns the layout information for the non-binned data
        frame.

        Returns:

            A dictionary with the data layout information for the binned frame.
        """
        return self._layout_info

    def bin_detector_data(
        self, *, data: Union[NDArray[numpy.float_], NDArray[numpy.int_]]
    ) -> NDArray[numpy.float_]:
        """
        Computes a binned version of the detector data frame.

        This function generates a binned version of the provided detector data frame.

        Since the `BinningPassthrough` algorithm performs no binning operation at all,
        this function always returns the detector data frame provided as input.

        Arguments:

            data: The detector data frame on which the binning must be performed.

        Returns:

            A binned version of the detector data frame.
        """
        return data.astype(numpy.float_)

    def bin_bad_pixel_map(
        self, *, mask: Union[NDArray[numpy.int_], None]
    ) -> Union[NDArray[numpy.int_], None]:
        """
        Computes a bad pixel map for the binned data frame.

        Starting from a map designed for the original detector frame, this function
        calculates a bad pixel map that can be used with the binned data frame
        generated by the algorithm.

        Since the `BinningPassthrough` algorithm performs no binning operation at all,
        this function always returns the bad pixel map provided as input.

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

            Either an array containing the binned map (if the input `mask` argument is
                not None) or None.
        """
        if mask is None:
            return None
        else:
            return mask

    def bin_pixel_maps(self, *, pixel_maps: TypePixelMaps) -> TypePixelMaps:
        """
        Computes pixel maps for a binned data frame.

        Starting from pixel maps designed for the original detector frame, this
        function bad calculates pixel maps that can be used with the binned data frame
        generated by the algorithm.

        Since the `BinningPassthrough` algorithm performs no binning operation at all,
        this function always returns the pixel maps provided as input.

        Arguments:

            pixel_maps: A dictionary storing the pixel maps for the original data frame.

        Returns:

            A dictionary storing the pixel maps for the binned frame.
        """
        return pixel_maps

    def bin_peak_positions(self, peak_list: TypePeakList) -> TypePeakList:
        """
        Computes peaks positions for a binned data frame.

        Starting from a list of peaks detected in the original data frame, this
        function calculates the coordinates of the same peaks in the binned data frame
        generated by the algorithm.

        Since the `BinningPassthrough` algorithm performs no binning operation at all,
        this function always returns the peak list provided as input.

        Arguments:

            peak_list: An dictionary storing information about a set of peaks detected
                in the original data frame.

        Returns:

            A dictionary which stores the information about the detected peaks and can
                be used with the binned frame.
        """
        return peak_list
