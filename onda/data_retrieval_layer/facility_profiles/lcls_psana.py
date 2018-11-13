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
#
#    Copyright 2014-2018 Deutsches Elektronen-Synchrotron DESY,
#    a research centre of the Helmholtz Association.
"""
Event and data retrieval from psana at LCLS.

Non detector-specific functions and classes used for event and data
retrieval from psana at the LCLS facility.
"""
from __future__ import absolute_import, division, print_function

import scipy.constants
from future.utils import raise_from

from onda.data_retrieval_layer.event_sources import psana_source
from onda.data_retrieval_layer.filters import event_filters, frame_filters
from onda.utils import exceptions, named_tuples

try:
    import psana  # pylint: disable=import-error
except ImportError:
    raise_from(
        exc=exceptions.MissingDependency(
            "The lcls_psana module could not be loaded. The following "
            "dependency does not appear to be available on the system: psana."
        ),
        cause=None
    )


############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################


initialize_event_source = (  # pylint: disable=invalid-name
    psana_source.initialize_event_source
)


event_generator = (  # pylint: disable=invalid-name
    psana_source.event_generator
)


open_event = (  # pylint: disable=invalid-name
    psana_source.open_event
)


close_event = (  # pylint: disable=invalid-name
    psana_source.close_event
)


get_num_frames_in_event = (  # pylint: disable=invalid-name
    psana_source.get_num_frames_in_event
)


EventFilter = (  # pylint: disable=invalid-name
    event_filters.AgeEventFilter
)


FrameFilter = (  # pylint: disable=invalid-name
    frame_filters.NullFrameFilter
)


#####################################################
#                                                   #
# PSANA DETECTOR INTERFACE INITIALIZATION FUNCTIONS #
#                                                   #
#####################################################


def detector_data_init(
        monitor_params,
        data_extraction_func_name
):
    """
    Initializes the psana detector interface for x-ray detector data.

    Args:

        monitor_params (MonitorParams): a
            :obj:`~onda.utils.parameters.MonitorParams` object
            containing the monitor parameters from the
            configuration file.

        data_extraction_func_name: specific name of the data extraction
            function with which this generic initialization function
            should be associated (e.g: 'detector_data',
            'detector2_data'. 'detector3_data', etc.). This is required
            to resuse this initialization function with multiple
            detectors. The `functools.partial` python function is used
            to create 'personalized' versions of this function for each
            detector, by fixing this argument.

    Returns:

        Detector: a handle (a psana Detector object) that can be used
        later to retrieve the data.
    """
    # Calls the psana interface initialization function corresponding
    # to the data extraction func name.
    return psana.Detector(
        monitor_params.get_param(
            section='DataRetrievalLayer',
            parameter='{0}_detector_name'.format(data_extraction_func_name),
            type_=str,
            required=True
        )
    )


def timestamp_init(monitor_params):
    """
    Initializes the psana detector interface for timestamp data.

    Args:

        monitor_params (MonitorParams): a
            :obj:`~onda.utils.parameters.MonitorParams` object
            containing the monitor parameters from the configuration
            file.

    Returns:

        Detector: a handle (a psana Detector object) that can be used
        later to retrieve the data.
    """
    # The event timestamp gets recovered in other ways by the event
    # recovery code. No need to initialize the psana interface: the
    # timestamp will already be in the event dictionary when OnDA
    # starts extracting the data.
    del monitor_params
    return None


def detector_distance_init(monitor_params):
    """
    Initializes the psana detector interface for detector dist. data.

    Args:

        monitor_params (MonitorParams): a
            :obj:`~onda.utils.parameters.MonitorParams` object
            containing the monitor parameters from the configuration
            file.

    Returns:

        Detector: a handle (a psana Detector object) that can be used
        later to retrieve the data.
    """
    return psana.Detector(
        monitor_params.get_param(
            section='DataRetrievalLayer',
            parameter='detector_distance_epics_name',
            type_=str,
            required=True
        )
    )


def beam_energy_init(monitor_params):
    """
    Initializes the psana detector interface for beam energy data.

    Args:

        monitor_params (MonitorParams): a
            :obj:`~onda.utils.parameters.MonitorParams` object
            containing the monitor parameters from the configuration
            file.

    Returns:

        Detector: a handle (a psana Detector object) that can be used
        later to retrieve the data.
    """
    del monitor_params
    return psana.Detector('EBeam')


def timetool_data_init(monitor_params):
    """
    Initializes the psana detector interface for data from a timetool.

    Args:

        monitor_params (MonitorParams): a
            :obj:`~onda.utils.parameters.MonitorParams` object
            containing the monitor parameters from the configuration
            file.

    Returns:

        Detector: a handle (a psana Detector object) that can be used
        later to retrieve the data.
    """
    return psana.Detector(
        monitor_params.get_param(
            section='DataRetrievalLayer',
            parameter='timetool_epics_name',
            type_=str,
            required=True
        )
    )


def digitizer_data_init(
        monitor_params,
        data_extraction_func_name
):
    """
    Initialize the psana detector interface for data from a digitizer.

    Args:

        monitor_params (MonitorParams): a
            :obj:`~onda.utils.parameters.MonitorParams` object
            containing the monitor parameters from the configuration
            file.

        data_extraction_func_name: specific name of the data extraction
            function with which this generic initialization function
            should be associated (e.g: 'digitizer_data',
            'digitizer2_data'. 'digitizer3_data', etc.). This is
            required to resuse this initialization function with
            multiple digitizers. The `functools.partial` python
            function is used to create 'personalized' versions of this
            function for each digitizer, by fixing this argument.

    Returns:

        Detector: a handle (a psana Detector object) that can be used
        later to retrieve the data.
    """
    return psana.Detector(
        monitor_params.get_param(
            section='DataRetrievalLayer',
            parameter='{0}_digitizer_name'.format(data_extraction_func_name),
            type_=str,
            required=True
        )
    )


def opal_data_init(monitor_params):
    """
    Initializes the psana detector interface for Opal camera data.

    Args:

        monitor_params (MonitorParams): a
            :obj:`~onda.utils.parameters.MonitorParams` object
            containing the monitor parameters from the configuration
            file.

    Returns:

        Detector: a handle (a psana Detector object) that can be used
        later to retrieve the data.
    """
    return psana.Detector(
        monitor_params.get_param(
            section='DataRetrievalLayer',
            parameter='opal_name',
            type_=str,
            required=True
        )
    )


def optical_laser_active_init(monitor_params):
    """
    Initializes the psana detector interface for the status of the
    optical laser.

    Args:

        monitor_params (MonitorParams): a
            :obj:`~onda.utils.parameters.MonitorParams` object
            containing the monitor parameters from the configuration
            file.

    Returns:

        Tuple[psana.Detector, evr_codes]: a tuple where the first
        entry is a psana Detector interface object, while the second
        is a list of EVR codes corresponding to the optical laser
        being active. Both can be used later to retrieve the data.
    """
    active_laser_evr_code = monitor_params.get_param(
        section='DataRetrievalLayer',
        parameter='evr_code_for_active_optical_laser',
        type_=int,
        required=True
    )

    evr_source_name = monitor_params.get_param(
        section='DataRetrievalLayer',
        parameter='evr_source_name',
        type_=str,
        required=True
    )

    return named_tuples.OpticalLaserStateDataRetrievalInfo(
        psana_detector_handle=psana.Detector(evr_source_name),
        active_laser_evr_code=active_laser_evr_code
    )


#############################
#                           #
# DATA EXTRACTION FUNCTIONS #
#                           #
#############################

def timestamp(event):
    """
    Retrieves the timestamp of the psana event.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        timestamp: the time at which the event was collected.
    """
    # Returns the timestamp stored in the event dictionary, without
    # extracting it again.
    return event['timestamp']


def detector_distance(event):
    """
    Retrieves the distance of the detector from the sample location.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        float: the distance between the detector and the sample in m.
    """
    # Recovers the detector distance from psana. It is in mm, so we
    # must divide it by 10000 to convert it to SI (m).
    return event['psana_detector_interface']['detector_distance']() / 1000.0


def beam_energy(event):
    """
    Retrieves the beam energy.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        float: the energy of the beam in J.
    """
    # Recovers the detector distance from psana. It is in eV, so we
    # must multiply it by e convert it to SI (J).
    return event['psana_detector_interface']['beam_energy'].get(
        event['psana_event']
    ).ebeamPhotonEnergy() * scipy.constants.e


def timetool_data(event):
    """
    Retrieves the data from a timetool.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        float: the readout of the timetool instrument.
    """
    return event['psana_detector_interface']['timetool_data']()


def digitizer_data(
        event,
        data_extraction_func_name
):
    """
    Retrieves the waveforms from a digitizer (All channels).

    Args:

        event (Dict): a dictionary with the event data.

        data_extraction_func_name (str): the name of the data
          extraction function ("digitizer_data", "digitizer2_data",
          "digitizer3_data", etc.) that is associated with this
          digitizer.

    Returns:

        psana object: a psana object storing the waveform data.
    """
    return (
        event[
            'psana_detector_interface'
        ][
            data_extraction_func_name
        ].waveform(event['psana_event'])
    )


def opal_data(event):
    """
    Retrieves data from an Opal camera.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        ndarray: a 2D array containing the image from the Opal
        camera.
    """
    return event['psana_detector_interface']['opal_data'].calib(
        event['psana_event']
    )


def optical_laser_active(event):
    """
    Retrieves the optical laser status.

    Returns whether the optical laser is active or not.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        bool: True if the optical laser is active. False otherwise.
    """
    current_evr_codes = (
        event[
            'psana_detector_interface'
        ][
            'optical_laser_active'
        ].psana_detector_handle.eventCodes(event['psana_event'])
    )

    return (
        event[
            'psana_detector_interface'
        ][
            'optical_laser_active'
        ].active_laser_evr_code in current_evr_codes
    )
