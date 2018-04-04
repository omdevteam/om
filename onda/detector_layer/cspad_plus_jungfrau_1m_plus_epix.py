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

from onda.detector_layer.cspad import detector_data, get_peakfinder8_info


def detector2_data(event):
    """
    Recover raw detector data for one frame for the second detector.

    Return the detector data for one single frame for the second
    detector, as provided by psana.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        ndarray: the raw detector data for one frame.
    """
    cspad_psana = event['psana_interface']['detector2_data'].calib(
        event['psana_event']
    )
    cspad_reshaped = cspad_psana.reshape(1024, 1024)
    return cspad_reshaped


def detector3_data(event):
    """
    Recover raw detector data for one frame for the second detector.

    Return the detector data for one single frame for the second
    detector, as provided by psana.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        ndarray: the raw detector data for one frame.
    """
    cspad_psana = event['psana_interface']['detector3_data'].calib(
        event['psana_event']
    )
    return cspad_psana
