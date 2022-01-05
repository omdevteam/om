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
"""
Retrieval of data from a ZMQ stream.

This module contains Data Retrieval classes that deal with ZMQ streams.
"""
from typing import Dict

from om.data_retrieval_layer import base as drl_base
from om.data_retrieval_layer import data_sources_generic as ds_generic
from om.data_retrieval_layer import data_sources_zmq as ds_zmq
from om.data_retrieval_layer import data_event_handlers_zmq as deh_zmq

from om.utils import parameters


class Jungfrau1MZmqDataRetrieval(drl_base.OmDataRetrieval):
    """
    See documentation of the `__init__` function.
    """

    def __init__(self, *, monitor_parameters: parameters.MonitorParams, source: str):
        """
        Data Retrieval for a Jungfrau 1M's ZMQ stream.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class implements OM's Data Retrieval Layer for a Jungfrau 1M detector
        broadcasting data via a ZMQ stream.

        * This class considers an individual data event corresponding to the content of
          a single ZMQ message sent by the Jungfrau 1M. Each message sent by the
          detector stores data related to a single detector data frame.

        * The ZMQ stream provides detector data, timestamp and frame ID for each event.

        * Since Jungfrau 1M's ZMQ messages do not contain any detector distance or
          beam energy information, their values are retrieved from OM's configuration
          parameters (specifically, the `fallback_detector_distance_in_mm` and
          `fallback_beam_energy_in_eV` entries in the `data_retrieval_layer`
          parameter group).

        * The source string required by this Data Retrieval class is the URL where the
          Jungfrau 1M detector broadcasts its data stream.

        Arguments:

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.

            source: A string describing the data event source.
        """

        data_sources: Dict[str, drl_base.OmDataSource] = {
            "timestamp": ds_zmq.TimestampJungfrau1MZmq(
                data_source_name="timestamp", monitor_parameters=monitor_parameters
            ),
            "event_id": ds_zmq.EventIdJungfrau1MZmq(
                data_source_name="eventid", monitor_parameters=monitor_parameters
            ),
            "frame_id": ds_generic.FrameIdZero(
                data_source_name="frameid", monitor_parameters=monitor_parameters
            ),
            "detector_data": ds_zmq.Jungfrau1MZmq(
                data_source_name="detector", monitor_parameters=monitor_parameters
            ),
            "beam_energy": ds_generic.FloatEntryFromConfiguration(
                data_source_name="fallback_beam_energy",
                monitor_parameters=monitor_parameters,
            ),
            "detector_distance": ds_generic.FloatEntryFromConfiguration(
                data_source_name="fallback_detector_distance",
                monitor_parameters=monitor_parameters,
            ),
        }

        self._data_event_handler: drl_base.OmDataEventHandler = (
            deh_zmq.Jungfrau1MZmqDataEventHandler(
                source=source,
                monitor_parameters=monitor_parameters,
                data_sources=data_sources,
            )
        )

    def get_data_event_handler(self) -> drl_base.OmDataEventHandler:
        """
        Retrieves the Data Event Handler used by the class.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Returns:

            The Data Event Handler used by the Data Retrieval class.
        """
        return self._data_event_handler
