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
# Copyright 2020 -2023 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Classes and function for handling data events.

This module contains classes and functions that manage and count data events processed
by OM.
"""
import sys
import time
from itertools import cycle
from typing import Any, Dict, Iterator, Union

from om.lib.parameters import get_parameter_from_parameter_group
from om.lib.rich_console import console, get_current_timestamp


class EventCounter:
    """
    See documentation for the `__init__` function.
    """

    def __init__(self, *, om_parameters: Dict[str, Any], node_pool_size: int) -> None:
        """
        Event count and management.

        This class stores all the information needed to count data events processed by
        OM.

        After this class has been initialized, it can be provided with information
        about OM's processed data events. The class can then be invoked to generate
        speed reports, and can be queried about whether the number of processed events
        requires data to be broadcast to external programs.

        Arguments:

            om_parameters: A set of OM configuration parameters collected together in a
                parameter group. The parameter group must contain the following entries:

                * `speed_report_interval`: The number of events that must pass between
                  consecutive speed reports from OM.

                * `data_broadcast_interval`: The number of events that must pas
                  between consecutive data broadcasts from OM.

                * `hit_frame_sending_interval`: How often the monitor should send
                  full detector frames to external programs, when events are labelled
                  as hits. If the value of this parameter is None, no hit frames are
                  ever sent. If the value is a number, it is the average number of hit
                  frames that OM skips before the next hit frame is broadcast to
                  external programs. Defaults to None.

                * `non_hit_frame_sending_interval`: How often the monitor should send
                  full detector frames to external programs, when events are labelled
                  as non-hits. If the value of this parameter is None, no non-hit frames
                  are ever sent. If the value is a number, it is the average number of
                  non-hit frames that OM skips before the next non-hit frame is
                  broadcast to external programs. Defaults to None.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        self._speed_report_interval: int = get_parameter_from_parameter_group(
            group=om_parameters,
            parameter="speed_report_interval",
            parameter_type=int,
        )

        self._data_broadcast_interval: int = get_parameter_from_parameter_group(
            group=om_parameters,
            parameter="data_broadcast_interval",
            parameter_type=int,
        )

        self._hit_frame_sending_interval: Union[
            int, None
        ] = get_parameter_from_parameter_group(
            group=om_parameters,
            parameter="hit_frame_sending_interval",
            parameter_type=int,
        )
        self._non_hit_frame_sending_interval: Union[
            int, None
        ] = get_parameter_from_parameter_group(
            group=om_parameters,
            parameter="non_hit_frame_sending_interval",
            parameter_type=int,
        )

        self._start_timestamp: float = time.time()
        self._num_events: int = 0
        self._num_hits: int = 0
        self._old_time: float = time.time()
        self._time: Union[float, None] = None
        self._ranks_for_frame_request: Iterator[int] = cycle(range(1, node_pool_size))

    def add_hit_event(self) -> None:
        """
        Adds hit events to the event counter.

        This function updates the number of hit events counted by this class.
        """
        self._num_events += 1
        self._num_hits += 1

    def add_non_hit_event(self) -> None:
        """
        Adds non-hit events to the event counter.

        This function updates the number of non-hit events counted by this class.
        """
        self._num_events += 1

    def get_start_timestamp(self) -> float:
        """
        Gets timestamp of class initialization.

        This function returns the time at which the event counter class was
        initialized. This usually corresponds to the moment when OM started processing
        events.

        Returns:

            The timestamp of for the initialization of the class.
        """
        return self._start_timestamp

    def should_broadcast_data(self) -> bool:
        """
        Whether data should be broadcast to external programs.

        This function computes if the number of processed events requires data to be
        broadcast to external programs.

        Returns:

            Whether data should be broadcast.
        """
        if self._data_broadcast_interval:
            return self._num_events % self._data_broadcast_interval == 0
        else:
            return False

    def should_send_hit_frame(self) -> bool:
        """
        Whether a hit detector data frame should be broadcast to external programs.

        This function computes if the number of processed hit events requires a hit
        detector data frame to be broadcast to external programs.

        Returns:

            Whether a hit detector frame should be broadcast.
        """
        if self._hit_frame_sending_interval:
            return self._num_events % self._hit_frame_sending_interval == 0
        else:
            return False

    def should_send_non_hit_frame(self) -> bool:
        """
        Whether a non-hit detector data frame should be broadcast to external programs.

        This function computes if the number of processed non-hit events requires a
        non-hit detector data frame to be broadcast to external programs.

        Returns:

            Whether a non-hit detector frame should be broadcast.
        """
        if self._non_hit_frame_sending_interval:
            return self._num_events % self._non_hit_frame_sending_interval == 0
        else:
            return False

    def get_rank_for_frame_request(self) -> int:
        """
        Gets the processing node rank to request a frame from.

        This function returns the rank of the processing node from which a hit or
        non-hit detector data frame should be requested for external broadcast.

        This class keeps an internal index of the nodes from which images have been
        requested in the past, and attempts to spread requests in a round-robin fashion
        amongst all processing nodes, with the goal of not overloading a single node
        with requests and of getting a representative sample of the data frames
        processed by each node.

        Returns:

            The rank of the processing node from which a detector data frame should be
            requested.
        """
        return next(self._ranks_for_frame_request)

    def get_num_events(self) -> int:
        """
        Gets number of processed events.

        Returns:

            The number of processed events.
        """
        return self._num_events

    def get_num_hits(self) -> int:
        """
        Gets number of processed hit events.

        Returns:

            The number of processed hit events.
        """
        return self._num_hits

    def report_speed(self) -> None:
        """
        Prints a speed report to the console.

        This prints the number of processed events to the console, together with an
        estimate of the processing speed, based on the number of events recorded by
        this class.
        """
        if self._speed_report_interval:
            if self._num_events % self._speed_report_interval == 0:
                now_time: float = time.time()
                time_diff: float = now_time - self._old_time
                events_per_second: float = float(self._speed_report_interval) / float(
                    now_time - self._old_time
                )
                console.print(
                    f"{get_current_timestamp()} Processed: {self._num_events} in "
                    f"{time_diff:.2f} seconds ({events_per_second:.3f} Hz)"
                )
                sys.stdout.flush()
                self._old_time = now_time
