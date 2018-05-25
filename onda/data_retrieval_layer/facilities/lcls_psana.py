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
Utilities to retrieve data from psana at the LCLS facility.

Exports:

    Functions:

        initialize_event_source: connect to the event source and
            configure it.

        event_generator: event recovery from HiDRA.

        open_event: open an event.

        close_event: close an event.

        get_num_frames_in_event: get number of frames in an event.

        detector_data_init: initialize psana interface for the
            retrieval of detector data.

        timestamp_init: initialize psana interface for the retrieval of
            timestamp information.

        detector_distance_init: initialize psana interface for the
            retrieval of detector distance information.

        beam_energy_init: initialize psana interface for the retrieval
            of beam energy information.

        timetool_data_init: initialize psana interface for the
            retrieval of timetool information.

        digitizer_data_init: initialize psana interface for the
            retrieval of digitizer data.

        opal_data_init: initialize psana interface for the
            retrieval of opal camera data.

        event_codes_init: initialize psana interface for the
            retrieval of EVR event code information.

        timestamp: recover the timestamp information of the event.

        detector_distance: recover the distance between the sample
            and the detector for the current event.

        beam_energy: recover the beam energy during the current event.

        timetool_data: recover the timetool data for the current event.

        digitizer_data: recover digitizer data for the current event.

        opal_data: recover opal camera data for the current event.

        event_codes: recover EVR event codes for the current event.

    Classes:

        EventFilter (class): filter and reject events.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import str  # pylint: disable=W0622

import numpy

import psana  # pylint: disable=E0401
from onda.data_retrieval_layer.facilities.frameworks import psana as onda_psana


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

    Initialize the psana Detector interface for the retrieval of
    x-ray detector data.

    Args:

        monitor_params (MonitorParams): a MonitorParams object
            containing the monitor parameters from the
            configuration file.

        data_extraction_func_name (str): the name of the data
          extraction function ("detector_data", "detector2_data",
          "detector3_data", etc.) that is associated with the current
          initialization.
    """
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

    Initialize the psana Detector interface for the retrieval of
    timestamp data.

    Args:

        monitor_params (MonitorParams): a MonitorParams object
            containing the monitor parameters from the
            configuration file.
    """
    return None


def detector_distance_init(monitor_params):
    """
    Initialize the detector distance data recovery.

    Initialize the psana Detector interface for the retrieval of
    detector distance data.

    Args:

        monitor_params (MonitorParams): a MonitorParams object
            containing the monitor parameters from the
            configuration file.
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

    Initialize the psana Detector interface for the retrieval of beam
    energy data.

    Args:

        monitor_params (MonitorParams): a MonitorParams object
            containing the monitor parameters from the
            configuration file.
    """
    return psana.Detector('EBeam'.encode('ascii'))


def timetool_data_init(monitor_params):
    """
    Initialize the timetool data recovery.

    Initialize the psana Detector interface for the retrieval of
    timetool data.

    Args:

        monitor_params (MonitorParams): a MonitorParams object
            containing the monitor parameters from the
            configuration file.
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

    Initialize the psana Detector interface for the retrieval of data
    from a digitizer.

    Args:

        monitor_params (MonitorParams): a MonitorParams object
            containing the monitor parameters from the
            configuration file.

        data_extraction_func_name (str): the name of the data
            extraction function ("digitizer_data", "digitizer2_data",
            "digitizer3_data", etc.) that is associated with the
            current initialization.
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

    Initialize the psana Detector interface for the retrieval of data
    from an Opal camera.

    Args:

        monitor_params (MonitorParams): a MonitorParams object
            containing the monitor parameters from the
            configuration file.
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

    Initialize the psana Detector interface for the retrieval of EVR
    event codes.

    Args:

        monitor_params (MonitorParams): a MonitorParams object
            containing the monitor parameters from the
            configuration file.
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

    Return the timestamp of the event (return the event timestamp from
    the event dictionary).

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        timestamp: the time at which the event was collected.
    """
    return event['timestamp']


def detector_distance(event):
    """
    Recover the distance of the detector from the sample location.

    Return the detector distance information (as provided by psana).

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        float: the distance between the detector and the sample in mm.
    """
    return event['psana_interface']['detector_distance']()


def beam_energy(event):
    """
    Recover the energy of the beam.

    Return the beam energy information (as provided by psana).

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        float: the energy of the beam in eV.
    """
    return event['psana_interface']['beam_energy'].get(
        event['psana_event']
    ).ebeamPhotonEnergy()


def timetool_data(event):
    """
    Recover the time delay between a trigger and the x-ray pulse.

    Return the timetool information provided by psana.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        float: the energy of the beam in eV.
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

    Return an image collected by an Opal camera, as provided by
    psana.

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

        monitor_params (MonitorParams): a MonitorParams object
            containing the monitor parameters from the
            configuration file.

    Returns:

        List: a list containing the EVR event codes for a specific
        psana event.
    """
    return event['psana_interface']['event_codes'].eventCodes(
        event['psana_event']
    )
