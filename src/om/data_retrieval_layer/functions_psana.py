# This file is part of OM.
#
# OM is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# OM is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with OM.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2020 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Retrieval of of data from the psana framework.

This module contains functions that retrieve data from the psana framework.
"""
from __future__ import absolute_import, division, print_function

from typing import Any, Dict, cast

import numpy  # type: ignore

import psana  # type: ignore
from om.utils import exceptions, parameters


def detector_data_init(monitor_params):
    # type: (parameters.MonitorParams) -> Any
    """
    Initializes the psana Detector interface for x-ray detector data at LCLS.

    This function initializes the Detector interface for the detector identified by the
    'psana_detector_name' entry in the 'DataRetrievalLayer' configuration parameter
    group.

    Arguments:

        monitor_params (:class:`~om.utils.parameters.MonitorParams`): an object
            storing the OM monitor parameters from the configuration file.

    Returns:

        psana.Detector.AreaDetector.AreaDetector: a psana object that can be used later
        to retrieve the data.
    """
    return psana.Detector(
        monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="psana_detector_name",
            parameter_type=str,
            required=True,
        )
    )


def timestamp_init(monitor_params):
    # type: (parameters.MonitorParams) -> None
    """
    Initializes the psana Detector interface for timestamp data at LCLS.

    Arguments:

        monitor_params (:class:`~om.utils.parameters.MonitorParams`): an object
            storing the OM monitor parameters from the configuration file.
    """
    # The event timestamp gets recovered in other ways by the event recovery code. No
    # need to initialize the psana interface: the timestamp will already be in the
    # event dictionary when OM starts extracting the data.
    del monitor_params
    return None


def detector_distance_init(monitor_params):
    # type: (parameters.MonitorParams) -> Any
    """
    Initializes the psana Detector interface for detector distance data at LCLS.

    Detector distance information is recovered from an Epics controller at LCLS.
    This function initializes the Detector interface for the Epics controller
    identified by the 'psana_detector_distance_epics_name' entry in the
    'DataRetrievalLayer' configuration parameter group.

    Arguments:

        monitor_params (:class:`~om.utils.parameters.MonitorParams`): an object
            storing the OM monitor parameters from the configuration file.

    Returns:

        psana.Detector.EpicsDetector.EpicsDetector: a psana object that can be used
        later to retrieve the data.
    """
    return psana.Detector(
        monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="psana_detector_distance_epics_name",
            parameter_type=str,
            required=True,
        )
    )


def beam_energy_init(monitor_params):
    # type: (parameters.MonitorParams) -> Any
    """
    Initializes the psana Detector interface for beam energy data at LCLS.

    Arguments:

        monitor_params (:class:`~om.utils.parameters.MonitorParams`): an object
            storing the OM monitor parameters from the configuration file.

    Returns:

        psana.Detector.DdlDetector.DdlDetector: a psana object that can be used later
        to retrieve the data.
    """
    del monitor_params
    #psana.Detector("EBeam")
    return psana.Detector("SIOC:SYS0:ML00:AO541")


def timetool_data_init(monitor_params):
    # type: (parameters.MonitorParams) -> Any
    """
    Initializes the psana Detector interface for timetool data at LCLS.

    Timetool data is recovered from an Epics controller at LCLS. This function
    initializes the Detector interface for the Epics controller identified by the
    'psana_timetools_epics_name' entry in the 'DataRetrievalLayer' configuration
    parameter group.

    Arguments:

        monitor_params (:class:`~om.utils.parameters.MonitorParams`): an object
            storing the OM monitor parameters from the configuration file.

    Returns:

        psana.Detector.EpicsDetector.EpicsDetector: a psana object that can be used
        later to retrieve the data.
    """
    # TODO: Determine return type
    return psana.Detector(
        monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="psana_timetool_epics_name",
            parameter_type=str,
            required=True,
        )
    )


def digitizer_data_init(monitor_params):
    # type: (parameters.MonitorParams) -> Any
    """
    Initializes the psana Detector interface for digitizer data at LCLS.

    This function initializes the Detector interface for the digitizer identified by
    the 'psana_digitizer_name' entry in the 'DataRetrievalLayer' configuration
    parameter group.

    Arguments:

        monitor_params (:class:`~om.utils.parameters.MonitorParams`): an object
            storing the OM monitor parameters from the configuration file.

    Returns:

        psana.Detector.WFDetector.WFDetector: a psana object that can be used later to
        retrieve the data.
    """
    return psana.Detector(
        monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="psana_digitizer_name",
            parameter_type=str,
            required=True,
        )
    )


def opal_data_init(monitor_params):
    # type: (parameters.MonitorParams) -> Any
    """
    Initializes the psana Detector interface for Opal camera data at LCLS.

    This function initialize the Detector interface for the Opel camera identified by
    the 'psana_opal_name' entry in the 'DataRetrievalLayer' configuration parameter
    group.

    Arguments:

        monitor_params (:class:`~om.utils.parameters.MonitorParams`): an object
            storing the OM monitor parameters from the configuration file.

    Returns:

        psana.Detector.AreaDetector.AreaDetector: a psana object that can be used later
        to retrieve the data.
    """
    return psana.Detector(
        monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="psana_opal_name",
            parameter_type=str,
            required=True,
        )
    )


def optical_laser_active_init(monitor_params):
    # type: (parameters.MonitorParams) -> Any
    """
    Initializes the psana Detector interface for an optical laser at LCLS.

    The status of an optical laser is determined by monitoring an EVR event source at
    LCLS. This function initializes the Detector interface for the EVR event source
    identified by the 'psana_evr_source_name' entry of the 'DataRetrievalLayer'
    configuration parameter group.

    Arguments:

        monitor_params (:class:`~om.utils.parameters.MonitorParams`): an object
            storing the OM monitor parameters from the configuration file.

    Returns:

        psana.Detector.EvrDetector.EvrDetector: a psana object that can be used later
        to retrieve the data.
    """
    evr_source_name = monitor_params.get_param(
        group="data_retrieval_layer",
        parameter="psana_evr_source_name",
        parameter_type=str,
        required=True,
    )

    return psana.Detector(evr_source_name)


def xrays_active_init(monitor_params):
    # type: (parameters.MonitorParams) -> Any
    """
    Initializes the psana Detector interface for the x-ray beam status at LCLS.

    The status of the x-ray beam is determined by monitoring an EVR event source at
    LCLS. This function initializes the Detector interface for the EVR event source
    identified by the 'psana_evr_source_name' entry of the 'DataRetrievalLayer'
    configuration parameter group.

    Arguments:

        monitor_params (:class:`~om.utils.parameters.MonitorParams`): an object
            storing the OM monitor parameters from the configuration file.

    Returns:

        psana.Detector.EvrDetector.EvrDetector: a psana object that can be used later
        to retrieve the data.
    """
    evr_source_name = monitor_params.get_param(
        group="data_retrieval_layer",
        parameter="psana_evr_source_name",
        parameter_type=str,
        required=True,
    )

    return psana.Detector(evr_source_name)


def timestamp(event):
    # type: (Dict[str, Any]) -> numpy.float64
    """
    Gets the timestamp of an event retrieved from psana at LCLS.

    Arguments:

        event (Dict[str, Any]): a dictionary storing the event data.

    Returns:

        numpy.float64: the timestamp of the event in seconds from the Epoch.
    """
    # Returns the timestamp stored in the event dictionary, without extracting it
    # again.
    timest = event["additional_info"]["timestamp"]
    if timest is None:
        raise exceptions.OmDataExtractionError(
            "Could not retrieve timestamp information from psana."
        )

    return cast(numpy.float64, timest)


def detector_distance(event):
    # type: (Dict[str, Any]) -> float
    """
    Gets the detector distance for an event retrieved from psana at LCLS.

    Detector distance information is recovered from an Epics controller at LCLS . This
    function retrieves the information from the Epics controller identified by the
    'psana_detector_distance_epics_name' entry in the 'DataRetrievalLayer'
    configuration parameter group.

    Arguments:

        event (Dict[str, Any]): a dictionary storing the event data.

    Returns:

        float: the distance between the detector and the sample in mm.
    """
    det_dist = event["additional_info"]["psana_detector_interface"][
        "detector_distance"
    ]()
    if det_dist is None:
        raise exceptions.OmDataExtractionError(
            "Could not retrieve detector distance information from psana."
        )

    return cast(float, det_dist)


def beam_energy(event):
    # type: (Dict[str, Any]) -> float
    """
    Gets the beam energy for an event retrieved from psana at LCLS.

    Arguments:

        event (Dict[str, Any]): a dictionary storing the event data.

    Returns:

        float: the energy of the beam in eV.
    """
    #beam_en = (
    #    event["additional_info"]["psana_detector_interface"]["beam_energy"]
    #    .get(event["data"])
    #    .ebeamPhotonEnergy()
    #)
    beam_en = event["additional_info"]["psana_detector_interface"][
        "beam_energy"
    ]()
    if beam_en is None:
        raise exceptions.OmDataExtractionError(
            "Could not retrieve beam energy information from psana."
        )

    return cast(float, beam_en)


def timetool_data(event):
    # type: (Dict[str, Any]) -> float
    """
    Gets timetool data for an event retrieved from psana at LCLS.

    Timetool data is recovered from an Epics controller at LCLS. This function
    retrieves the data from the Epics controller identified by the
    'psana_timetools_epics_name' entry in the 'DataRetrievalLayer' configuration
    parameter group.

    Arguments:

            event (Dict[str, Any]): a dictionary storing the event data.

    Returns:

        float: the readout of the timetool instrument.
    """
    # TODO: Determine return type
    time_tl = event["additional_info"]["psana_detector_interface"]["timetool_data"]()
    if time_tl is None:
        raise exceptions.OmDataExtractionError(
            "Could not retrieve time tool data from psana."
        )

    return cast(float, time_tl)


def digitizer_data(event):
    # type: (Dict[str, Any]) -> numpy.ndarray
    """
    Get digitizer data for an event retrieved from psana at LCLS.

    This function retrieves data from the digitizer identified by the
    'psana_digitizer_name' entry in the 'DataRetrievalLayer' configuration parameter
    group.

    Arguments:

        event (Dict[str, Any]): a dictionary storing the event data.

    Returns:

        numpy.array: the waveform from the digitizer.
    """
    # TODO: Determine return type
    digit_data = event["additional_info"]["psana_detector_interface"][
        "digitizer_data"
    ].waveform(event["data"])
    if digit_data is None:
        raise exceptions.OmDataExtractionError(
            "Could not retrieve digitizer data from psana."
        )

    return cast(numpy.ndarray, digit_data)


def opal_data(event):
    # type: (Dict[str, Any]) -> numpy.ndarray
    """
    Gets Opal camera data for an event retrieved from psana at LCLS.

    This function retrieves data from the Opel camera identified by the
    'psana_opal_name' entry in the 'DataRetrievalLayer' configuration parameter group.

    Arguments:

        event (Dict[str, Any]): a dictionary storing the event data.

    Returns:

        numpy.ndarray: a 2D array containing the image from the Opal camera.
    """
    op_data = event["additional_info"]["psana_detector_interface"]["opal_data"].calib(
        event["data"]
    )
    if op_data is None:
        raise exceptions.OmDataExtractionError(
            "Could not retrieve Opel camera data from psana."
        )

    return cast(numpy.ndarray, op_data)


def optical_laser_active(event):
    # type: (Dict[str, Any]) -> bool
    """
    Gets the status of an optical laser for an event retrieved from psana at LCLS.

    The status of an optical laser is determined by monitoring an EVR event source at
    LCLS. This function determines the status of the optical laser by checking if
    the EVR source provides a specific event code for the current frame.

    * The name of the source must be specified in the 'psana_evr_source_name' entry of
      the 'DataRetrievalLayer' configuration parameter group.

    * The EVR event code that signals an active optical laser must be provided in
      the 'psana_evr_code_for_active_optical_laser' entry in the same parameter group.

    * If the source shows this EVR code for the current frame, the optical laser is
      considered active.

    Arguments:

        event (Dict[str, Any]): a dictionary storing the event data.

    Returns:

        bool: True if the optical laser is active for the current frame. False
        otherwise.
    """
    current_evr_codes = event["additional_info"]["psana_detector_interface"][
        "optical_laser_active"
    ].psana_detector_handle.eventCodes(event["data"])
    if current_evr_codes is None:
        raise exceptions.OmDataExtractionError(
            "Could not retrieve event codes from psana."
        )

    return (
        event["additional_info"]["psana_detector_interface"][
            "optical_laser_active"
        ].active_laser_evr_code
        in current_evr_codes
    )


def xrays_active(event):
    # type: (Dict[str, Any]) -> bool
    """
    Initializes the psana Detector interface for the x-ray beam status at LCLS.

    The status of an optical laser is determined by monitoring an EVR event source at
    LCLS. This function determines the status of the x-ray beam by checking if the EVR
    source provides a specific event code for the current frame.

    * The name of the source must be specified in the 'psana_evr_source_name' entry of
      the 'DataRetrievalLayer' configuration parameter group.

    * The EVR event code that signals an active x-ray beam must be provided in the
      'psana_evr_code_for_active_xray_beam" entry in the same parameter group.

    * If the source shows this EVR code for the current frame, the x-ray beam is
      considered active.

    Arguments:

        event (Dict[str, Any]): a dictionary storing the event data.

    Returns:

        bool: True if the x-ray beam is active for the current frame. False otherwise.
    """
    current_evr_codes = event["additional_info"]["psana_detector_interface"][
        "xrays_active"
    ].psana_detector_handle.eventCodes(event["data"])
    if current_evr_codes is None:
        raise exceptions.OmDataExtractionError(
            "Could not retrieve event codes from psana."
        )

    return (
        event["additional_info"]["psana_detector_interface"][
            "xrays_active"
        ].active_laser_evr_code
        in current_evr_codes
    )
