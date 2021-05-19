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
# Copyright 2020 -2021 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Retrieval of data from the psana framework.

This module contains functions that retrieve data from the psana software framework
(used at the LCLS facility) using the psana Detector interface. It also contains
functions that initialize the Detector interface itself.
"""
from typing import Any, Dict, List, Union, cast

import numpy  # type: ignore
from om.utils import exceptions, parameters

try:
    import psana  # type: ignore
except ImportError:
    raise exceptions.OmMissingDependencyError(
        "The following required module cannot be imported: psana"
    )


def detector_data_init(monitor_parameters: parameters.MonitorParams) -> Any:
    """
    Initializes the psana Detector interface for x-ray detector data at LCLS.

    This function initializes the Detector interface for the detector identified by the
    'psana_detector_name' entry in the 'data_retrieval_layer' parameter group of the
    configuration file.

    Arguments:

        monitor_parameters: A [MonitorParams]
            [om.utils.parameters.MonitorParams] object storing the OM monitor
            parameters from the configuration file.

    Returns:

        A psana object that can be used later to retrieve the data.
    """
    return psana.Detector(
        monitor_parameters.get_param(
            group="data_retrieval_layer",
            parameter="psana_detector_name",
            parameter_type=str,
            required=True,
        )
    )


def timestamp_init(monitor_parameters: parameters.MonitorParams) -> None:
    """
    Initializes the psana Detector interface for timestamp data at LCLS.

    This function initializes the timestamp Detector interface, preparing it to
    retrieve timing information provided by the LCLS timing system.

    Arguments:

        monitor_parameters: A [MonitorParams]
            [om.utils.parameters.MonitorParams] object storing the OM monitor
            parameters from the configuration file.
    """
    # The event timestamp gets recovered in other ways by the event recovery code. No
    # need to initialize the psana interface: the timestamp will already be in the
    # event dictionary when OM starts extracting the data.
    return None


def detector_distance_init(monitor_parameters: parameters.MonitorParams) -> Any:
    """
    Initializes the psana Detector interface for detector distance data at LCLS.

    At LCLS, detector distance information is recovered from an Epics variable which
    reports the position of a stage. This function initializes the relevant Detector
    interface using the Epics variable identified by the
    'psana_detector_distance_epics_name' entry in the 'data_retrieval_layer' parameter
    group of the configuration file.

    Arguments:

        monitor_parameters: A [MonitorParams]
            [om.utils.parameters.MonitorParams] object storing the OM monitor
            parameters from the configuration file.

    Returns:

        A psana object that can be used later to retrieve the data.
    """
    return psana.Detector(
        monitor_parameters.get_param(
            group="data_retrieval_layer",
            parameter="psana_detector_distance_epics_name",
            parameter_type=str,
            required=True,
        )
    )


def beam_energy_init(monitor_parameters: parameters.MonitorParams) -> Any:
    """
    Initializes the psana Detector interface for beam energy data at LCLS.

    This function initializes the beam energy Detector interface, preparing it to
    retrieve energy information provided by LCLS' accelerator diagnostics.

    Arguments:

        monitor_parameters: A [MonitorParams]
            [om.utils.parameters.MonitorParams] object storing the OM monitor
            parameters from the configuration file.

    Returns:

        A psana object that can be used later to retrieve the data.
    """
    # psana.Detector("EBeam")
    return psana.Detector("SIOC:SYS0:ML00:AO192")


def timetool_data_init(monitor_parameters: parameters.MonitorParams) -> Any:
    """
    Initializes the psana Detector interface for timetool data at LCLS.

    At LCLS, timetool data is recovered from an Epics variable. This function
    initializes the timetool Detector interface using the Epics variable identified by
    the 'psana_timetools_epics_name' entry in the 'data_retrieval_layer' parameter
    group of the configuration file.

    Arguments:

        monitor_parameters: A [MonitorParams]
            [om.utils.parameters.MonitorParams] object storing the OM monitor
            parameters from the configuration file.

    Returns:

        A psana object that can be used later to retrieve the data.
    """
    return psana.Detector(
        monitor_parameters.get_param(
            group="data_retrieval_layer",
            parameter="psana_timetool_epics_name",
            parameter_type=str,
            required=True,
        )
    )


def digitizer_data_init(monitor_parameters: parameters.MonitorParams) -> Any:
    """
    Initializes the psana Detector interface for digitizer data at LCLS.

    This function initializes the Detector interface for the digitizer identified by
    the 'psana_digitizer_name' entry in the 'data_retrieval_layer' parameter group of
    the configuration file.

    Arguments:

        monitor_parameters: A [MonitorParams]
            [om.utils.parameters.MonitorParams] object storing the OM monitor
            parameters from the configuration file.

    Returns:

        A psana object that can be used later to retrieve the data.
    """
    return psana.Detector(
        monitor_parameters.get_param(
            group="data_retrieval_layer",
            parameter="psana_digitizer_name",
            parameter_type=str,
            required=True,
        )
    )


def opal_data_init(monitor_parameters: parameters.MonitorParams) -> Any:
    """
    Initializes the psana Detector interface for Opal camera data at LCLS.

    This function initialize the Detector interface for the Opal camera identified by
    the 'psana_opal_name' entry in the 'data_retrieval_layer' parameter group of the
    configuration file.

    Arguments:

        monitor_parameters: A [MonitorParams]
            [om.utils.parameters.MonitorParams] object storing the OM monitor
            parameters from the configuration file.

    Returns:

        A psana object that can be used later to retrieve the data.
    """
    return psana.Detector(
        monitor_parameters.get_param(
            group="data_retrieval_layer",
            parameter="psana_opal_name",
            parameter_type=str,
            required=True,
        )
    )


def optical_laser_active_init(monitor_parameters: parameters.MonitorParams) -> Any:
    """
    Initializes the psana Detector interface for an optical laser at LCLS.

    At LCLS, the status of an optical laser is determined by monitoring an EVR event
    source. This function initializes the Detector interface for the EVR event source
    identified by the 'psana_evr_source_name' entry in the 'data_retrieval_layer'
    parameter group of the configuration file.

    Arguments:

        monitor_parameters: A [MonitorParams]
            [om.utils.parameters.MonitorParams] object storing the OM monitor
            parameters from the configuration file.

    Returns:

        A psana object that can be used later to retrieve the data.
    """
    evr_source_name = monitor_parameters.get_param(
        group="data_retrieval_layer",
        parameter="psana_evr_source_name",
        parameter_type=str,
        required=True,
    )

    return psana.Detector(evr_source_name)


def xrays_active_init(monitor_parameters: parameters.MonitorParams) -> Any:
    """
    Initializes the psana Detector interface for the x-ray beam status at LCLS.

    At LCLS, the status of the x-ray beam is determined by monitoring an EVR event
    source. This function initializes the Detector interface for the EVR event source
    identified by the 'psana_evr_source_name' entry in the 'data_retrieval_layer'
    parameter group of the configuration file.

    Arguments:

        monitor_parameters: A [MonitorParams]
            [om.utils.parameters.MonitorParams] object storing the OM monitor
            parameters from the configuration file.

    Returns:

        A psana object that can be used later to retrieve the data.
    """
    evr_source_name = monitor_parameters.get_param(
        group="data_retrieval_layer",
        parameter="psana_evr_source_name",
        parameter_type=str,
        required=True,
    )

    return psana.Detector(evr_source_name)


def event_id_init(monitor_parameters: parameters.MonitorParams) -> None:
    """
    Initializes the psana Detector interface for the event identifier at LCLS.

    This function initializes the event identifier Detector interface, preparing it to
    retrieve a label that unambiguosly identifies the event being processed.

    Arguments:

        monitor_parameters: A [MonitorParams]
            [om.utils.parameters.MonitorParams] object storing the OM monitor
            parameters from the configuration file.
    """
    # No need to initialize the psana Detector interface: the event_id is extracted
    # directly from the even by the relevant Data Extraction Function.
    return None


def frame_id_init(monitor_parameters: parameters.MonitorParams) -> None:
    """
    Initializes the psana Detector interface for the frame identifier at LCLS.

    This function initializes the frame identifier Detector interface, preparing it to
    retrieve a label that unambiguosly identifies, within the current event, the frame
    being processed.

    Arguments:

        monitor_parameters: A [MonitorParams]
            [om.utils.parameters.MonitorParams] object storing the OM monitor
            parameters from the configuration file.
    """
    # No need to initialize the psana Detector interface: the frame_id is extracted
    # directly from the even by the relevant Data Extraction Function.
    return None


def timestamp(event: Dict[str, Any]) -> numpy.float64:
    """
    Gets the timestamp of an event retrieved from psana at LCLS.

    At LCLS, the time stamp of a data event is provided by the LCLS timing system.

    Arguments:

        event: A dictionary storing the event data.

    Returns:

        The timestamp of the event in seconds from the Epoch.
    """
    # Returns the timestamp stored in the event dictionary, without extracting it
    # again.
    # TODO: Determine return type
    timest: numpy.float64 = event["additional_info"]["timestamp"]
    if timest is None:
        raise exceptions.OmDataExtractionError(
            "Could not retrieve timestamp information from psana."
        )

    return timest


def detector_distance(event: Dict[str, Any]) -> float:
    """
    Gets the detector distance for an event retrieved from psana at LCLS.

    At LCLS, detector distance information is retrieved from an Epics variable. This
    function retrieves the information from the Epics variable identified by the
    'psana_detector_distance_epics_name' entry in the 'data_retrieval_ayer'
    parameter group of the configuration file.

    Arguments:

        event: A dictionary storing the event data.

    Returns:

        The distance between the detector and the sample in mm.
    """
    det_dist: Union[float, None] = event["additional_info"]["psana_detector_interface"][
        "detector_distance"
    ]()
    if det_dist is None:
        raise exceptions.OmDataExtractionError(
            "Could not retrieve detector distance information from psana."
        )

    return det_dist


def beam_energy(event: Dict[str, Any]) -> float:
    """
    Gets the beam energy for an event retrieved from psana at LCLS.

    At LCLS, detector beam energy information is retrieved from an Epics variable. This
    function retrieves the information from the Epics variable identified by the
    'psana_detector_distance_epics_name' entry in the 'data_retrieval_layer'
    parameter group of the configuration file.


    Arguments:

        event: A dictionary storing the event data.

    Returns:

        The energy of the beam in eV.
    """
    # beam_en = (
    #    event["additional_info"]["psana_detector_interface"]["beam_energy"]
    #    .get(event["data"])
    #    .ebeamPhotonEnergy()
    # )
    wavelength: Union[float, None] = event["additional_info"][
        "psana_detector_interface"
    ]["beam_energy"]()
    if wavelength is None:
        raise exceptions.OmDataExtractionError(
            "Could not retrieve beam energy information from psana."
        )
    h: float = 6.626070e-34  # J.m
    c: float = 2.99792458e8  # m/s
    joulesPerEv: float = 1.602176621e-19  # J/eV
    photonEnergy: float = (h / joulesPerEv * c) / (wavelength * 1e-9)

    return photonEnergy
    # return beam_en


def timetool_data(event: Dict[str, Any]) -> float:
    """
    Gets timetool data for an event retrieved from psana at LCLS.

    At LCLS, timetool data is recovered from an Epics variable. This function retrieves
    the information from the Epics variable identified by the
    'psana_timetools_epics_name' entry in the 'data_retrieval_layer' parameter group of
    the configuration file.

    Arguments:

        event: A dictionary storing the event data.

    Returns:

        The readout of the timetool instrument.
    """
    # TODO: Determine return type
    time_tl: Union[float, None] = event["additional_info"]["psana_detector_interface"][
        "timetool_data"
    ]()
    if time_tl is None:
        raise exceptions.OmDataExtractionError(
            "Could not retrieve time tool data from psana."
        )

    return time_tl


def digitizer_data(event: Dict[str, Any]) -> numpy.ndarray:
    """
    Get digitizer data for an event retrieved from psana at LCLS.

    This function retrieves data from the digitizer identified by the
    'psana_digitizer_name' entry in the 'data_retrieval_layer' parameter group of the
    configuration file.

    Arguments:

        event: A dictionary storing the event data.

    Returns:

        The waveform from the digitizer.
    """
    # TODO: Determine return type
    digit_data: Union[numpy.ndarray, None] = event["additional_info"][
        "psana_detector_interface"
    ]["digitizer_data"].waveform(event["data"])
    if digit_data is None:
        raise exceptions.OmDataExtractionError(
            "Could not retrieve digitizer data from psana."
        )

    return digit_data


def opal_data(event: Dict[str, Any]) -> numpy.ndarray:
    """
    Gets Opal camera data for an event retrieved from psana at LCLS.

    This function retrieves data from the Opal camera identified by the
    'psana_opal_name' entry in the 'data_retrieval_layer' parameter group of the
    configuration file  .

    Arguments:

        event: A dictionary storing the event data.

    Returns:

        A 2D array containing the image from the Opal camera.
    """
    op_data: Union[numpy.ndarray, None] = event["additional_info"][
        "psana_detector_interface"
    ]["opal_data"].calib(event["data"])
    if op_data is None:
        raise exceptions.OmDataExtractionError(
            "Could not retrieve Opel camera data from psana."
        )

    return op_data


def optical_laser_active(event: Dict[str, Any]) -> bool:
    """
    Gets the status of an optical laser for an event retrieved from psana at LCLS.

    At LCLS, the status of an optical laser is determined by monitoring an EVR event.
    This function determines the status of the optical laser by checking if the EVR
    source provides a specific event code for the current frame.

    * The name of the event source must be specified in the 'psana_evr_source_name'
      entry in the 'data_retrieval_layer' parameter group of the configuration file.

    * The EVR event code that signals an active optical laser must be provided in
      the 'psana_evr_code_for_active_optical_laser' entry in the same parameter group.

    * If the source shows this EVR code for the current frame, the optical laser is
      considered active.

    Arguments:

        event: A dictionary storing the event data.

    Returns:

        True if the optical laser is active for the current frame. False
        otherwise.
    """
    current_evr_codes: Union[List[int], None] = event["additional_info"][
        "psana_detector_interface"
    ]["optical_laser_active"].psana_detector_handle.eventCodes(event["data"])
    if current_evr_codes is None:
        raise exceptions.OmDataExtractionError(
            "Could not retrieve event codes from psana."
        )

    return event["additional_info"]["active_laser_evr_code"] in current_evr_codes


def xrays_active(event: Dict[str, Any]) -> bool:
    """
    Initializes the psana Detector interface for the x-ray beam status at LCLS.

    At LCLS, the status of the x-ray beam is determined by monitoring an EVR event
    source. This function determines the status of the x-ray beam by checking if the
    EVR source provides a specific event code for the current frame.

    * The name of the event source must be specified in the 'psana_evr_source_name'
      entry of the 'data_retrieval_layer' parameter group of the configuration file.

    * The EVR event code that signals an active x-ray beam must be provided in the
      'psana_evr_code_for_active_xray_beam" entry in the same parameter group.

    * If the source shows this EVR code for the current frame, the x-ray beam is
      considered active.

    Arguments:

        event: A dictionary storing the event data.

    Returns:

        True if the x-ray beam is active for the current frame. False otherwise.
    """
    current_evr_codes: Union[List[int], None] = event["additional_info"][
        "psana_detector_interface"
    ]["xrays_active"].psana_detector_handle.eventCodes(event["data"])
    if current_evr_codes is None:
        raise exceptions.OmDataExtractionError(
            "Could not retrieve event codes from psana."
        )

    return event["additional_info"]["active_xrays_evr_code"] in current_evr_codes


def event_id(event: Dict[str, Any]) -> str:
    """
    Gets a unique identifier for an event retrieved from a Pilatus detector.

    This function returns a label that unambiguously identifies, within an experiment,
    the event currently being processed. For the LCLS facility, three numbers are
    needed to unambigously identify an event: the portion of the event timestamp that
    corresponds to seconds, the portion of the timestamp that corresponds to
    nanoseconds, and a fiducial number. The event label at LCLS is a string which
    unifies these three numbers separating them with dashes.

    Arguments:

        event: A dictionary storing the event data.

    Returns:

        A unique event identifier.
    """
    event_id: Any = event["data"].get(psana.EventId)
    event_time: Any = event_id.time()
    return "{0}-{1}-{2}".format(event_time[0], event_time[1], event_id.fiducials())


def frame_id(event: Dict[str, Any]) -> str:
    """
    Gets a unique identifier for a Pilatus detector data frame.

    This function returns a label that unambiguously identifies, within an event, the
    frame currently being processed. Each psana event only contains one detector frame,
    therefore this function always returns the string "0".

    Arguments:

        event: A dictionary storing the event data.

    Returns:

        A unique frame identifier (within an event).
    """
    return str(0)
