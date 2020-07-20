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
Retrieval of CSPAD detector data from psana.

This module contains functions that retrieve data from a CSPAD x-ray detector using the
psana framework.
"""
from __future__ import absolute_import, division, print_function

from typing import Dict

import numpy  # type: ignore

from om.utils import data_event, exceptions


#####################
#                   #
# UTILITY FUNCTIONS #
#                   #
#####################


def get_peakfinder8_info():
    # type: () -> Dict[str, int]
    """
    Retrieves the peakfinder8 information for the CSPAD detector.

    Returns:

        Dict[str, int]: a dictionary storing the peakfinder8 information.
    """
    return {
        "asic_nx": 194,
        "asic_ny": 185,
        "nasics_x": 8,
        "nasics_y": 8,
    }


#############################
#                           #
# DATA EXTRACTION FUNCTIONS #
#                           #
#############################


def detector_data(event):
    # type: (data_event.DataEvent) -> numpy.ndarray
    """
    Retrieves one frame of CSPAD detector data from psana.

    Arguments:

        event (:class:`~om.utils.data_event.DataEvent`): an object storing the event
            data.

    Returns:

        numpy.ndarray: one frame of detector data.
    """
    cspad_psana = event.framework_info["psana_detector_interface"][
        "detector_data"
    ].calib(event.data)
    if cspad_psana is None:
        raise exceptions.OmDataExtractionError(
            "Could not retrieve detector data from psana."
        )

    # Rearranges the data into 'slab' format.
    cspad_reshaped = cspad_psana.reshape((4, 8, 185, 388))  # type: numpy.ndarray
    cspad_slab = numpy.zeros(
        shape=(1480, 1552), dtype=cspad_reshaped.dtype
    )  # type: numpy.ndarray
    for i in range(cspad_reshaped.shape[0]):
        cspad_slab[
            :, i * cspad_reshaped.shape[3] : (i + 1) * cspad_reshaped.shape[3]
        ] = cspad_reshaped[i].reshape(
            (cspad_reshaped.shape[1] * cspad_reshaped.shape[2], cspad_reshaped.shape[3])
        )

    return cspad_slab
