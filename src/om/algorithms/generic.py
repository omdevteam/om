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

This module contains algorithms that perform generic processing the data: common
operations that are not tied to a specific experimental technique (e.g.: detector frame
masking and correction, radial averaging, data accumulation, etc.).
"""
import sys
from typing import Any, Dict, List, Union, Tuple

import h5py  # type:ignore
import numpy  # type: ignore

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
        dark_filename: Union[str, None] = None,
        dark_hdf5_path: Union[str, None] = None,
        mask_filename: Union[str, None] = None,
        mask_hdf5_path: Union[str, None] = None,
        gain_filename: Union[str, None] = None,
        gain_hdf5_path: Union[str, None] = None,
        parameters: Union[Dict[str, Any], None] = None,
    ) -> None:
        """
        Detector data frame correction.

        This algorithm can store a dark data frame, a bad pixel mask, and a gain map
        (all three are optionals). Upon request, it can apply all of these to a
        detector data frame.

        Arguments:

            dark_filename: The relative or absolute path to an HDF5 file containing a
                dark data frame. Defaults to None.

                * If this and the 'dark_hdf5_path' arguments are not None, the dark
                  data is loaded and used by the algorithm.

                * The dark data frame must be a numpy array of the same shape as the
                  data frame on which the algorithm will be applied.

            dark_hdf5_path: The internal HDF5 path to the data block where the dark
                data frame is located. Defaults to None.

                * If the 'dark_filename' argument is not None, this argument must also
                  be provided, and cannot be None. Otherwise it is ignored.

            mask_filename: The relative or absolute path to an HDF5 file containing a
                mask. Defaults to None.

                * If this and the 'mask_hdf5_path' arguments are not None, the mask is
                  loaded and used by the algorithm.

                * The mask data must be a numpy array of the same shape as the data
                  frame on which the algorithm will be applied.

                * Each pixel in the mask must have a value of either 0, meaning that
                  the corresponding pixel in the data frame should be set to 0, or 1,
                  meaning that the value of the corresponding pixel should be left
                  alone.

            mask_hdf5_path: The internal HDF5 path to the data block where the mask
                data is located. Defaults to None.

                * If the 'mask_filename' argument is not None, this argument must also
                  be provided, and cannot be None. Otherwise it is ignored.

            gain_filename: The relative or absolute path to an HDF5 file containing a
                gain map. Defaults to None.

                * If this and the 'gain_hdf5_path' arguments are not None, the gain map
                  is loaded and used by the algorithm.

                * The map must be a numpy array of the same shape as the data frame
                  on which the algorithm will be applied.

                * Each pixel in the gain map must store the gain factor that will be
                  applied to the corresponding pixel in the data frame.

            gain_hdf5_path: The internal HDF5 path to the data block where the gain map
                data is located. Defaults to None.

                * If the 'gain_filename' argument is not None, this argument must also
                  be provided, and cannot be None. Otherwise it is ignored.
        """

        if parameters is not None:
            dark_filename = param_utils.get_parameter_from_parameter_group(
                group=parameters, parameter="dark_filename", parameter_type=str
            )
            dark_hdf5_path = param_utils.get_parameter_from_parameter_group(
                group=parameters, parameter="dark_hdf5_path", parameter_type=str
            )
            mask_filename = param_utils.get_parameter_from_parameter_group(
                group=parameters, parameter="mask_filename", parameter_type=str
            )
            mask_hdf5_path = param_utils.get_parameter_from_parameter_group(
                group=parameters, parameter="mask_hdf5_path", parameter_type=str
            )
            gain_filename = param_utils.get_parameter_from_parameter_group(
                group=parameters, parameter="gain_filename", parameter_type=str
            )
            gain_hdf5_path = param_utils.get_parameter_from_parameter_group(
                group=parameters, parameter="gain_hdf5_path", parameter_type=str
            )

        if mask_filename is not None:
            if mask_hdf5_path is not None:
                try:
                    mask_hdf5_file_handle: Any
                    with h5py.File(mask_filename, "r") as mask_hdf5_file_handle:
                        self._mask: Union[numpy.ndarray, None] = mask_hdf5_file_handle[
                            mask_hdf5_path
                        ][:]
                except (IOError, OSError, KeyError) as exc:
                    exc_type, exc_value = sys.exc_info()[:2]
                    # TODO: Fix types
                    raise RuntimeError(
                        "The following error occurred while reading the {0} field "
                        "from the {1} gain map HDF5 file: {2}: {3}".format(
                            mask_filename,
                            mask_hdf5_path,
                            exc_type.__name__,  # type: ignore
                            exc_value,
                        )
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
                        self._dark: Union[numpy.ndarray, None] = (
                            dark_hdf5_file_handle[dark_hdf5_path][:] * self._mask
                        )
                except (IOError, OSError, KeyError) as exc:
                    exc_type, exc_value = sys.exc_info()[:2]
                    # TODO: Fix types
                    raise RuntimeError(
                        "The following error occurred while reading the {0} field from"
                        "the {1} dark data HDF5 file: {2}: {3}".format(
                            dark_filename,
                            dark_hdf5_path,
                            exc_type.__name__,  # type: ignore
                            exc_value,
                        )
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
                        self._gain: Union[numpy.ndarray, None] = (
                            gain_hdf5_file_handle[gain_hdf5_path][:] * self._mask
                        )
                except (IOError, OSError, KeyError) as exc:
                    exc_type, exc_value = sys.exc_info()[:2]
                    # TODO: Fix types
                    raise RuntimeError(
                        "The following error occurred while reading the {0} field from"
                        "the {1} dark data HDF5 file: {2}: {3}".format(
                            gain_filename,
                            gain_hdf5_path,
                            exc_type.__name__,  # type: ignore
                            exc_value,
                        )
                    ) from exc
            else:
                raise exceptions.OmHdf5PathError(
                    "Correction Algorithm: missing HDF5 path for gain map."
                )
        else:
            # True here is equivalent to an all-one map.
            self._gain_map = True

    def apply_correction(self, data: numpy.ndarray) -> numpy.ndarray:
        """
        Applies the correction to a detector data frame.

        This function initially applies the mask, if provided, to the data frame. The
        dark data, if provided, is then subtracted. Finally, the result is multiplied
        by the gain map, again only if the latter is provided.

        Arguments:

            data: The detector data frame on which the correction must be applied.

        Returns:

            The corrected data.
        """
        return (data * self._mask - self._dark) * self._gain_map


class RadialProfile:
    """
    See documentation of the '__init__' function.
    """

    def __init__(
        self,
        *,
        radius_pixel_map: numpy.ndarray,
        bad_pixel_map: Union[numpy.ndarray, None] = None,
        radius_step: Union[float, None] = None,
        parameters: Union[Dict[str, Any], None] = None,
    ) -> None:
        """
        Algorithm for calculation of radial average.

        This algorithm stores all the parameters needed to calculate the pixel-based
        radial profile of a detector data frame. It also calculates the profile for a
        frame upon request.

        Arguments:

            bad_pixel_map: An array storing a bad pixel map. The map can be used to
                mark areas of the data frame that must be excluded from the profile. If
                the value of this argument is None, no area will be excluded from the
                profile. Defaults to None.

                * The map must be a numpy array of the same shape as the data frame on
                  which the algorithm will be applied.

                * Each pixel in the map must have a value of either 0, meaning that
                  the corresponding pixel in the data frame should be ignored, or 1,
                  meaning that the corresponding pixel should be included in the
                  profile.

                * The map is only used to exclude areas from the profile: the data is
                  not modified in any way.

            radius_pixel_map: A numpy array with radius information.

                * The array must have the same shape as the data frame on which the
                  algorithm will be applied.

                * Each element of the array must store, for the corresponding pixel in
                  the data frame, the distance in pixels from the origin
                  of the detector reference system (usually the center of the
                  detector).

            radius_step: The width (in pixels) of each step of the radial average.
        """
        if parameters is not None:
            bad_pixel_map_fname = param_utils.get_parameter_from_parameter_group(
                group=parameters, parameter="bad_pixel_map_filename", parameter_type=str
            )
            if bad_pixel_map_fname is not None:
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

            if bad_pixel_map_fname is not None:
                try:
                    map_hdf5_file_handle: Any
                    with h5py.File(bad_pixel_map_fname, "r") as map_hdf5_file_handle:
                        bad_pixel_map = map_hdf5_file_handle[bad_pixel_map_hdf5_path][:]
                except (IOError, OSError, KeyError) as exc:
                    exc_type, exc_value = sys.exc_info()[:2]
                    # TODO: Fix type check
                    raise RuntimeError(
                        "The following error occurred while reading the {0} field from"
                        "the {1} bad pixel map HDF5 file:"
                        "{2}: {3}".format(
                            bad_pixel_map_fname,
                            bad_pixel_map_hdf5_path,
                            exc_type.__name__,  # type: ignore
                            exc_value,
                        )
                    ) from exc
            else:
                bad_pixel_map = None

            radius_step = param_utils.get_parameter_from_parameter_group(
                group=parameters,
                parameter="radius_step",
                parameter_type=float,
            )
        else:
            print(
                "OM Warning: Initializing the RadialProfile algorithm with "
                "individual parameters (radius_pixel_map, bad_pixel_map, radius_step) "
                "is deprecated and will be removed in a future version of OM. Please "
                "use the new parameter group-based initialization interface (which "
                "requires only the parameters and radius_pixel_map arguments)."
            )

        if radius_step is None:
            raise RuntimeError(
                "OM ERROR: Some parameters required for the initialization of the "
                "RadialProfile algorithm have not been defined. Please check the "
                "command used to initialize the algorithm."
            )

        # Calculate radial bins
        num_bins: int = int(radius_pixel_map.max() / radius_step)
        radial_bins: numpy.ndarray = numpy.linspace(
            0, num_bins * radius_step, num_bins + 1
        )

        # Create an array that labels each pixel according to the bin to which it
        # belongs.
        self._radial_bin_labels: numpy.ndarray = (
            numpy.searchsorted(radial_bins, radius_pixel_map, "right") - 1
        )
        self._mask: Union[numpy.ndarray, bool]
        if bad_pixel_map is None:
            self._mask = True
        else:
            self._mask = bad_pixel_map.astype(bool)

    def calculate_profile(self, data: numpy.ndarray) -> numpy.ndarray:
        """
        Calculate the radial profile of a detector data frame.

        This function calculates the radial profile based of the detector data frame
        provided as input to the function.

        Arguments:

            data: the detector data frame from which the radial profile will be
                calculated.

        Returns:

            The radial profile calculated from the input data frame.
        """

        radius_sum: numpy.ndarray = numpy.bincount(
            self._radial_bin_labels[self._mask].ravel(), data[self._mask].ravel()
        )
        radius_count: numpy.ndarray = numpy.bincount(
            self._radial_bin_labels[self._mask].ravel()
        )
        with numpy.errstate(divide="ignore", invalid="ignore"):
            # numpy.errstate allows to ignore the divide by zero warning
            radial_average = numpy.nan_to_num(radius_sum / radius_count)

        return radial_average


class DataAccumulation:
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        num_events_to_accumulate: Union[int, None],
        parameters: Union[Dict[str, Any], None] = None,
    ) -> None:
        """
        Data accumulation and bulk retrieval.

        This algorithm accumulates a predefined number of data entries (each data entry
        must have the format of a dictionary). When the right number of entries has
        been added to the accumulator, the collected data is returned to the user in
        bulk, and the accumulator resets.

        Arguments:

            num_events_to_accumulate (int): the number of data entries that can be
                added to the accumulator before the collected data is returned.
        """
        if parameters is not None:
            num_events_to_accumulate = param_utils.get_parameter_from_parameter_group(
                group=parameters,
                parameter="num_events_to_accumulate",
                parameter_type=int,
            )
        else:
            print(
                "OM Warning: Initializing the DataAccumulation algorithm with "
                "individual parameters (num_events_to_accumulate) is deprecated and "
                "will be removed in a future version of OM. Please use the new "
                "parameter group-based initialization interface (which requires only "
                "the parameters argument)."
            )

        if num_events_to_accumulate is None:
            raise RuntimeError(
                "OM ERROR: Some parameters required for the initialization of the "
                "DataAccumulation algorithm have not been defined. Please check the "
                "command used to initialize the algorithm."
            )

        self._num_events_to_accumulate: int = num_events_to_accumulate
        self._accumulator: List[Dict[str, Any]] = []
        self._num_events_in_accumulator: int = 0

    def add_data(self, data: Dict[str, Any]) -> Union[List[Dict[str, Any]], None]:
        """
        Adds data to the accumulator.

        If the accumulator, after adding the data, reaches the predefined number of
        entries, this function additionally resets the accumulator and returns the
        collected data.

        Arguments:

            data: A data entry to be added to the accumulator.

        Returns:

            Either a list containing the accumulated data (if the accumulator is
            reset), or None, if more data entries can still be added to the
            accumulator.
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
    See documentation of the '__init__' function.
    """

    def __init__(  # noqa: C901
        self,
        *,
        parameters: Union[Dict[str, Any], None] = None,
    ) -> None:
        """
        Algorithm for binning of the detector image.

        This algorithm stores all the parameters needed to bin the detector data frame.
        It also calculates binned detector image, binned bad pixel mask and binned
        pixel maps upon request.

        Arguments:

            detector_type: The type of detector on which binning will be applied.
                For the detector types which are currently supported see the
                documentation of :func:`~[om.algorithms.crystallography.get_peakfinder8_info` function)

            bin_size: The bin size in pixels.

            bad_pixel_map: An array storing a bad pixel map. The map can be used to
                mark areas of the data frame that must be excluded from the calculation
                of the binned image. If the value of this argument is None, no area will
                be excluded from the calculation. Defaults to None.

                * The map must be a numpy array of the same shape as the data frame on
                  which the algorithm will be applied.

                * Each pixel in the map must have a value of either 0, meaning that
                  the corresponding pixel in the data frame should be ignored, or 1,
                  meaning that the corresponding pixel should be included in the
                  calculation.

            min_good_pix_count: The minimum number of good pixels (pixels where 
                'bad_pixel_map' value is 1) in the bin required for the binned pixel to
                be considered good. Defaults to 'bin_size' squared.

            bad_pixel_value: The value written in the pixels of the binned detector
                image which are considered bad. A binned pixel is considered bad if the
                number of good pixels in the original bin is lower than
                'min_good_pix_count'. Defaults to MAXINT if the input array type is
                integer, otherwise defaults to numpy.nan.
        """
        if parameters is not None:        
            self._layout_info: cryst_algs.TypePeakfinder8Info = cryst_algs.get_peakfinder8_info(
                detector_type=param_utils.get_parameter_from_parameter_group(
                    group=parameters,
                    parameter="detector_type",
                    parameter_type=str,
                    required=True,
                )
            )
            self._bin_size: int = param_utils.get_parameter_from_parameter_group(
                group=parameters,
                parameter="bin_size",
                parameter_type=int,
                required=True,
            )
            bad_pixel_map_fname: str = param_utils.get_parameter_from_parameter_group(
                group=parameters,
                parameter="bad_pixel_map_filename",
                parameter_type=str,
            )
            if bad_pixel_map_fname is not None:
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

            if bad_pixel_map_fname is not None:
                try:
                    map_hdf5_file_handle: Any
                    with h5py.File(bad_pixel_map_fname, "r") as map_hdf5_file_handle:
                        bad_pixel_map = map_hdf5_file_handle[bad_pixel_map_hdf5_path][:]
                except (IOError, OSError, KeyError) as exc:
                    exc_type, exc_value = sys.exc_info()[:2]
                    # TODO: Fix type check
                    raise RuntimeError(
                        "The following error occurred while reading the {0} field from"
                        "the {1} bad pixel map HDF5 file:"
                        "{2}: {3}".format(
                            bad_pixel_map_fname,
                            bad_pixel_map_hdf5_path,
                            exc_type.__name__,  # type: ignore
                            exc_value,
                        )
                    ) from exc
            else:
                bad_pixel_map = None

            min_good_pix_count: Union[
                int, None
            ] = param_utils.get_parameter_from_parameter_group(
                group=parameters,
                parameter="min_good_pix_count",
                parameter_type=int,
            )
            self._bad_pixel_value: Union[
                int,float,None
            ] = param_utils.get_parameter_from_parameter_group(
                group=parameters,
                parameter="bad_pixel_value",
                parameter_type=int,
            )
        else:
            raise RuntimeError(
                "OM ERROR: Some parameters required for the initialization of the "
                "Binning algorithm have not been defined. Please check the command "
                "used to initialize the algorithm."
            )

        self._original_asic_nx: int = self._layout_info["asic_ny"]
        self._original_asic_ny: int = self._layout_info["asic_nx"]
        self._original_nx: int = self._layout_info["asic_ny"] * self._layout_info["nasics_y"]
        self._original_ny: int = self._layout_info["asic_nx"] * self._layout_info["nasics_x"]

        self._extended_asic_nx: int = int(numpy.ceil(self._original_asic_nx / self._bin_size)) * self._bin_size
        self._extended_asic_ny: int = int(numpy.ceil(self._original_asic_ny / self._bin_size)) * self._bin_size
        self._extended_nx: int = self._extended_asic_nx * self._layout_info["nasics_y"]
        self._extended_ny: int = self._extended_asic_ny * self._layout_info["nasics_x"]
    
        self._binned_asic_nx: int = self._extended_asic_nx // self._bin_size
        self._binned_asic_ny: int = self._extended_asic_ny // self._bin_size
        self._binned_nx: int = self._extended_nx // self._bin_size
        self._binned_ny: int = self._extended_ny // self._bin_size

        if bad_pixel_map is None:
            self._mask: numpy.ndarray = numpy.ones((self._original_nx, self._original_ny), dtype=numpy.int)
        else:
            self._mask: numpy.ndarray = bad_pixel_map

        # Binned mask = num good pixels per bin
        self._binned_mask: numpy.ndarray = self._bin_data_array(self._mask)

        if min_good_pix_count is None:
            self._min_good_pix_count: int = self._bin_size ** 2
        else:
            self._min_good_pix_count: int = min_good_pix_count

    def _extend_data_array(self, data: numpy.ndarray) -> numpy.ndarray:
        # Extends original data array with zeros making asic size divisible by bin_size
        # Returns new array of the size (self._extended_nx, self._extended_ny)
        extended_data: numpy.ndarray = numpy.zeros((self._extended_nx, self._extended_ny))
        i: int
        j: int
        for i in range(self._layout_info["nasics_x"]):
            for j in range(self._layout_info["nasics_y"]):
                extended_data[
                    i * self._extended_asic_nx : i * self._extended_asic_nx + self._original_asic_nx,
                    j * self._extended_asic_ny : j * self._extended_asic_ny + self._original_asic_ny
                ] = data[
                    i * self._original_asic_nx : (i + 1) * self._original_asic_nx,
                    j * self._original_asic_ny : (j + 1) * self._original_asic_ny
                ]
        return extended_data

    def _bin_data_array(self, data: numpy.ndarray) -> numpy.ndarray:
        # Gets extended data array with the asics dimensions divisible by bin size and
        # sums pixel values in the bins. Returns binned data array.
        extended_data: numpy.ndarray = self._extend_data_array(data)
        binned_data: numpy.ndarray = extended_data.reshape(
            self._binned_nx, 
            self._bin_size,
            self._binned_ny, 
            self._bin_size
        ).sum(3).sum(1)
        return binned_data

    def get_binned_layout_info(self) -> cryst_algs.TypePeakfinder8Info:
        """
        Gets binned detector layout information.

        This function returns detector layout information of the image after binning.

        Returns:

            A [TypePeakfinder8Info][om.algorithms.crystallography.TypePeakfinder8Info]
            dictionary storing the binned data layout information.
        """
        return {
            "asic_nx": self._binned_asic_ny,
            "asic_ny": self._binned_asic_nx,
            "nasics_x": self._layout_info["nasics_x"],
            "nasics_y": self._layout_info["nasics_y"],
        }

    def get_binned_data_shape(self) -> Tuple[int, int]:
        """
        Gets binned data shape.

        This function returns the dimensions of the detector data frame in pixels after
        binning.

        Returns:

            A tuple containing the binned data array shape.
        """
        return self._extended_nx // self._bin_size, self._extended_ny // self._bin_size

    def apply_binning(self, data: numpy.ndarray) -> numpy.ndarray:
        """
        Applies binning to the detector data frame.

        This function calculates binned detector image. First, it calculates the
        average values of good pixels in each bin. Then it multiplies them by the total
        number of pixels in the bin (i.e. 'bin_size' squared). Lastly, it sets the
        values of the bins with fewer than 'min_good_pix_count' good pixels to
        'bad_pixel_value'.

        Arguments:

            data: The detector data frame on which the binning must be performed.

        Returns:

            The binned data.
        """

        # Set bad pixels to zero:
        data = data * self._mask
        # Bin data and scale to the number of good pixels per bin:
        with numpy.errstate(divide="ignore", invalid="ignore"):
            binned_data = self._bin_data_array(data) / self._binned_mask * self._bin_size ** 2

        data_type: numpy.dtype = data.dtype
        if numpy.issubdtype(data_type, numpy.integer):
            if self._bad_pixel_value is None:
                self._bad_pixel_value = numpy.iinfo(data_type).max
            binned_data[numpy.where(binned_data > self._bad_pixel_value)] = self._bad_pixel_value
        elif self._bad_pixel_value is None:
            self._bad_pixel_value = numpy.nan

        binned_data[numpy.where(self._binned_mask < self._min_good_pix_count)] = self._bad_pixel_value

        return binned_data

    def bin_bad_pixel_mask(self, mask: Union[numpy.ndarray, None]):
        """
        Applies binning to the bad pixel mask.

        This function calculates the bad pixel mask applicable to the binned data from
        the bad pixel mask of the original data shape. It returns a numpy array with
        the same dimensions as the binned data. The values of the bins containing only
        good pixels (pixels where mask value is 1) are set to 1, the values of all
        the other bins, i.e. bins with at least one bad pixel, are set to 0.

        Arguments:

            mask: An array storing a bad pixel map.                

                * The map must be a numpy array of the same shape as the data frame on
                  which the binning algorithm is applied.

                * Each pixel in the map must have a value of either 0, meaning that
                  the corresponding pixel in the data frame should be considered bad,
                  or 1, meaning that the corresponding pixel should be considered good.

        Returns:

            Either a numpy array containing the binned mask (if 'mask' is not None) or
            None.
        """
        if mask is None:
            return None
        else:
            return self._bin_data_array(mask) // self._bin_size**2

    def bin_pixel_maps(self, pixel_maps: TypePixelMaps):
        """
        Applies binning to the pixel maps.

        This function calculates pixel maps applicable to the binned detector image.

        Arguments:

            pixel_maps: A [TypePixelMaps][om.utils.crystfel_geometry.TypePixelMaps] 
            dictionary storing the pixel maps.

        Returns:

            A [TypePixelMaps][om.utils.crystfel_geometry.TypePixelMaps] 
            dictionary storing binned pixel maps.
        """

        binned_pixel_maps: TypePixelMaps = {}
        key: str
        for key in "x", "y", "z", "radius":
            binned_pixel_maps[key] = self._bin_data_array(
                pixel_maps[key]
            ) / self._bin_size**3
        binned_pixel_maps["phi"] = self._bin_data_array(
            pixel_maps["phi"]
        ) / self._bin_size**2

        return binned_pixel_maps

    def get_bin_size(self) -> int:
        """
        Gets the bin size.

        Returns:

            The bin size in pixels.
        """
        return self._bin_size