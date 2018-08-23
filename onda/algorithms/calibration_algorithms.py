#    This file is part of OnDA.
#
#    OnDA is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    OnDA is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with OnDA.  If not, see <http://www.gnu.org/licenses/>.
"""
Algorithms for detector calibration.

This module contains the implementation of algorithms used to preform
detector calibration (i.e.: all the corrections and ajustments that
need to be applied to the detector *before* looking at the data).
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import h5py
from future.utils import raise_from


#######################
# LAMBDA CALIBRATION  #
#######################

class SingleModuleLambdaCalibration(object):
    """
    See __init__ for documentation.
    """

    def __init__(self,
                 calibration_filename):
        """
        Calibrate a single-module Lambda detector.

        Apply a flatfield correction to module data.

        Args:

            calibration_filename (str): name of an HDF5 file with the
                calibration data. The file must contain the flatfield
                data for the module in an entry called '/flatfield'.
        """

        try:
            with h5py.File(
                name=calibration_filename,
                mode='r'
            ) as fhandle:
                self._flatfield = fhandle['/flatfield']
        except OSError:
            raise_from(
                RuntimeError(
                    "Error reading the {} HDF5 file.".format(
                        calibration_filename
                    )
                ),
                cause=None
            )

    def apply_calibration(self,
                          data):
        """
        Apply the calibration.

        Multiply the module data by a flatfield.

        Args:

            data (numpy.ndarray): the module data on which the
                calibration must be applied.

        Returns:

            ndarray:  the corrected data.
        """
        return data * self._flatfield
