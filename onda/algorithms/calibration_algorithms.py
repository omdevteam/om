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

This module contains algorithms that apply corrections for artifacts caused by detector
design or operation (i.e., not sample- or experiment-related).
"""
from __future__ import absolute_import, division, print_function

import numpy

from onda.utils import exceptions, named_tuples, hdf5  # pylint: disable=unused-import


class Agipd1MCalibration(object):
    """
    See documentation of the '__init__' function.
    """

    def __init__(self, calibration_filename):
        # type: (str) -> None
        """
        Calibration of the AGIPD 1M detector.

        This algorithm stores the calibration parameters for an AGIPD 1M detector and
        applies the calibration to a detector data frame upon request.

        Arguments:

            calibration_filename (str): the absolute or relative path to an HDF5 file
                with the calibration parameters. The HDF5 file must have the
                following internal structure:

                * /AnalogOffset
                * /DigitalGainLevel
                * /RelativeGain

                TODO: describe file structure.
        """
        self._offset = hdf5.load_hdf5_data(
            hdf5_filename=calibration_filename, hdf5_path="/AnalogOffset"
        )
        self._digital_gain = hdf5.load_hdf5_data(
            hdf5_filename=calibration_filename, hdf5_path="/DigitalGainLevel"
        )
        self._relative_gain = hdf5.load_hdf5_data(
            hdf5_filename=calibration_filename, hdf5_path="/RelativeGain"
        )

    def apply_calibration(self, data_and_calib_info):
        # type: (named_tuples.DataAndCalibrationInfo) -> numpy.ndarray
        """
        Applies the calibration to a detector data frame.

        This function determines the gain stage of each pixel in the data frame, and
        applies the relevant gain and offset corrections.

        Arguments:

            data (:class:`~onda.utils.named_tuples.DataAndCalibrationInfo`): a named
                tuple containing the data frame to calibrate, and some additional
                necessary information. In detail:

                * The 'data' field of the named tuple must contain the detector data
                  frame to calibrate.

                * The 'info' field must be a dictionary containing two keys:

                  - A key called 'gain' whose value is a numpy array of the same shape
                    as the data frame to calibrate. Each pixel in this array must
                    contain the information needed to determine the gain stage of the
                    corresponding pixel in the data frame.

                  - A key  called 'num_frame', whose value is the index, within an
                    event, of the detector frame to calibrate.

        Returns:

            numpy.ndarray:  the corrected data frame.
        """
        gain_state = numpy.zeros_like(data_and_calib_info.data, dtype=int)
        gain = data_and_calib_info.info["gain"]
        num_frame = data_and_calib_info.info["num_frame"]
        gain_state[
            numpy.where(gain > numpy.squeeze(self._digital_gain[1, num_frame, ...]))
        ] = 1
        gain_state[
            numpy.where(gain > numpy.squeeze(self._digital_gain[2, num_frame, ...]))
        ] = 2

        return (
            data_and_calib_info.data
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
