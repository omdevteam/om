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
Algorithms for detector calibration.

Algorithms for the corrections and ajustments that need to be applied to detector data
due to detector design and electronic noise.
"""
from __future__ import absolute_import, division, print_function

import h5py
import numpy
from future.utils import raise_from


class SingleModuleLambdaCalibration(object):
    """
    Algorithm for the calbration of a single module Lambda detector.

    Applies flatfield correction to a single lambda module.
    """

    def __init__(self, calibration_filename):
        """
        Initalizes the SingleModuleLambdaCalibration class.

        Args:

            calibration_filename (str): name of an HDF5 file with the calibration
                data. The file must contain the flatfield data for the module at
                the "/flatfield" hdf5 path.
        """

        try:
            with h5py.File(name=calibration_filename, mode="r") as fhandle:
                self._flatfield = fhandle["/flatfield"]
        except OSError:
            raise_from(
                RuntimeError(
                    "Error reading the {} HDF5 file.".format(calibration_filename)
                ),
                None,
            )

    def apply_calibration(self, data):
        """
        Applies the calibration.

        Multiplies the detector data by a flatfield.

        Args:

            data (ndarray): the module data on which to apply the calibration.

        Returns:

            ndarray:  the corrected data.
        """
        return data * self._flatfield


class Agipd1MCalibration(object):
    """
    Algorithm for the calbration of an AGIPD 1M detector.

    Applies precomputed gain and offsets for all three gain stages to all data from
    a pulse train.
    """

    def __init__(self, calibration_filename):
        """
        Initalizes the Agipd1MCalibration class.

        Args:

            calibration_filename (str): name of an HDF5 file with the calibration
                data. The file must have the following structure:
        """
        try:

            with h5py.File(name=calibration_filename, mode="r") as fhandle:
                self._offset = fhandle["/AnalogOffset"][:]
                self._digital_gain = fhandle["/DigitalGainLevel"][:]
                self._relative_gain = fhandle["/RelativeGain"][:]

        except OSError:
            raise_from(
                RuntimeError(
                    "Error reading the {} HDF5 file.".format(calibration_filename)
                ),
                None,
            )

    def apply_calibration(self, data):
        """
        Applies the calibration.

        Determines in which gain stage each pixel is, subtracts the relevant offset,
        then multiplies the value by the relative gain.

        Args:

            data (Tuple[ndarray, Dict]): a named tuple where the first field, named
                "data", stores the pulse train data (in "slab" format) on which to
                apply the calibration, while the second, named "info", is a dictionary
                which contains at least two values. The first one, with key "gain",
                is an array, of the same shape as the data, which stores the gain
                information for the data provided by the detector. The second, with
                key "num_frame' stores the index of the frame being corrected.

        Returns:

            ndarray:  the corrected data.
        """
        gain = data.info["gain"]
        num_frame = data.info["num_frame"]
        gain_state = numpy.zeros_like(data.data, dtype=int)
        gain_state[
            numpy.where(gain > numpy.squeeze(self._digital_gain[1, num_frame, ...]))
        ] = 1
        gain_state[
            numpy.where(gain > numpy.squeeze(self._digital_gain[2, num_frame, ...]))
        ] = 2

        return (
            data.data
            - numpy.choose(
                gain_state,
                (
                    numpy.squeeze(self._offset[0, num_frame, ...]),
                    numpy.squeeze(self._offset[1, num_frame, ...]),
                    numpy.squeeze(self._offset[2, num_frame, ...]),
                ),
            )
        ) * numpy.choose(
            gain_state,
            (
                numpy.squeeze(self._relative_gain[0, num_frame, ...]),
                numpy.squeeze(self._relative_gain[1, num_frame, ...]),
                numpy.squeeze(self._relative_gain[2, num_frame, ...]),
            ),
        )
