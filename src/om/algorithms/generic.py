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
masking and correction, data accumulation, etc.).
"""
import sys
from typing import Any, Dict, List, Union

import h5py  # type:ignore
import numpy  # type: ignore

from om.utils import exceptions


class Correction:
    """
    See documentation of the `__init__` function.
    """

    def __init__(  # noqa: C901
        self,
        dark_filename: Union[str, None] = None,
        dark_hdf5_path: Union[str, None] = None,
        mask_filename: Union[str, None] = None,
        mask_hdf5_path: Union[str, None] = None,
        gain_filename: Union[str, None] = None,
        gain_hdf5_path: Union[str, None] = None,
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
                        "The following error occurred while reading the {0} field from "
                        "the {1} gain map HDF5 file: {2}: {3}".format(
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


class DataAccumulator:
    """
    See documentation of the `__init__` function.
    """

    def __init__(self, num_events_to_accumulate: int) -> None:
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
