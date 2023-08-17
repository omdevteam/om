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

This module contains classes and functions that allow OM to write data to files in HDF5
format.
"""
import sys
from typing import Any, Dict, Union

import h5py  # type: ignore
import numpy
from numpy.typing import NDArray

from om.lib.exceptions import OmHdf5FileReadingError
from om.lib.parameters import get_parameter_from_parameter_group


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

        The loaded data array.

    Raises:

        OmHdf5FileReadingError: Raised when an error is encountered while reading the
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


def parse_parameters_and_load_hdf5_data(
    *,
    parameters: Dict[str, Any],
    hdf5_filename_parameter: str,
    hdf5_path_parameter: str,
) -> Union[NDArray[numpy.int_], NDArray[numpy.float_], None]:
    """
    Reads data from an HDF5 file identified by a set of configuration parameters.

    This function retrieves the path to a data file, and the internal HDF5 path to a
    block storing data, from a set of configuration parameters, then loads the data.


    Arguments:

        parameters: A set of OM configuration parameters collected together in a
            parameter group. The parameter group must contain the following
            entries:

            * An entry, whose name is specified by the `hdf5_filename_parameter`
              argument of this function, storing the relative of absolute path to an
              HDF5 file containing the data to load.

            * An entry, whose name is specified by the `hdf5_path_parameter` argument
              argument of this function, storing the internal path, within the HDF5
              file, to the block storing the data to load.

        hdf5_filename_parameter: The name of the entry in the parameter set that
            stores the path to the data file.

        hdf5_path_parameter: The name of the entry in the parameter set that stores
            the internal HDF5 path to the block storing the data.

    Returns:

        The loaded data.
    """
    # Bad pixel map
    hdf5_filename: Union[str, None] = get_parameter_from_parameter_group(
        group=parameters,
        parameter=hdf5_filename_parameter,
        parameter_type=str,
    )
    if hdf5_filename is not None:
        hdf5_path: Union[str, None] = get_parameter_from_parameter_group(
            group=parameters,
            parameter=hdf5_path_parameter,
            parameter_type=str,
            required=True,
        )

        if hdf5_path is not None:
            return load_hdf5_data(hdf5_filename=hdf5_filename, hdf5_path=hdf5_path)
        else:
            return None
    else:
        return None
