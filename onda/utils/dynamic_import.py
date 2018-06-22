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

        monitor_params (:obj:`onda.utils.parameters.MonitorParams`):
            a MonitorParams object containing the monitor
            parameters from the configuration file.

    Returns:

        module: the imported processing layer.
    """
    # Try to import the module from the current folder.
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

        # Try to import the module from the OnDA folder structure.
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
    parameters. Search for the python file with the parallelization
    layer implementation in the working directory first. If the file is
    not found there, look for it in the OnDA folder structure.

    Args:

        monitor_params (:obj:`onda.utils.parameters.MonitorParams`):
            a MonitorParams object containing the monitor
            parameters from the configuration file.

    Returns:

        module: the imported parallelization layer.
    """
    try:

        # Try to import the module from the current folder.
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

        # Try to import the module from the OnDA folder structure.
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
    parameters. Search for the python file with the data retrieval
    layer implementation in the working directory first. If the file is
    not found there, look for it in the OnDA folder structure.

    Args:

        monitor_params (:obj:`onda.utils.parameters.MonitorParams`):
            a MonitorParams object containing the monitor
            parameters from the configuration file.

    Returns:

        module: the imported data retrieval layer.
    """
    try:

        # Try to import the module from the current folder.
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

        # Try to import the module from the OnDA folder structure.
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


def init_event_handling_funcs(monitor_params):
    """
    Retrieve event handling functions.

    Collect and return specific event handling functions, importing
    them from the data retrieval layer. Raise a
    MissingEventHandlingFunction exception if any function is not
    found.

    Args:

        monitor_params (:obj:`onda.utils.parameters.MonitorParams`):
            a MonitorParams object containing the monitor
            parameters from the configuration file.

    Returns:

        Dict: a dictionary with the event handling functions. The
        functions are stored in the dictionary with keys identical
        to their function names.

    Raises:

        MissingEventHandlingFunction: if an event handling function is
            not found.
    """

    # Import the data retrieval layer.
    data_ret_layer = import_data_retrieval_layer(monitor_params)

    # Create the dictionary that will store the recovered functions.
    event_handl_func_dict = {}

    # Iterate over a fixed list of functions.
    for func_name in [
            'initialize_event_source',
            'event_generator',
            'EventFilter',
            'open_event',
            'close_event',
            'get_num_frames_in_event'
    ]:

        # Try to retrieve the function. Raise an exception in case of
        # failure.
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


def init_data_extraction_funcs(monitor_params):
    """
    Retrieve data extraction functions.

    Collect and return the required data extraction functions from
    the data retrieval layers. Raise a
    MissingDataExtractionFunction exception if any function is not
    found.

    Args:

        monitor_params (:obj:`onda.utils.parameters.MonitorParams`):
            a MonitorParams object containing the monitor
            parameters from the configuration file.

    Returns:

        Dict: a dictionary with the data extraction functions. The
        functions are stored in the dictionary with keys identical
        to their function names.

    Raises:

        MissingDataExtractionFunction: if a data extraction function is
        not found.
    """

    # Read from the configuration file the list of required data
    # extraction functions.
    data_extraction_funcs = [
        x.strip() for x in monitor_params.get_param(
            section='Onda',
            parameter='required_data',
            type_=list,
            required=True
        )
    ]

    # Import the data retrieval layer.
    data_ret_layer = import_data_retrieval_layer(monitor_params)

    # Create the dictionary that will store the recovered functions.
    data_ext_func_dict = {}

    # Iterate over the list of functions.
    for func_name in data_extraction_funcs:

        # Try to retrieve the function. Raise an exception in case of
        # failure.
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


def init_psana_interface_funcs(monitor_params):
    """
    Retrieve the psana detector interface initialization functions.

    Collect and return the required psana Detector interface
    initialization functions from the data retrieval layer. Raise a
    MissingDataExtractionFunction exception if any function is not
    found

    Args:

        monitor_params (:obj:`onda.utils.parameters.MonitorParams`):
            a MonitorParams object containing the monitor
            parameters from the configuration file.

    Returns:

        Dict: a dictionary with the psana interface initialization
        functions. The functions are stored in the dictionary with keys
        identical to their function names.

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

    # Import the data retrieval layer.
    data_ret_layer = import_data_retrieval_layer(monitor_params)

    # Create the dictionary that will store the recovered functions.
    psana_interface_func_dict = {}

    # Iterate over the list of functions.
    for func_name in data_extraction_funcs:
        try:

            # Try to retrieve a function with the name obtained by
            # adding the '_init' suffix to the the data extraction
            # function name (This is the convention OnDA uses for
            # naming the psana detector initialization functions).
            # Raise an exception in case of failure.
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
    Import the peakfinder8 detector information.

    Import the peakfiner8 detector information for a specific detector
    from the data retrieval layer.

    Args:

        monitor_params (:obj:`onda.utils.parameters.MonitorParams`):
            a MonitorParams object containing the monitor
            parameters from the configuration file.

        detector: detector for which the peakfinder8 information must
            be recovered, identified by the name of the
            data extraction function used to extract its data (i.e.:
            "detector_data", "detector2_data", etc.).

    Returns:

        `:obj:onda.utils.named_tuples.Peakfinder8DetInfo`: the
        peakfinder8-related detector information.
    """
    # Import the data retrieval layer.
    data_ret_layer = import_data_retrieval_layer(monitor_params)

    # Import from the data retrieval layer the peakfinder8 info
    # retrieval function for the specified detector. The convention
    # that OnDA uses to name these function is:
    # get_peakfinder8_info_<detector_name>.
    get_pf8_info_func = getattr(
        data_ret_layer,
        'get_peakfinder8_info_{}'.format(detector)
    )

    # Call the imported function and return its return value.
    return get_pf8_info_func()


def get_file_extensions(monitor_params):
    """
    Import the file extension information.

    Import the file extension information from the data retrieval
    layer.

    Args:

        monitor_params (:obj:`onda.utils.parameters.MonitorParams`):
            a MonitorParams object containing the monitor
            parameters from the configuration file.

    Returns:

        Tuple: a tuple with the file extensions allowed for the
        detector(s) currently in use.
    """
    # Import the data retrieval layer.
    data_retrieval_layer = import_data_retrieval_layer(
        monitor_params
    )

    # Import from the data retrieval layer the file extension retrieval
    # function.
    file_extension_info_func = getattr(
        data_retrieval_layer,
        'get_file_extensions'
    )

    # Call the imported function and return its return value.
    return file_extension_info_func()


def get_hidra_transfer_type(monitor_params):
    """
    Get the HiDRA transport type currently used by OnDA.

    Get the HiDRA transport information used by the current OnDA data
    retrieval layer.

    Args:

        monitor_params (:obj:`onda.utils.parameters.MonitorParams`):
            a MonitorParams object containing the monitor
            parameters from the configuration file.

    Returns:

        str: astring enconding the HiDRA trasport type (the possible
        values are 'data' or 'metadata'.
    """
    # Import the data retrieval layer.
    data_retrieval_layer = import_data_retrieval_layer(
        monitor_params
    )

    # Import from the data retrieval layer the HiDRA transport type
    # retrieval function.
    hidra_transport_type_func = getattr(
        data_retrieval_layer,
        'get_hidra_transport_type'
    )

    # Call the imported function and return its return value.
    return hidra_transport_type_func()
