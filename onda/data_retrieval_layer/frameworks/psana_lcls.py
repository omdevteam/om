# This file is part of OnDA.
#
# OnDA is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# OnDA is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with OnDA.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Retrieval of events from HiDRA.

Functions and classes used to retrieve data events from psana.
"""
from __future__ import absolute_import, division, print_function

import numpy
import scipy
from future.utils import iteritems, raise_from

from onda.utils import dynamic_import, exceptions, named_tuples

try:
    import psana  # pylint: disable=import-error
except ImportError as exc:
    raise_from(
        exc=exceptions.MissingDependency(
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

    # Computes how many events the current worker node should process. Split the
    # events as equally as possible amongst the workers with the last worker
    # getting a smaller number of events if the number of files to be processed cannot
    # be exactly divided by the number of workers.
    for run in psana_source.runs():
        times = run.times()

        num_events_curr_node = int(numpy.ceil(len(times) / float(mpi_pool_size - 1)))

        events_curr_node = times[
            (node_rank - 1) * num_events_curr_node : node_rank * num_events_curr_node
        ]

        for evt in events_curr_node:
            yield run.event(evt)


def initialize_event_source(source, mpi_pool_size, monitor_params):
    """
    Initializes the psana event source.

    This function must be called on the master node before the :obj:`event_generator`
    function is called on the worker nodes.

    Args:

        source (str): a psana experiment string.

        mpi_pool_size (int): size of the node pool that includes the node where the
            function is called.

        monitor_params (MonitorParams): a :obj:`~onda.utils.parameters.MonitorParams`
            object containing the monitor parameters from the configuration file.
    """
    del source
    del mpi_pool_size
    del monitor_params
    # Psana needs no initialization, so thid function does nothing.


def event_generator(source, node_rank, mpi_pool_size, monitor_params):
    """
    Initializes the recovery of events from psana.

    Returns an iterator over the events that should be processed by the worker that
    calls the function. This function must be called on each worker node after the
    :obj:`initialize_event_source` function has been called on the master node.

    Args:

        source (str): a psana experiment string.

        node_rank (int): rank of the node where the function is called.

        mpi_pool_size (int): size of the node pool that includes the node where the
            function is called.

        monitor_params (MonitorParams): a :obj:`~onda.utils.parameters.MonitorParams`
            object containing the monitor parameters from the configuration file.

    Yields:

        Dict: A dictionary containing the metadata and data of an event.
    """
    # Detects if data is being read from an online or offline source.
    if "shmem" in source:
        offline = False
    else:
        offline = True
    if offline and not source[-4:] == ":idx":
        source += ":idx"

    # If the psana calibration directory is provided in the
    # configuration file, adds it as an option to psana.
    psana_calib_dir = monitor_params.get_param(
        section="DataRetrievalLayer", parameter="psana_calibration_directory", type_=str
    )
    if psana_calib_dir:
        psana.setOption(
            "psana.calib-dir".encode("ascii"), psana_calib_dir.encode("ascii")
        )
    else:
        print("Calibration directory not provided or not found.")

    psana_source = psana.DataSource(source)
    psana_interface_funcs = dynamic_import.get_psana_det_interface_funcs(monitor_params)

    # Calls all the required psana detector interface initialization
    # functions and stores the returned handlers in a dictionary.
    psana_det_interface = {}
    for f_name, func in iteritems(psana_interface_funcs):
        psana_det_interface[f_name.split("_init")[0]] = func(monitor_params)

    if offline:
        psana_events = _psana_offline_event_generator(
            psana_source=psana_source, node_rank=node_rank, mpi_pool_size=mpi_pool_size
        )
    else:
        psana_events = psana_source.events()

    for psana_event in psana_events:
        event = {
            "psana_detector_interface": psana_det_interface,
            "psana_event": psana_event,
        }

        # Recovers the timestamp from the psana event
        # (in epoch format) and stores it in the event dictionary.
        timestamp_epoch_format = psana_event.get(psana.EventId).time()

        event["timestamp"] = numpy.float64(
            str(timestamp_epoch_format[0]) + "." + str(timestamp_epoch_format[1])
        )

        yield event


def open_event(event):
    """
    Opens an event retrieved from psana.

    Makes the content of a retrieved psana event available in the 'data' entry of the
    event dictionary.

    Args:

        event (Dict): a dictionary with the event data.
    """
    # Psana events do not need to be opened. This function does
    # nothing.
    del event


def close_event(event):
    """
    Closes an event retrieved from psana.

    Args:

        event (Dict): a dictionary with the event data.
    """
    # Psana events do not need to be closed. This function does
    # nothing.
    del event


def get_num_frames_in_event(event):
    """
    Number of frames in an psana event.

    Returns the number of frames in an event retrieved from psana.

    Args:

        event (Dict): a dictionary with the event data.

    Retuns:

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


def detector_data_init(monitor_params, data_extraction_func_name):
    """
    Initializes the psana detector interface for x-ray detector data.

    Args:

        monitor_params (MonitorParams): a
            :obj:`~onda.utils.parameters.MonitorParams` object containing the monitor
            parameters from the configuration file.

        data_extraction_func_name: specific name of the data extraction function with
            which this generic initialization function should be associated (e.g:
            'detector_data', 'detector2_data'. 'detector3_data', etc.). This is
            required to resuse this initialization function with multiple detectors.
            The `functools.partial` python function is used to create 'personalized'
            versions of this function for each detector, by fixing this argument.

    Returns:

        Detector: a handle (a psana Detector object) that can be used later to
        retrieve the data.
    """
    # Calls the psana interface initialization function corresponding to the data
    # extraction func name.
    return psana.Detector(
        monitor_params.get_param(
            section="DataRetrievalLayer",
            parameter="psana_{0}_detector_name".format(data_extraction_func_name),
            type_=str,
            required=True,
        )
    )


def timestamp_init(monitor_params):
    """
    Initializes the psana detector interface for timestamp data.

    Args:

        monitor_params (MonitorParams): a
            :obj:`~onda.utils.parameters.MonitorParams` object containing the monitor
            parameters from the configuration file.

    Returns:

        Detector: a handle (a psana Detector object) that can be used later to
        retrieve the data.
    """
    # The event timestamp gets recovered in other ways by the event recovery code. No
    # need to initialize the psana interface: the timestamp will already be in the
    # event dictionary when OnDA starts extracting the data.
    del monitor_params
    return None


def detector_distance_init(monitor_params):
    """
    Initializes the psana detector interface for detector dist. data.

    Args:

        monitor_params (MonitorParams): a :obj:`~onda.utils.parameters.MonitorParams`
            object containing the monitor parameters from the configuration file.

    Returns:

        Detector: a handle (a psana Detector object) that can be used later to
        retrieve the data.
    """
    return psana.Detector(
        monitor_params.get_param(
            section="DataRetrievalLayer",
            parameter="psana_detector_distance_epics_name",
            type_=str,
            required=True,
        )
    )


def beam_energy_init(monitor_params):
    """
    Initializes the psana detector interface for beam energy data.

    Args:

        monitor_params (MonitorParams): a :obj:`~onda.utils.parameters.MonitorParams`
            object containing the monitor parameters from the configuration file.

    Returns:

        Detector: a handle (a psana Detector object) that can be used later to
        retrieve the data.
    """
    del monitor_params
    return psana.Detector("EBeam")


def timetool_data_init(monitor_params):
    """
    Initializes the psana detector interface for data from a timetool.

    Args:

        monitor_params (MonitorParams): a :obj:`~onda.utils.parameters.MonitorParams`
            object containing the monitor parameters from the configuration file.

    Returns:

        Detector: a handle (a psana Detector object) that can be used later to
        retrieve the data.
    """
    return psana.Detector(
        monitor_params.get_param(
            section="DataRetrievalLayer",
            parameter="psana_timetool_epics_name",
            type_=str,
            required=True,
        )
    )


def digitizer_data_init(monitor_params, data_extraction_func_name):
    """
    Initialize the psana detector interface for data from a digitizer.

    Args:

        monitor_params (MonitorParams): a
            :obj:`~onda.utils.parameters.MonitorParams` object containing the monitor
            parameters from the configurationfile.

        data_extraction_func_name: specific name of the data extraction function with
            which this generic initialization function should be associated (e.g:
            'digitizer_data', 'digitizer2_data'. 'digitizer3_data', etc.). This is
            required to resuse this initialization function with multiple digitizers.
            The `functools.partial` python function is used to create 'personalized'
            versions of this function for each digitizer, by fixing this argument.

    Returns:

        Detector: a handle (a psana Detector object) that can be used later to
        retrieve the data.
    """
    return psana.Detector(
        monitor_params.get_param(
            section="DataRetrievalLayer",
            parameter="psana_{0}_digitizer_name".format(data_extraction_func_name),
            type_=str,
            required=True,
        )
    )


def opal_data_init(monitor_params):
    """
    Initializes the psana detector interface for Opal camera data.

    Args:

        monitor_params (MonitorParams): a :obj:`~onda.utils.parameters.MonitorParams`
            object containing the monitor parameters from the configuration file.

    Returns:

        Detector: a handle (a psana Detector object) that can be used later to
        retrieve the data.
    """
    return psana.Detector(
        monitor_params.get_param(
            section="DataRetrievalLayer",
            parameter="psana_opal_name",
            type_=str,
            required=True,
        )
    )


def optical_laser_active_init(monitor_params):
    """
    Initializes the psana detector interface for the status of the optical laser.

    Args:

        monitor_params (MonitorParams): a :obj:`~onda.utils.parameters.MonitorParams`
            object containing the monitor parameters from the configuration file.

    Returns:

        Tuple[psana.Detector, evr_codes]: a tuple where the first entry is a psana
        Detector interface object, while the second is a list of EVR codes
        corresponding to the optical laser being active. Both can be used later to
        retrieve the data.
    """
    active_laser_evr_code = monitor_params.get_param(
        section="DataRetrievalLayer",
        parameter="psana_evr_code_for_active_optical_laser",
        type_=int,
        required=True,
    )

    evr_source_name = monitor_params.get_param(
        section="DataRetrievalLayer",
        parameter="psana_evr_source_name",
        type_=str,
        required=True,
    )

    return named_tuples.OpticalLaserStateDataRetrievalInfo(
        psana_detector_handle=psana.Detector(evr_source_name),
        active_laser_evr_code=active_laser_evr_code,
    )


def xrays_active_init(monitor_params):
    """
    Initializes the psana detector interface for the status of the optical laser.

    Args:

        monitor_params (MonitorParams): a :obj:`~onda.utils.parameters.MonitorParams`
            object containing the monitor parameters from the configuration file.

    Returns:

        Tuple[psana.Detector, evr_codes]: a tuple where the first entry is a psana
        Detector interface object, while the second is a list of EVR codes
        corresponding to the optical laser being active. Both can be used later to
        retrieve the data.
    """
    active_laser_evr_code = monitor_params.get_param(
        section="DataRetrievalLayer",
        parameter="psana_evr_code_for_active_xray_laser",
        type_=int,
        required=True,
    )

    evr_source_name = monitor_params.get_param(
        section="DataRetrievalLayer",
        parameter="psana_evr_source_name",
        type_=str,
        required=True,
    )

    return named_tuples.OpticalLaserStateDataRetrievalInfo(
        psana_detector_handle=psana.Detector(evr_source_name),
        active_laser_evr_code=active_laser_evr_code,
    )


def target_time_delay_init(monitor_params):
    """
    Initializes the psana detector interface for target time delay.

    Args:

        monitor_params (MonitorParams): a :obj:`~onda.utils.parameters.MonitorParams`
            object containing the monitor parameters from the configuration file.

    Returns:

        Detector: a handle (a psana Detector object) that can be used later to
        retrieve the data.
    """
    return psana.Detector(
        monitor_params.get_param(
            section="DataRetrievalLayer",
            parameter="psana_target_time_delay_epics_name",
            type_=str,
            required=True,
        )
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
    # Returns the timestamp stored in the event dictionary, without extracting it
    # again.
    return event["timestamp"]


def detector_distance(event):
    """
    Retrieves the distance of the detector from the sample location.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        float: the distance between the detector and the sample in m.
    """
    # Recovers the detector distance from psana. It is in mm, so we must divide it by
    # 10000 to convert it to SI (m).
    return event["psana_detector_interface"]["detector_distance"]() / 1000.0


def beam_energy(event):
    """
    Retrieves the beam energy.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        float: the energy of the beam in J.
    """
    # Recovers the detector distance from psana. It is in eV, so we must multiply it
    # by e convert it to SI (J).
    return (
        event["psana_detector_interface"]["beam_energy"]
        .get(event["psana_event"])
        .ebeamPhotonEnergy()
        * scipy.constants.e
    )


def timetool_data(event):
    """
    Retrieves the data from a timetool.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        float: the readout of the timetool instrument.
    """
    return event["psana_detector_interface"]["timetool_data"]()


def digitizer_data(event, data_extraction_func_name):
    """
    Retrieves the waveforms from a digitizer (All channels).

    Args:

        event (Dict): a dictionary with the event data.

        data_extraction_func_name (str): the name of the data extraction function
            ("digitizer_data", "digitizer2_data", "digitizer3_data", etc.) that is
            associated with this digitizer.

    Returns:

        psana object: a psana object storing the waveform data.
    """
    return event["psana_detector_interface"][data_extraction_func_name].waveform(
        event["psana_event"]
    )


def opal_data(event):
    """
    Retrieves data from an Opal camera.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        ndarray: a 2D array containing the image from the Opal camera.
    """
    return event["psana_detector_interface"]["opal_data"].calib(event["psana_event"])


def optical_laser_active(event):
    """
    Retrieves the optical laser status.

    Returns whether the optical laser is active or not.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        bool: True if the optical laser is active. False otherwise.
    """
    current_evr_codes = event["psana_detector_interface"][
        "optical_laser_active"
    ].psana_detector_handle.eventCodes(event["psana_event"])

    return (
        event["psana_detector_interface"]["optical_laser_active"].active_laser_evr_code
        in current_evr_codes
    )


def xrays_active(event):
    """
    Retrieves the x-ray laser status.

    Returns whether the x-rays are active or not.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        bool: True if the x-rays is active. False otherwise.
    """
    current_evr_codes = event["psana_detector_interface"][
        "xrays_active"
    ].psana_detector_handle.eventCodes(event["psana_event"])

    return (
        event["psana_detector_interface"]["xrays_active"].active_laser_evr_code
        in current_evr_codes
    )


def target_time_delay(event):
    """
    Retrieves the target pump-probe time delay.

    Returns whether the target time delay.

    Args:

        event (Dict): a dictionary with the event data.

    Returns:

        float: The target time delay in ps.
    """
    # Target time delay at cxi is negative and given in nanoseconds. It needs to be
    # mode positive to match the usual convention. It needa also to be converted to
    # picoseconds lets also limit the precision to 1 fs and round to ensure proper
    # binning.
    return round(event["psana_detector_interface"]["target_time_delay"]() * -1000, 3)
