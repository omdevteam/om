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
# Copyright 2020 -2021 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Algorithms for detector calibration.

This module contains algorithms that can be used to calibrate raw detector data. Each
algorithm deals with a specific detector.
"""
from typing import Any, BinaryIO, List

import h5py  # type: ignore
import numpy  # type: ignore


class Jungfrau1MCalibration:
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        dark_filenames: List[str],
        gain_filenames: List[str],
        photon_energy_kev: float,
    ) -> None:
        """
        Calibration of the Jungfrau 1M detector.

        This algorithm stores the calibration parameters for a Jungfrau 1M detector
        and applies them to a raw detector data frame upon request.

        Arguments:

            dark_filenames: A list of relative or absolute paths to files containing
                dark data for the calibration of the detector.

            gain_filenames: A list of relative or absolute paths to files containing
                gain data for the calibration of the detector.

            photon_energy_kev: the photon energy at which the detector will be operated.
        """
        # 2 for Jungfrau 1M
        num_panels: int = len(dark_filenames)

        self._dark: numpy.ndarray = numpy.ndarray(
            (3, 512 * num_panels, 1024), dtype=numpy.float32
        )
        self._gain: numpy.ndarray = numpy.ndarray(
            (3, 512 * num_panels, 1024), dtype=numpy.float64
        )
        panel_id: int
        for panel_id in range(num_panels):
            gain_file: BinaryIO = open(gain_filenames[panel_id], "rb")
            dark_file: Any = h5py.File(dark_filenames[panel_id], "r")
            gain: int
            for gain in range(3):
                self._dark[gain, 512 * panel_id : 512 * (panel_id + 1), :] = dark_file[
                    "gain%d" % gain
                ][:]
                self._gain[
                    gain, 512 * panel_id : 512 * (panel_id + 1), :
                ] = numpy.fromfile(
                    gain_file, dtype=numpy.float64, count=1024 * 512
                ).reshape(
                    (512, 1024)
                )
            gain_file.close()
            dark_file.close()

        # TODO: Energy should be in eV
        self._photon_energy_kev: float = photon_energy_kev

    def apply_calibration(self, data: numpy.ndarray) -> numpy.ndarray:
        """
        Applies the calibration to a detector data frame.

        This function determines the gain stage of each pixel in the provided data
        frame, and applies the relevant gain and offset corrections.

        Arguments:

            data: The detector data frame to calibrate.

        Returns:

            The corrected data frame.
        """
        corrected_data: numpy.ndarray = data.astype(numpy.float32)

        where_gain: List[numpy.ndarray] = [
            numpy.where(data & 2 ** 14 == 0),
            numpy.where((data & (2 ** 14) > 0) & (data & 2 ** 15 == 0)),
            numpy.where(data & 2 ** 15 > 0),
        ]

        gain: int
        for gain in range(3):
            corrected_data[where_gain[gain]] -= self._dark[gain][where_gain[gain]]
            corrected_data[where_gain[gain]] /= (
                self._gain[gain][where_gain[gain]] * self._photon_energy_kev
            )

        return corrected_data
