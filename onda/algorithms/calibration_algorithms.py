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

    def __init__(self, calibration_filename, cellid_list):
        # type: (str, List[int]) -> None
        """
        Calibration of the AGIPD 1M detector.

        This algorithm stores the calibration parameters for an AGIPD 1M detector and
        applies the calibration to a detector data frame upon request. Since the the
        full set of correction parameters for the AGIPD 1M detector takes up a lot of
        memory, only the parameters needed to correct frames originating from a subset
        of cells care loaded. This algorithm will be able to correct only frames that
        originate from the cells specified in the cellid_list parameter.

        Arguments:

            calibration_filename (str): the absolute or relative path to an HDF5 file
                with the calibration parameters. The HDF5 file must have the
                following internal structure:

                * /AnalogOffset
                * /DigitalGainLevel
                * /RelativeGain

                TODO: describe file structure.

            cellid_list (Tuple[int]): list of cells for which the correction parameters
                should be loaded.
        """
        self._offset = numpy.ndarray(
            (3, len(cellid_list), 8192, 128), dtype=numpy.int16
        )
        self._digital_gain = numpy.ndarray(
            (3, len(cellid_list), 8192, 128), dtype=numpy.int16
        )
        self._relative_gain = numpy.ndarray(
            (3, len(cellid_list), 8192, 128), dtype=numpy.float32
        )

        for index, cell in enumerate(cellid_list):
            self._offset[:, index, ...] = numpy.squeeze(
                hdf5.load_hdf5_data(
                    hdf5_filename=calibration_filename,
                    hdf5_path="/AnalogOffset",
                    selection=(
                        slice(0, 3),
                        slice(cell, cell + 1),
                        slice(0, 16),
                        slice(0, 512),
                        slice(0, 128),
                    ),
                )
            ).reshape(3, 8192, 128)
            self._digital_gain[:, index, ...] = numpy.squeeze(
                hdf5.load_hdf5_data(
                    hdf5_filename=calibration_filename,
                    hdf5_path="/DigitalGainLevel",
                    selection=(
                        slice(0, 3),
                        slice(cell, cell + 1),
                        slice(0, 16),
                        slice(0, 512),
                        slice(0, 128),
                    ),
                )
            ).reshape(3, 8192, 128)
            self._relative_gain[:, index, ...] = numpy.squeeze(
                hdf5.load_hdf5_data(
                    hdf5_filename=calibration_filename,
                    hdf5_path="/RelativeGain",
                    selection=(
                        slice(0, 3),
                        slice(cell, cell + 1),
                        slice(0, 16),
                        slice(0, 512),
                        slice(0, 128),
                    ),
                )
            ).reshape(3, 8192, 128)
            self._detector_mask = hdf5.load_hdf5_data(
                hdf5_filename=calibration_filename, hdf5_path="/DetectorMask"
            ).reshape(16, 512, 128)
        self._cellid_list = cellid_list

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

                  - A key  called 'cell', whose value is the cell, within an event,
                    from which the frame to calibrate originates.

        Returns:

            numpy.ndarray:  the corrected data frame.
        """
        gain_state = numpy.zeros_like(data_and_calib_info.data, dtype=int)
        gain = data_and_calib_info.info["gain"]
        try:
            num_frame = self._cellid_list.index(data_and_calib_info.info["cell"])
        except ValueError:
            raise exceptions.OndaDetectorCalibrationError(
                "Cannot find calibration parameters for cell {0}".format(
                    data_and_calib_info.info["cell"]
                )
            )

        gain_state[
            numpy.where(gain > numpy.squeeze(self._digital_gain[1, num_frame, ...]))
        ] = 1
        gain_state[
            numpy.where(gain > numpy.squeeze(self._digital_gain[2, num_frame, ...]))
        ] = 2

        _value, _count = numpy.unique(gain_state, return_counts=True)
        print("number of pixels in gain 1/0 is {}/{}...".format(_count[1], _count[0]))

        gain_states, gain_pixel_counts = numpy.unique(gain_state)

        gain_offset_correction = (
            (
                data_and_calib_info.data
                - numpy.choose(
                    gain_state,
                    (
                        numpy.squeeze(self._offset[0, num_frame, ...]),
                        numpy.squeeze(self._offset[1, num_frame, ...]),
                        numpy.squeeze(self._offset[2, num_frame, ...]),
                    ),
                )
            )
            * numpy.choose(
                gain_state,
                (
                    numpy.squeeze(self._relative_gain[0, num_frame, ...]),
                    numpy.squeeze(self._relative_gain[1, num_frame, ...]),
                    numpy.squeeze(self._relative_gain[2, num_frame, ...]),
                ),
            )
        ).reshape(16, 512, 128)

        masked_image = gain_offset_correction * self._detector_mask
        median_mask = numpy.median(masked_image, axis=(1, 2))
        return (
            (gain_offset_correction[:, :, :] - median_mask[:, None, None]).reshape(
                8192, 128
            ),
            (gain_states, gain_pixel_counts),
        )
