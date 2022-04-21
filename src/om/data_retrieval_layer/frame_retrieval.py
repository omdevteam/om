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

from om.protocols import data_extraction_layer as drl_protocol
from om.utils import exceptions, parameters
from types import ModuleType
from typing import Any, Dict, Type
import importlib
import sys


class OmFrameDataRetrieval:
    """
    See documentation for the `__init__` function.
    """

    def __init__(
        self, *, monitor_parameters: parameters.MonitorParams, source: str
    ) -> None:
        """
        Retrieval of single detector frame data.

        This class deals with the retrieval, from a data source, of a single
        standalone detector data frame, with all the information that refers to it,
        as opposed to a series of events and frames as an OnDA Monitor does. This class
        has a single method that can be used to retrieve a detector frame and all its
        related data. An event and a frame identifier are used to determine the frame
        that should be retrieved.

        An instance of this class can be created on any type of OM node and even in a
        standalone program outside of an OnDA Monitor.

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

        try:
            data_retrieval_layer_module: ModuleType = importlib.import_module(
                "data_retrieval_layer"
            )
        except ImportError:
            try:
                data_retrieval_layer_module = importlib.import_module(
                    f"om.data_retrieval_layer"
                )
            except ImportError as exc:
                exc_type, exc_value = sys.exc_info()[:2]
                # TODO: Fix types
                if exc_type is not None:
                    raise exceptions.OmInvalidDataBroadcastUrl(
                        f"The python module file data_retrieval_layer.py cannot be "
                        "found or loaded due to the following "
                        f"error: {exc_type.__name__}: {exc_value}"
                    ) from exc

        try:
            data_retrieval_layer_class: Type[drl_protocol.OmDataRetrieval] = getattr(
                data_retrieval_layer_module, data_retrieval_layer_class_name
            )
        except AttributeError:
            raise exceptions.OmMissingDataRetrievalClassError(
                f"The {data_retrieval_layer_class_name} class cannot be found in the "
                "data_retrieval_layer file."
            )

        data_retrieval_layer: drl_protocol.OmDataRetrieval = data_retrieval_layer_class(
            monitor_parameters=monitor_parameters,
            source=source,
        )

        self._data_event_handler: drl_protocol.OmDataEventHandler = (
            data_retrieval_layer.get_data_event_handler()
        )

        self._data_event_handler.initialize_frame_data_retrieval()

    def retrieve_frame_data(self, event_id: str, frame_id: str) -> Dict[str, Any]:
        """
        Retrieves all data related to the requested detector frame.

        This function retrieves all the data related to the detector frame specified
        by the provided event and frame unique identifiers.

        Arguments:

            event_id: a string that uniquely identifies a data event.

            frame_id: a string that identifies a particular frame within the data
                event.

        Returns:

            All data related to the requested detector data frame.
        """
        return self._data_event_handler.retrieve_frame_data(
            event_id=event_id, frame_id=frame_id
        )
