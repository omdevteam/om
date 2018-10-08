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
from __future__ import absolute_import, division, print_function

import time

import numpy


class AgeEventFilter(object):
    """
    See __init__ for documentation.
    """

    def __init__(self,
                 monitor_params):
        """
        Filter events based on their 'age'.

        Reject files whose 'age' (the time between the data collection
        and the moment OnDA receives the data) is higher than a
        predefined threshold.

        Args:

            monitor_params (MonitorParams): a
                :obj:`~onda.utils.parameters.MonitorParams` object
                containing the monitor parameters from the
                configuration file.
        """
        # Read the rejection threshold from the configuration file
        # and store it in an attribute.
        rejection_threshold = monitor_params.get_param(
            section='DataRetrievalLayer',
            parameter='event_rejection_threshold',
            type_=float
        )

        if rejection_threshold:
            self._event_rejection_threshold = rejection_threshold
        else:
            self._event_rejection_threshold = 10000000000

    def should_reject(self,
                      event):
        """
        Decide if the event should be rejected.

        Args:

            event (Dict): a dictionary with the event data.

        Returns:

            bool: True if the event should be rejected. False if the
            event should be processed.
        """
        time_now = numpy.float64(time.time())  # pylint: disable=E1101
        if (time_now - event['timestamp']) > self._event_rejection_threshold:

            # Store the timestamp in the event dictionary so it does
            # not have to be extracted again if the timestamp is one
            # of the requested data sources.
            return True
        else:
            return False


class NullEventFilter(object):
    """
    See __init__ for documentation.
    """

    def __init__(self,
                 monitor_params):   # pylint: disable=W0613
        """
        Null filter.

        Do not filter events.

        Args:

            monitor_params (MonitorParams): a
                :obj:`~onda.utils.parameters.MonitorParams` object
                containing the monitor parameters from the
                configuration file.
        """
        pass

    def should_reject(self,
                      event):     # pylint: disable=W0613
        """
        Decide if the event should be rejected.

        Args:

            event (Dict): a dictionary with the event data.

        Returns:

            bool: True if the event should be rejected. False if the
            event should be processed.
        """
        return False
