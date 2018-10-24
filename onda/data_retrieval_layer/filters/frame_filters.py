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
<<<<<<< HEAD
from __future__ import absolute_import, division, print_function
=======
#
#    Copyright © 2014-2018 Deutsches Elektronen-Synchrotron DESY,
#    a research centre of the Helmholtz Association.
"""
Frame filters.

Filters to skip the processing of single frames according to various
criteria.
"""
from __future__ import absolute_import, division, print_function

>>>>>>> develop

class NullFrameFilter(object):
    """
    Null frame filter.

    This filter does not filter any frames.
    """

    def __init__(self, monitor_params):  # pylint: disable=W0613
        """
        Initializes the NullFrameFilter class.

        Args:

            monitor_params (MonitorParams): a
                :obj:`~onda.utils.parameters.MonitorParams` object
                containing the monitor parameters from the
                configuration file.
        """
        pass

    def should_reject(self,
                      num_frames_in_event,  # pylint: disable=W0613
                      frame_offset):     # pylint: disable=W0613
        """
        Decides if the frame should be rejected (not processed).

        For this null frame filter, this function never rejects
        frames.

        Args:

            event (Dict): a dictionary with the event data.

        Returns:

            bool: True if the frame should be rejected. False if the
            frame should be processed.
        """
        return False


class IndexBasedFrameFilter(object):
    """
    Index-based frame filter.

    This filter looks at the index of the frame within the event, and
    rejects events whose index is included in a list provided by the
    user.
    """

    def __init__(
            self,
            monitor_params
    ):
        """
        Initializes the IndexBasedFrameFilter class.

        Args:

            monitor_params (MonitorParams): a
                :obj:`~onda.utils.parameters.MonitorParams` object
                containing the monitor parameters from the
                configuration file.
        """
        # Reads the list of frames to reject from the configuration
        # file and stores it in an attribute.
        frame_indexes_to_reject = monitor_params.get_param(
            section='General',
            parameter='frame_indexes_to_skip',
            type_=list
        )

        if not frame_indexes_to_reject:
            # If no list of frame indexes to reject is provided, stores
            # an empty list.
            self._frame_idxs_to_rej = tuple()
        else:
            self._frame_idxs_to_rej = tuple(frame_indexes_to_reject)

    def should_reject(
            self,
            num_frames_in_event,
            frame_offset
    ):
        """
        Decides if the frame should be rejected (not processed).

        Args:

            event (Dict): a dictionary with the event data.

        Returns:

            bool: True if the frame should be rejected. False if the
            frame should be processed.
        """
        if num_frames_in_event + frame_offset in self._frame_idxs_to_rej:
            return True
        else:
            return False
