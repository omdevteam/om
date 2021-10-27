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
Generic data sources.

This module contains Data Source classes that work with data of any origin.
"""
from typing import Any, Dict, Union

import numpy  # type: ignore

from om.data_retrieval_layer import base as drl_base
from om.utils.parameters import MonitorParams


def get_calibration_request(
    *, source_base_name: str, monitor_parameters: MonitorParams
) -> bool:
    # Helper function to retrieve from the monitor configuration parameters a flag
    # that determines if calibrated data should be retrieved for a specific detector.
    calibrated_data_required: Union[bool, None] = monitor_parameters.get_parameter(
        group="data_retrieval_layer",
        parameter=f"{source_base_name}_calibration",
        parameter_type=bool,
    )
    if calibrated_data_required is None:
        calibrated_data_required = True
    return calibrated_data_required


class TimestampFromEvent(drl_base.OmDataSource):
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
        Timestamp information from the data event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of timestamp information stored in the data
        event itself. Several software frameworks provide timestamp information for
        each data event, and store it in the event itself. OM retrieves this
        information when the event is opened, and stores it in a way that allows it to
        be retrieved by this class. This class is a subclass of the
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
        Initializes the event timestamp data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        No initialization is needed to retrieve timestamp information from within a
        data event, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> numpy.float64:
        """
        Retrieves timestamp information from a data event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves the timestamp information for a data event, when it is
        stored in the event itself.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The timestamp from the data event.
        """
        return event["additional_info"]["timestamp"]


class FloatEntryFromConfiguration(drl_base.OmDataSource):
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
        Numerical value from a configuration parameter.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of a numerical value from an OM
        configuration parameter in the `data_retrieval_layer` parameter group.
        Specifically, this class retrieves the parameter whose name matches
        `{data_source_name}`, treating it as a required parameter. It raises therefore
        an exception if the parameter is not available. This class is a subclass of the
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
        Initializes the numerical configuration parameter data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves the `{data_source_name}` parameter from the
        `data_retrieval_layer` OM configuration parameter group, and stores it for
        a fast subsequent recall.
        """
        self._value: float = self._monitor_parameters.get_parameter(
            group="data_retrieval_layer",
            parameter=f"{self._data_source_name}",
            required=True,
            parameter_type=float,
        )

    def get_data(self, *, event: Dict[str, Any]) -> float:
        """
        Retrieves the numerical value from a configuration parameter.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves the value of the numerical configuration parameter that
        is associated with the current data source.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The value of the configuration parameter.
        """
        return self._value


class FrameIdZero(drl_base.OmDataSource):
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
        Frame identifier for single-frame data files.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of a unique frame identifier for
        single-frame files that do not store any identifying information.
        When no other information is available, OM labels a frame using the index
        of the frame within the file which contains it. For single-frame files, the
        frame identifier is therefore "0". This class is a subclass of the
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
        Initializes the single-frame file frame identifier data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        No initialization is needed to retrieve a frame identifier for a single-frame
        data file, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> Any:
        """
        Retrieves the frame identifier.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function returns "0" as frame identifier for the current frame.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The value of the Epics variable.
        """
        return "0"
