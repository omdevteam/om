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
Data retrieval from event lists.
"""

from typing import Dict

from om.data_retrieval_layer.data_event_handlers_event_list import (
    EventListEventHandler,
)

from om.lib.parameters import MonitorParameters
from om.protocols.data_retrieval_layer import (
    OmDataEventHandlerProtocol,
    OmDataRetrievalProtocol,
)


class EventListDataRetrieval(OmDataRetrievalProtocol):
    """
    See documentation for the `__init__` function.
    """

    def __init__(
        self,
        *,
        monitor_parameters: MonitorParameters,
        source: str,
        event_list_file: str
    ) -> None:
        """
        Data retrieval from event lists.

        This class implements OM's Data Retrieval Layer for a set of event IDs for a
        certain data retrieval protocol.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        TODO: write documentation.

        Arguments:

            monitor_parameters: An object storing OM's configuration parameters.

            source: A string describing the data event source.

            event_list_file: A string describing the path to the event list file.
        """
        self._data_event_handler: OmDataEventHandlerProtocol = EventListEventHandler(
            source=source,
            event_list_file=event_list_file,
            monitor_parameters=monitor_parameters,
            data_sources={},
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
