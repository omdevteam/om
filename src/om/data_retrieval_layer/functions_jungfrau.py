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
Retrieval of Jungfrau 4M detector data.

This module contains functions that retrieve data from a Jungfrau 4M x-ray detector.
"""
from __future__ import absolute_import, division, print_function

from typing import Any, Dict

import numpy  # type: ignore

from om.utils import exceptions


def detector_data(event):
    # type: (Dict[str, Any]) -> numpy.ndarray
    """
    Retrieves one frame of CSPAD detector data from psana.

    Arguments:

        event (Dict[str, Any]): a dictionary storing the event data.

    Returns:

        numpy.ndarray: one frame of detector data.
    """
    # jungfrau_psana = event["additional_info"]["psana_detector_interface"][
    #     "detector_data"
    # ].raw(event["data"])
    jungfrau_psana = event["additional_info"]["psana_detector_interface"][
        "detector_data"
    ].raw(event["data"])
    if jungfrau_psana is None:
        raise exceptions.OmDataExtractionError(
            "Could not retrieve detector data from psana."
        )

    # Rearranges the data into 'slab' format.
    jungfrau_reshaped = jungfrau_psana.reshape(8 * 512, 1024)  # type: numpy.ndarray

    return jungfrau_reshaped
