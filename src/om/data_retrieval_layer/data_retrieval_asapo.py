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
Retrieval of data from ASAP::O.

This module contains Data Retrieval classes that deal with the ASAPO software framework
(used at the PETRA III facility).
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
from om.data_retrieval_layer.data_sources_generic import FrameIdZero
from om.lib.parameters import MonitorParameters
from om.protocols.data_retrieval_layer import (
    OmDataEventHandlerBase,
    OmDataRetrievalBase,
    OmDataSourceBase,
)


class EigerAsapoDataRetrieval(OmDataRetrievalBase):
    """
    See documentation of the `__init__` function.
    """

    def __init__(self, *, monitor_parameters: MonitorParameters, source: str):
        """
        Data Retrieval from ASAPO at the PETRA III facility, with Eiger 16M detector.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class implements OM's Data Retrieval Layer for an Eiger 16M detector using
        ASAPO software framework.

        * This class considers an individual data event as equivalent to the content of
          an ASAPO event, which stores data related to a single detector frame.

        * ASAPO provides timestamp, beam energy and detector distance information for
          each event.

        * The source string required by this Data Event Handler is either beamtime ID
          (for online data retrieval) or beamtime ID and ASAPO stream name separated by
          ":" (for offline data retrieval).

        Arguments:

            monitor_parameters: A [MonitorParameters]
                [om.library.parameters.MonitorParameters] object storing the OM monitor
                parameters from the configuration file.

            source: A string describing the data event source.
        """

        data_sources: Dict[str, OmDataSourceBase] = {
            "timestamp": TimestampAsapo(
                data_source_name="timestamp", monitor_parameters=monitor_parameters
            ),
            "event_id": EventIdAsapo(
                data_source_name="eventid", monitor_parameters=monitor_parameters
            ),
            "frame_id": FrameIdZero(
                data_source_name="frameid", monitor_parameters=monitor_parameters
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

        self._data_event_handler: OmDataEventHandlerBase = AsapoDataEventHandler(
            source=source,
            monitor_parameters=monitor_parameters,
            data_sources=data_sources,
        )

    def get_data_event_handler(self) -> OmDataEventHandlerBase:
        """
        Retrieves the Data Event Handler used by the class.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Returns:

            The Data Event Handler used by the Data Retrieval class.
        """
        return self._data_event_handler
