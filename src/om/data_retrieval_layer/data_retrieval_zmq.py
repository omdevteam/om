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
Retrieval of data from a ZMQ stream.

This module contains Data Retrieval classes that deal with ZMQ data streams.
"""
from typing import Dict

from om.data_retrieval_layer.data_event_handlers_zmq import (
    Jungfrau1MZmqDataEventHandler,
)
from om.data_retrieval_layer.data_sources_generic import FloatEntryFromConfiguration
from om.data_retrieval_layer.data_sources_zmq import (
    EventIdJungfrau1MZmq,
    Jungfrau1MZmq,
    TimestampJungfrau1MZmq,
)
from om.lib.parameters import MonitorParameters
from om.protocols.data_retrieval_layer import (
    OmDataEventHandlerProtocol,
    OmDataRetrievalProtocol,
    OmDataSourceProtocol,
)


class Jungfrau1MZmqDataRetrieval(OmDataRetrievalProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(self, *, monitor_parameters: MonitorParameters, source: str):
        """
        Data Retrieval for Jungfrau 1M's ZMQ stream.

        This class implements OM's Data Retrieval Layer for a Jungfrau 1M detector
        broadcasting data via a ZMQ stream.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        * This class considers an individual data event corresponding to the content of
          a single ZMQ message sent by the Jungfrau 1M. Each message sent by the
          detector stores data related to a single detector data frame.

        * The ZMQ stream provides detector data, timestamp and an event identifier for
          each event.

        * Since Jungfrau 1M's ZMQ messages do not contain any detector distance or
          beam energy information, their values are retrieved from OM's configuration
          parameters (specifically, the `fallback_detector_distance_in_mm` and
          `fallback_beam_energy_in_eV` entries in the `data_retrieval_layer`
          parameter group).

        * The source string required by this Data Retrieval class is the URL where the
          Jungfrau 1M detector broadcasts data.

        Arguments:

            monitor_parameters: An object storing OM's configuration parameters.

            source: A string describing the data event source.
        """

        data_sources: Dict[str, OmDataSourceProtocol] = {
            "timestamp": TimestampJungfrau1MZmq(
                data_source_name="timestamp", monitor_parameters=monitor_parameters
            ),
            "event_id": EventIdJungfrau1MZmq(
                data_source_name="eventid", monitor_parameters=monitor_parameters
            ),
            "detector_data": Jungfrau1MZmq(
                data_source_name="detector", monitor_parameters=monitor_parameters
            ),
            "beam_energy": FloatEntryFromConfiguration(
                data_source_name="fallback_beam_energy",
                monitor_parameters=monitor_parameters,
            ),
            "detector_distance": FloatEntryFromConfiguration(
                data_source_name="fallback_detector_distance",
                monitor_parameters=monitor_parameters,
            ),
        }

        self._data_event_handler: OmDataEventHandlerProtocol = (
            Jungfrau1MZmqDataEventHandler(
                source=source,
                monitor_parameters=monitor_parameters,
                data_sources=data_sources,
            )
        )

    def get_data_event_handler(self) -> OmDataEventHandlerProtocol:
        """
        Retrieves the Data Event Handler used by the Data Retrieval class.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Returns:

            The Data Event Handler used by the Data Retrieval class.
        """
        return self._data_event_handler
