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
Retrieval and handling of data from the http/REST interface.

This module contains Data Retrieval classes that deal with the HTTP/REST interface
used by detectors manufactured by the company Dectris.
"""
from typing import Dict

from om.data_retrieval_layer.data_event_handlers_http import EigerHttpDataEventHandler
from om.data_retrieval_layer.data_sources_generic import FloatEntryFromConfiguration
from om.data_retrieval_layer.data_sources_http import (
    Eiger16MHttp,
    EventIdEiger16MHttp,
    TimestampEiger16MHttp,
)
from om.lib.parameters import MonitorParameters
from om.protocols.data_retrieval_layer import (
    OmDataEventHandlerProtocol,
    OmDataRetrievalProtocol,
    OmDataSourceProtocol,
)


class EigerHttpDataRetrieval(OmDataRetrievalProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(self, *, monitor_parameters: MonitorParameters, source: str):
        """
        Data Retrieval from Eiger's HTTP/REST interface.

        This class implements OM's Data Retrieval Layer for the HTTPS/REST interface of
        an Eiger detector.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        * This class considers an individual data event as equivalent to the content of
          a tif file retrieved from the Eiger's HTTP/REST interface, which stores
          data related to a single detector frame.

        * A string with the format: `{SeriesID_FrameID}`, where SeriesID and FrameID
          are two values generated for each event by the HTTP/REST interface, is used
          as event identifier.

        * Since Eiger's HTTP/REST monitor interface does not provide any detector
          distance or beam energy information, their values are retrieved from OM's
          configuration parameters (specifically, the `fallback_detector_distance_in_mm`
          and `fallback_beam_energy_in_eV` entries in the `data_retrieval_layer`
          parameter group).

        * The source string for this Data Retrieval class is the base URL of the
          'monitor' subsystem of the Eiger's HTTP/REST interface:
          `http://<address_of_dcu>/monitor/api/<version>`.

        Arguments:

            monitor_parameters: An object storing OM's configuration parameters.

            source: A string describing the data event source.
        """

        data_sources: Dict[str, OmDataSourceProtocol] = {
            "timestamp": TimestampEiger16MHttp(
                data_source_name="timestamp", monitor_parameters=monitor_parameters
            ),
            "event_id": EventIdEiger16MHttp(
                data_source_name="eventid", monitor_parameters=monitor_parameters
            ),
            "detector_data": Eiger16MHttp(
                data_source_name="detector", monitor_parameters=monitor_parameters
            ),
            "beam_energy": FloatEntryFromConfiguration(
                data_source_name="fallback_beam_energy_in_eV",
                monitor_parameters=monitor_parameters,
            ),
            "detector_distance": FloatEntryFromConfiguration(
                data_source_name="fallback_detector_distance_in_mm",
                monitor_parameters=monitor_parameters,
            ),
        }

        self._data_event_handler: OmDataEventHandlerProtocol = (
            EigerHttpDataEventHandler(
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
