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
#
#    Copyright 2014-2018 Deutsches Elektronen-Synchrotron DESY,
#    a research centre of the Helmholtz Association.
"""
Algorithms for detector calibration.

Algorithms for all the corrections and ajustments that need to be
applied to detector data due to detector design and electronic noise.
"""
from __future__ import absolute_import, division, print_function

import h5py
from future.utils import raise_from

#######################
# LAMBDA CALIBRATION  #
#######################


class SingleModuleLambdaCalibration(object):
    """
    Algorithm for the calbration of a single module Lambda detector.

    Applies flatfield correction to a single lambda module.
    """

    def __init__(self, calibration_filename):
        """
        Initalizes the SingleModuleLambdaCalibration class.

        Args:

            calibration_filename (str): name of an HDF5 file with the
                calibration data. The file must contain the flatfield
                data for the module at the "/flatfield" hdf5 path.
        """

        try:
            with h5py.File(name=calibration_filename, mode="r") as fhandle:
                self._flatfield = fhandle["/flatfield"]
        except OSError:
            raise_from(
                RuntimeError(
                    "Error reading the {} HDF5 file.".format(
                        calibration_filename
                    )
                ),
                None,
            )

    def apply_calibration(self, data):
        """
        Applies the calibration.

        Multiplies the detector data by a flatfield.

        Args:

            data (ndarray): the module data on which to apply the
            calibration.

        Returns:

            ndarray:  the corrected data.
        """
        return data * self._flatfield
