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
Dynamic importing of objects from various OnDA layers.

Classes and functions used to import information from different layers
of OnDA, without worrying about their precise location.
"""
from __future__ import absolute_import, division, print_function

import importlib

from future.utils import raise_from

from onda.utils import exceptions


def import_processing_layer(monitor_params):
    """
    Imports the correct processing layer.

    Imports the processing layer specified in the configuration
    file. Searches for the python file with the processing layer
    implementation in the working directory first. If the file is not
    found there, looks for it in the OnDA folder structure.

    Args:

        monitor_params (MonitorParams): a
            :obj:`~onda.utils.parameters.MonitorParams` object
            containing the monitor parameters from the configuration
            file.

    Returns:

        module: the imported processing layer.
    """
    try:
        processing_layer = importlib.import_module(
            '{0}'.format(
                monitor_params.get_param(
                    section='Onda',
                    parameter='processing_layer',
                    type_=str,
                    required=True
                )
            )
        )
    except ImportError:
        processing_layer = importlib.import_module(
            'onda.processing_layer.{0}'.format(
                monitor_params.get_param(
                    section='Onda',
                    parameter='processing_layer',
                    type_=str,
                    required=True
                )
            )
        )

    return processing_layer


def import_parallelization_layer(monitor_params):
    """
    Imports the correct parallelization layer.

    Import sthe parallelization layer specified in the configuration
    file. Searches for the python file with the parallelization layer
    implementation in the working directory first. If the file is not
    found there, looks for it in the OnDA folder structure.

    Args:

        monitor_params (MonitorParams): a
            :obj:`~onda.utils.parameters.MonitorParams` object
            containing the monitor parameters from the configuration
            file.

    Returns:

        module: the imported parallelization layer.
    """
    try:
        data_retrieval_layer = importlib.import_module(
            '{0}'.format(
                monitor_params.get_param(
                    section='Onda',
                    parameter='parallelization_layer',
                    type_=str,
                    required=True
                )
            )
        )
    except ImportError:
        data_retrieval_layer = importlib.import_module(
            'onda.parallelization_layer.{0}'.format(
                monitor_params.get_param(
                    section='Onda',
                    parameter='data_retrieval_layer',
                    type_=str,
                    required=True
                )
            )
        )

    return data_retrieval_layer


def import_data_retrieval_layer(monitor_params):
    """
    Import sthe correct data retrieval layer.

    Imports the data retrieval layer specified in the configuration
    file. Searches for the python file with the data retrieval layer
    implementation in the working directory first. If the file is not
    found there, looks for it in the OnDA folder structure.

    Args:

        monitor_params (MonitorParams): a
            :obj:`~onda.utils.parameters.MonitorParams` object
            containing the monitor parameters from the configuration
            file.

    Returns:

        module: the imported data retrieval layer.
    """
    try:
        data_retrieval_layer = importlib.import_module(
            '{0}'.format(
                monitor_params.get_param(
                    section='Onda',
                    parameter='data_retrieval_layer',
                    type_=str,
                    required=True
                )
            )
        )
    except ImportError:
        data_retrieval_layer = importlib.import_module(
            'onda.data_retrieval_layer.{0}'.format(
                monitor_params.get_param(
                    section='Onda',
                    parameter='data_retrieval_layer',
                    type_=str,
                    required=True
                )
            )
        )

    return data_retrieval_layer


def get_event_handling_funcs(monitor_params):
    """
    Retrieves event handling functions.

    Retrieves the event handling functions from the data retrieval
    layer. Raises a MissingEventHandlingFunction exception if a
    function is not found.

    Args:

        monitor_params (MonitorParams): a
            :obj:`~onda.utils.parameters.MonitorParams` object
            containing the monitor parameters from the configuration
            file.

    Returns:

        Dict[Callable]: a dictionary with the event handling functions.
        The functions are stored in the dictionary with keys that match
        the function names.

    Raises:

        MissingEventHandlingFunction: if an event handling function is
        not found.
    """
    data_ret_layer = import_data_retrieval_layer(monitor_params)
    event_handl_func_dict = {}
    for func_name in [
            'initialize_event_source',
            'event_generator',
            'open_event',
            'close_event',
            'get_num_frames_in_event',
            'EventFilter',
            'FrameFilter',
    ]:
        try:
            event_handl_func_dict[func_name] = getattr(
                data_ret_layer, func_name
            )
        except AttributeError:
            raise_from(
                exc=exceptions.MissingEventHandlingFunction(
                    "Event handling function {0} is not "
                    "defined.".format(func_name)
                ),
                cause=None
            )

    return event_handl_func_dict


def get_data_extraction_funcs(monitor_params):
    """
    Retrieves data extraction functions.

    Retrieves the required data extraction functions from the data
    retrieval layer. Raises a MissingDataExtractionFunction exception
    if a function is not found.

    Args:

        monitor_params (MonitorParams): a
            :obj:`~onda.utils.parameters.MonitorParams` object
            containing the monitor parameters from the configuration
            file.

    Returns:

        Dict[Callable]: a dictionary with the data extraction
        functions. The functions are stored in the dictionary with keys
        that match the function names.

    Raises:

        MissingDataExtractionFunction: if a data extraction function is
        not found.
    """
    data_extraction_funcs = [
        x.strip() for x in monitor_params.get_param(
            section='Onda',
            parameter='required_data',
            type_=list,
            required=True
        )
    ]
    data_ret_layer = import_data_retrieval_layer(monitor_params)
    data_ext_func_dict = {}
    for func_name in data_extraction_funcs:
        try:
            data_ext_func_dict[func_name] = getattr(
                data_ret_layer, func_name
            )
        except AttributeError:
            raise_from(
                exc=exceptions.MissingDataExtractionFunction(
                    "Data extraction function {0} not "
                    "defined".format(func_name)
                ),
                cause=None
            )

    return data_ext_func_dict


def get_psana_det_interface_funcs(monitor_params):
    """
    Retrieves the psana detector interface initialization functions.

    Retrieves the required psana Detector interface initialization
    functions from the data retrieval layer. Raises a
    MissingDataExtractionFunction exception if any function is not
    found.

    Args:

        monitor_params (MonitorParams): a
            :obj:`~onda.utils.parameters.MonitorParams` object
            containing the monitor parameters from the configuration
            file.

    Returns:

        Dict[Callable]: a dictionary with the psana detector interface
        initialization functions. The functions are stored in the
        dictionary with keys that match the function names.

    Raises:

        MissingPsanaInitializationFunction: if a psana detector
            interface initialization function is not found.
    """
    # Reads from the configuration file the list of required data
    # extraction functions:, then looks for matching initialization
    # functions.
    data_extraction_funcs = [
        x.strip() for x in monitor_params.get_param(
            section='Onda',
            parameter='required_data',
            type_=list,
            required=True
        )
    ]

    data_ret_layer = import_data_retrieval_layer(monitor_params)
    psana_interface_func_dict = {}
    for func_name in data_extraction_funcs:
        try:
            # Tries to retrieve a function with the name obtained by
            # adding the '_init' suffix to the the data extraction
            # function name (This is the convention OnDA uses for
            # naming the psana detector initialization functions).
            psana_interface_func_dict[func_name] = getattr(
                data_ret_layer, func_name + '_init'
            )
        except AttributeError:
            raise_from(
                exc=exceptions.MissingPsanaInitializationFunction(
                    "Psana Detector interface initialization function "
                    "{} not defined".format(func_name)
                ),
                cause=None
            )

    return psana_interface_func_dict


def get_peakfinder8_info(monitor_params,
                         detector):
    """
    Gets the peakfinder8 information for a specific detector.

    Args:

        monitor_params (MonitorParams): a
            :obj:`~onda.utils.parameters.MonitorParams` object
            containing the monitor parameters from the configuration
            file.

        detector: detector for which the peakfinder8 information must
            be recovered, identified by the name of the
            data extraction function used to extract its data (i.e.:
            "detector_data", "detector2_data", etc.).

    Returns:

        Peakfinder8DetInfo: the peakfinder8-related detector
        information.
    """
    data_ret_layer = import_data_retrieval_layer(monitor_params)

    # Imports from the data retrieval layer the peakfinder8 info
    # retrieval function for the specified detector. The convention
    # that OnDA uses to name these functions is:
    # get_peakfinder8_info_<detector_name>.
    get_pf8_info_func = getattr(
        data_ret_layer,
        'get_peakfinder8_info_{}'.format(detector)
    )

    return get_pf8_info_func()


def get_file_extensions(monitor_params):
    """
    Gets the file extensions used by the current detector(s).

    Returns the extensions used for files written by the the current
    detector(s).

    Args:

        monitor_params (MonitorParams): a
            :obj:`~onda.utils.parameters.MonitorParams` object
            containing the monitor parameters from the configuration
            file.

    Returns:

        Tuple: a tuple with the file extensions allowed for the
        detector(s) currently in use.
    """
    data_retrieval_layer = import_data_retrieval_layer(
        monitor_params
    )

    file_extension_info_func = getattr(
        data_retrieval_layer,
        'get_file_extensions'
    )

    return file_extension_info_func()


def get_hidra_transfer_type(monitor_params):
    """
    Gets the HiDRA transport type.

    Retrieves the type of transport that OnDA should use when
    retrieving data from HiDRA.

    Args:

        monitor_params (MonitorParams): a
            :obj:`~onda.utils.parameters.MonitorParams` object
            containing the monitor parameters from the configuration
            file.

    Returns:

        str: the HiDRA trasport type ('data' or 'metadata').
    """
    data_retrieval_layer = import_data_retrieval_layer(
        monitor_params
    )

    hidra_transport_type_func = getattr(
        data_retrieval_layer,
        'get_hidra_transport_type'
    )

    return hidra_transport_type_func()
