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
# Copyright 2020 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Algorithms for detector calibration.

This module contains algorithms that apply corrections for artifacts caused by detector
design or operation (i.e., not sample- or experiment-related).
"""
from __future__ import absolute_import, division, print_function

from typing import Any, Dict, Tuple

import h5py  # type: ignore
import numpy  # type: ignore


class Agipd1MCalibration(object):
    """
    See documentation of the '__init__' function.
    """

    def __init__(self, calibration_filename, cellid_list):
        # type: (str, Tuple[int]) -> None
        """
        Calibration of the AGIPD 1M detector.

        This class stores the calibration parameters for an AGIPD 1M detector and
        applies the calibration to a detector data frame upon request. Since the the
        full set of correction parameters for the AGIPD 1M detector takes up a lot of
        memory, only the parameters needed to correct frames originating from a subset
        of cells are loaded and stored. The subset of cells is chosen when the class is
        instantiated, via the *cellid_list* parameter. It will then be possible to
        apply the correction only on detector frames originating from the chosen set of
        cells.

        Arguments:

            calibration_filename (str): the absolute or relative path to an HDF5 file
                with the calibration parameters. The following data blocks should be
                present in the file:

                - */AnalogOffset*: a data block storing the offset coefficients for all
                  pixels, cells and gain stages.

                - */DigitalGainLevel*: a data block storing the information needed to
                  determine the gain state of each pixel and cell.

                - */RelativeGain*: a data block storing the gain coefficients for all
                  pixels, cells and gain stages.

                - */DetectorMask*: a data block storing a mask that should be applied to
                  each data frame. The pixels in the mask must have a value of either
                  0, meaning that the corresponding pixel in the data frame should be
                  set to 0, or 1, meaning that the value of the corresponding pixel
                  must be left alone.

                The */AnalogOffset*, */DigitalGainLevel*, */RelativeGain* data blocks
                must have an internal structure organized according to the following
                axis layout:

                - *axis 0*: the three gain stages

                - *axis 1*: the cell number

                - *axis 2*: the ss coordinate of the 16 detector modules, seen as one
                  big surface, stacked from module 0 to 15 along the longest edge,
                  with the shortest edges touching.

                - *axis 3*: the fs coordinate of the 16 detector modules, seen as one
                  big surface, stacked from module 0 to 15 along the longest edge
                  with the shortest edges touching.

            cellid_list (Tuple[int]): the list of cells for which the correction
                parameters should be loaded and stored.
        """
        self._offset = numpy.ndarray(
            (3, len(cellid_list), 8192, 128), dtype=numpy.int16
        )  # type: numpy.ndarray
        self._digital_gain = numpy.ndarray(
            (3, len(cellid_list), 8192, 128), dtype=numpy.int16
        )  # type: numpy.ndarray
        self._relative_gain = numpy.ndarray(
            (3, len(cellid_list), 8192, 128), dtype=numpy.float32
        )  # type: numpy.ndarray

        with h5py.File(calibration_filename) as hdf5_fh:
            for index, cell in enumerate(cellid_list):
                self._offset[:, index, ...] = numpy.squeeze(
                    hdf5_fh["/AnalogOffset"][:, cell : cell + 1, ...]
                ).reshape(3, 8192, 128)
                self._digital_gain[:, index, ...] = numpy.squeeze(
                    hdf5_fh["/DigitalGainLevel"][:, cell : cell + 1, ...]
                ).reshape(3, 8192, 128)
                self._relative_gain[:, index, ...] = numpy.squeeze(
                    hdf5_fh["/RelativeGain"][:, cell : cell + 1, ...]
                ).reshape(3, 8192, 128)
            self._detector_mask = hdf5_fh["/DetectorMask"][:].reshape(16, 512, 128)
        self._cellid_list = cellid_list

    def apply_calibration(self, data_and_calibration_info):
        # type: (Dict[str, Any]) -> numpy.ndarray
        """
        Applies the calibration to a detector data frame.

        This function determines the gain stage of each pixel in the data frame, and
        applies the relevant gain and offset corrections.

        Arguments:

            data_and_calibration_info (Dict[str, Any]: a dictionary containing the data
                frame to calibrate, and some additional necessary information. The
                dictionary should contain the following entries:

                * An entry with key 'data', whose value is the detector data frame to
                  calibrate.

                * An entry with key 'info', whose value is a nested dictionary with the
                  following keys:

                  - A key called 'gain' whose value is a numpy array of the same shape
                    as the data frame to calibrate. Each pixel in this array must
                    contain the information needed to determine the gain stage of the
                    corresponding pixel in the data frame.

                  - A key called 'cell', whose value is the cell number from which the
                    frame to calibrate originates.

        Returns:

            numpy.ndarray:  the corrected data frame.
        """
        gain_state = numpy.zeros_like(
            data_and_calibration_info["data"], dtype=int
        )  # type: numpy.ndarray
        gain = data_and_calibration_info["info"]["gain"]  # type: numpy.ndarray
        try:
            num_frame = self._cellid_list.index(
                data_and_calibration_info["info"]["cell"]
            )  # type: int
        except ValueError:
            raise RuntimeError(
                "Cannot find calibration parameters for cell {0}".format(
                    data_and_calibration_info["info"]["cell"]
                )
            )

        gain_state[
            numpy.where(gain > numpy.squeeze(self._digital_gain[1, num_frame, ...]))
        ] = 1
        gain_state[
            numpy.where(gain > numpy.squeeze(self._digital_gain[2, num_frame, ...]))
        ] = 2
        gain_offset_correction = (
            (
                data_and_calibration_info["data"]
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
        ).reshape(
            16, 512, 128
        )  # type: numpy.ndarray
        masked_image = (
            gain_offset_correction * self._detector_mask
        )  # type: numpy.ndarray
        median_mask = numpy.median(masked_image, axis=(1, 2))  # type: numpy.ndarray

        return (
            (gain_offset_correction[:, :, :] - median_mask[:, None, None]).reshape(
                8192, 128
            ),
        )
