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
DataEvent structure.
"""
from __future__ import absolute_import, division, print_function

import sys
import types
from typing import Any, Callable, Dict  # pylint: disable=unused-import

from future.utils import iteritems

from onda.utils import exceptions


class DataEvent(object):
    """
    See documentaion of the '__init__' function.
    """

    def __init__(self, event_handling_funcs, data_extraction_funcs):
        # type: (Dict[str, Callable], Dict[str, Callable]) -> None
        """
        Data event.

        This object stores all the information related to a data event retrieved from a
        facility. Methods to open, close and manipulate the event (as well as extract
        information from it) are attached to each instance of this object at creation
        time.

        Arguments:

            event_handling_funcs (Dict[str, Callable]): a dictionary whose values are
                Event Handling functions to be attached to the object.

                * Five event handling functions must be defined:

                    - 'initalize_event_source'
                    - 'event_generator'
                    - 'open_even'
                    - 'close_event'
                    - 'get_num_frames_in_event'

                The dictionary must contain keys corresponding to these function names.

                * The dictionary values must store the corresponding function
                  implementation.

            data_extraction_funcs (Dict[str, Callable]): a dictionary whose values are
                Data Extraction functions to be attached to the object.

                * Each dictionary value must store a function implementetion that will
                  be attached to the object with a name defined by the corresponding
                  dictionary key.
        """
        self.open_event = types.MethodType(event_handling_funcs["open_event"], self)
        self.close_event = types.MethodType(event_handling_funcs["close_event"], self)
        self.get_num_frames_in_event = types.MethodType(
            event_handling_funcs["get_num_frames_in_event"], self
        )

        self.data = None
        self.metadata = None
        self.timestamp = None
        self.current_frame = None
        self.framework_info = {}
        self.data_extraction_functions = data_extraction_funcs

    def extract_data(self):
        # type: () -> Dict[str, Any]
        """
        Extracts data from event.

        This function calls all the Data Extraction functions that have been attached
        to the event object, and returns the extracted data.

        Returns:

            Dict[str, Any]: a dictionary storing the values returned by the data
            extraction functions.

            * Each dictionary key identifies a function. The corresponding dictionary
              value stores the the data return by each function.
        """
        data = {}
        try:
            for f_name, func in iteritems(self.data_extraction_functions):
                data[f_name] = func(self)
        # One should never do the following, but it is not possible to anticipate
        # every possible error raised by the facility frameworks.
        except Exception:  # pylint: disable=broad-except
            exc_type, exc_value = sys.exc_info()[:2]
            if exc_type is not None:
                raise exceptions.OndaDataExtractionError(
                    "OnDA Warning: Cannot interpret {0} event data due to the "
                    "following error: {1}: {2}".format(
                        func.__name__, exc_type.__name__, exc_value
                    )
                )

        return data
