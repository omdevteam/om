#    This file is part of cfelpyutils.
#
#    cfelpyutils is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    cfelpyutils is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with cfelpyutils.  If not, see <http://www.gnu.org/licenses/>.
"""
Utilities for HDF5 files.

This module contains utilities for the processing of HDF5. This module builds
on what the h5py module already provides.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import h5py
import numpy


def load_nparray_from_hdf5_file(data_filename, data_group):
    """Loads a numpy.ndarray from an HDF5 file.

    Args:

       data_filename (str): filename of the file to read.

       data_group (str): internal HDF5 path of the data block to read.

    Returns:

       nparray (numpy.ndarray): numpy array with the data read from the file.
    """
    try:

        with h5py.File(data_filename, 'r') as hdfile:
            nparray = numpy.array(hdfile[data_group])
            hdfile.close()
    except:
        raise RuntimeError('Error reading file {0} (data block: {1}).'.format(data_filename, data_group))
    else:
        return nparray
