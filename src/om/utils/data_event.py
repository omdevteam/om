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
DataEvent structure.

This module contains the DataEvent class, which stores all information related to a
data event.
"""
from __future__ import absolute_import, division, print_function

import sys
import types
from typing import Any, Callable, Dict

from future.utils import iteritems

from onda.utils import exceptions


class DataEvent(object):
    """
    See documentation of the '__init__' function.
    """

    def __init__(self, event_handling_funcs, data_extraction_funcs):
        # type: (Dict[str, Callable], Dict[str, Callable]) -> None
        """
        Data event.

        This class stores all the information related to a data event. Methods to
        open, close and manipulate the event are attached to each instance of this
        class at creation time, along with functions to extract data from it.

        Arguments:

            event_handling_funcs (Dict[str, Callable]): a dictionary containing
                Event Handling functions to be attached to the class instance being
                created.

                * Five event handling functions must be defined:

                  - 'initialize_event_source'
                  - 'event_generator'
                  - 'open_even'
                  - 'close_event'
                  - 'get_num_frames_in_event'

                * The dictionary must contain keys corresponding to all these function
                  names.

                * The corresponding dictionary values must store the function
                  implementations.

            data_extraction_funcs (Dict[str, Callable]): a dictionary containing
                Data Extraction functions to be attached to the class instance being
                created.

                * Each dictionary value must store a function implementation.

                * The corresponding dictionary key will define the name with which the
                  function will be attached to the class instance.
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
        Extracts data from an event.

        This function calls in sequence all the Data Extraction functions that have
        been attached to the event, and returns the extracted data.

        Returns:

            Dict[str, Any]: a dictionary storing the values returned by the Data
            Extraction functions.

            * Each dictionary key identifies a function attached to the event.

            * The corresponding dictionary value stores the data returned by the
              function.
        """
        data = {}
        try:
            for f_name, func in iteritems(self.data_extraction_functions):
                data[f_name] = func(self)
        # One should never do the following, but it is not possible to anticipate
        # every possible error raised by the facility frameworks.
        except Exception:
            exc_type, exc_value = sys.exc_info()[:2]
            if exc_type is not None:
                raise exceptions.OndaDataExtractionError(
                    "OnDA Warning: Cannot interpret {0} event data due to the "
                    "following error: {1}: {2}".format(
                        func.__name__, exc_type.__name__, exc_value
                    )
                )

        return data
