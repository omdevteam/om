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
# Copyright 2020 -2023 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
#TODO: Docstring
"""

from typing import Any, Dict, Union, cast

import numpy
import torch
from numpy.typing import NDArray
from peaknet import app
from peaknet.plugins import apply_mask

from om.lib.hdf5 import parse_parameters_and_load_hdf5_data
from om.lib.parameters import get_parameter_from_parameter_group

from ._crystallography import TypePeakList


class PeakNetPeakDetection:
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        parameters: Dict[str, Any],
    ) -> None:
        """
        PeakNet algorithm for peak detection.

        `parameters` contains:
        - path_model_weight
        - path_yaml_config
        """
        # Unpack parameters...
        path_model_weight = get_parameter_from_parameter_group(
            group=parameters,
            parameter="path_model_weight",
            parameter_type=str,
        )
        path_yaml_config = get_parameter_from_parameter_group(
            group=parameters,
            parameter="path_yaml_config",
            parameter_type=str,
        )

        print("DEBUG: Using peaknet!!!")

        # Load param: bad pixel map
        self._bad_pixel_map: Union[NDArray[numpy.int_], None] = cast(
            Union[NDArray[numpy.int_], None],
            parse_parameters_and_load_hdf5_data(
                parameters=parameters,
                hdf5_filename_parameter="bad_pixel_map_filename",
                hdf5_path_parameter="bad_pixel_map_hdf5_path",
            ),
        )
        print(f"DEBUG: No bad pixel map: {self._bad_pixel_map is None}")

        # Load param: cheetah geom
        self._cheetah_geom: Union[str, None] = get_parameter_from_parameter_group(
            group=parameters,
            parameter="cheetah_geom",
            parameter_type=str,
        )

        # Load param: cheetah geom
        self._min_num_peaks: Union[int, None] = get_parameter_from_parameter_group(
            group=parameters,
            parameter="min_num_peaks",
            parameter_type=int,
        )

        # Initialize peak finder
        self.peak_finder = app.PeakFinder(
            path_chkpt=path_model_weight, path_yaml_config=path_yaml_config
        )
        self.device = self.peak_finder.device
        print(f"DEBUG: Device: {self.device}")

    def find_peaks(
        self, *, data: Union[NDArray[numpy.int_], NDArray[numpy.float_]]
    ) -> TypePeakList:
        """
        Finds peaks in a detector data frame.

        This function detects peaks in a provided detector data frame, and returns
        information about their location, size and intensity.

        Arguments:

            data: The detector data frame on which the peak-finding operation must be
                performed.

        Returns:

            A [TypePeakList][om.algorithms.crystallography.TypePeakList] dictionary
                with information about the detected peaks.

        """
        if self._bad_pixel_map is not None:
            data = apply_mask(data, self._bad_pixel_map, mask_value=0)

        data = torch.tensor(data)[
            None,
            None,
        ].to(self.device, non_blocking=True)

        # Use peaknet peak finding...
        peak_list, _ = self.peak_finder.find_peak_w_softmax(data,
            min_num_peaks          = self.peak_finder.config.OM.MIN_NUM_PEAKS,
            uses_geom              = False,
            returns_prediction_map = False,
            uses_mixed_precision   = self.peak_finder.config.OM.USES_MIXED_PRECISION
        )

        # Adapt the peak array to the psocake convention...
        # peak_list: (B, 3), where 3 means seg, y, x
        y, x = [], []
        peak_list = numpy.array(peak_list)
        num_peaks = peak_list.shape[0]
        if num_peaks > 0:
            y, x = peak_list.transpose(1, 0)[1:]

        return {
            "num_peaks"          : num_peaks,
            "fs"                 : x,
            "ss"                 : y,
            "intensity"          : [0] * num_peaks,
            "num_pixels"         : [0] * num_peaks,
            "max_pixel_intensity": [0] * num_peaks,
            "snr"                : [0] * num_peaks,
        }

        ## # Use peaknet peak finding...
        ## peak_list = self.peak_finder.find_peak_w_softmax(
        ##     data,
        ##     min_num_peaks=10,
        ##     uses_geom=False,
        ##     returns_prediction_map=False,
        ##     uses_mixed_precision=True,
        ## )

        ## # Adapt the peak array to the Cheetah convention...
        ## x = [entry[1] for entry in peak_list]
        ## y = [entry[2] for entry in peak_list]
        ## peak_list = [
        ##     y,
        ##     x,
        ##     [0] * len(y),
        ##     [0] * len(y),
        ##     [0] * len(y),
        ##     [0] * len(y),
        ##     [0] * len(y),
        ## ]

        ## return {
        ##     "num_peaks": len(peak_list[0]),
        ##     "fs": peak_list[0],
        ##     "ss": peak_list[1],
        ##     "intensity": peak_list[2],
        ##     "num_pixels": peak_list[4],
        ##     "max_pixel_intensity": peak_list[5],
        ##     "snr": peak_list[6],
        ## }
