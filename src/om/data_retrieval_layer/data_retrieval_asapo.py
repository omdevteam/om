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
Data retrieval from ASAP::O.

This module contains Data Retrieval classes that deal with the ASAP::O software
framework (used at the PETRA III facility).
"""
from typing import Dict

from om.data_retrieval_layer.data_event_handlers_asapo import AsapoDataEventHandler
from om.data_retrieval_layer.data_sources_asapo import (
    BeamEnergyAsapo,
    DetectorDistanceAsapo,
    EigerAsapo,
    EventIdAsapo,
    TimestampAsapo,
)
from om.lib.parameters import MonitorParameters
from om.protocols.data_retrieval_layer import (
    OmDataEventHandlerProtocol,
    OmDataRetrievalProtocol,
    OmDataSourceProtocol,
)


class EigerAsapoDataRetrieval(OmDataRetrievalProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(self, *, monitor_parameters: MonitorParameters, source: str):
        """
        Data retrieval for Eiger 16M from ASAP::O at the PETRA III facility.

        This class implements OM's Data Retrieval Layer for an Eiger 16M detector using
        the ASAP::O software framework.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        * This class considers an individual data event as equivalent to the content of
          an ASAP::O event, which stores data related to a single detector frame.

        * The ASAP::O stream name and the ID of the ASAP::O event within the stream,
          combined into a single string, are used as event identifier.

        * ASAP::O provides timestamp, beam energy and detector distance information for
          each event.

        * The source string required by this Data Retrieval class is either the ID of
          the beamtime for which OM is being used (for online data retrieval) or the ID
          of the beamtime and the name of the ASAP::O stream separated by a colon (for
          offline data retrieval).

        Arguments:

            monitor_parameters: An object storing OM's configuration parameters.

            source: A string describing the data event source.
        """

        data_sources: Dict[str, OmDataSourceProtocol] = {
            "timestamp": TimestampAsapo(
                data_source_name="timestamp", monitor_parameters=monitor_parameters
            ),
            "event_id": EventIdAsapo(
                data_source_name="eventid", monitor_parameters=monitor_parameters
            ),
            "detector_data": EigerAsapo(
                data_source_name="detector", monitor_parameters=monitor_parameters
            ),
            "beam_energy": BeamEnergyAsapo(
                data_source_name="beam_energy",
                monitor_parameters=monitor_parameters,
            ),
            "detector_distance": DetectorDistanceAsapo(
                data_source_name="detector_distance",
                monitor_parameters=monitor_parameters,
            ),
        }

        self._data_event_handler: OmDataEventHandlerProtocol = AsapoDataEventHandler(
            source=source,
            monitor_parameters=monitor_parameters,
            data_sources=data_sources,
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
