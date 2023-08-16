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
# Copyright 2020 -2023 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Algorithms for the processing of x-ray emission spectroscopy data.

This module contains algorithms that perform data processing operations for X-ray
Emission Spectroscopy.
"""

from typing import Any, Dict, Union, cast

import numpy
from numpy.typing import NDArray
from scipy import ndimage  # type: ignore

from om.lib.parameters import get_parameter_from_parameter_group


class EnergySpectrumRetrieval:
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        parameters: Dict[str, Any],
    ) -> None:
        """
        Beam energy spectrum retrieval.

        This algorithm stores all the parameters needed to extract energy spectra from
        camera data frames.

        After the algorithm has been initialized, it can be invoked to calculate an
        energy spectrum from a data frame.

        Warning:

            This algorithm is designed to be applied to camera frames, rather than
            data frames from multi-panel area detectors.

        Arguments:

            parameters: A set of OM configuration parameters collected together in a
                parameter group. The parameter group must contain the following
                entries:

                * `intensity_threshold_in_ADU`: An intensity threshold, in ADU units,
                    for pixels in the camera frame to be considered in the spectrum
                    calculation. Pixel below this threshold are ignored.

                * `rotation_in_degrees`: The rotation, in degrees, that should be
                    applied to the to align the spectrum information with the vertical
                    axis of the camera data frame.

                * `min_row_in_pix_for_integration`: The starting row index for the
                    section of the camera data frame containing the spectrum
                    information (pixels outside this area are ignored).

                * `min_row_in_pix_for_integration`: The ending row index for the
                    section of the camera data frame containing the spectrum
                    information (pixels outside this area are ignored).
        """
        self._intensity_threshold: float = get_parameter_from_parameter_group(
            group=parameters,
            parameter="intensity_threshold_in_ADU",
            parameter_type=float,
        )

        self._rotation: float = get_parameter_from_parameter_group(
            group=parameters,
            parameter="rotation_in_degrees",
            parameter_type=float,
            required=True,
        )
        self._min_row: int = get_parameter_from_parameter_group(
            group=parameters,
            parameter="min_row_in_pix_for_integration",
            parameter_type=int,
            required=True,
        )
        self._max_row: int = get_parameter_from_parameter_group(
            group=parameters,
            parameter="max_row_in_pix_for_integration",
            parameter_type=int,
            required=True,
        )

    # TODO: Enforce return dict content for the function below

    def calculate_spectrum(
        self, *, data: Union[NDArray[numpy.float_], NDArray[numpy.int_]]
    ) -> Dict[str, NDArray[numpy.float_]]:
        """
        Calculates beam energy spectrum information from a camera data frame.

        This function extracts energy spectrum information from a provided camera data
        frame. It returns the raw spectrum information, plus a smoother, filtered
        version of it.

        The function initially rotates the camera image to align the spectrum
        information with the vertical axis of the camera data frame. It then computes
        the beam energy spectrum by integrating the region where the energy is recorded
        along the horizontal axis of the data frame.

        Optionally, the algorithm can apply an ADU threshold can to the camera data. If
        a threshold is provided when the algorithm is initialized, this function
        excludes from the spectrum calculation all the pixels below the threshold.

        Arguments:

            data: The camera data frame from which the spectrum information must be
                extracted.

        Returns:

            A dictionary storing the spectrum information extracted from the camera
                frame.

                * The value corresponding to the key named `spectrum` is a 1D array
                storing the raw spectrum information.

                * The value corresponding to the key named `spectrum_smooth` is a 1D
                array storing a filtered, smoothed version of the spectrum.
        """

        # Apply a threshold

        # TODO: Perhaps better type hints can be found for this
        if self._intensity_threshold:
            data[data < self._intensity_threshold] = 0
        imr: Union[NDArray[numpy.float_], NDArray[numpy.int_]] = cast(
            Union[NDArray[numpy.float_], NDArray[numpy.int_]],
            ndimage.rotate(data, self._rotation, order=0),
        )
        spectrum: NDArray[numpy.float_] = numpy.mean(
            imr[:, self._min_row : self._max_row], axis=1
        )
        spectrum_smoothed: NDArray[numpy.float_] = ndimage.filters.gaussian_filter1d(
            spectrum, 2
        )

        return {
            "spectrum": spectrum,
            "spectrum_smoothed": spectrum_smoothed,
        }
