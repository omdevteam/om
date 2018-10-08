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

class NullFrameFilter(object):
    """
    See __init__ for documentation.
    """

    def __init__(self,
                 monitor_params):   # pylint: disable=W0613
        """
        Null filter.

        Do not filter frames.

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
        Decide if the event should be rejected.

        Args:

            num_frames_in_event (int): number of frames in the
                event under examination.

            frame_offset (int): offset, within the event, of the frame
                under examination.

        Returns:

            bool: True if the event should be rejected. False if the
            event should be processed.
        """
        return False


class IndexBasedFrameFilter(object):
    """
    See __init__ for documentation.
    """

    def __init__(self,
                 monitor_params):   # pylint: disable=W0613
        """
        Filter frames based on the frame index.

        Reject the frame if its index within the event appears in a
        provided list of frame indexes reject.

        Args:

            monitor_params (MonitorParams): a
                :obj:`~onda.utils.parameters.MonitorParams` object
                containing the monitor parameters from the
                configuration file.
        """
        # Read the list of frames to reject from the configuration file
        # and store it in an attribute.
        frame_indexes_to_reject = monitor_params.get_param(
            section='General',
            parameter='frame_indexes_to_skip',
            type_=list
        )

        if not frame_indexes_to_reject:

            # If no list of frame indexes to reject is provided, store
            # an empty list.
            self._frame_idxs_to_rej = tuple()

        else:
            self._frame_idxs_to_rej = tuple(frame_indexes_to_reject)

    def should_reject(self,
                      num_frames_in_event,  # pylint: disable=W0613
                      frame_offset):     # pylint: disable=W0613
        """
        Decide if the event should be rejected.

        Args:

            num_frames_in_event (int): number of frames in the
                event under examination.

            frame_offset (int): offset, within the event, of the frame
                under examination.

        Returns:

            bool: True if the event should be rejected. False if the
            event should be processed.
        """
        if (
                (num_frames_in_event + frame_offset) in self._frame_idxs_to_rej
        ):
            return True
        else:
            return False
