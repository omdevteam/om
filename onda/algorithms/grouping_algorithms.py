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
Grouping algorithms.

Algorithms to classify data into groups and classes.
"""
from __future__ import absolute_import, division, print_function

import numpy


class FrameIdGrouping(object):
    def __init__(self, monitor_params):

        group_mapping = monitor_params.get_param(
            section="DataRetrievalLayer",
            parameter="frame_id_to_group_mapping",
            type_=dict,
            required=True,
        )

        self._internal_dict = {}
        self._num_groups = len(group_mapping)

        for key in group_mapping:
            for value in group_mapping[key]:
                self._internal_dict[str(value)] = int(key)

    def get_group(self, data):

        try:
            ret_val = self._internal_dict[data["frame_id"]]
        except KeyError:
            ret_val = self._num_groups - 1
        return ret_val


class TargetTimeDelayGrouping(object):
    def __init__(self, monitor_params):

        self.group_bin_edges = monitor_params.get_param(
            section="Grouping",
            parameter="time_delay_group_bin_edges",
            type_=list,
            required=True,
        )

    def get_group(self, data):

        delay = data["target_time_delay"]
        group_id = numpy.digitize(delay, self.group_bin_edges) - 1
        return group_id
