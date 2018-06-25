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
Psana at the LCLS facility.

This module implements event handling functions, psana interface
initialization functions and data extraction functions used when
interacting with the psana framework at the LCLS facility.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import str  # pylint: disable=W0622

import numpy
import scipy.constants

import psana  # pylint: disable=E0401
from onda.data_retrieval_layer.components.event_sources import onda_psana


def _psana_offline_event_generator(psana_source,
                                   node_rank,
                                   mpi_pool_size):
    for run in psana_source.runs():
        times = run.times()
        size_for_this = int(
            numpy.ceil(len(times) / float(mpi_pool_size - 1))
        )
        events_for_this = times[
            (node_rank - 1) * size_for_this:node_rank * size_for_this
        ]
        for evt in events_for_this:
            yield run.event(evt)


#######################################
#                                     #
# LCLS-PSANA EVENT HANDLING FUNCTIONS #
#                                     #
#######################################

initialize_event_source = (  # pylint: disable=C0103
    onda_psana.initialize_event_source
)


event_generator = (  # pylint: disable=C0103
    onda_psana.event_generator
)


EventFilter = (  # pylint: disable=C0103
    onda_psana.EventFilter
)


open_event = (  # pylint: disable=C0103
    onda_psana.open_event
)


close_event = (  # pylint: disable=C0103
    onda_psana.close_event
)


get_num_frames_in_event = (  # pylint: disable=C0103
    onda_psana.get_num_frames_in_event
)


#################################################
#                                               #
# LCLS-PSANA INTERFACE INITIALIZATION FUNCTIONS #
#                                               #
#################################################

def detector_data_init(monitor_params,
                       data_extraction_func_name):  # pylint: disable=W0613
    """
    Initialize detector data recovery.

    Initialize the psana detector interface for the retrieval of
    x-ray detector data.

    Args:

        monitor_params (:obj:`onda.utils.parameters.MonitorParams`):
            a MonitorParams object containing the monitor parameters
            from the configuration file.

        data_extraction_func_name (str): the name of the data
          extraction function ("detector_data", "detector2_data",
          "detector3_data", etc.) that is associated with the current
          initialization.

    Returns:

        Detector: a handler (a psana Detector object) that can be used
        later to recover the data.
    """
    # Call the psana interface initialization function corresponding to
    # the data extraction func name.
    return psana.Detector(
        monitor_params.get_param(
            section='PsanaDataRecoveryLayer',
            parameter='{0}_detector_name'.format(data_extraction_func_name),
            type_=str,
            required=True
        ).encode('ascii')
    )


def timestamp_init(monitor_params):  # pylint: disable=W0613
    """
    Initialize timestamp data recovery.

    Initialize the psana detector interface for the retrieval of
    timestamp data.

    Args:

        monitor_params (:obj:`onda.utils.parameters.MonitorParams`):
            a MonitorParams object containing the monitor parameters
            from the configuration file.

    Returns:

        Detector: a handler (a psana Detector object) that can be used
        later to recover the data.
    """
    # The event timestamp gets recovered in other ways by the event
    # recovery code. No need to initialize the psana interface: the
    # timestamp will already be in the event dictionary when OnDA
    # starts extracting the data.
    return None


def detector_distance_init(monitor_params):
    """
    Initialize the detector distance data recovery.

    Initialize the psana Detector interface for the retrieval of
    detector distance data.

    Args:

        monitor_params (:obj:`onda.utils.parameters.MonitorParams`):
            a MonitorParams object containing the monitor parameters
            from the configuration file.

    Returns:

        Detector: a handler (a psana Detector object) that can be used
        later to recover the data.
    """
    return psana.Detector(
        monitor_params.get_param(
            section='PsanaDataRecoveryLayer',
            parameter='detector_dist_epics_name',
            type_=str,
            required=True
        ).encode('ascii')
    )


def beam_energy_init(monitor_params):  # pylint: disable=W0613
    """
    Initialize the beam energy data recovery.

    Initialize the psana detector interface for the retrieval of beam
    energy data.

    Args:

        monitor_params (:obj:`onda.utils.parameters.MonitorParams`):
            a MonitorParams object containing the monitor parameters
            from the configuration file.

    Returns:

        Detector: a handler (a psana Detector object) that can be used
        later to recover the data.
    """
    return psana.Detector('EBeam'.encode('ascii'))


def timetool_data_init(monitor_params):
    """
    Initialize the timetool data recovery.

    Initialize the psana detector interface for the retrieval of
    timetool data.

    Args:

         monitor_params (:obj:`onda.utils.parameters.MonitorParams`):
            a MonitorParams object containing the monitor parameters
            from the configuration file.

    Returns:

        Detector: a handler (a psana Detector object) that can be used
        later to recover the data.
    """
    return psana.Detector(
        monitor_params.get_param(
            section='PsanaDataRecoveryLayer',
            parameter='timetool_epics_name',
            type_=str,
            required=True
        ).encode('ascii')
    )


def digitizer_data_init(monitor_params,
                        data_extraction_func_name):
    """
    Initialize the first digitizer data recovery.

    Initialize the psana detector interface for the retrieval of data
    from a digitizer.

    Args:

        monitor_params (:obj:`onda.utils.parameters.MonitorParams`):
            a MonitorParams object containing the monitor parameters
            from the configuration file.

        data_extraction_func_name (str): the name of the data
            extraction function ("digitizer_data", "digitizer2_data",
            "digitizer3_data", etc.) that is associated with the
            current initialization.

    Returns:

        Detector: a handler (a psana Detector object) that can be used
        later to recover the data.
    """
    return psana.Detector(
        monitor_params.get_param(
            section='PsanaDataRecoveryLayer',
            parameter='{0}_digitizer_name'.format(data_extraction_func_name),
            type_=str,
            required=True
        ).encode('ascii')
    )


def opal_data_init(monitor_params):
    """
    Initialize the opal data recovery.

    Initialize the psana detector interface for the retrieval of data
    from an Opal camera.

    Args:

        monitor_params (:obj:`onda.utils.parameters.MonitorParams`):
            a MonitorParams object containing the monitor parameters
            from the configuration file.

    Returns:

        Detector: a handler (a psana Detector object) that can be used
        later to recover the data.
    """
    return psana.Detector(
        monitor_params.get_param(
            section='PsanaDataRecoveryLayer',
            parameter='opal_name',
            type_=str,
            required=True
        ).encode('ascii')
    )


def event_codes_init():
    """
    Intialize the EVR event data recovery.

    Initialize the psana detector interface for the retrieval of EVR
    event codes.

    Args:

         monitor_params (:obj:`onda.utils.parameters.MonitorParams`):
            a MonitorParams object containing the monitor parameters
            from the configuration file.

    Returns:

        Detector: a handler (a psana Detector object) that can be used
        later to recover the data.
    """
    return psana.Detector('evr0'.encode('ascii'))


########################################
#                                      #
# LCLS-PSANA DATA EXTRACTION FUNCTIONS #
#                                      #
########################################

def timestamp(event):
    """
    Recover the timestamp of the event.

    Return the timestamp of the event as provided by psana.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        timestamp: the time at which the event was collected.
    """
    # Return the timestamp stored in the event dictionary, without
    # extracting it again.
    return event['timestamp']


def detector_distance(event):
    """
    Recover the distance of the detector from the sample location.

    Return the detector distance information as provided by psana.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        float: the distance between the detector and the sample in m.
    """
    # Recover the detector distance. It is in mm, so divide it by
    # a thousand to convert it to SI (m).
    return event['psana_interface']['detector_distance']()/1000.0


def beam_energy(event):
    """
    Recover the energy of the beam.

    Return the beam energy information as provided by psana.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        float: the energy of the beam in J.
    """
    # Recover the detector distance. It is in eV, so multiply it by
    # e convert it to SI (J).
    return event['psana_interface']['beam_energy'].get(
        event['psana_event']
    ).ebeamPhotonEnergy() * scipy.constants.e


def timetool_data(event):
    """
    Recover the timetool timetool.

    Return the timetool information as provided by psana.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        float: the readout of the timetool instrument.
    """
    return event['psana_interface']['timetool_data']()


def digitizer_data(event,
                   data_extraction_func_name):
    """
    Recover the waveforms from a digitizer.

    Return the waveforms for a digitizer as provided by psana (All
    channels).

    Args:

        event (Dict): a dictionary with the event data.

        data_extraction_func_name (str): the name of the data
          extraction function ("digitizer_data", "digitizer2_data",
          "digitizer3_data", etc.) that is associated with this
          digitizer.

    Returns:

        psana object: a psana object storing the waveform data.
    """
    return event['psana_interface'][data_extraction_func_name].waveform(
        event['psana_event']
    )


def opal_data(event):
    """
    Recover an Opal camera data.

    Return an image collected by an Opal camera as provided by psana.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        ndarray: a 2d array containing the image from the Opal camera.
    """
    return event['psana_interface']['opal_data'].calib(
        event['psana_event']
    )


def event_codes(event):
    """
    Recover the EVR event codes.

    Return the EVR event codes as provided by psana.

    Args:

      event (Dict): a dictionary with the event data.

    Returns:

        List: a list containing the EVR event codes for a specific
        psana event.
    """
    return event['psana_interface']['event_codes'].eventCodes(
        event['psana_event']
    )
