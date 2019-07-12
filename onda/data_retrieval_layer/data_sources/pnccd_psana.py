# This file is part of OnDA.
#
# OnDA is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# OnDA is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with OnDA.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Retrieval of pnCCD detector data from psana.
"""
from __future__ import absolute_import, division, print_function

import numpy

from onda.utils import (  # pylint: disable=unused-import
    exceptions,
    named_tuples,
    data_event,
)


#####################
#                   #
# UTILITY FUNCTIONS #
#                   #
#####################


def get_peakfinder8_info():
    # type () -> named_tuples.Peakfinder8Info
    """
    Retrieves the peakfinder8 information for the pnCCD detector.

    Returns:

        :class:`~onda.utils.named_tuples.Peakfinder8Info`: a named tuple storing the
        peakfinder8 information.
    """

    return named_tuples.Peakfinder8Info(
        asic_nx=1024, asic_ny=512, nasics_x=1, nasics_y=2
    )


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

        event (:class:`~onda.utils.data_event.DataEvent`): an object storing the event
            data.

    Returns:

        numpy.ndarray: one frame of detector data.
    """
    pnccd_psana = event.framework_info["psana_detector_interface"][
        data_extraction_func_name
    ].calib(event.framework_info["psana_event"])
    if pnccd_psana is None:
        raise exceptions.OndaDataExtractionError(
            "Could not retrieve detector from psana."
        )

    # Rearranges the data into 'slab' format.
    pnccd_slab = numpy.zeros(shape=(1024, 1024), dtype=pnccd_psana.dtype)
    pnccd_slab[0:512, 0:512] = pnccd_psana[0]
    pnccd_slab[512:1024, 0:512] = pnccd_psana[1][::-1, ::-1]
    pnccd_slab[512:1024, 512:1024] = pnccd_psana[2][::-1, ::-1]
    pnccd_slab[0:512, 512:1024] = pnccd_psana[3]

    return pnccd_slab
