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
Utilities to process EPIX detector data at the LCLS facility.

Exports:

    Namedtuples:

        Peakfinder8DetInfo: peakfinder8-related information.

    Functions:

        get_peakfinder8_info: get peakfinder8-related detector info.

        detector_data: recover the raw detector data for a frame.
"""
import collections


###############
#             #
# NAMEDTUPLES #
#             #
###############

Peakfinder8DetInfo = collections.namedtuple(  # pylint: disable=C0103
    typename='Peakfinder8DetectorInfo',
    field_names=['asic_nx', 'asic_ny', 'nasics_x', 'nasics_y']
)
"""
Peakfinder8-related information.

A namedtuple where the four fields (named respectively 'asics_nx',
'asics_ny', 'nasics_x', and  'nasics_y)' are the four parameters used
by the peakfinder8 algorithm to describe the format of theinput data.
"""


###############################
#                             #
# LCLS-EPIX UTILITY FUNCTIONS #
#                             #
###############################

def get_peakfinder8_info():
    """
    Return peakfinder8 detector info.

    Return the peakfinder8 information for the CSPAD detector.

    Returns:

        Peakfinder8DetInfo: the peakfinder8-related detector
        information.
    """
    return Peakfinder8DetInfo(1024, 512, 1, 2)


########################################
#                                      #
# LCLS-EPIX DATA EXTRACTION FUNCTIONS #
#                                      #
########################################

def detector_data(event,
                  data_extraction_func_name):
    """
    Recover raw detector data for one frame.

    Return the detector data for one single frame as provided by psana.

    Args:

        event (Dict): a dictionary with the event data.

        data_extraction_func_name (str): the name of the data
          extraction function ("detector_data", "detector2_data",
          "detector3_data", etc.) that is associated with this
          detector.

    Returns:

        ndarray: the raw detector data for one frame.
    """
    cspad_psana = event['psana_interface'][data_extraction_func_name].calib(
        event['psana_event']
    )
    return cspad_psana
