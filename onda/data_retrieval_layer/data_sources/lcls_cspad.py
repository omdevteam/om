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
"""
Retrieval of data from the CSPAD detector at LCLS.

This module contains the implementation of several functions used
to retrieve data from the CSPAD detector as used at the LCLS facility.
"""
import numpy

from onda.utils import named_tuples


#####################
#                   #
# UTILITY FUNCTIONS #
#                   #
#####################

def get_peakfinder8_info():
    """
    Retrieve the peakfinder8 detector information.

    Returns:

        Peakfinder8DetInfo: the peakfinder8-related detector
        information.
    """
    return named_tuples.Peakfinder8DetInfo(
        asic_nx=194,
        asic_ny=185,
        nasics_x=8,
        nasics_y=8
    )


#############################
#                           #
# DATA EXTRACTION FUNCTIONS #
#                           #
#############################

def detector_data(event, data_extraction_func_name):
    """
    Retrieve one frame of detector data.

    Args:

        event (Dict): a dictionary with the event data.

        data_extraction_func_name (str): the name of the data
          extraction function ("detector_data", "detector2_data",
          "detector3_data", etc.) that is associated with the current
          detector.

    Returns:

        numpy.ndarray: one frame of detector data.
    """
    # Recover the data from psana.
    cspad_psana = (
        event['psana_detector_interface'][data_extraction_func_name].calib(
            event['psana_event']
        )
    )

    # Rearrange the data into 'slab' format.
    cspad_reshaped = cspad_psana.reshape((4, 8, 185, 388))
    cspad_slab = numpy.zeros(
        shape=(1480, 1552),
        dtype=cspad_reshaped.dtype
    )
    for i in range(cspad_reshaped.shape[0]):
        cspad_slab[
            :,
            i * cspad_reshaped.shape[3]: (i+1) * cspad_reshaped.shape[3]
        ] = cspad_reshaped[i].reshape(
            (
                cspad_reshaped.shape[1] * cspad_reshaped.shape[2],
                cspad_reshaped.shape[3]
            )
        )

    # Return the rearranged data.
    return cspad_slab
