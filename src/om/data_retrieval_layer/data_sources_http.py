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
HTTP-based data sources.

This module contains Data Source classes that deal with data retrieved from the
HTTP/REST interface used by detectors from the Dectris company.
"""
import time
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
        Detector frame data from Eiger 16M's HTTP/REST interface.

        This class deals with the retrieval of Eiger 16M detector frame data from
        events obtainedEiger 16M's HTTP/REST interface

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

        No initialization is needed to retrieve data from Eiger 16M'S HTTP/REST
        interface, so this function actually does nothing.
        """
        pass

    def get_data(
        self, *, event: Dict[str, Any]
    ) -> Union[NDArray[numpy.float_], NDArray[numpy.int_]]:
        """
        Retrieves an Eiger 16M detector data frame.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function extracts the detector frame information from the provided
        data event, where it is stored in the form of a TIFF image. This function
        returns the detector frame as a 2D array storing pixel information.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            One frame of detector data.
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

        This class deals with the retrieval of timestamp information for events
        obtained from Eiger 16M's HTTPS/REST interface.

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
        Initializes the Eiger 16M http/REST timestamp data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        No initialization is needed to retrieve timestamp information for an Eiger 16M
        HTTP/REST event, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> numpy.float64:
        """
        Retrieves timestamp information for an Eiger 16M'S HTTP/REST event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves the timestamp information associated with the provided
        Eiger 16M HTTPS/REST event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The timestamp of the Jungfrau 1M data event.
        """
        event["additional_info"]["image_file"].seek(162)

        # temporary fix to get some realistic delays in the GUI because Eiger gives
        # the same timestamp for all images in the run:
        return numpy.float64(time.time())

        # return numpy.float64(
        #     datetime.strptime(
        #         time_str[0:-3] + time_str[-2:], "%Y-%m-%dT%H:%M:%S.%f%z"
        #     ).timestamp()
        # )


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

        This class deals with the retrieval of a unique event identifier for events
        obtained from Eiger 16M's HTTP/REST interface.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        A data event retrieved from Eiger 16M's HTTP/REST interface contains detector
        frame data in the format of a TIFF image. The combination of the series_id and
        frame_id tags retrieved from the header of the TIFF image are used to
        generate an event identifier.

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
        Initializes the Eiger 16M event identifier data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        No initialization is needed to retrieve an event identifier for Eiger 16M
        event data, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> str:
        """
        Retrieves an event identifier for a Eiger 16M data event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        A data event retrieved from Eiger 16M's HTTP/REST interface contains detector
        frame data in the format of a TIFF image. The combination of the series_id and
        frame_id tags retrieved from the header of the TIFF image are used to
        generate an event identifier.
        This function constructs the event identifier for the provided event by joining
        the content of the the series_id and frame_id tags of the TIFF image stored in
        the event. The resulting identifier has the form:
        `<series_id>_<frame_id>.

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
