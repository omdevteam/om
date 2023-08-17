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
HTTP-based data sources.

This module contains Data Source classes that deal with data retrieved from the
HTTP/REST interface of detectors manufactured by the company Dectris.
"""
import datetime
from typing import Any, Dict, Union

import numpy
from numpy.typing import NDArray
from PIL import Image  # type: ignore

from om.lib.parameters import MonitorParameters
from om.protocols.data_retrieval_layer import OmDataSourceProtocol


class Eiger16MHttp(OmDataSourceProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        data_source_name: str,
        monitor_parameters: MonitorParameters,
    ):
        """
        Detector data frames from Eiger 16M's HTTP/REST interface.

        This class deals with the retrieval of Eiger 16M detector data frames from the
        detector's HTTP/REST interface.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, in communications with the user or for the retrieval
                of a sensor's initialization parameters.

            monitor_parameters: An object storing OM's configuration parameters
        """
        self._data_source_name = data_source_name
        self._monitor_parameters = monitor_parameters

    def initialize_data_source(self) -> None:
        """
        Initializes the Eiger 16M's HTTP/REST data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        No initialization is needed to retrieve detector data frames from the Eiger
        16M'S HTTP/REST- interface, so this function actually does nothing.
        """
        pass

    def get_data(
        self, *, event: Dict[str, Any]
    ) -> Union[NDArray[numpy.float_], NDArray[numpy.int_]]:
        """
        Retrieves an Eiger 16M detector data frame.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function extracts the detector data frame stored in the provided
        HTTP/REST-based event. It returns the detector frame as a 2D array storing
        pixel information.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A detector data frame.
        """
        image: Any = Image.open(event["additional_info"]["image_file"])
        return numpy.asarray(image, dtype=int)


class TimestampEiger16MHttp(OmDataSourceProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        data_source_name: str,
        monitor_parameters: MonitorParameters,
    ):
        """
        Timestamp information from Eiger's 16M HTTP/REST interface.

        This class deals with the retrieval of timestamp information for data events
        originating from an Eiger 16M's HTTPS/REST interface.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, in communications with the user or for the retrieval
                of a sensor's initialization parameters.

            monitor_parameters: An object storing OM's configuration parameters.
        """
        self._data_source_name = data_source_name
        self._monitor_parameters = monitor_parameters

    def initialize_data_source(self) -> None:
        """
        Initializes the Eiger 16M's HTTP/REST interface timestamp data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        No initialization is needed to retrieve timestamp information from the Eiger
        16M's HTTP/REST interface, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> numpy.float64:
        """
        Retrieves timestamp information from an Eiger 16M'S HTTP/REST interface.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves the timestamp information associated with the provided
        HTTPS/REST-based event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The timestamp of the Jungfrau 1M data event.
        """
        event["additional_info"]["image_file"].seek(162)
        time_str: str = event["additional_info"]["image_file"].read(29).decode()

        return numpy.float64(
            datetime.datetime.strptime(
                time_str[0:-3] + time_str[-2:], "%Y-%m-%dT%H:%M:%S.%f%z"
            ).timestamp()
        )


class EventIdEiger16MHttp(OmDataSourceProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        data_source_name: str,
        monitor_parameters: MonitorParameters,
    ):
        """
        Event identifier from Eiger 16M's HTTP/REST interface.

        This class deals with the retrieval of unique event identifiers for events
        originating from an Eiger 16M's HTTP/REST interface.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, in communications with the user or for the retrieval
                of a sensor's initialization parameters.

            monitor_parameters: An object storing OM's configuration parameters.
        """
        self._data_source_name = data_source_name
        self._monitor_parameters = monitor_parameters

    def initialize_data_source(self) -> None:
        """
        Initializes the Eiger 16M's HTTP/REST interface event identifier data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        No initialization is needed to retrieve event identifiers for Eiger 16M data
        events, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> str:
        """
        Retrieves an event identifier from an Eiger 16M'S HTTP/REST interface.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        A data event retrieved from Eiger 16M's HTTP/REST interface contains detector
        frame data in the format of a TIFF image. The combination of the series_id and
        frame_id tags retrieved from the header of the TIFF image are used to
        generate an event identifier, with the format: `<series_id>_<frame_id>.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A unique event identifier.
        """
        event["additional_info"]["image_file"].seek(42)
        series_id: int
        frame_id: int
        series_id, _, _, frame_id = numpy.frombuffer(
            event["additional_info"]["image_file"].read(16), "i4"
        )
        return f"{series_id}_{frame_id}"
