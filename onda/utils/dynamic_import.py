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
Dynamic importing of objects from different layers.

This module contains the implementation of several functions that can
be used to import information from the different layers of the OnDA
framework, without worrying about their precise location.
"""
import importlib
from builtins import str  # pylint: disable=W0622

from future.utils import raise_from

from onda.utils import exceptions


def import_processing_layer(monitor_params):
    """
    Import the correct processing layer.

    Import the processing layer specified in the configuration
    file. Search for the python file with the processing layer
    implementation in the working directory first. If the file is not
    found there, look for it in the OnDA folder structure.

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
    Import the correct parallelization layer.

    Import the parallelization layer specified in the configuration
    file. Search for the python file with the parallelization layer
    implementation in the working directory first. If the file is not
    found there, look for it in the OnDA folder structure.

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
    Import the correct data retrieval layer.

    Import the data retrieval layer specified in the configuration
    file. Search for the python file with the data retrieval layer
    implementation in the working directory first. If the file is not
    found there, look for it in the OnDA folder structure.

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
                    parameter='data_retrieval_layer_profile',
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
                    parameter='data_retrieval_layer_profile',
                    type_=str,
                    required=True
                )
            )
        )

    return data_retrieval_layer


def get_event_handling_funcs(monitor_params):
    """
    Retrieve event handling functions.

    Retrieve the event handling functions from the data retrieval
    layer. Raise a MissingEventHandlingFunction exception if any
    function is not found.

    Args:

        monitor_params (MonitorParams): a
            :obj:`~onda.utils.parameters.MonitorParams` object
            containing the monitor parameters from the configuration
            file.

    Returns:

        Dict[Callable]: a dictionary with the event handling functions.
        The functions are stored in the dictionary using keys that
        match the function names.

    Raises:

        MissingEventHandlingFunction: if an event handling function is
            not found.
    """
    data_ret_layer = import_data_retrieval_layer(monitor_params)
    event_handl_func_dict = {}
    for func_name in [
            'initialize_event_source',
            'event_generator',
            'EventFilter',
            'open_event',
            'close_event',
            'get_num_frames_in_event'
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
    Retrieve data extraction functions.

    Retrieve the required data extraction functions from the data
    retrieval layer. Raise a MissingDataExtractionFunction exception if
    any function is not found.

    Args:

        monitor_params (MonitorParams): a
            :obj:`~onda.utils.parameters.MonitorParams` object
            containing the monitor parameters from the configuration
            file.

    Returns:

        Dict[Callable]: a dictionary with the data extraction
        functions. The functions are stored in the dictionary using
        keys that match the function names.

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
    Retrieve the psana detector interface initialization functions.

    Retrieve the required psana Detector interface initialization
    functions from the data retrieval layer. Raise a
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
        dictionary using keys that match the function names.

    Raises:

        MissingPsanaInitializationFunction: if a psana detector
            interface initialization function is not found.
    """
    # Read from the configuration file the list of required data
    # extraction functions: we must look for matching initialization
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

            # Try to retrieve a function with the name obtained by
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
    Get the peakfinder8 information for a specific detector.

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

    # Import from the data retrieval layer the peakfinder8 info
    # retrieval function for the specified detector. The convention
    # that OnDA uses to name these function is:
    # get_peakfinder8_info_<detector_name>.
    get_pf8_info_func = getattr(
        data_ret_layer,
        'get_peakfinder8_info_{}'.format(detector)
    )

    return get_pf8_info_func()


def get_file_extensions(monitor_params):
    """
    Get the allowed file extensions for the current detector(s).

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
    Get the HiDRA transport type currently used by OnDA.

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
