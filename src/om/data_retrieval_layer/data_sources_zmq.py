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
ZMQ-based data sources.

This module contains Data Source classes that deal with data retrieved from ZMQ data
streams.
"""
from typing import Any, Dict, Tuple, Type, TypeVar, Union, cast

import numpy
from numpy.typing import NDArray

from om.data_retrieval_layer.data_sources_common import OmJungfrau1MDataSourceMixin
from om.typing import OmDataSourceProtocol

T = TypeVar("T")


class OmBaseZmqDataSourceMixin:
    """
    See documentation of the `__init__` function.
    """

    def __new__(cls: Type[T], *args: Any, **kwargs: Any) -> T:
        if cls is OmBaseZmqDataSourceMixin:
            raise TypeError(
                f"{cls.__name__} is a Mixin class and should not be instantiated"
            )
        return object.__new__(cls)

    def __init__(
        self,
        *,
        data_source_name: str,
        parameters: Dict[str, Any],
    ):
        """
        Timestamp information from a Jungfrau 1M's ZMQ data stream.

        This class deals with the retrieval of timestamp information for Jungfrau 1M
        data events originating from a ZMQ stream broadcast by the detector.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, for communication with the user or retrieval of
                initialization parameters.

            monitor_parameters: An object storing OM's configuration parameters.
        """
        del data_source_name
        del parameters

    def initialize_data_source(self) -> None:
        """
        Initializes the Jungfrau 1M's ZMQ stream timestamp data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        No initialization is needed to retrieve timestamp information for Jungfrau 1M
        data events originating from a ZMQ stream, so this function actually does
        nothing.
        """
        pass


class TimestampJungfrau1MZmq(OmBaseZmqDataSourceMixin, OmDataSourceProtocol):
    """
    See documentation of the `__init__` function.
    """

    def get_data(self, *, event: Dict[str, Any]) -> numpy.float64:
        """
        Retrieves timestamp information from a Jungfrau 1M's ZMQ data stream.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function returns the timestamp information associated, in the ZMQ data
        stream broadcast by the detector, to the provided event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The timestamp for the data event.
        """

        return cast(numpy.float64, event["data"][0]["timestamp"])


class EventIdJungfrau1MZmq(OmBaseZmqDataSourceMixin, OmDataSourceProtocol):
    """
    See documentation of the `__init__` function.
    """

    def get_data(self, *, event: Dict[str, Any]) -> str:
        """
        Retrieves an event identifier from a Jungfrau 1M's ZMQ data stream.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function returns the frame number associated, in the ZMQ data stream
        broadcast by the detector to the provided event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A unique event identifier.
        """
        return str(event["data"][0]["frame_number"])


class Jungfrau1MZmq(OmJungfrau1MDataSourceMixin, OmDataSourceProtocol):
    """
    See documentation of the `__init__` function.
    """

    def get_data(
        self, *, event: Dict[str, Any]
    ) -> Union[NDArray[numpy.float_], NDArray[numpy.int_]]:
        """
        Retrieves a Jungfrau 1M detector data frame from a ZMQ data stream.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves the detector data frame associated with the provided
        ZMQ-based event. It returns the frame as a 2D array storing pixel information.
        Data is retrieved in calibrated or non-calibrated form depending on the value
        of the `{data_source_name}_calibration` entry in OM's `data_retrieval_layer`
        configuration parameter group.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A detector data frame.
        """
        msg: Tuple[Dict[str, Any], Dict[str, Any]] = event["data"]
        data: NDArray[numpy.int_] = numpy.concatenate(
            [
                numpy.frombuffer(msg[i]["data"], dtype=numpy.int16).reshape((512, 1024))
                for i in range(2)
            ]
        )

        if self._calibrated_data_required:
            return self._calibration.apply_calibration(data=data)
        else:
            return data
