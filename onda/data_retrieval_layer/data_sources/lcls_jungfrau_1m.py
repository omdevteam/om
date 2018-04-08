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
Functions and classes for the processing of data from the CSPAD
detector.
"""
import collections


def get_peakfinder8_info():
    """
    Return peakfinder8 detector info.

    Return the peakfinder8 information for the Eiger detector.

    Returns:

        Tuple[int, int, int, int]: A tuple where the four fields (named
        respectively 'asics_nx', 'asics_ny', 'nasics_x', and
        'nasics_y)' are the four parameters used by the peakfinder8
        algorithm to describe the format of the input data.
    """
    Peakfinder8DetInfo = collections.namedtuple(  # pylint: disable=C0103
        typename='Peakfinder8DetectorInfo',
        field_names=['asic_nx', 'asic_ny', 'nasics_x', 'nasics_y']
    )
    return Peakfinder8DetInfo(1024, 512, 1, 2)


def detector_data(event,
                  data_extraction_func_name):
    """
    Recover raw detector data for one frame.

    Return the detector data for one single frame as provided by psana.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        ndarray: the raw detector data for one frame.
    """
    cspad_psana = event['psana_interface'][data_extraction_func_name].calib(
        event['psana_event']
    )
    cspad_reshaped = cspad_psana.reshape(1024, 1024)
    return cspad_reshaped
