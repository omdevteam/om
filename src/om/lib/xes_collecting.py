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
TODO
"""

from typing import Any, Dict, Tuple, Union

import numpy
from numpy.typing import NDArray

from om.algorithms.xes import XesAnalysis


class XesPlots:
    """
    TODO
    """

    def __init__(self, *, xes_parameters: Dict[str, Any], time_resolved: bool) -> None:
        """
        TODO
        """

        self._time_resolved: bool = time_resolved

        self._spectra_cumulative_sum: Union[
            NDArray[numpy.float_], NDArray[numpy.int_], None
        ] = None
        self._spectra_cumulative_sum_smoothed: Union[NDArray[numpy.float_], None] = None

        self._cumulative_2d: Union[
            NDArray[numpy.float_], NDArray[numpy.int_], None
        ] = None
        self._cumulative_2d_pumped: Union[
            NDArray[numpy.float_], NDArray[numpy.int_], None
        ] = None
        self._cumulative_2d_dark: Union[
            NDArray[numpy.float_], NDArray[numpy.int_], None
        ] = None

        self._num_events_pumped: int = 0
        self._num_events_dark: int = 0
        self._num_events: int = 0

        self._xes_analysis = XesAnalysis(parameters=xes_parameters)

    def update_plots(
        self,
        *,
        detector_data: Union[NDArray[numpy.float_], NDArray[numpy.int_]],
        optical_laser_active: bool,
    ) -> Tuple[
        Union[NDArray[numpy.float_], NDArray[numpy.int_], None],
        Union[NDArray[numpy.float_], None],
        Union[NDArray[numpy.float_], NDArray[numpy.int_], None],
        Union[NDArray[numpy.float_], None],
        Union[NDArray[numpy.float_], None],
        Union[NDArray[numpy.float_], None],
    ]:
        self._num_events += 1

        if self._time_resolved:
            if optical_laser_active:
                self._num_events_pumped += 1
            else:
                self._num_events_dark += 1

        if self._cumulative_2d is None:
            self._cumulative_2d = detector_data
        else:
            self._cumulative_2d += (
                (detector_data - self._cumulative_2d * 1.0) / self._num_events * 1.0
            )

        # Calculate normalized spectrum from cumulative 2D images.
        cumulative_xes: Dict[
            str, NDArray[numpy.float_]
        ] = self._xes_analysis.generate_spectrum(data=self._cumulative_2d)

        self._spectra_cumulative_sum = cumulative_xes["spectrum"]
        self._spectra_cumulative_sum_smoothed = cumulative_xes["spectrum_smoothed"]

        spectra_cumulative_sum_pumped: Union[NDArray[numpy.float_], None] = None
        spectra_cumulative_sum_dark: Union[NDArray[numpy.float_], None] = None
        spectra_cumulative_sum_difference: Union[NDArray[numpy.float_], None] = None

        if numpy.mean(numpy.abs(self._spectra_cumulative_sum)) > 0:
            self._spectra_cumulative_sum /= numpy.mean(
                numpy.abs(self._spectra_cumulative_sum)
            )
        if numpy.mean(numpy.abs(self._spectra_cumulative_sum_smoothed)) > 0:
            self._spectra_cumulative_sum_smoothed /= numpy.mean(
                numpy.abs(self._spectra_cumulative_sum_smoothed)
            )

        if self._time_resolved:
            # Sum the spectra for pumped (optical_laser_active) and dark
            if self._cumulative_2d_pumped is None:
                self._cumulative_2d_pumped = detector_data * 0
            if self._cumulative_2d_dark is None:
                self._cumulative_2d_dark = detector_data * 0

            # Need to calculate a running average
            if optical_laser_active:
                self._cumulative_2d_pumped += (
                    (detector_data - self._cumulative_2d_pumped * 1.0)
                    / self._num_events_pumped
                    * 1.0
                )
            else:
                self._cumulative_2d_dark += (
                    (detector_data - self._cumulative_2d_dark * 1.0)
                    / self._num_events_dark
                    * 1.0
                )

            # Calculate spectrum from cumulative 2D images
            cumulative_xes_pumped: Dict[
                str, NDArray[numpy.float_]
            ] = self._xes_analysis.generate_spectrum(data=self._cumulative_2d_pumped)
            spectra_cumulative_sum_pumped = cumulative_xes_pumped["spectrum"]

            # calculate spectrum from cumulative 2D images
            cumulative_xes_dark: Dict[
                str, NDArray[numpy.float_]
            ] = self._xes_analysis.generate_spectrum(data=self._cumulative_2d_dark)
            spectra_cumulative_sum_dark = cumulative_xes_dark["spectrum"]

            # normalize spectra
            if numpy.mean(numpy.abs(spectra_cumulative_sum_pumped)) > 0:
                spectra_cumulative_sum_pumped /= numpy.mean(
                    numpy.abs(spectra_cumulative_sum_pumped)
                )
            if numpy.mean(numpy.abs(spectra_cumulative_sum_dark)) > 0:
                spectra_cumulative_sum_dark /= numpy.mean(
                    numpy.abs(spectra_cumulative_sum_dark)
                )

            spectra_cumulative_sum_difference = (
                spectra_cumulative_sum_pumped - spectra_cumulative_sum_dark
            )

        return (
            self._spectra_cumulative_sum,
            self._spectra_cumulative_sum_smoothed,
            self._cumulative_2d,
            spectra_cumulative_sum_pumped,
            spectra_cumulative_sum_dark,
            spectra_cumulative_sum_difference,
        )
