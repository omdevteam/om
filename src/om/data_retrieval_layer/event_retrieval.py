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
This module contains classes that deals with the retrieval of single standalone events.
"""
from typing import Any, Dict, Type, cast

from om.lib.layer_management import import_class_from_layer
from om.lib.parameters import MonitorParameters
from om.protocols.data_retrieval_layer import (
    OmDataEventHandlerProtocol,
    OmDataRetrievalProtocol,
)


class OmEventDataRetrieval:
    """
    See documentation for the `__init__` function.
    """

    def __init__(self, *, monitor_parameters: MonitorParameters, source: str) -> None:
        """
        Retrieval of single standalone data events.

        This class deals with the retrieval of single standalone data events from a
        data source.

        Arguments:

            monitor_parameters: An object storing OM's configuration parameters.

            source: A string describing the data event source.
        """
        data_retrieval_layer_class_name: str = monitor_parameters.get_parameter(
            group="om",
            parameter="data_retrieval_layer",
            parameter_type=str,
            required=True,
        )

        data_retrieval_layer_class: Type[OmDataRetrievalProtocol] = cast(
            Type[OmDataRetrievalProtocol],
            import_class_from_layer(
                layer_name="data_retrieval_layer",
                class_name=data_retrieval_layer_class_name,
            ),
        )

        data_retrieval_layer: OmDataRetrievalProtocol = data_retrieval_layer_class(
            monitor_parameters=monitor_parameters,
            source=source,
        )

        self._data_event_handler: OmDataEventHandlerProtocol = (
            data_retrieval_layer.get_data_event_handler()
        )

        self._data_event_handler.initialize_event_data_retrieval()

    def retrieve_event_data(self, event_id: str) -> Dict[str, Any]:
        """
        Retrieves all data attached to the requested data event.

        This function retrieves all the information associated with the data event
        specified by the provided identifier. The data is returned in the form of a
        dictionary.

        * Each dictionary key identifies a Data Source in the event for which
          information has been retrieved.

        * The corresponding dictionary values store the data associated with each
          Data Source.

        Arguments:

            event_id: a string that uniquely identifies a data event.

        Returns:

            A dictionary storing all data related the retrieved event.
        """
        return self._data_event_handler.retrieve_event_data(event_id=event_id)
