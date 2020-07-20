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
Retrieval of pnCCD detector data from psana.

This module contains functions that retrieve data from a pnCCD x-ray detector using the
psana framework.
"""
from __future__ import absolute_import, division, print_function

import numpy

from om.utils import exceptions, data_event


#####################
#                   #
# UTILITY FUNCTIONS #
#                   #
#####################


def get_peakfinder8_info():
    # type () -> Dict[str, Union[int, float]]
    """
    Retrieves the peakfinder8 information for the pnCCD detector.

    Returns:

        Dict[str, Union[int, float]]: a named tuple storing the peakfinder8
        information.
    """
    return {
        "asic_nx": 1024,
        "asic_ny": 512,
        "nasics_x": 1,
        "nasics_y": 2,
    }


#############################
#                           #
# DATA EXTRACTION FUNCTIONS #
#                           #
#############################


def detector_data(event, data_extraction_func_name):
    # type: (data_event.DataEvent, str) -> numpy.ndarray
    """
    Retrieves from psana one frame of pnCCD detector data.

    Arguments:

        event (:class:`~om.utils.data_event.DataEvent`): an object storing the event
            data.

    Returns:

        numpy.ndarray: one frame of detector data.
    """
    pnccd_psana = event.framework_info["psana_detector_interface"][
        data_extraction_func_name
    ].calib(event.framework_info["psana_event"])
    if pnccd_psana is None:
        raise exceptions.OmDataExtractionError(
            "Could not retrieve detector from psana."
        )

    # Rearranges the data into 'slab' format.
    pnccd_slab = numpy.zeros(shape=(1024, 1024), dtype=pnccd_psana.dtype)
    pnccd_slab[0:512, 0:512] = pnccd_psana[0]
    pnccd_slab[512:1024, 0:512] = pnccd_psana[1][::-1, ::-1]
    pnccd_slab[512:1024, 512:1024] = pnccd_psana[2][::-1, ::-1]
    pnccd_slab[0:512, 512:1024] = pnccd_psana[3]

    return pnccd_slab
