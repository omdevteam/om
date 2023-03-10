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
Generic utilities for data retrieval.

This module contains utility classes and functions used by several Data Retrieval
Layer modules.
"""
from typing import Any, BinaryIO, Dict, List, Tuple

import h5py  # type: ignore
import numpy
from numpy.typing import NDArray

from om.lib.exceptions import OmMissingDataSourceClassError
from om.protocols.data_retrieval_layer import OmDataSourceBase


class Jungfrau1MCalibration:
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
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

            photon_energy_kev: the photon energy at which the detector will be
                operated.
        """
        num_panels: int = len(dark_filenames)
        self._dark: NDArray[numpy.float_] = numpy.ndarray(
            (3, 512 * num_panels, 1024), dtype=numpy.float32
        )
        self._gain: NDArray[numpy.float_] = numpy.ndarray(
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

        self._photon_energy_kev: float = photon_energy_kev

    def apply_calibration(self, *, data: NDArray[numpy.int_]) -> NDArray[numpy.float_]:

        """
        Applies the calibration to a detector data frame.

        This function determines the gain stage of each pixel in the provided data
        frame, and applies the relevant gain and offset corrections.

        Arguments:

            data: The detector data frame to calibrate.

        Returns:

            The corrected data frame.
        """
        calibrated_data: NDArray[numpy.float_] = data.astype(numpy.float32)

        where_gain: List[Tuple[NDArray[numpy.int_], ...]] = [
            numpy.where(data & 2**14 == 0),
            numpy.where((data & (2**14) > 0) & (data & 2**15 == 0)),
            numpy.where(data & 2**15 > 0),
        ]

        gain: int
        for gain in range(3):
            calibrated_data[where_gain[gain]] -= self._dark[gain][where_gain[gain]]
            calibrated_data[where_gain[gain]] /= (
                self._gain[gain][where_gain[gain]] * self._photon_energy_kev
            )

        return calibrated_data


def filter_data_sources(
    *,
    data_sources: Dict[str, OmDataSourceBase],
    required_data: List[str],
) -> List[str]:
    """
    Selects only the required Data Sources.

    This function filters the list of all Data Sources associated with a
    Data Retrieval class, returning only the subset of Data Sources needed to retrieve
    the data requested by the user.

    Arguments:

        data_sources: A list containing the names of all
            Data Sources available for a Data Retrieval class.

        required_data: A list containing the names of the data items requested by the
            user.

    Returns:

        A list of Data Source names containing only the required Data Sources.
    """
    required_data_sources: List[str] = []
    entry: str
    for entry in required_data:
        if entry == "timestamp":
            continue
        if entry in data_sources:
            required_data_sources.append(entry)
        else:
            raise OmMissingDataSourceClassError(f"Data source {entry} is not defined")
    return required_data_sources
