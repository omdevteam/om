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
Utilities to process data from the JUngfrau 1M detector at LCLS.

This module implements several functions used to process data from the
Jungfrau 1M detector at the LCLS facility.
"""
from onda.utils import named_tuples


#####################
#                   #
# UTILITY FUNCTIONS #
#                   #
#####################

def get_peakfinder8_info():
    """
    Return peakfinder8 detector info.

    Return peakfinder8 information for the CSPAD detector.

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


def detector_data(event,
                  data_extraction_func_name):
    """
    Recover raw detector data for one frame.

    Return the detector data for one single frame.

    Args:

        event (Dict): a dictionary with the event data.

        data_extraction_func_name (str): the name of the data
          extraction function ("detector_data", "detector2_data",
          "detector3_data", etc.) that is associated with this
          detector.

    Returns:

        ndarray: the raw detector data for one frame.
    """
    # Recover the data from psana.
    cspad_psana = (
        event['psana_detector_interface'][data_extraction_func_name].calib(
            event['psana_event']
        )
    )

    # Rearrange the data into 'slab' format.
    cspad_reshaped = cspad_psana.reshape(1024, 1024)

    # Retrun the rearranged data.
    return cspad_reshaped
