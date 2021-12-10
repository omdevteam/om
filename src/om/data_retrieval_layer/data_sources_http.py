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

This module contains Data Source classes that deal with data retrieved from http/REST
detector interface.
"""
import numpy
import time

from datetime import datetime
from PIL import Image  # type: ignore
from typing import Any, BinaryIO, Dict, List, Tuple, Union, cast

from om.data_retrieval_layer import base as drl_base
from om.data_retrieval_layer import data_sources_generic as ds_generic
from om.utils.parameters import MonitorParams


class Eiger16MHttp(drl_base.OmDataSource):
    """
    See documentation of the `__init__` function.

    Base class: [`OmDataSource`][om.data_retrieval_layer.base.OmDataSource]
    """

    def __init__(
        self,
        *,
        data_source_name: str,
        monitor_parameters: MonitorParams,
    ):
        """
        Detector frame data from Eiger 16M http/REST interface.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of Eiger 16M detector frame data from
        the tif images retrieved from http/REST detector interface. It is a subclass of
        the [OmDataSource][om.data_retrieval_layer.base.OmDataSource] class.

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, for communication with the user or retrieval of
                initialization parameters.

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.
        """
        self._data_source_name = data_source_name
        self._monitor_parameters = monitor_parameters

    def initialize_data_source(self) -> None:
        """
        Initializes the Eiger 16M http/REST data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        No initialization is needed to retrieve data from Eiger 16M tif files, so this
        function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> numpy.ndarray:
        """
        Retrieves an Eiger 16M detector data frame.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function extracts the detector frame information from the content of the
        tif file attached to the data event. It returns it as a 2D array storing pixel
        data.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            One frame of detector data.
        """
        image: Any = Image.open(event["additional_info"]["image_file"])
        return numpy.asarray(image, dtype=int)


class TimestampEiger16MHttp(drl_base.OmDataSource):
    """
    See documentation of the `__init__` function.

    Base class: [`OmDataSource`][om.data_retrieval_layer.base.OmDataSource]
    """

    def __init__(
        self,
        *,
        data_source_name: str,
        monitor_parameters: MonitorParams,
    ):
        """
        Timestamp information for Eiger 16M http/REST event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of timestamp information from Eiger 16M tif
        files retrieved from the http/REST detector interface. This class is a subclass
        of the [OmDataSource][om.data_retrieval_layer.base.OmDataSource] class.

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, for communication with the user or retrieval of
                initialization parameters.

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.
        """
        self._data_source_name = data_source_name
        self._monitor_parameters = monitor_parameters

    def initialize_data_source(self) -> None:
        """
        Initializes the Eiger 16M http/REST timestamp data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        No initialization is needed to retrieve timestamp data for a Eiger 16M
        http/REST event, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> numpy.float64:
        """
        Retrieves timestamp information for a Eiger 16M http/REST event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves the timestamp information for a Eiger 16M detector
        data frame from the image tif file retrieved from the http/REST detector
        interface.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The timestamp of the Jungfrau 1M data event.
        """
        event["additional_info"]["image_file"].seek(162)
        time_str: str = event["additional_info"]["image_file"].read(29).decode()

        # temporary fix to get some realistic delays in the GUI because Eiger gives
        # the same timestamp for all images in the run:
        return numpy.float64(time.time())

        return numpy.float64(
            datetime.strptime(
                time_str[0:-3] + time_str[-2:], "%Y-%m-%dT%H:%M:%S.%f%z"
            ).timestamp()
        )


class EventIdEiger16MHttp(drl_base.OmDataSource):
    """
    See documentation of the `__init__` function.

    Base class: [`OmDataSource`][om.data_retrieval_layer.base.OmDataSource]
    """

    def __init__(
        self,
        *,
        data_source_name: str,
        monitor_parameters: MonitorParams,
    ):
        """
        Event identifier for Eiger 16M http/REST events.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of a unique event identifier for
        Eiger 16M data events retrieved as tif files from http/REST detector interface.
        The combination of the series_id and frame_id retrieved from the header of the
        tif file are used as event identifier. This class is a subclass of the
        [OmDataSource][om.data_retrieval_layer.base.OmDataSource] class.

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, for communication with the user or retrieval of
                initialization parameters.

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.
        """
        self._data_source_name = data_source_name
        self._monitor_parameters = monitor_parameters

    def initialize_data_source(self) -> None:
        """
        Initializes the Eiger 16M event identifier data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        No initialization is needed to retrieve an event identifier for Eiger 16M
        event data, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> str:
        """
        Retrieves an event identifier for a Eiger 16M data event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function constructs the event identifier for an event from the series_id
        and frame_id separated by the "_" symbol.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A unique event identifier.
        """
        event["additional_info"]["image_file"].seek(42)
        series_id: int
        frame_id: int
        series_id, _, _, frame_id = numpy.frombuffer(  # type: ignore
            event["additional_info"]["image_file"].read(16), "i4"
        )
        return f"{series_id}_{frame_id}"
