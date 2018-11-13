#    This file is part of OnDA.
#
#    OnDA is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    OnDA is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with OnDA.  If not, see <http://www.gnu.org/licenses/>.
#
#    Copyright 2014-2018 Deutsches Elektronen-Synchrotron DESY,
#    a research centre of the Helmholtz Association.
"""
Retrieval of data from the pnCCD detector at LCLS.

Functions and classes used to retrieve data from the EPIX detector as
used at the LCLS facility.
"""
from __future__ import absolute_import, division, print_function

import numpy

from onda.utils import named_tuples


#####################
#                   #
# UTILITY FUNCTIONS #
#                   #
#####################


def get_peakfinder8_info():
    """
    Peakfinder8 info for the pnCCD detector at LCLS.

    Retrieves the peakfinder8 information matching the data format used
    by the pnCCD detector at the LCLS facility.

    Returns:

        Peakfinder8DetInfo: the peakfinder8-related detector
        information.
    """
    return named_tuples.Peakfinder8DetInfo(
        asic_nx=1024,
        asic_ny=512,
        nasics_x=1,
        nasics_y=2
    )


#############################
#                           #
# DATA EXTRACTION FUNCTIONS #
#                           #
#############################


def detector_data(
        event,
        data_extraction_func_name
):
    """
    One frame of pnCCD detector data at LCLS.

    Extracts one frame of pnCCD detector data from an event retrieved
    at the LCLS facility.

    Args:

        event (Dict): a dictionary with the event data.

        data_extraction_func_name: specific name of the data extraction
            function with which this generic data extraction function
            should be associated (e.g: 'detector_data',
            'detector2_data'. 'detector3_data', etc.). This is required
            to resuse this data extraction function with multiple
            detectors. The `functools.partial` python function is used
            to create 'personalized' versions of this function for each
            detector, by fixing this argument.

    Returns:

        ndarray: one frame of detector data.
    """
    # Recovers the data from psana.
    pnccd_psana = (
        event['psana_detector_interface'][data_extraction_func_name].calib(
            event['psana_event']
        )
    )

    # Rearranges the data into 'slab' format.
    pnccd_slab = numpy.zeros(shape=(1024, 1024), dtype=pnccd_psana.dtype)
    pnccd_slab[0:512, 0:512] = pnccd_psana[0]
    pnccd_slab[512:1024, 0:512] = pnccd_psana[1][::-1, ::-1]
    pnccd_slab[512:1024, 512:1024] = pnccd_psana[2][::-1, ::-1]
    pnccd_slab[0:512, 512:1024] = pnccd_psana[3]

    # Returns the rearranged data.
    return pnccd_slab
