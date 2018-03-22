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

        initialize_event_handling_functions: initialize the
        data extraction functions, recovering the correct functions
        from the detector and data recovery layers.

        initialize_data_extraction_functions: initialize the
        data extraction functions, recovering the correct functions
        from the detector and data recovery layers.
"""
import collections
import importlib

from future.utils import raise_from

from onda.utils import exceptions


def import_detector_layer(monitor_params):
    """
    Import the detector layer specified in the configuration file.

    Args:

        monitor_params (Dict): a dictionary containing the monitor
            parameters from the configuration file, already converted
            to the corrected types.

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


def initialize_event_handling_functions(suffix,
                                        monitor_params):
    """
    Recover anc collect event handling functions.

    Collect and return specific event handling functions,
    importing them from the detector layer when necessary.

    Args:

        suffix (str): suffix to be added to the function names, in
            order to import data-recovery-specific versions of the
            handling functions.

        monitor_params (Dict): a dictionary containing the monitor
            parameters from the configuration file, already converted
            to the corrected types.

    Returns:

        Tuple[Callable, Callable, Callabe, Callable]: a tuple with the
            four event handling functions: event_generator, open_event,
            close_event, num_frames_in_event. The tuple is named: the
            four fields are respectively called 'event_generator',
            'open_event', 'close_event', 'num_frames_in_event'.
    """
    detector_layer = import_detector_layer(monitor_params)

    # Internal nametuple used to store the event handling functions.
    EventHandlingFuncs = collections.namedtuple(
        typename='EventHandlingFuncs',
        field_names=[
            'event_generator',
            'open_event',
            'close_event',
            'num_frames_in_event'
        ]
    )

    open_event = getattr(
        object=detector_layer,
        name='open_event_{}'.format(suffix)
    )

    close_event = getattr(
        object=detector_layer,
        name='close_event_{}'.format(suffix)
    )

    num_frames_event = getattr(
        object=detector_layer,
        name='num_frames_event_{}'.format(suffix)
    )

    # Instantiate the tuple filling the right functions. The
    # event_generator is defined here in the data recovery layer, while
    # for the other three functions, data-recovery-specific versions
    # are imported from the detector layer.
    return EventHandlingFuncs(
        globals()['event_generator'],
        open_event,
        close_event,
        num_frames_event
    )


def initialize_data_extraction_functions(suffix,
                                         monitor_params):
    """
    Recover and collect data extraction functions.

    Collect and return the required data extraction functions from
    various layers. Recover from the configuration file the list of
    required data extraction functions. Look for data-recovery-specific
    versions of the functions in the detector layer first, and if they
    are not found, in the data recovery layer later. Raise a
    MissingDataExtractionFunction if a function is not found anywhere.

    Args:

        suffix (str): suffix to be added to the function names, in
            order to import data-recovery-specific versions of the
            handling functions.

        monitor_params (Dict): a dictionary containing the monitor
            parameters from the configuration file, already converted
            to the corrected types.

    Returns:

        Tuple[Callable, Callable, Callabe, Callable]: a tuple with the
        four event handling functions: event_generator, open_event,
        close_event, num_frames_in_event. The tuple is named: the four
        fields are respectively called 'event_generator', 'open_event',
        'close_event', 'num_frames_in_event'.

    Raises:

        MissingDataExtractionFunction: if a data-recovery-specific data
        extraction function is not found anywhere.
    """
    func_list = []
    data_extraction_funcs = [
        x.strip() for x in monitor_params.get_param(
            section='Onda',
            parameter='required_data',
            type_=list,
            required=True
        )
    ]
    detector_layer = import_detector_layer(monitor_params)
    for func in data_extraction_funcs:
        decorated_func_name = '{0}_{1}'.format(func, suffix)
        try:
            func_list.append(
                getattr(
                    object=detector_layer,
                    name=decorated_func_name
                )
            )
        except AttributeError:
            try:
                func_list.append(
                    globals()[decorated_func_name]
                )
            except KeyError:
                raise_from(
                    exc=exceptions.MissingDataExtractionFunction(
                        "Data extraction function not defined for the"
                        "following data type: {0}".format(func)
                    ),
                    cause=None
                )

    # Internal nametuple used to store the data extractionfunctions.
    DataExtractionFuncs = collections.namedtuple(
        typename='DataExtractionFuncs',
        field_names=data_extraction_funcs
    )
    return DataExtractionFuncs(func_list)
