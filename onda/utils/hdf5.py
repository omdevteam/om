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
Utility functions to manipulate HDF5 files.
"""
from __future__ import absolute_import, division, print_function

import sys
from typing import Any  # pylint: disable=unused-import

import h5py
from future.utils import raise_from

from onda.utils import exceptions


def load_hdf5_data(hdf5_filename, hdf5_path):
    # type: (str, str) -> Any
    """
    Loads data from an HDF5 file.

    This function loads into memory the whole content of a data block located in an
    HDF5 file.

    Arguments:

        hdf_filename (str): the relative or absolute path to an HDF5 file containing
            the data to load.

        mask_hdf5_path (str): the internal HDF5 path to the data block that must be
            loaded.

    Returns:

        Any: the data loaded from the HDF5 file.

    Raises:

        :class:`~onda.utils.exceptions.OndaHdf5FileReadingError`: if any error occurs
        while reading the data from the file.
    """
    try:
        with h5py.File(name=hdf5_filename, mode="r") as fhandle:
            data = fhandle[hdf5_path][:]
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
