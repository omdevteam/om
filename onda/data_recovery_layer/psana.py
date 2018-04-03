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
Functions and classes to recover and process data from HiDRA.

Exports:

    Functions:

        initialize_event_source: connect to the event source and
            configure it.

        event_generator: event recovery from HiDRA.

    Classes:

        EventFilter (class): filter and reject events.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import collections
import psana
import os.path
import socket
import sys
from builtins import str  # pylint: disable=W0622

from future.utils import raise_from

from onda.data_recovery_layer import hidra_api
from onda.utils import dynamic_import, exceptions




def initialize_event_source(source,  # pylint: disable=W0613
                            node_rank,  # pylint: disable=W0613
                            mpi_pool_size,  # pylint: disable=W0613
                            monitor_params):  # pylint: disable=W0613
    """
    Initialize event generator.

    Connect to the event generator and configure it. Psana does not
    need to be configured, so do nothing.

    Args:

        source (str): the IP or hostname of the machine where hidra is
            running.

        node_rank (int): rank of the node where the function is called

        mpi_pool_size (int): size of the node pool that includes the
            node where the function is called.

        monitor_params (MonitorParams): a MonitorParams object
            containing the monitor parameters from the
            configuration file.
    """
    pass


def event_generator(source,
                    node_rank,
                    mpi_pool_size,  # pylint: disable=W0613
                    monitor_params):
    """
    Initialize psana event recovery.

    Initialize the connection with Psana. Return an iterator which will
    recover an event from psana at each step (This function is a
    python generator).

    Args:

        source (str): the IP or hostname of the machine where hidra is
            running.

        node_rank (int): rank of the node where the function is called

        mpi_pool_size (int): size of the node pool that includes the
            node where the function is called.

        monitor_params (MonitorParams): a MonitorParams object
            containing the monitor parameters from the
            configuration file.

     Yields:

        Dict: A dictionary containing the data and the metadata of an
        event recovered from Psana (usually corresponding to a frame).
    """
    if 'shmem' in source:
        offline=False
    else:
        offline=True

    # If the psana calibration directory is provided in the
    # configuration file, add it as an option to psana.
    psana_calib_dir = monitor_params.get_param(
        section='PsanaDataRecoveryLayer',
        parameter='psana_calibration_directory',
        type_=str
    )
    if psana_calib_dir:
        psana.setOption(
            'psana.calib-dir'.encode('ascii'),
            psana_calib_dir.encode('ascii')
        )

    # Automatically add 'idx' to the source string for offline data,
    # if it is not already there.
    if offline and not self._source[-4:] == ':idx':
        source += ':idx'
    
    # Set the psana data source.
    psana_source = psana.DataSource(source.encode('ascii'))
    
    # Recover the psana detector interface initialization functions.
    psana_interface_funcs = dynamic_import.init_psana_interface_funcs(
        monitor_params
    )
    
    # Call all the required psana interface functions and store the
    # returned handlers in a dictionary.
    psana_interface_funcs = {}
    for func_name in psana_interface_funcs:
        psana_interface[func_name] = getattr(
            object=psana_interface_funcs,
            name=func_name
        )(monitor_params)

    # SImply recover the event iterator from the psana DataSource
    # object if running online. Otherwise, split the events
    # based on the number of workers and have each worker iterate
    # only on the events assigned to him.
    if offline:
        def psana_events_generator():
        for r in psana_source.runs():
            times = r.times()
            mylength = int(ceil(len(times) / float(mpi_pool_size - 1)))
            mytimes = times[(node_rank - 1) * mylength:node_rank * mylength]
            for mt in mytimes:
                yield r.event(mt)
    else:
        psana_events = psana_source.events()
    
    for psana_event in psana_events
        # Recover the psana?event from psana. Create the event
        # dictionary and store the psana_event there, together with
        # the psana interface functions. Then yield the event.
        event = {
            'psana_interface_funcs': psana_interface_funcs,
            'psana_event': psana_event
        }
        yield event


class EventFilter(object):
    """
    Filter events.

    Reject files whose 'age' (the time between the data collection and
    the moment OnDA receives the data) is higher than a predefined
    threshold.
    """
    def __init__(self,
                 monitor_params):
        """
        Initialize the EventFilter class.

        Args:

        monitor_params (MonitorParams): a MonitorParams object
            containing the monitor parameters from the
            configuration file.
        """
        # Read the maximum 'age' threshold from the configuration file
        # and store it in an attribute.
        rejection_threshold = monitor_params.get_param(
            section='PsanaDataRecoveryLayer',
            parameter='event_rejection_threshold'
            type_=float
        )
        if rejection_threshold:
            self._event_rejection_threshold = rejection_threshold
            
            
    def should_reject(self,
                      event):
        """
        Decide on event rejection.

        Decide if the event should be rejected based on its 'age' (
        the time between data collection and the moment OnDA gets
        the event.

        Args:

            event (Dict): a dictionary with the event data.

        Returns:

            bool: True if the event should be rejected. False if the
            event should be processed.
        """
        # Recover the timestamp from the sana event
        timestamp_epoch_format = event['psana_event'].get(
            psana.EventId
        ).time()
        
        timestamp = float64(
            str(timestamp_epoch_format[0]) + '.' +
            str(timestamp_epoch_format[1])
        )
        
        time_now = float64(time.time())
        if (time_now - timestamp) > self._event_rejection_threshold:
            # Store the timestamp in the event dictionary so it does
            # have to be extracted again if the user requests it.
            event['timestamp'] = timestamp
            return True
        else:
            return False


############################################
#                                          #
# PSANA INTERFACE INITIALIZATION FUNCTIONS #
#                                          #
############################################

def detector_data_init(monitor_params):  # pylint: disable=W0613
    """
    Initialize detector data recovery.

    Initialize the psana Detector interface for the data from the
    x-ray detector.

    Args:

        monitor_params (MonitorParams): a MonitorParams object
            containing the monitor parameters from the
            configuration file.
    """
    return psana.Detector(
        monitor_params.get_param(
            section='PsanaDataRecoveryLayer',
            parameter='detector_name',
            type_=str,
            required=True
        ).encode('ascii')
    )


def timestamp_init(monitor_params):
    """
    Initialize timestamp data recovery.

    Initialize the psana Detector interface for the timestamp data.

    Args:

        monitor_params (MonitorParams): a MonitorParams object
            containing the monitor parameters from the
            configuration file.
    """
    return None


def detector_distance_init(monitor_params):
    """
    Initialize the detector distance data recovery.

    Initialize the psana Detector interface for the detector distance
    data.

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

    Initialize the psana Detector interface for the beam energy data.
    
    Args:

        monitor_params (MonitorParams): a MonitorParams object
            containing the monitor parameters from the
            configuration file.
    """
    return psana.Detector('EBeam'.encode('ascii'))


def timetool_data_init(monitor_params):
    """
    Initialize the timetool data recovery.

    Initialize the psana Detector interface for the timetool data.

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

def digitizer_data_init(monitor_params):
    """
    Initialize the first digitizer data recovery.

    Initialize the psana Detector interface for the data from the
    first digitizer.

    Args:

        monitor_params (MonitorParams): a MonitorParams object
            containing the monitor parameters from the
            configuration file.
    """
    return psana.Detector(
        monitor_params.get_param(
            section='PsanaDataRecoveryLayer',
            parameter='digitizer_name',
            type_=str,
            required=True
        ).encode('ascii')
    )


def digitizer2_data_init(monitor_params):
    """
    Initialize the second digitizer data recovery.

    Initialize the psana Detector interface for the data from the
    second digitizer.

    Args:

        monitor_params (MonitorParams): a MonitorParams object
            containing the monitor parameters from the
            configuration file.
    """
    return psana.Detector(
        monitor_params.get_param(
            section='PsanaDataRecoveryLayer',
            parameter='digitizer2_name',
            type_=str,
            required=True
        ).encode('ascii')
    )


def digitizer3_data_init(monitor_params):
    """
    Initialize the second digitizer data recovery.

    Initialize the psana Detector interface for the data from the
    third digitizer.

    Args:

        monitor_params (MonitorParams): a MonitorParams object
            containing the monitor parameters from the
            configuration file.
    """
    return psana.Detector(
        monitor_params.get_param(
            section='PsanaDataRecoveryLayer',
            parameter='digitizer3_name',
            type_=str,
            required=True
        ).encode('ascii')
    )


def digitizer4_data_init(monitor_params):
    """
    Initialize the second digitizer data recovery.

    Initialize the psana Detector interface for the data from the
    fourth digitizer.

    Args:

        monitor_params (MonitorParams): a MonitorParams object
            containing the monitor parameters from the
            configuration file.
    """
    return psana.Detector(
        monitor_params.get_param(
            section='PsanaDataRecoveryLayer',
            parameter='digitizer4_name',
            type_=str,
            required=True
        ).encode('ascii')
    )


def opal_data_init(monitor_params):
    """
    Initialize the opal data recovery.

    Initialize the psana Detector interface for the data from the
    Opal camera.

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
    
    Initialize the psana Detector interface for EVR event codes.

    Args:

        monitor_params (MonitorParams): a MonitorParams object
            containing the monitor parameters from the
            configuration file.
    """
    return psana.Detector('evr0'.encode('ascii'))


###################################
#                                 #
# PSANA DATA EXTRACTION FUNCTIONS #
#                                 #
###################################


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
    
    
def _detector_distance(event):
     """
    Recover the distance of the detector from the sample location.

    Return the detector distance information (as provided by psana).

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        float: the distance between the detector and the sample in mm.
    """
    return event['psana_interface_funcs']['detector_distance']()

    
def _beam_energy(event):
    """
    Recover the energy of the beam.

    Return the beam energy information (as provided by psana).

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        float: the energy of the beam in eV.
    """
    return event['psana_interface_funcs']['beam_energy'].get(
        event['psana_event']
    ).ebeamPhotonEnergy()


def timetool_data(event):
    """
    Recover the time delay between the trigger and the pulse.

    Return the timetool information provided by psana.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        float: the energy of the beam in eV.
    """
    return event['psana_interface_funcs']['timetool_data']()


def digitizer_data(event):
    """
    Recover the waveform from the first digitizer.

    Return the waveforms for the first digitizer as provided by
    psana (All channels).

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        psana object: a psana object storing the waveform data.
    """
    return event['psana_interface_funcs']['digitizer_data'].waveform(
        event['psana_event']
    )


def digitizer2_data(event):
    """
    Recover the waveform from the second digitizer.

    Return the waveforms for the second digitizer as provided by
    psana (All channels).

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        psana object: a psana object storing the waveform data.
    """
    return event['psana_interface_funcs']['digitizer2_data'].waveform(
        event['psana_event']
    )


def digitizer3_data(event):
    """
    Recover the waveform from the third digitizer.

    Return the waveforms for the third digitizer as provided by
    psana (All channels).

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        psana object: a psana object storing the waveform data.
    """
    return event['psana_interface_funcs']['digitizer3_data'].waveform(
        event['psana_event']
    )


def digitizer4_data(event):
    """
    Recover the waveform from the fourth digitizer.

    Return the waveforms for the fourth digitizer as provided by
    psana (All channels).

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        psana object: a psana object storing the waveform data.
    """
    return event['psana_interface_funcs']['digitize4_data'].waveform(
        event['psana_event']
    )
    
    
def opal_data(event):
    """
    Recover the Opal camera data.

    Return the image collected by the Opal camera, as provided by
    psana.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        ndarray: a 2d array containing the image from the Opal camera.
    """
    return event['psana_interface_funcs']['opal_data'].calib(
        event['psana_event']
    )


def _event_codes_dataext(event):
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
    return return event['psana_interface_funcs']['event_codes'].eventCodes(
        event['psana_event']
    )


