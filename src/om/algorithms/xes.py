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
Algorithms for the processing of x-ray emission spectroscopy data.

This module contains algorithms that perform data processing operations related to
x-ray emission spectroscopy (beam energy spectrum retrieval, etc.).
"""

from typing import Any, Dict, cast

import numpy
from numpy.typing import NDArray
from scipy import ndimage  # type: ignore

from om.library.parameters import get_parameter_from_parameter_group


class XESAnalysis:
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

        This algorithm stores all the parameters needed to extract beam energy
        spectra from camera data frames. It can then extract a beam energy spectrum
        from a provided camera frame. The algorithm rotates the frame image until the
        beam energy information is aligned with the vertical axis. The data from the
        area containing the information is then integrated in a direction parallel to
        the axis. Optionally, this algorithm can apply an ADU threshold to the camera
        data, and use only the pixels whose values exceeds the threshold to compute the
        spectrum.

        Arguments:

            parameters: A set of OM configuration parameters collected together in a
                parameter group. The parameter group must contain the following
                entries:

                * `intensity_threshold_in_ADU`: An intensity threshold, in ADU units,
                  for pixels in the camera frame to be considered in the spectrum
                  calculation.

                * `rotation_in_degrees`: The rotation in degrees that should be applied
                  to the camera image to align the spectrum information to the vertical
                  axis.

                * `min_row_in_pix_for_integration`: The row index defining the start of
                  the integration region for the spectrum information.

                * `max_row_in_pix_for_integration` The row index defining the end of
                  the integration region for the spectrum information.
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

    def generate_spectrum(
        self, *, data: NDArray[numpy.float_]
    ) -> Dict[str, NDArray[numpy.float_]]:
        """
        Calculates beam energy spectrum information from a 2D camera data frame.

        This function extracts beam energy spectrum information from a provided camera
        data frame. It returns the raw spectrum information, plus a smoother, filtered
        version of it.

        Arguments:

            data: The camera data frame from which the spectrum information must be
                extracted.

        Returns:

            A dictionary storing the spectrum information extracted from the
                camera frame.

                * The value corresponding to the key named `spectrum` is a 1D array
                storing the raw spectrum information.

                * The value corresponding to the key named `spectrum_smooth` is a 1D
                array storing a filtered, smoothed version of the spectrum.
        """

        # Apply a threshold
        if self._intensity_threshold:
            data[data < self._intensity_threshold] = 0
        imr: NDArray[numpy.float_] = ndimage.rotate(data, self._rotation, order=0)
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


def _running_mean(x: NDArray[numpy.float_], n: int) -> NDArray[numpy.float_]:
    # TODO: Document this function.
    return cast(
        NDArray[numpy.float_],
        ndimage.filters.uniform_filter1d(x, n, mode="constant")[: -(n - 1)],
    )
