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
Retrieval of CSPAD detector data from psana.

This module contains functions that retrieve CSPAD detector data from the psana
software framework (used at the LCLS facility).
"""
from typing import Any, Dict

import numpy  # type: ignore

from om.utils import exceptions


def detector_data(event: Dict[str, Any]) -> numpy.ndarray:
    """
    Retrieves a CSPAD detector data frame from psana.

    This function retrieves a single CSPAD detector frame from psana. It returns the
    frame as a 2D array storing pixel data.

    Arguments:

        event: A dictionary storing the event data.

    Returns:

        One frame of detector data.
    """
    cspad_psana: numpy.ndarray = event["additional_info"]["psana_detector_interface"][
        "detector_data"
    ].calib(event["data"])
    if cspad_psana is None:
        raise exceptions.OmDataExtractionError(
            "Could not retrieve detector data from psana."
        )

    # Rearranges the data into 'slab' format.
    cspad_reshaped: numpy.ndarray = cspad_psana.reshape((4, 8, 185, 388))
    cspad_slab: numpy.ndarray = numpy.zeros(
        shape=(1480, 1552), dtype=cspad_reshaped.dtype
    )
    index: int
    for index in range(cspad_reshaped.shape[0]):
        cspad_slab[
            :, index * cspad_reshaped.shape[3] : (index + 1) * cspad_reshaped.shape[3]
        ] = cspad_reshaped[index].reshape(
            (cspad_reshaped.shape[1] * cspad_reshaped.shape[2], cspad_reshaped.shape[3])
        )

    return cspad_slab
