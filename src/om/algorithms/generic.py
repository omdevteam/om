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
Generic algorithms.

This module contains algorithms that perform generic data processing operations, not
tied to a specific experimental technique (e.g.: data accumulation, radial averaging,
binning, etc.).
"""
from typing import Any, Dict, TypeVar, Union, cast

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
        initialized, it can be invoked to compute the radial profile of a data frame.

        Arguments:

            radius_pixel_map: A pixel map storing radius information for the detector
                data frame on which the algorithm is applied.

                * The array must have the same shape as the data frame on which the
                  algorithm is applied.

                * Each element of the array must store, for the corresponding pixel in
                  the data frame, its distance (in pixels) from the origin of the
                  detector reference system (usually the center of the detector).

            radial_parameters: A set of OM configuration parameters collected together
                in a parameter group. The parameter group must contain the following
                entries:

                * `radius_bin_size`: The width, in pixels, of each radius bin in the
                  radial profile.

                * `bad_pixel_map_filename`: The relative or absolute path to an HDF5
                   file containing a bad pixel map. The map can be used to exclude
                   regions of the data frame from the calculation of the radial
                   profile. If the value of this entry is None, the calculation
                   includes the full frame. Defaults to None.

                    - The map must be a numpy array with the same shape as the data
                      frame on which the algorithm is applied.

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

        # Calculates the radial bins
        self._num_bins: int = int(radius_pixel_map.max() / radius_step)
        radial_bins: NDArray[numpy.float_] = numpy.linspace(
            0, self._num_bins * radius_step, self._num_bins + 1
        )

        # Creates an array that labels each pixel according to the bin to which it
        # belongs.
        self._radial_bin_labels: NDArray[numpy.int_] = (
            numpy.searchsorted(radial_bins, radius_pixel_map, "right") - 1
        )

    def get_radial_bin_labels(self) -> NDArray[numpy.int_]:
        """
        Gets the radial bin label information.

        This function returns an array, with the same shape as the data frame on which
        the algorithm is applied, containing bin labelling information. Each element of
        the array corresponds to a pixel in the data frame, and stores the index of
        the radial bin in which the pixel falls according to the radius information
        provided to the algorithm.

        Returns:

            An array containing the bin labelling information.
        """
        return self._radial_bin_labels

    def get_bad_pixel_map(self) -> Union[NDArray[numpy.bool_], None]:
        """
        Gets the bad pixel map provided to the algorithm.

        This function returns the bad pixel map provided to the algorithm at
        initialization. If no bad pixel map was provided, the function returns None.

        Returns:

            The bad pixel map provided to the algorithm at initialization, or None if
            no map was provided.
        """

        if self._mask is not True and self._mask is not False:
            return self._mask
        else:
            return None

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
        the data in a data frame, or to generate pixel maps and masks that are
        compatible with the binned data.

        Arguments:

            layout_info: An object storing information about the internal data layout
                of the detector frame on which the algorithm is applied (number and
                size of ASICs, etc.).

            parameters: A set of OM configuration parameters collected together in a
                parameter group. The parameter group must contain the following
                entries:

                * `bin_size`: The size of the binning area in pixels (A square area of
                   `bin_size` x `bin_size` pixels in the original data frame
                   is transformed by the algorithm into a single binned pixel).

                * `bad_pixel_map_filename`: The absolute or relative path to an HDF5
                  file containing a bad pixel map. The map can be used to exclude
                  regions of the the data frame from the binning calculation. If the
                  value of this entry is None, the full frame is used to compute the
                  binned data. Defaults to None.

                    * The map must be a numpy array of the same shape as the data frame
                      on which the algorithm is applied.

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
                  from the binning calculation using a bad pixel map). Defaults to a
                  number corresponding to all the pixels in the binning area (the
                  square value of the `bin_size` argument).

                * `bad_pixel_value`: The value to be written in the binned data frame
                  when a pixel is invalid (too many pixels in the original inning area
                  are excluded by the calculation). Defaults to `MAXINT` if the data to
                  bin is of integer type, otherwise defaults to `numpy.nan`.
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
        # the pixel values in the bins. Returns the binned data array.
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
        """
        Whether the algorithm performs a simple passthrough operation.

        This function returns information on whether the algorithm performs a simple
        passthrough operation (See
        [BinningPassthrough][om.algorithms.generic.BinningPassthrough]). For this
        algorithm, the function always returns False.

        Returns:

            Whether the algorithm performs a simple passthrough operation.
        """
        return False

    def get_bin_size(self) -> int:
        """
        Gets the size of the binning area.

        This function returns the size of the area in the original data that gets
        transformed in a single pixel in the binned data. Specifically, the function
        returns the length of the edge of the area: if an area of size
        `bin size x bin size` in the original data ends up in a single binned pixel,
        the function returns the value of `bin_size`.

        Returns:

            The length of the edge of the binning area.
        """
        return self._bin_size

    def get_binned_layout_info(self) -> TypeDetectorLayoutInformation:
        """
        Gets the data layout information for the binned data frame.

        This function returns information about the internal data layout of a binned
        frame generated by the algorithm.

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

        This function computes the binned version of a provided detector data frame.
        For each binning area in the original data frame, the function initially
        computes the average value of all pixels, excluding the ones that are must be
        ignored. It then multiplies the calculated average value by the total number of
        pixels in the binning area. The result is used to fill, in the binned frame,
        the binned pixel corresponding to the original area. If, however, the binned
        pixel is determined to be invalid (too many pixels in the original area must
        be ignored), this function uses a fallback value to fill it.

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
        Computes a bad pixel map for a binned data frame.

        Starting from a bad pixel map designed for the original detector frame, this
        function calculates a bad pixel map that can be used with a binned data frame
        generated by the algorithm.

        In the bad pixel map computed by this function, only binned pixels originating
        from binning areas containing exclusively good pixels are marked as good. If
        even a single bad pixel was present in the original binning area, this function
        labels the corresponding binned pixel as bad.

        Arguments:

            mask: An array storing a bad pixel map for the original data frame.

                * The map must be a numpy array of the same shape as the data frame on
                  which the binning algorithm is applied.

                * Each pixel in the map must have a value of either 0, meaning that
                  the corresponding pixel in the data frame should be considered bad,
                  or 1, meaning that the corresponding pixel should be considered good.

                * This argument is mandatory. However, the argument can be set to None,
                  in which case the function will do nothing and return None.

        Returns:

            Either an array containing the binned map or None if the `mask` input
            argument is None.
        """
        if mask is None:
            return None
        else:
            return self._bin_data_array(data=mask) // self._bin_size**2

    def bin_pixel_maps(self, *, pixel_maps: TypePixelMaps) -> TypePixelMaps:
        """
        Computes pixel maps for a binned data frame.

        Starting from pixel maps designed for the original detector frame, this
        function calculates pixel maps that can be used with a binned data frame
        generated by the algorithm.

        Arguments:

            pixel_maps: A dictionary storing the pixel maps for the original detector
                frame.

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

        Starting from a list of peaks detected in the original detector frame, this
        function calculates the coordinates of the same peaks in a binned data frame
        generated by the algorithm.

        Arguments:

            peak_list: An dictionary storing information about a set of peaks detected
                in the original detector frame.

        Returns:

            A dictionary storing information about the detected peaks in the binned
            data frame.
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
        Passthrough binning of detector data frames.

        This algorithm has the same interface as the
        [Binning][om.algorithms.generic.Binning] algorithm. All the functions, however,
        perform no operation at all, simply returning the original detector layout
        information, detector data frame, bad pixel map, or pixel maps.

        This algorithm exists to avoid filling the code base with if statements that
        just check if binning is required and call the Binning algorithm accordingly.

        After a single initial check of the form:

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
                detector data frame on which the algorithm is applied (number and size
                of ASICs, etc.).
        """
        self._layout_info: TypeDetectorLayoutInformation = layout_info

    def is_passthrough(self) -> bool:
        """
        Whether the algorithm performs a passthrough operation.

        This function returns information on whether the algorithm performs a simple
        passthrough operation. For this algorithm, the function always returns True.

        Returns:

            Whether the algorithm performs a simple passthrough operation.
        """
        return True

    def get_bin_size(self) -> int:
        """
        Gets the size of the binning area.

        This function returns the size of the area in the original data that gets
        transformed in a single pixel in the binned data.

        Since the `BinningPassthrough` algorithm performs no binning operation at all,
        this function always returns 1.

        Returns:

            The size of the edge of binning area.
        """
        return 1

    def get_binned_layout_info(self) -> TypeDetectorLayoutInformation:
        """
        Gets the data layout information for the binned data frame.

        This function returns information about the internal data layout of a binned
        frame generated by the algorithm.

        Since the `BinningPassthrough` algorithm performs no binning operation at all,
        this function always returns the layout information initially provided to the
        algorithm.

        Returns:

            A dictionary with the data layout information for the binned frame.
        """
        return self._layout_info

    def bin_detector_data(
        self, *, data: Union[NDArray[numpy.float_], NDArray[numpy.int_]]
    ) -> NDArray[numpy.float_]:
        """
        Computes a binned version of the detector data frame.

        This function generates the binned version of a provided detector data frame.

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

        Starting from a bad pixel map designed for the original detector frame, this
        function calculates a bad pixel map that can be used with a binned data frame
        generated by the algorithm.

        Since the `BinningPassthrough` algorithm performs no binning operation at all,
        this function always returns the bad pixel map provided as input.

        Arguments:

            mask: An array storing a bad pixel map for the original data frame.

                * The map must be a numpy array of the same shape as the data frame on
                  which the binning algorithm is applied.

                * Each pixel in the map must have a value of either 0, meaning that
                  the corresponding pixel in the data frame should be considered bad,
                  or 1, meaning that the corresponding pixel should be considered good.

                * This argument is mandatory. However, the argument can be set to None,
                  in which case the function will do nothing and return None.

        Returns:

            Either an array containing the binned map or None if the `mask` input
            argument is None.
        """
        if mask is None:
            return None
        else:
            return mask

    def bin_pixel_maps(self, *, pixel_maps: TypePixelMaps) -> TypePixelMaps:
        """
        Computes pixel maps for a binned data frame.

        Starting from pixel maps designed for the original detector frame, this
        function calculates pixel maps that can be used with a binned data frame
        generated by the algorithm.

        Since the `BinningPassthrough` algorithm performs no binning operation at all,
        this function always returns the pixel maps provided as input.

        Arguments:

            pixel_maps: A dictionary storing the pixel maps for the original detector
                frame.

        Returns:

            A dictionary storing the pixel maps for the binned frame.
        """
        return pixel_maps

    def bin_peak_positions(self, peak_list: TypePeakList) -> TypePeakList:
        """
        Computes peaks positions for a binned data frame.

        Starting from a list of peaks detected in the original detector frame, this
        function calculates the coordinates of the same peaks in a binned data frame
        generated by the algorithm.

        Since the `BinningPassthrough` algorithm performs no binning operation at all,
        this function always returns the peak list provided as input.

        Arguments:

            peak_list: An dictionary storing information about a set of peaks detected
                in the original detector frame.

        Returns:

            A dictionary storing information about the detected peaks in the binned
            data frame.
        """
        return peak_list
