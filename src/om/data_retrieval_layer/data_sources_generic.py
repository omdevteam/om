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
Generic data sources.

This module contains Data Source classes that deal with data whose origin is not tied
to a specific facility or experiment.
"""
from typing import Any, Dict, Union, cast

import numpy

from om.lib.parameters import MonitorParameters
from om.protocols.data_retrieval_layer import OmDataSourceProtocol


def get_calibration_request(
    *, source_protocols_name: str, monitor_parameters: MonitorParameters
) -> bool:
    # Helper function to retrieve from the monitor configuration parameters a flag
    # that determines if calibrated data should be retrieved for a specific detector.
    calibrated_data_required: Union[bool, None] = monitor_parameters.get_parameter(
        group="data_retrieval_layer",
        parameter=f"{source_protocols_name}_calibration",
        parameter_type=bool,
    )
    if calibrated_data_required is None:
        calibrated_data_required = True
    return calibrated_data_required


class TimestampFromEvent(OmDataSourceProtocol):
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
        Timestamp information from data events.

        This class deals with the retrieval of the timestamp information stored in data
        events. Several software frameworks provide direct timestamp information about
        the events they generate. OM retrieves this information and stores it in the
        data event structure. This class retrieves it from there.

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
        Initializes the event timestamp data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        No initialization is needed to retrieve timestamp information from data events,
        so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> numpy.float64:
        """
        Retrieves the timestamp information from a data event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves the timestamp information stored in the provided data
        event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The timestamp from the data event.
        """
        return cast(numpy.float64, event["additional_info"]["timestamp"])


class FloatEntryFromConfiguration(OmDataSourceProtocol):
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
        Numerical values from configuration parameters.

        This class deals with the retrieval of numerical values from OM's configuration
        parameters.

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
        Initializes the numerical configuration parameter data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves the value of the `{data_source_name}` entry from OM's
        `data_retrieval_layer` configuration parameter group, and stores it for
        subsequent recall. The function treats the entry as a required parameter (i.e.:
        it raises an exception if the parameter is not available), and requires its
        value to be a float number.
        """
        self._value: float = self._monitor_parameters.get_parameter(
            group="data_retrieval_layer",
            parameter=f"{self._data_source_name}",
            required=True,
            parameter_type=float,
        )

    def get_data(self, *, event: Dict[str, Any]) -> float:
        """
        Retrieves the numerical value of an OM's configuration parameter

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function returns the value of the configuration parameter retrieved by the
        the Data Source.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The value of the configuration parameter.
        """
        return self._value
