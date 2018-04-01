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


def _import_function_from_layer(layer,
                                name,
                                decorator):
    # Import a function from a layer, adding the decorator, if
    # provided, to the name. If a decorator is provided, try first to
    # import the function with the decorated name from the specified
    # layer. If this fails, try to import the function with the
    # undecorated name instead. When no decorator is provided, try
    # directly to import the function with the undecorated name.
    if decorator is not None:
        try:
            return getattr(layer, '{0}_{1}'.format(name, decorator))
        except AttributeError:
            return getattr(layer, name)
    else:
        return getattr(layer, name)


def _import_function(func_name,
                     data_recovery_layer,
                     detector_layer):
    # Import a function from the specified layers. Try to import the
    # function from the detector layer. If this fails, try to import it
    # from the data recovery layer. For each layer, first try to import
    # the data-recovery-specific version of the function, if this
    # fails, try to import the generic version of the function.
    data_recovery_layer_name = data_recovery_layer.__name__.split('.')[-1]
    try:
        return _import_function_from_layer(
            layer=detector_layer,
            name=func_name,
            decorator=data_recovery_layer_name
        )
    except AttributeError:
        return _import_function_from_layer(
            layer=data_recovery_layer,
            name=func_name,
            decorator=data_recovery_layer_name
        )


def import_detector_layer(monitor_params):
    """
    Import the detector layer specified in the configuration file.

    Args:

        monitor_params (MonitorParams): a MonitorParams object
            containing the monitor parameters from the
            configuration file.

    Returns:

        object: the imported detector layer as a module
    """
    detector_layer = importlib.import_module(
        'onda.detector_layer.{0}'.format(
            monitor_params.get_param(
                section='Onda',
                parameter='detector_layer',
                type_=str,
                required=True
            )
        )
    )
    return detector_layer


def import_func_from_detector_layer(func_name,
                                    monitor_params):
    """
    Import the specified function from the detector layer.

    Import the requested function from the correct detector layer,
    correctly choosing between specific and non specific-version of the
    function.

    Args:

        func_name (str): name of the function to import

        monitor_params (MonitorParams): a MonitorParams object
            containing the monitor parameters from the
            configuration file.

    Returns:

        Callable: the imported function.
    """
    detector_layer = import_detector_layer(monitor_params)

    # Use as 'decorator' the name of the data recovery layer.
    data_recovery_layer_name = monitor_params.get_param(
        section='Onda',
        parameter='data_recovery_layer',
        type_=str,
        required=True
    )
    try:
        function = _import_function_from_layer(
            layer=detector_layer,
            name=func_name,
            decorator=data_recovery_layer_name
        )
    except AttributeError:
        raise_from(
            exc=RuntimeError(
                "Function {} not defined in the "
                "detector_layer.".format(func_name)
            ),
            cause=None
        )

    return function


def import_data_recovery_layer(monitor_params):
    """
    Import the data recovery layer specified in the configuration
    file.

    Args:

        monitor_params (MonitorParams): a MonitorParams object
            containing the monitor parameters from the
            configuration file.

    Returns:

        object: the imported data recovery layer as a module.
    """
    detector_layer = importlib.import_module(
        'onda.data_recovery_layer.{0}'.format(
            monitor_params.get_param(
                section='Onda',
                parameter='data_recovery_layer',
                type_=str,
                required=True
            )
        )
    )
    return detector_layer


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
    data_rec_layer = import_data_recovery_layer(monitor_params)
    detector_layer = import_detector_layer(monitor_params)

    # Recover the functions and store them into a list.
    event_handl_func_list = []
    for func_name in [
            'initialize_event_source',
            'event_generator',
            'open_event',
            'close_event',
            'get_num_frames_in_event'
    ]:
        try:
            event_handl_func_list.append(
                _import_function(
                    func_name=func_name,
                    data_recovery_layer=data_rec_layer,
                    detector_layer=detector_layer
                )
            )
        except AttributeError:
            raise_from(
                exc=exceptions.MissingEventHandlingFunction(
                    "Event handling function {0} is not "
                    "defined.".format(func_name)
                ),
                cause=None
            )

    # Initialize a tuple with the content of the list.
    EventHandlingFuncs = collections.namedtuple(  # pylint: disable=C0103
        typename='EventHandlingFuncs',
        field_names=[
            'initialize_event_source',
            'event_generator',
            'open_event',
            'close_event',
            'get_num_frames_in_event'
        ]
    )

    return EventHandlingFuncs(*event_handl_func_list)


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
    detector_layer = import_detector_layer(monitor_params)
    data_rec_layer = import_data_recovery_layer(monitor_params)
    func_list = []
    for func_name in data_extraction_funcs:
        try:
            func_list.append(
                _import_function(
                    func_name=func_name,
                    data_recovery_layer=data_rec_layer,
                    detector_layer=detector_layer
                )
            )
        except AttributeError:
            raise_from(
                exc=exceptions.MissingDataExtractionFunction(
                    "Data extraction function {0} not "
                    "defined".format(func_name)
                ),
                cause=None
            )

    DataExtractionFuncs = collections.namedtuple(  # pylint: disable=C0103
        typename='DataExtractionFuncs',
        field_names=data_extraction_funcs
    )
    return DataExtractionFuncs(*func_list)


def init_psana_detector_int_funcs(monitor_params):
    """
    Recover and collect the psana Detector interface init functions.

    Collect and return the required psana Detector interface init
    functions from various layers. Recover from the configuration file
    the list of required data extraction functions. Look for
    data-recovery-specific versions of the functions in the detector
    layer first, and if they are not found, in the data recovery layer
    later. Raise a MissingDataExtractionFunction exception if a
    function is not found anywhere.

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
    detector_layer = import_detector_layer(monitor_params)
    data_rec_layer = import_data_recovery_layer(monitor_params)
    func_list = []
    for func_name in data_extraction_funcs:
        try:
            func_list.append(
                _import_function(
                    func_name=func_name,
                    data_recovery_layer=data_rec_layer,
                    detector_layer=detector_layer
                )
            )
        except AttributeError:
            raise_from(
                exc=exceptions.MissingPsanaInitializationFunction(
                    "Psana Detector interface initialization function "
                    "{} not defined".format(func_name)
                ),
                cause=None
            )

    PsanaInitializationFuncs = collections.namedtuple(  # pylint: disable=C0103
        typename='PsanaInitializationFuncs',
        field_names=data_extraction_funcs
    )
    return PsanaInitializationFuncs(*func_list)
