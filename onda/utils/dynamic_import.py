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
Functions for the dynamic importing of objects from different layers.

Exports:

    Functions:

        import_detector_layer: import the correct detector layer.

        import_data_recovery_layer: import the correct data recovery
            layer.

        import_func_from_detector_layer: import the correct function
            from the detector layer.

        init_event_handling_funcs: initialize the
            data extraction functions, recovering the correct functions
            from the detector and data recovery layers.

        init_data_extraction_funcs: initialize the
            data extraction functions, recovering the correct functions
            from the detector and data recovery layers.
"""
import collections
import importlib
from builtins import str  # pylint: disable=W0622

from future.utils import raise_from

from onda.utils import exceptions


def _import_data_retrieval_layer(monitor_params):
    # Import the data recovery layer specified in the configuration
    # file.
    data_retrieval_layer = importlib.import_module(
        'onda.data_retrieval_layer.profiles.{0}'.format(
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
    Recover and collect event handling functions.

    Collect and return specific event handling functions, importing
    them from various layers. Look for the all functions first in the
    detector layer, and if they are not found, in the data recovery
    layer. Raise a MissingEventHandlingFunction exception if a function
    is not found anywhere.

    Args:

        monitor_params (MonitorParams): a MonitorParams object
            containing the monitor parameters from the
            configuration file.

    Returns:

        Tuple[Callable, Callable, Callabe, Callable, Callable]: a tuple
        with the four event handling functions: event_generator,
        open_event,close_event, num_frames_in_event. The tuple is
        named: the five fields are respectively called
        'initialize_event_source', event_generator', 'open_event',
        'close_event', 'num_frames_in_event'.

    Raises:

        MissingEventHandlingFunction: if an event handling function is
            not found anywhere.
    """
    data_ret_layer = _import_data_retrieval_layer(monitor_params)

    # Recover the functions and store them into a list.
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


def init_data_extraction_funcs(monitor_params):
    """
    Recover and collect data extraction functions.

    Collect and return the required data extraction functions from
    various layers. Recover from the configuration file the list of
    required data extraction functions. Look for data-recovery-specific
    versions of the functions in the detector layer first, and if they
    are not found, in the data recovery layer later. Raise a
    MissingDataExtractionFunction exception if a function is not found
    anywhere.

    Args:

        suffix (str): suffix to be added to the function names, in
            order to import data-recovery-specific versions of the
            handling functions.

        monitor_params (MonitorParams): a MonitorParams object
            containing the monitor parameters from the
            configuration file.

    Returns:

        Tuple: a tuple with the requested data extraction functions.
        Every field in the tuple has the name of the corresponding
        data extraction function.

    Raises:

        MissingDataExtractionFunction: if a data extraction function is
        not found anywhere.
    """
    data_extraction_funcs = [
        x.strip() for x in monitor_params.get_param(
            section='Onda',
            parameter='required_data',
            type_=list,
            required=True
        )
    ]
    data_ret_layer = _import_data_retrieval_layer(monitor_params)
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


def init_psana_interface_funcs(monitor_params):
    """
    Recover and collect the psana Detector interface init functions.

    Collect and return the required psana Detector interface init
    functions from various layers. Recover from the configuration file
    the list of required data extraction functions. Look for
    the psana initialization functions in the detector layer first, and
    if they are not found, in the data recovery layer later. Raise a
    MissingDataExtractionFunction exception if a function is not found
    anywhere.

    Args:

        monitor_params (MonitorParams): a MonitorParams object
            containing the monitor parameters from the
            configuration file.

    Returns:

        Tuple: a tuple with the requested psana Detector interface
        initialization functions. Every field in the tuple has the name
        of the corresponding initialization function.

    Raises:

        MissingPsanaInitializationFunction: if a one of the functions
        is not found anywhere.
    """
    data_extraction_funcs = [
        x.strip() for x in monitor_params.get_param(
            section='Onda',
            parameter='required_data',
            type_=list,
            required=True
        )
    ]
    data_ret_layer = _import_data_retrieval_layer(monitor_params)
    psana_interface_func_dict = {}
    for func_name in data_extraction_funcs:
        try:
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
                         corresponding_to):
    data_retrieval_layer = _import_data_retrieval_layer(
        monitor_params
    )

    get_pf8_info_func = getattr(
        data_retrieval_layer,
        'get_peakfinder8_info_{}'.format(corresponding_to)
    )

    return get_pf8_info_func()
