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
# Copyright 2020 -2021 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.

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

        TODO: Documentation

        Arguments:

            monitor_parameters: An object storing OM's configuration parameters.
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
        self._num_events += 1
        self._num_hits += 1

    def add_non_hit_event(self) -> None:
        self._num_events += 1

    def get_start_timestamp(self) -> float:
        return self._start_timestamp

    def should_broadcast_data(self) -> bool:
        if self._data_broadcast_interval:
            return self._num_events % self._data_broadcast_interval == 0
        else:
            return False

    def should_send_hit_frame(self) -> bool:
        if self._hit_frame_sending_interval:
            return self._num_events % self._hit_frame_sending_interval == 0
        else:
            return False

    def should_send_non_hit_frame(self) -> bool:
        if self._non_hit_frame_sending_interval:
            return self._num_events % self._non_hit_frame_sending_interval == 0
        else:
            return False

    def get_rank_for_frame_request(self) -> int:
        return next(self._ranks_for_frame_request)

    def get_num_events(self) -> int:
        return self._num_events

    def report_speed(self) -> None:
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
