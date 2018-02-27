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
Functions and classes to process data stored in files.

Exports:

    Functions:

        event_generator: initalize event recovery from files.

        initialize_event_handling_functions: initialize the data
        extraction functions, recovering the correct functions from the
        detector layer.

        initialize_data_extraction_functions: initialize the data
        extraction functions, recovering the correct functions from the
        detector layer.

    Classes:

        EventFilter (class): filter and reject events.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import collections
import importlib
import os.path

import numpy
from future.utils import raise_from

from onda.utils import exceptions


def _import_detector_layer(monitor_params):
    # Import the detector layer.
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


def event_generator(source, node_role, node_rank, mpi_pool_size,
                    _):
    """
    Initialize the event recovery from files.

    Initialize the recovery of events from files. When called on a worker node,
    read a list of files to be processed from the file specified by the
    'source' parameter, then return an iterator over the portion of the list
    that should be  processed by the worker node calling the function (This
    function is a python generator). When called on the master node, do
    nothing.

    Args:

        source (str): the full path to a file containing the list of files
            to be processed (their full path).

        node_rank (int): rank of the node where the function is called

        mpi_pool_size (int): size of the node pool that includes the node
            where the function is called.

        monitor_params (:obj:`onda.utils.parameters.MonitorParameters`): an
            object of type MonitorParameters with the monitor parameters.

     Yields:

        Dict: A dictionary containing the metadata of a file from the list.
    """
    if node_role == 'worker':
        # Open the source file and read the list of files to process. Raise an
        # exception in case of failure.
        try:
            with open(source, 'r') as fhandle:
                filelist = fhandle.readlines()
        except OSError:
            raise_from(
                exc=RuntimeError(
                    "Error reading the {} source file.".format(
                        source
                    )
                ),
                source=None
            )

        # Compute how many files the current worker node should process. Split
        # the files as equally as possible amongst the workers, with the last
        # worker getting a smaller number of files if the number of files to
        # be processed cannot be exactly divided by the number of workers.
        # Then extract the portion of the list that should be processed by
        # the current worker.
        mylength = int(
            numpy.ceil(
                len(filelist) / float(mpi_pool_size - 1)
            )
        )
        myfiles = filelist[
            ((node_rank - 1) * mylength):(node_rank * mylength)
        ]

        for entry in myfiles:
            # Create the event dictionary object. Add two custom entries that
            # are needed by the data extraction functions: the full path
            # to the file, and the file creation date (a first approximation
            # of the timestamp). Then yield the event.
            event = {'full_path': entry}
            event['file_creation_time'] = os.stat(entry).st_crtime

            yield event


class EventFilter(object):
    """
    Filter events.

    Reject files whose extensions does not match the detector file extensions.
    """

    def __init__(self, monitor_params):
        """
        Initialize the EventFilter class.

        Args:

            monitor_params (:obj:`onda.utils.parameters.MonitorParameters`):
            an object of type MonitorParameters with the monitor parameters.
        """
        # Recover the list of allowed file extensions from the detector layer
        # and store it in an attribute.
        detector_layer = _import_detector_layer(monitor_params)
        self._file_extensions = detector_layer.get_file_extensions()

    def should_reject(self, event):
        """
        Decide if the event should be rejected based on the list of extensions
        allowed for the detector in use.

        Args:

            event (dict): a dictionary with the event data.

        Returns:

            bool: True if the event should be rejected. False if the event
            should be processed.
        """
        # Check if the filename ends with one of the allowed file extensions.
        # If it doesn't, reject the file.
        if os.path.basename(event).endswith(self._file_extensions):
            return False
        return True


def initialize_event_handling_functions(monitor_params):
    """
    Recover anc collect event handling functions.

    Collect and return filelist-specific event handling functions, importing
    them from the detector layer when necessary.

    Args:

        monitor_params (:obj:`onda.utils.parameters.MonitorParameters`):
            an object of type MonitorParameters with the monitor parameters.

    Returns:

        Tuple[Callable, Callable, Callabe, Callable]: a tuple with the four
            event handling functions: event_generator, open_event,
            close_event, num_frames_in_event. The tuple is named: the four
            fields are respectively called 'event_generator', 'open_event',
            'close_event', 'num_frames_in_event'.
    """
    detector_layer = _import_detector_layer(monitor_params)

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

    # Instantiate the tuple filling the right functions. The event_generator
    # is defined here in the data recovery layer, while for the other three
    # functions, filelist-specific versions are imported from the detector
    # layer.
    return EventHandlingFuncs(
        event_generator,
        detector_layer.open_event_filelist,
        detector_layer.close_event_filelist,
        detector_layer.num_frames_event_filelist
    )


def initialize_data_extraction_functions(monitor_params):
    """
    Recover and collect data extraction functions.

    Collect and return the required data extraction functions from various
    layers. Recover from the configuration file the list of required data
    extraction function. Look for filelist-specific versions of the functions
    in the detector layer first, and if they are not found, in the data
    recovery layer later. Raises a MissingDataExtractionFunction if
    a function is not found anywhere.

    Args:

        monitor_params (:obj:`onda.utils.parameters.MonitorParameters`):
            an object of type MonitorParameters with the monitor parameters.

    Returns:

        Tuple[Callable, Callable, Callabe, Callable]: a tuple with the four
        event handling functions: event_generator, open_event,
        close_event, num_frames_in_event. The tuple is named: the four
        fields are respectively called 'event_generator', 'open_event',
        'close_event', 'num_frames_in_event'.

    Raises:

        MissingDataExtractionFunction: if an filelist-specific data extraction
        function is not found anywhere.
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

    detector_layer = _import_detector_layer(monitor_params)
    for func in data_extraction_funcs:
        decorated_func_name = '{0}_filelist'.format(func)

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
