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

This module contains algorithms that carry out x-ray emission spectroscopy-related data
processing (spectrum generation, etc.).
"""

from typing import Any, Dict, Union

import numpy  # type: ignore
from scipy import ndimage  # type: ignore

from om.utils import parameters as param_utils


class XESAnalysis:
    """
    See documentation of the '__init__' function.
    """

    def __init__(
        self,
        *,
        intensity_threshold: Union[float, None] = None,
        rotation: Union[float, None] = None,
        min_row: Union[int, None] = None,
        max_row: Union[int, None] = None,
        parameters: Union[Dict[str, Any], None] = None,
    ) -> None:
        """
        XES algorithm for calculating spectra from 2D camera.

        This algorithm extracts spectrum information from a 2D camera image. The image
        is rotated until the spectrum information is aligned to the vertical axis. The
        image area containing the spectrum information is then integrated in a
        direction parallel to the vertical axis. Optionally, this algorithm can apply
        an intensity threshold to the data and consider only pixels whose value exceeds
        the threshold.

        Arguments:

            intensity_threshold: An intensity threshold, in ADU units, for spectrum
                data for being considered.

            rotation (int): The rotation in degrees that should be applied to align the
                linear signal on 2D camera with vertical axis.

            min_row (int): The minimum row index defining the region of integration for
                the spectrum after the signal has been rotated.

            max_row (int): The maximim row index defining the region of integration for
                the spectrum after the signal has been rotated.
        """
        if parameters is not None:
            intensity_threshold = param_utils.get_parameter_from_parameter_group(
                group=parameters,
                parameter="intensity_threshold_in_ADU",
                parameter_type=float,
            )
            rotation = param_utils.get_parameter_from_parameter_group(
                group=parameters,
                parameter="rotation_in_degrees",
                parameter_type=float,
                required=True,
            )
            min_row = param_utils.get_parameter_from_parameter_group(
                group=parameters,
                parameter="min_row_in_pix_for_integration",
                parameter_type=int,
                required=True,
            )
            max_row = param_utils.get_parameter_from_parameter_group(
                group=parameters,
                parameter="max_row_in_pix_for_integration",
                parameter_type=int,
                required=True,
            )
        else:
            print(
                "OM Warning: Initializing the XESAnalysis algorithm with individual "
                "parameters (intensity threshold, rotation, min_row and max_row) is "
                "deprecated and will be removed in a future version of OM. Please use "
                "the new parameter group-based initialization interface (which "
                "requires only the parameters and photon_energy_kev arguments)."
            )

        if rotation is None or min_row is None or max_row is None:
            raise RuntimeError(
                "OM ERROR: Some parameters required for the initialization of the "
                "XESAnalysis algorithm have not been defined. Please check the command "
                "used to initialize the algorithm."
            )

        self._intensity_threshold: Union[float, None] = intensity_threshold
        self._rotation: Union[float, None] = rotation
        self._min_row: Union[int, None] = min_row
        self._max_row: Union[int, None] = max_row

    def generate_spectrum(self, data: numpy.ndarray) -> Dict[str, numpy.ndarray]:
        """
        Calculates spectrum information from camera image data.

        This function extracts spectrum information from a camera frame. It returns
        the raw spectrum information together with a smoothed version.

        Arguments:

            data (numpy.ndarray): The camera image data from which the spectrum will be
                generated.

        Returns:

            A dictionary with information about the XES spectrum extracted from the
            camera image data. The dictionary has the following keys:

            - A key named "spectrum" whose value is a 1D array of storing the raw
              spectral energy information.

            - A key named "spectrum_smooth" whose value is a 1D array storing a
              filtered, smoothed version of the spectral energy information.
        """

        # Apply a threshold
        if self._intensity_threshold:
            data[data < self._intensity_threshold] = 0
        imr: numpy.ndarray = ndimage.rotate(data, self._rotation, order=0)
        spectrum: numpy.ndarray = numpy.mean(
            imr[:, self._min_row : self._max_row], axis=1
        )
        spectrum_smoothed: numpy.ndarray = ndimage.filters.gaussian_filter1d(
            spectrum, 2
        )

        return {
            "spectrum": spectrum,
            "spectrum_smoothed": spectrum_smoothed,
        }


def _running_mean(x: numpy.ndarray, n: int) -> numpy.ndarray:
    # TODO: Document this function.
    return ndimage.filters.uniform_filter1d(x, n, mode="constant")[: -(n - 1)]
