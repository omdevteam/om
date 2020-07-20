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
Retrieval of events from psana at LCLS.

This module contains functions and classes that retrieve data events from the psana
framework at the LCLS facility.
"""
from __future__ import absolute_import, division, print_function

from types import ModuleType
from typing import Any, Callable, Dict, List, cast

import numpy  # type: ignore
from future.utils import iteritems, raise_from  # type: ignore

from om.utils import data_event, dynamic_import, exceptions, parameters
from om.utils.data_event import TypeEventGenerator, TypeEventHandlingFuncs

try:
    import psana  # type: ignore
except ImportError as exc:
    raise_from(
        exc=exceptions.OmMissingDependencyError(
            "The psana module could not be loaded. The following dependency does not "
            "appear to be available on the system: psana."
        ),
        cause=exc,
    )


############################
#                          #
# EVENT HANDLING FUNCTIONS #
#                          #
############################


def _psana_offline_event_generator(psana_source, node_rank, mpi_pool_size):
    # type: (psana._DataSource, int, int) -> Any
    # Computes how many events the current worker node should process. Splits the
    # events as equally as possible amongst the workers. If the number of events cannot
    # be exactly divided by the number of workers, an additional worker is assigned
    # the residual events.
    for run in psana_source.runs():
        times = run.times()
        num_events_curr_node = int(
            numpy.ceil(len(times) / float(mpi_pool_size - 1))
        )  # type: int
        events_curr_node = times[
            (node_rank - 1) * num_events_curr_node : node_rank * num_events_curr_node
        ]
        for evt in events_curr_node:

            yield run.event(evt)


def initialize_event_source(source, node_pool_size, monitor_params):
    # type: (str, int, parameters.MonitorParams) -> Any
    """
    Initializes the psana event source at LCLS.

    This function must be called on the master node before the :func:`event_generator`
    function is called on the worker nodes. There is no need to initialize the psana
    event source, so this function actually does nothing.

    Arguments:

        source (str): a psana-style DataSource string.

        node_pool_size (int): the total number of nodes in the OM pool, including all
            the worker nodes and the master node.

        monitor_params (:class:`~om.utils.parameters.MonitorParams`): an object
            storing the OM monitor parameters from the configuration file.
    """
    del source
    del node_pool_size
    del monitor_params


def event_generator(
    source,  # type: str
    node_rank,  # type: int
    node_pool_size,  # type: int
    monitor_params,  # type: parameters.MonitorParams
):
    # type: (...) -> TypeEventGenerator
    """
    Retrieves events from psana at LCLS.

    This function must be called on each worker node after the
    :func:`initialize_event_source` function has been called on the master node.
    The function is a generator and it returns an iterator over the events that the
    calling worker must process.

    Arguments:

        source (str): a psana-style DataSource string.

        node_rank (int): the rank, in the OM pool, of the worker node calling the
            function.

        node_pool_size (int): the total number of nodes in the OM pool, including all
            the worker nodes and the master node.

        monitor_params (:class:`~om.utils.parameters.MonitorParams`): an object
            storing the OM monitor parameters from the configuration file.

    Yields:

        :class:`~om.utils.data_event.DataEvent`: an object storing the event data.
    """
    # Detects if data is being read from an online or offline source.
    if "shmem" in source:
        offline = False  # type: bool
    else:
        offline = True
    if offline and not source[-4:] == ":idx":
        source += ":idx"

    # If the psana calibration directory is provided in the configuration file, it is
    # added as an option to psana.
    psana_calib_dir = monitor_params.get_param(
        group="data_retrieval_layer",
        parameter="psana_calibration_directory",
        parameter_type=str,
    )  # type: str
    if psana_calib_dir is not None:
        psana.setOption(
            "psana.calib-dir".encode("ascii"), psana_calib_dir.encode("ascii")
        )
    else:
        print("OM Warning: Calibration directory not provided or not found.")
    psana_source = psana.DataSource(source.encode("ascii"))
    data_retrieval_layer_filename = monitor_params.get_param(
        group="om", parameter="data_retrieval_layer", parameter_type=str, required=True,
    )  # type: str
    data_retrieval_layer = dynamic_import.import_data_retrieval_layer(
        data_retrieval_layer_filename=data_retrieval_layer_filename
    )  # type: ModuleType
    required_data = monitor_params.get_param(
        group="om", parameter="required_data", parameter_type=list, required=True
    )  # type: List[str]
    psana_detector_interface_funcs = dynamic_import.get_psana_detector_interface_funcs(
        required_data=required_data, data_retrieval_layer=data_retrieval_layer
    )
    event_handling_functions = dynamic_import.get_event_handling_funcs(
        data_retrieval_layer=data_retrieval_layer
    )  # type: TypeEventHandlingFuncs
    data_extraction_functions = dynamic_import.get_data_extraction_funcs(
        required_data=required_data, data_retrieval_layer=data_retrieval_layer
    )  # type: Dict[str, Callable[[data_event.DataEvent], Any]]
    event = data_event.DataEvent(
        event_handling_funcs=event_handling_functions,
        data_extraction_funcs=data_extraction_functions,
    )  # type: data_event.DataEvent

    # Calls all the required psana detector interface initialization functions and
    # stores the returned objects in a dictionary.
    event.framework_info["psana_detector_interface"] = {}
    for f_name, func in iteritems(psana_detector_interface_funcs):
        event.framework_info["psana_detector_interface"][
            f_name.split("_init")[0]
        ] = func(monitor_params)

    # Initializes the psana event source and starts retrieving events.
    if offline:
        psana_events = _psana_offline_event_generator(
            psana_source=psana_source, node_rank=node_rank, mpi_pool_size=node_pool_size
        )
    else:
        psana_events = psana_source.events()
    for psana_event in psana_events:
        event.data = psana_event

        # Recovers the timestamp from the psana event (as seconds from the Epoch) and
        # stores it in the event dictionary to be retrieved later.
        timestamp_epoch_format = psana_event.get(psana.EventId).time()
        event.framework_info["timestamp"] = numpy.float64(
            str(timestamp_epoch_format[0]) + "." + str(timestamp_epoch_format[1])
        )

        yield event


def open_event(event):
    # type: (data_event.DataEvent) -> None
    """
    Opens an event retrieved from psana at LCLS.

    Psana events do not need to be opened, so this function actually does nothing.

    NOTE: This function is designed to be injected as a member function into an
    :class:`~om.utils.data_event.DataEvent` object.

    Arguments:

        event (:class:`~om.utils.data_event.DataEvent`): an object storing the event
            data.
    """
    del event


def close_event(event):
    # type: (data_event.DataEvent) -> None
    """
    Closes an event retrieved from psana at LCLS.

    Psana events do not need to be closed, so this function actually does nothing.

    NOTE: This function is designed to be injected as a member function into an
    :class:`~om.utils.data_event.DataEvent` object.

    Arguments:

        event (:class:`~om.utils.data_event.DataEvent`): an object storing the event
            data.
    """
    del event


def get_num_frames_in_event(event):
    # type: (data_event.DataEvent) -> int
    """
    Gets the number of frames in an event retrieved from psana at LCLS.

    Psana events are frame-based, and always contain just one frame. This function
    always returns 1.

    NOTE: This function is designed to be injected as a member function into an
    :class:`~om.utils.data_event.DataEvent` object.

    Arguments:

        event (:class:`~om.utils.data_event.DataEvent`): an object storing the event
            data.

    Returns:

        int: the number of frames in the event.
    """
    del event

    # Psana events usually contain just one frame.
    return 1


#####################################################
#                                                   #
# PSANA DETECTOR INTERFACE INITIALIZATION FUNCTIONS #
#                                                   #
#####################################################


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
        ).encode("ascii")
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
        ).encode("ascii")
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
    return psana.Detector("EBeam".encode("ascii"))


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
        ).encode("ascii")
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
        ).encode("ascii")
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
        ).encode("ascii")
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
    ).encode("ascii")

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
    ).encode("ascii")

    return psana.Detector(evr_source_name)


#############################
#                           #
# DATA EXTRACTION FUNCTIONS #
#                           #
#############################


def timestamp(event):
    # type: (data_event.DataEvent) -> numpy.float64
    """
    Gets the timestamp of an event retrieved from psana at LCLS.

    Arguments:

        event (:class:`~om.utils.data_event.DataEvent`): an object storing the event
            data.

    Returns:

        numpy.float64: the timestamp of the event in seconds from the Epoch.
    """
    # Returns the timestamp stored in the event dictionary, without extracting it
    # again.
    timest = event.framework_info["timestamp"]
    if timest is None:
        raise exceptions.OmDataExtractionError(
            "Could not retrieve timestamp information from psana."
        )

    return cast(numpy.float64, timest)


def detector_distance(event):
    # type: (data_event.DataEvent) -> float
    """
    Gets the detector distance for an event retrieved from psana at LCLS.

    Detector distance information is recovered from an Epics controller at LCLS . This
    function retrieves the information from the Epics controller identified by the
    'psana_detector_distance_epics_name' entry in the 'DataRetrievalLayer'
    configuration parameter group.

    Arguments:

        event (:class:`~om.utils.data_event.DataEvent`): an object storing the event
            data.

    Returns:

        float: the distance between the detector and the sample in mm.
    """
    det_dist = event.framework_info["psana_detector_interface"]["detector_distance"]()
    if det_dist is None:
        raise exceptions.OmDataExtractionError(
            "Could not retrieve detector distance information from psana."
        )

    return cast(float, det_dist)


def beam_energy(event):
    # type: (data_event.DataEvent) -> float
    """
    Gets the beam energy for an event retrieved from psana at LCLS.

    Arguments:

        event (:class:`~om.utils.data_event.DataEvent`): an object storing the event
            data.

    Returns:

        float: the energy of the beam in eV.
    """
    beam_en = (
        event.framework_info["psana_detector_interface"]["beam_energy"]
        .get(event.data)
        .ebeamPhotonEnergy()
    )
    if beam_en is None:
        raise exceptions.OmDataExtractionError(
            "Could not retrieve beam energy information from psana."
        )

    return cast(float, beam_en)


def timetool_data(event):
    # type: (data_event.DataEvent) -> float
    """
    Gets timetool data for an event retrieved from psana at LCLS.

    Timetool data is recovered from an Epics controller at LCLS. This function
    retrieves the data from the Epics controller identified by the
    'psana_timetools_epics_name' entry in the 'DataRetrievalLayer' configuration
    parameter group.

    Arguments:

        event (:class:`~om.utils.data_event.DataEvent`): an object storing the event
            data.

    Returns:

        float: the readout of the timetool instrument.
    """
    # TODO: Determine return type
    time_tl = event.framework_info["psana_detector_interface"]["timetool_data"]()
    if time_tl is None:
        raise exceptions.OmDataExtractionError(
            "Could not retrieve time tool data from psana."
        )

    return cast(float, time_tl)


def digitizer_data(event):
    # type: (data_event.DataEvent) -> numpy.ndarray
    """
    Get digitizer data for an event retrieved from psana at LCLS.

    This function retrieves data from the digitizer identified by the
    'psana_digitizer_name' entry in the 'DataRetrievalLayer' configuration parameter
    group.

    Arguments:

        event (:class:`~om.utils.data_event.DataEvent`): an object storing the event
            data.

    Returns:

        numpy.array: the waveform from the digitizer.
    """
    # TODO: Determine return type
    digit_data = event.framework_info["psana_detector_interface"][
        "digitizer_data"
    ].waveform(event.data)
    if digit_data is None:
        raise exceptions.OmDataExtractionError(
            "Could not retrieve digitizer data from psana."
        )

    return cast(numpy.ndarray, digit_data)


def opal_data(event):
    # type: (data_event.DataEvent) -> numpy.ndarray
    """
    Gets Opal camera data for an event retrieved from psana at LCLS.

    This function retrieves data from the Opel camera identified by the
    'psana_opal_name' entry in the 'DataRetrievalLayer' configuration parameter group.

    Arguments:

        event (:class:`~om.utils.data_event.DataEvent`): an object storing the event
            data.

    Returns:

        numpy.ndarray: a 2D array containing the image from the Opal camera.
    """
    op_data = event.framework_info["psana_detector_interface"]["opal_data"].calib(
        event.data
    )
    if op_data is None:
        raise exceptions.OmDataExtractionError(
            "Could not retrieve Opel camera data from psana."
        )

    return cast(numpy.ndarray, op_data)


def optical_laser_active(event):
    # type: (data_event.DataEvent) -> bool
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

        event (:class:`~om.utils.data_event.DataEvent`): an object storing the event
           data.

    Returns:

        bool: True if the optical laser is active for the current frame. False
        otherwise.
    """
    current_evr_codes = event.framework_info["psana_detector_interface"][
        "optical_laser_active"
    ].psana_detector_handle.eventCodes(event.data)
    if current_evr_codes is None:
        raise exceptions.OmDataExtractionError(
            "Could not retrieve event codes from psana."
        )

    return (
        event.framework_info["psana_detector_interface"][
            "optical_laser_active"
        ].active_laser_evr_code
        in current_evr_codes
    )


def xrays_active(event):
    # type: (data_event.DataEvent) -> bool
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

        event (:class:`~om.utils.data_event.DataEvent`): an object storing the event
           data.

    Returns:

        bool: True if the x-ray beam is active for the current frame. False otherwise.
    """
    current_evr_codes = event.framework_info["psana_detector_interface"][
        "xrays_active"
    ].psana_detector_handle.eventCodes(event.data)
    if current_evr_codes is None:
        raise exceptions.OmDataExtractionError(
            "Could not retrieve event codes from psana."
        )

    return (
        event.framework_info["psana_detector_interface"][
            "xrays_active"
        ].active_laser_evr_code
        in current_evr_codes
    )
