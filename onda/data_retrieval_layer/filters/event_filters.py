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
Event filters.

Filters to skip the processing of events according to various criteria.
"""
from __future__ import absolute_import, division, print_function

import os.path
import time

import numpy

from onda.utils import dynamic_import


class NullEventFilter(object):
    """
    Null event filter.

    This filter does not filter any events.
    """

    def __init__(
            self,
            monitor_params
    ):
        """
        Initializes the NullEventFilter class.

        Args:

            monitor_params (MonitorParams): a
                :obj:`~onda.utils.parameters.MonitorParams` object
                containing the monitor parameters from the
                configuration file.
        """
        del monitor_params
        # No initialization needed. This function does nothing.

    def should_reject(
            self,
            event
    ):
        """
        Decides if the event should be rejected (not processed).

        For this null event filter, this function never rejects
        events.

        Args:

            event (Dict): a dictionary with the event data.

        Returns:

            bool: True if the event should be rejected. False if the
            event should be processed.
        """
        del event


class AgeEventFilter(object):
    """
    Age-based event filter.

    This filter rejects events whose 'age' (the time between the data
    collection and the moment OnDA receives the data) is higher than a
    predefined threshold.
    """

    def __init__(
            self,
            monitor_params
    ):
        """
        Initializes the AgeEventFilter class.

        Args:

            monitor_params (MonitorParams): a
                :obj:`~onda.utils.parameters.MonitorParams` object
                containing the monitor parameters from the
                configuration file.
        """
        # Reads the rejection threshold from the configuration file
        # and stores it in an attribute.
        rejection_threshold = monitor_params.get_param(
            section='DataRetrievalLayer',
            parameter='event_rejection_threshold',
            type_=float
        )

        if rejection_threshold:
            self._event_rejection_threshold = rejection_threshold
        else:
            # If no threshold is provided, uses a very high threshold
            # (more than 300 years).
            self._event_rejection_threshold = 10000000000


    def should_reject(
            self,
            event
    ):
        """
        Decides if the event should be rejected (not processed).

        Args:

            event (Dict): a dictionary with the event data.

        Returns:

            bool: True if the event should be rejected. False if the
            event should be processed.
        """
        time_now = numpy.float64(time.time())  # pylint: disable=no-member
        if (time_now - event['timestamp']) > self._event_rejection_threshold:
            return True
        else:
            return False


class ExtensionEventFilter(object):
    """
    FIle-extension-based event filter.

    This filter looks at the file from which an event has been
    retrieved (when applicable), extracts its extension and compares
    it to the list of extensions used with files written by the
    detector(s) being used. It rejects the event if the file does not
    have the correct extension.
    """

    def __init__(
            self,
            monitor_params
    ):
        """
        Initializes the ExtensionEventFilter class.

        Args:

            monitor_params (MonitorParams): a
                :obj:`~onda.utils.parameters.MonitorParams` object
                containing the monitor parameters from the
                configuration file.
        """
        self._file_extensions = dynamic_import.get_file_extensions(
            monitor_params
        )

    def should_reject(
            self,
            event
    ):
        """
        Decides if the event should be rejected (not processed).

        Args:

            event (Dict): a dictionary with the event data.

        Returns:

            bool: True if the event should be rejected. False if the
            event should be processed.
        """
        if os.path.basename(event['full_path']).endswith(self._file_extensions):
            return False
        else:
            return True
