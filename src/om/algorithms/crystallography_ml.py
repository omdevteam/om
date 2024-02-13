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

from typing import Any, Dict, List, Union, cast

import numpy
import torch
from numpy.typing import NDArray
from peaknet import app_om as app
from peaknet.plugins import apply_mask
from pydantic import BaseModel, Field, model_validator
from ruamel.yaml import YAML

from om.lib.hdf5 import load_hdf5_data
from om.lib.parameters import validate_parameters

from .crystallography import TypePeakList


class _PeakNetPeakDetectionParameters(BaseModel):
    path_model_weight: str = Field(default=None)
    path_config: str = Field(default=None)
    cheetah_geom: str
    min_num_peaks: int
    bad_pixel_map_filename: Union[str, None] = Field(default=None)
    bad_pixel_map_hdf5_path: Union[str, None] = Field(default=None)

    @model_validator(mode="after")
    def check_hd5_path(self) -> "_PeakNetPeakDetectionParameters":
        if (
            self.bad_pixel_map_filename is not None
            and self.bad_pixel_map_hdf5_path is None
        ):
            raise ValueError(
                "If the bad_pixel_map_filename parameter is specified, "
                "the bad_pixel_map_hdf5_path must also be provided"
            )
        return self


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
        - path_config
        """

        peaknet_parameters: _PeakNetPeakDetectionParameters = validate_parameters(
            model=_PeakNetPeakDetectionParameters,
            parameter_group=parameters,
        )

        # Attempt to load the yaml config...
        self.peaknet_config = app.PeakFinder.get_default_config()
        if peaknet_parameters.path_config is not None:
            with open(peaknet_parameters.path_config, "r") as fh:
                yaml_content = YAML(typ="safe")
                yaml_content.load(fh)
                self.peaknet_config = yaml_content

        # Load param: bad pixel map
        if (
            peaknet_parameters.bad_pixel_map_filename is not None
            and peaknet_parameters.bad_pixel_map_hdf5_path is not None
        ):
            self._bad_pixel_map: Union[NDArray[numpy.int_], None] = cast(
                Union[NDArray[numpy.int_], None],
                load_hdf5_data(
                    hdf5_filename=peaknet_parameters.bad_pixel_map_filename,
                    hdf5_path=peaknet_parameters.bad_pixel_map_hdf5_path,
                ),
            )
        else:
            self._bad_pixel_map = None

        # Initialize peak finder
        self.peak_finder = app.PeakFinder(
            path_chkpt=peaknet_parameters.path_model_weight, config=self.peaknet_config
        )
        self.device = self.peak_finder.device

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

        tensor_data: torch.Tensor = torch.tensor(data)[
            None,
            None,
        ].to(self.device, non_blocking=True)

        # Use peaknet peak finding...
        # TODO: What's the type of peak list here?
        peak_list = self.peak_finder.find_peak_w_softmax(
            tensor_data,
            min_num_peaks=10,
            uses_geom=False,
            returns_prediction_map=False,
            uses_mixed_precision=True,
        )

        # Adapt the peak array to the Cheetah convention...
        x = [entry[1] for entry in peak_list]
        y = [entry[2] for entry in peak_list]
        peak_list: List[float] = [
            y,
            x,
            [0] * len(y),
            [0] * len(y),
            [0] * len(y),
            [0] * len(y),
            [0] * len(y),
        ]

        return {
            "num_peaks": len(peak_list[0]),
            "fs": peak_list[0],
            "ss": peak_list[1],
            "intensity": peak_list[2],
            "num_pixels": peak_list[4],
            "max_pixel_intensity": peak_list[5],
            "snr": peak_list[6],
        }
