# This file is part of OnDA.
#
# OnDA is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# OnDA is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with OnDA.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Utility functions for HDF5 files.

This module contains utility functions that manipulate HDF5 files (load whole or
partial data blocks, write to normal or VDS files, etc.).
"""
from __future__ import absolute_import, division, print_function

import sys
from typing import Any  # pylint: disable=unused-import

import h5py
from future.utils import raise_from

from onda.utils import exceptions


def load_hdf5_data(hdf5_filename, hdf5_path, selection=None):
    # type: (str, str, Opional[Tuple[slice]]) -> Any
    """
    Loads a data block from an HDF5 file.

    This function loads into memory the content of a data block located in an HDF5
    file. If the selection argument is provided, it defines the portion of the data
    block that will be read from the file, otherwise the whole block will be read.

    Arguments:

        hdf_filename (str): the relative or absolute path to an HDF5 file containing
            the data to load.

        hdf5_path (str): the internal HDF5 path to the data block to load.

        selection (Tuple[slice]): the portion of content of the data block to load,
            expressed as a list of slices along the axes of the block. If this
            argument is None, the whole content of the data block will be loaded.
            Defaults to None.

    Returns:

        Any: the data loaded from the HDF5 file.

    Raises:

        :class:`~onda.utils.exceptions.OndaHdf5FileReadingError`: if any error occurs
            while reading the data from the file.
    """
    try:
        with h5py.File(name=hdf5_filename, mode="r") as fhandle:
            if selection is None:
                data = fhandle[hdf5_path][:]
            else:
                # TODO: Add boundary checks.
                data = fhandle[hdf5_path][selection]
            return data
    except (IOError, OSError, KeyError) as exc:
        exc_type, exc_value = sys.exc_info()[:2]
        raise_from(
            exc=exceptions.OndaHdf5FileReadingError(
                "The following error occurred while reading the {0} HDF5 "
                "file: {1}: {2}".format(hdf5_filename, exc_type.__name__, exc_value)
            ),
            cause=exc,
        )
