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
'''
Functions and classes to process Pilatus data stored in files.
'''


from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
import collections

import fabio
from scipy.constants import c, electron_volt, h


Peakfinder8DetectorInfo = collections.namedtuple(  # pylint: disable-msg=C0103
    typename='Peakfinder8DetectorInfo',
    field_names=['asics_nx', 'asics_ny', 'nasics_x', 'nasics_y']
)
'''
A namedtuple used for peakfinder8-related detector information.

The four fields are the four parameters used by the peakfinder8 algorithm to
describe the data format of the input data.
'''

FilenameAndFrameIndex = collections.namedtuple(   # pylint: disable-msg=C0103
    typename='FilenameAndFrameIndex',
    field_names=['filename', 'frame_index']
)
'''
A namedtuple to store filename and frame_index information.

The first field is the full path to the file containing the data, the second
field is the index of a frame in the data block, located in the file, that
stores the raw detector data. This information is used to locate a specific
frame in multi-frame data files. .
'''

FILE_EXTENSIONS = ('.cbf')
'''
Allowed file extensions.
'''

PEAKFINDER8_DETECTOR_INFO = Peakfinder8DetectorInfo(
    2463, 2527, 1, 1
)
'''
Peakfinder8-related detector information.
'''


def open_event(event):
    '''
    Open event.

    Return a fabio module cbf_obj object and the creation date of the file
    as timestamp.

    Args:

        event(str): the full path of the Pilatus data file.

    Returns:

        dict: A dictionary containing three entries: 'cbf_obj', the fabio
        cbf_obj object storing the data from the file, 'file_creation_time',
        the creation time of the file (in timestamp format), and 'filename',
        the full path to the file containing the data
    '''

    # Create the dictionary that will be returned.
    opened_event = {}

    # Open the file and recover the fabio cbf_obj object.
    opened_event['cbf_obj'] = fabio.open(event, 'r')

    # Recover the creation time of the file.
    opened_event['file_creation_time'] = os.stat(event).st_ctime

    # Store the file name in the returned dictionary.abs
    opened_event['filename'] = event

    # Return a tuple with the information.
    return opened_event


def close_event(_):
    '''
    Close event.

    Actually doing nothing. There is no need to close a fabio cbf_obj object.

    '''

    pass


def get_num_frames_in_event(_):
    '''
    The number of frames in an event.

    Cbf files usually store 1 frame per file.
    '''

    # Just return 1.
    return 1


def raw_data(opened_event):
    '''
    Recover raw detector data for one frame.

    Extract raw detector data from the fabio cbf_obj object contained in
    the input dictionary.

    Args:

        opened_event (dict): dictionary containing the opened event
            information.

    Returns:

        ndarray: the raw detector data.

    '''

    # Extract and return the detector data.
    return opened_event['cbf_obj'].data


def timestamp(opened_event):
    '''
    Recover the timestamp of the event.

    Extract the timestamp event from the input dictionary.

    Args:

        opened_event (dict): dictionary containing the opened event
            information.

    Returns:

        timestamp: the creation time of the file containing the detector data.
    '''

    # Return the creation time of the file.
    return opened_event['file_creation_time']


def beam_energy(opened_event):
    '''
    Recover the energy of the beam.

    Return the information from the header of the CBF file if the information
    is there, otherwise fall back to the value found in the configuration
    file

    Args:

        opened_event (dict): dictionary containing the opened event
            information.

    Returns:

        float: the energy of the beam in eV.
    '''

    try:
        # Try to read the data from the header of the CBF file.
        header_data_list = opened_event['cbf_obj'].header[
            u'_array_data.header_contents'
        ].split('\r\n')
        wavelength = float(header_data_list[15].split()[2])

        # If successful, convert to eV and return.
        return float(h * c / (wavelength * electron_volt))
    except (AttributeError, IndexError, ValueError):
        # If the data cannot be found in the heaeder of the CBF file,
        # return the value provided in the configuration file.
        return float(
            opened_event['monitor_params'].get_param(
                section='General',
                parameter='fallback_beam_energy',
                type_=float,
                required=True
            )
        )


def detector_distance(opened_event):
    '''
    Recover the distance of the detector from the sample location.

    Return the information from the header of the CBF file if the information
    is there, otherwise fall back to the value found in the configuration
    file

    Args:

        opened_event (dict): dictionary containing the opened event
            information.

    Returns:

        float: the distance between the detector and the sample in mm.
    '''

    try:
        # Try to read the data from the header of the CBF file.
        header_data_list = opened_event['cbf_obj'].header[
            u'_array_data.header_contents'
        ].split('\r\n')

        # If successful, return the value.
        return float(header_data_list[16].split()[2])
    except (AttributeError, IndexError, ValueError):
        # If the data cannot be found in the heaeder of the CBF file,
        # return the value provided in the configuration file.
        return float(
            opened_event['monitor_params'].get_param(
                section='General',
                parameter='fallback_detector_distance',
                type_=float,
                required=True
            )
        )


def filename_and_frame_index(opened_event):
    '''
    Recover the path to the data file and the index of the processed frame.

    Return the information from the opened event dictionary.

    Args:

        opened_event (dict): dictionary containing the opened event
            information.

    Returns:

        FilenameAndFrameIndex: a tuple FilenameAndFrameIndex contaning the
        file and frame data.
    '''

    # Recover the file path from the opened_event dictionary. Just return
    # 0 and the frame index.
    return FilenameAndFrameIndex(
        opened_event['filename'],
        0
    )
