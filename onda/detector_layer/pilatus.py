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


def get_file_extensions():
    '''
    Return allowed file extensions.

    Returns:

        tuple: a tuple containing the list of allowed file extensions.
    '''

    # Return a tuple with the list of allowed extensions.
    return ('.cbf',)


def get_peakfinder8_detector_info():
    '''
    Return peakfinder8 detector info.

    Returns:

        tuple: A tuple where the four fields (named respectively 'asics_nx',
        'asics_ny', 'nasics_x', and 'nasics_y)'are the four parameters used by
        the peakfinder8 algorithm to describe the format of the input data.
    '''

    # A namedtuple used for peakfinder8-related detector information.
    Peakfinder8DetInfo = collections.namedtuple(  # pylint: disable-msg=C0103
        typename='Peakfinder8DetectorInfo',
        field_names=['asics_nx', 'asics_ny', 'nasics_x', 'nasics_y']
    )

    return Peakfinder8DetInfo(2463, 2527, 1, 1)


def open_event_filelist(event):
    '''
    Open event.

    Store the content of the cbf file as a fabio module cbf_obj object
    in the 'data' entry of the event dictionary.

    Args:

        event (dict): a dictionary with the event data.

    '''

    # Open the file and recover the fabio cbf_obj object,
    # then store it into the 'data' entry of the event dictionary.
    event['data'] = fabio.open(event['metadata']['full_path'])


def close_event_filelist(_):
    '''
    Close event.

    Do nothing. There is no need to close a fabio cbf_obj object.

    '''

    pass


def num_frames_in_event_filelist(_):
    '''
    The number of frames in the file.

    Cbf files usually store 1 frame per file.
    '''

    # Just return 1.
    return 1


def raw_data_filelist(event):
    '''
    Recover raw detector data for one frame.

    Extract raw detector data from the fabio cbf_obj object contained in
    the input dictionary.

    Args:

        event (dict): a dictionary with the event data.

    Returns:

        ndarray: the raw detector data.
    '''

    # Extract and return the detector data.
    return event['data'].data


def timestamp_filelist(event):
    '''
    Recover the timestamp of the event.

    Extract the timestamp event from the input dictionary.

    Args:

        event (dict): a dictionary with the event data.

    Returns:

        timestamp: the creation time of the file containing the detector data.
    '''

    # Return the creation time of the file.
    return os.stat(event['metadata']['full_path']).st_crtime


def beam_energy_filelist(event):
    '''
    Recover the energy of the beam.

    Return the information from the header of the CBF file if the information
    is there, otherwise fall back to the value found in the configuration
    file

    Args:

        event (dict): a dictionary with the event data.

    Returns:

        float: the energy of the beam in eV.
    '''

    try:
        # Try to read the data from the header of the CBF file.
        header_data_list = event['data']['cbf_obj'].header[
            u'_array_data.header_contents'
        ].split('\r\n')
        wavelength = float(header_data_list[15].split()[2])

        # If successful, convert to eV and return.
        return float(h * c / (wavelength * electron_volt))
    except (AttributeError, IndexError, ValueError):
        # If the data cannot be found in the heaeder of the CBF file,
        # return the value provided in the configuration file.
        return float(
            event['monitor_params'].get_param(
                section='General',
                parameter='fallback_beam_energy',
                type_=float,
                required=True
            )
        )


def detector_distance_filelist(event):
    '''
    Recover the distance of the detector from the sample location.

    Return the information from the header of the CBF file if the information
    is there, otherwise fall back to the value found in the configuration
    file

    Args:

        event (dict): a dictionary with the event data.

    Returns:

        float: the distance between the detector and the sample in mm.
    '''

    try:
        # Try to read the data from the header of the CBF file.
        header_data_list = event['data']['cbf_obj'].header[
            u'_array_data.header_contents'
        ].split('\r\n')

        # If successful, return the value.
        return float(header_data_list[16].split()[2])
    except (AttributeError, IndexError, ValueError):
        # If the data cannot be found in the heaeder of the CBF file,
        # return the value provided in the configuration file.
        return float(
            event['monitor_params'].get_param(
                section='General',
                parameter='fallback_detector_distance',
                type_=float,
                required=True
            )
        )


def filename_and_frame_index_filelist(event):
    '''
    Recover the path to the data file and the index of the processed frame.

    Return the information from the opened event dictionary.

    Args:

        event (dict): dictionary containing the opened event
            information.

    Returns:

        tuple: a tuple where the first field ('filename') is the full path
        to the data file, and the second ('frame_index') is index of the
        processed frame.
    '''

    # A namedtuple used to store filename and index information.
    FnameAndFrameIndex = collections.namedtuple(  # pylint: disable-msg=C0103
        typename='FilenameAndFrameIndex',
        field_names=['filename', 'frame_index']
    )

    # Recover the file path from the opened_event dictionary. Just return
    # 0 and the frame index.
    return FnameAndFrameIndex(event['metadata']['full_path'], 0)



def detector_data_hidra():

    dsadassdsa


detector_data_filelist = detector_data_hidra
