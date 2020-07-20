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
Dynamic import from various OM layers.

This module contains functions that import required modules, classes and functions from
different parts of OM.
"""
from __future__ import absolute_import, division, print_function

import importlib
from types import ModuleType
from typing import Any, Callable, Dict, Generator, List, Tuple

from future.utils import raise_from  # type: ignore
from mypy_extensions import TypedDict

from om.utils import data_event, exceptions, parameters


TypeEventGenerator = Generator[data_event.DataEvent, None, None]

TypeEventHandlingFuncs = TypedDict(
    "TypeEventHandlingFuncs",
    {
        "initialize_event_source": Callable[[str, int, parameters.MonitorParams], Any],
        "event_generator": Callable[
            [str, int, int, parameters.MonitorParams], TypeEventGenerator,
        ],
        "get_num_frames_in_event": Callable[[data_event.DataEvent], int],
        "open_event": Callable[[data_event.DataEvent], None],
        "close_event": Callable[[data_event.DataEvent], None],
    },
    total=False,
)


def import_processing_layer(processing_layer_filename):
    # type: (str) -> ModuleType
    """
    Imports the specified Processing Layer.

    This function searches for the python file with the implementation of the
    Processing Layer in the working directory first. If the file is not found there,
    this function looks for it in the standard OM folder structure.

    Arguments:

        processing_layer_filename (str): the name of a python file containing the
            processing layer implementation.

    Returns:

        ModuleType: the imported processing layer.
    """
    try:
        processing_layer = importlib.import_module(
            processing_layer_filename
        )  # type: ModuleType
    except ImportError:
        processing_layer = importlib.import_module(
            "om.processing_layer.{0}".format(processing_layer_filename)
        )

    return processing_layer


def import_data_retrieval_layer(data_retrieval_layer_filename):
    # type: (str) -> ModuleType
    """
    Imports the specified Data Retrieval Layer.

    This function searches for the python file with the implementation of the
    Data Retrieval Layer in the working directory first. If the file is not found
    there, this function looks for it in the standard OM folder structure.

    Arguments:

        data_retrieval_layer_filename (str): the name of a python file containing the
            processing layer implementation.

    Returns:

        ModuleType: the imported processing layer.
    """
    try:
        data_retrieval_layer = importlib.import_module(
            data_retrieval_layer_filename
        )  # type: ModuleType
    except (ImportError, ModuleNotFoundError):
        print(
            "om.data_retrieval_layer.profiles.{0}".format(data_retrieval_layer_filename)
        )
        data_retrieval_layer = importlib.import_module(
            "om.data_retrieval_layer.profiles.{0}".format(data_retrieval_layer_filename)
        )

    return data_retrieval_layer


def import_parallelization_layer(parallelization_layer_filename):
    # type: (str) -> ModuleType
    """
    Imports the specified Parallelization Layer.

    This function searches for the python file with the implementation of the
    Parallelization Layer in the working directory first. If the file is not found
    there, this function looks for it in the standard OM folder structure.

    Arguments:

        processing_layer_filename (str): the name of a python file containing the
            processing layer implementation.

    Returns:

        ModuleType: the imported processing layer.
    """
    try:
        parallelization_layer = importlib.import_module(
            parallelization_layer_filename
        )  # type: ModuleType
    except ImportError:
        parallelization_layer = importlib.import_module(
            "om.parallelization_layer.{0}".format(parallelization_layer_filename)
        )

    return parallelization_layer


def get_event_handling_funcs(data_retrieval_layer):  # noqa: C901
    # type: (ModuleType) -> TypeEventHandlingFuncs
    """
    Retrieves Event Handling Functions from the Data Retrieval Layer.

    This function retrieves the following Event Handling functions:

    - 'initialize_event_source'
    - 'event_generator'
    - 'open_even'
    - 'close_event'
    - 'get_num_frames_in_event'

    Arguments:

        data_retrieval_layer (ModuleType): the Data Retrieval Layer module.

    Returns:

        TypeEventHandlingFuncs: a dictionary whose keys are the names of the Event
        Handling Functions, and whose values are their implementations.

    Raises:

        :class:`~om.utils.exceptions.OmMissingEventHandlingFunctionError`: if one
            of the Event Handling Function is not found in the Data Retrieval Layer.
    """
    event_handling_funcs = {}  # type: TypeEventHandlingFuncs

    try:
        event_handling_funcs["initialize_event_source"] = getattr(
            data_retrieval_layer, "initialize_event_source"
        )
    except AttributeError as exc:
        raise_from(
            exc=exceptions.OmMissingEventHandlingFunctionError(
                "Event handling function initialize_event_source is not defined."
            ),
            cause=exc,
        )

    try:
        event_handling_funcs["event_generator"] = getattr(
            data_retrieval_layer, "event_generator"
        )
    except AttributeError as exc:
        raise_from(
            exc=exceptions.OmMissingEventHandlingFunctionError(
                "Event handling function event_generator is not defined."
            ),
            cause=exc,
        )

    try:
        event_handling_funcs["open_event"] = getattr(data_retrieval_layer, "open_event")
    except AttributeError as exc:
        raise_from(
            exc=exceptions.OmMissingEventHandlingFunctionError(
                "Event handling function open_event is not defined."
            ),
            cause=exc,
        )

    try:
        event_handling_funcs["close_event"] = getattr(
            data_retrieval_layer, "close_event"
        )
    except AttributeError as exc:
        raise_from(
            exc=exceptions.OmMissingEventHandlingFunctionError(
                "Event handling function close_event is not defined."
            ),
            cause=exc,
        )

    try:
        event_handling_funcs["get_num_frames_in_event"] = getattr(
            data_retrieval_layer, "get_num_frames_in_event"
        )
    except AttributeError as exc:
        raise_from(
            exc=exceptions.OmMissingEventHandlingFunctionError(
                "Event handling function get_num_frames_in_event is not defined."
            ),
            cause=exc,
        )

    return event_handling_funcs


def get_data_extraction_funcs(
    required_data,  # type: List[str]
    data_retrieval_layer,  # type: ModuleType
):
    # type: (...) -> Dict[str, Callable[[data_event.DataEvent], Any]]
    """
    Retrieves Data Extraction Functions from the Data Retrieval Layer.

    Arguments:

        required_data (List[str]): a list with the the names of the Data Extraction
            Functions that must be retrieved.

        data_retrieval_layer (TypeModule): the Data Retrieval Layer module.

    Returns:

       Dict[str, Callable[[data_event.DataEvent], Any]]: a dictionary whose keys match
       the names in the 'required_data' argument, and whose values store the
       corresponding function implementations.

    Raises:

        :class:`~om.utils.exceptions.OmMissingDataExtractionFunctionError`: if a
            required Data Extraction Function is not found in the Data Retieval Layer.
    """
    data_extraction_funcs_list = [x.strip() for x in required_data]  # type: List[str]
    data_extraction_funcs = {}  # type: Dict[str, Callable[[data_event.DataEvent], Any]]
    for func_name in data_extraction_funcs_list:
        try:
            data_extraction_funcs[func_name] = getattr(data_retrieval_layer, func_name)
        except AttributeError as exc:
            raise_from(
                exc=exceptions.OmMissingDataExtractionFunctionError(
                    "Data extraction function {0} not defined".format(func_name)
                ),
                cause=exc,
            )

    return data_extraction_funcs


def get_psana_detector_interface_funcs(
    required_data,  # type: List[str]
    data_retrieval_layer,  # type: ModuleType
):
    # type: (...) -> Dict[str, Callable[[str], Any]]
    """
    Retrieves the psana Detector Interface Initialization Functions.

    Arguments:

        required_data (List[str]): a list with the names of the psana Detector
            Interface Initialization Functions that must be retrieved.

        data_retrieval_layer (TypeModule): the Data Retrieval Layer module.

    Returns:

        Dict[str, Callable[[str], Any]]: a dictionary whose keys match the names in the
        'required_data' argument, but with an '_init' extension appended at the end of
        each name. The corresponding dictionary values store the function
        implementations.

    Raises:

        :class:`~om.utils.exceptions.MissingPsanaInitializationFunctionError`: if a
            required psana Detector Interface Initialization Function is not found in
            the Data Retrieval layer.
    """
    psana_detector_interface_func_list = [
        x.strip() for x in required_data
    ]  # type: List[str]
    psana_detector_interface_funcs = {}  # type: Dict[str, Callable[[str], Any]]
    for func_name in psana_detector_interface_func_list:
        try:
            # Tries to retrieve a function with the name obtained by adding the
            # '_init' suffix to the the data extraction function name (This is the
            # convention OM uses for naming the psana detector initialization
            # functions).
            psana_detector_interface_funcs[func_name] = getattr(
                data_retrieval_layer, "{0}_init".format(func_name)
            )
        except AttributeError as exc:
            raise_from(
                exc=exceptions.OmMissingPsanaInitializationFunctionError(
                    "Psana Detector interface initialization function {0} "
                    "not defined".format(func_name)
                ),
                cause=exc,
            )

    return psana_detector_interface_funcs


def get_peakfinder8_info(monitor_params):
    # type: (parameters.MonitorParams) -> Dict[str, int]
    """
    Gets the peakfinder8 information for the main x-ray detector.

    This function retrieves the peakfinder8 information for the main x-ray detector
    currently defined in the Data Retrieval Layer.

    Arguments:

        monitor_params (:class:`~om.utils.parameters.MonitorParams`): an object
            storing the OM monitor parameters from the configuration file.

    Returns:

        Dict[str, int]: a named tuple storing the peakfinder8 information.
    """
    data_retrieval_layer_filename = monitor_params.get_param(
        group="om", parameter="data_retrieval_layer", parameter_type=str, required=True,
    )  # type: str
    data_retrieval_layer = import_data_retrieval_layer(
        data_retrieval_layer_filename
    )  # type: ModuleType
    peakfinder8_retrieval_func = getattr(
        data_retrieval_layer, "get_peakfinder8_info"
    )  # type:  Callable[[], Dict[str, int]]

    return peakfinder8_retrieval_func()


def get_file_extensions(monitor_params):
    # type: (parameters.MonitorParams) -> Tuple[str, ...]
    """
    Retrieves a list of extensions used by files written by the main x-ray detector.

    This function retrieves the file extensions used by the main x-ray detector
    currently defined in the Data Retrieval Layer.

    Arguments:

        monitor_params (:class:`~om.utils.parameters.MonitorParams`): an object
            storing the OM monitor parameters from the configuration file.

    Returns:

        Tuple[str, ...]: a tuple storing the file extensions
    """
    data_retrieval_layer_filename = monitor_params.get_param(
        group="om", parameter="data_retrieval_layer", parameter_type=str, required=True,
    )  # type: str
    data_retrieval_layer = import_data_retrieval_layer(
        data_retrieval_layer_filename
    )  # type: ModuleType
    file_extension_info_func = getattr(
        data_retrieval_layer, "get_file_extensions"
    )  # type:  Callable[[], Tuple[str, ...]]

    return file_extension_info_func()


def get_hidra_transfer_type(monitor_params):
    # type: (parameters.MonitorParams) -> str
    """
    Gets the HiDRA transport type for the main x-ray detector.

    This function retrieves the standard HiDRA data transfer type for the main x-ray
    detector currently defined in the Data Retrieval Layer.

    Arguments:

        monitor_params (:class:`~om.utils.parameters.MonitorParams`): an object
            storing the OM monitor parameters from the configuration file.

    Returns:

        str: the HiDRA transport type for the x-ray detector ('data' or 'metadata').
    """
    data_retrieval_layer_filename = monitor_params.get_param(
        group="om", parameter="data_retrieval_layer", parameter_type=str, required=True,
    )  # type: str
    data_retrieval_layer = import_data_retrieval_layer(
        data_retrieval_layer_filename
    )  # type: ModuleType
    hidra_transport_parameter_typefunc = getattr(
        data_retrieval_layer, "get_hidra_transport_type"
    )  # type: Callable[[], str]

    return hidra_transport_parameter_typefunc()
