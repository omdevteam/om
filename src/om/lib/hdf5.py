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
HDF5 writing.

This module contains classes and functions that allow OM to load data from files in
HDF5 format.
"""
import sys
from typing import Any, Dict, Union

import h5py  # type: ignore
import numpy
from numpy.typing import NDArray

from om.lib.exceptions import OmHdf5FileReadingError


def load_hdf5_data(
    *,
    hdf5_filename: str,
    hdf5_path: str,
) -> Union[NDArray[numpy.int_], NDArray[numpy.float_], None]:
    """
    Loads data from an HDF5 file.

    This function loads data from an HDF5 file.

    Arguments:

        hdf5_filename: The relative of absolute path to an HDF5 file containing the
            data to load.

        hdf5_path: The internal path, within the HDF5 file, to the block storing the
            data to load.

    Returns:

        The loaded data.

    Raises:

        OmHdf5FileReadingError: Raised if an error is encountered while reading the
            file.
    """

    try:
        hdf5_file_handle: Any
        with h5py.File(hdf5_filename, "r") as hdf5_file_handle:
            data: Union[NDArray[numpy.float_], NDArray[numpy.int_]] = hdf5_file_handle[
                hdf5_path
            ][:]
    except (IOError, OSError, KeyError) as exc:
        exc_type, exc_value = sys.exc_info()[:2]
        raise OmHdf5FileReadingError(
            "The following error occurred while reading "  # type: ignore
            f"the {hdf5_path} field from the {hdf5_filename} dark "
            f"data HDF5 file: {exc_type.__name__}: {exc_value}"
        ) from exc
    return data
