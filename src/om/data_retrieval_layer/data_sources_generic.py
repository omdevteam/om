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

    Base class: [`OmDataEventHandler`][om.data_retrieval_layer.base.OmDataSource]
    """

    def __init__(
        self,
        *,
        data_source_name: str,
        monitor_parameters: MonitorParams,
    ):
        """
        #TODO: docs

        Arguments:

            source_name: the name of the current data source, used to identify the
                source when needed (communication with the user, retrieval of
                initialization parameters.

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.
        """
        self._data_source_name = data_source_name
        self._monitor_parameters = monitor_parameters

    def initialize_data_source(self) -> None:
        """
        #TODO: Docs
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> numpy.float64:
        """
        Retrieves an Epics variable from psana.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves the value of an Epics variable from psana.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The value of the Epics variable.
        """
        return event["additional_info"]["timestamp"]


class FloatEntryFromConfiguration(drl_base.OmDataSource):
    """
    See documentation of the `__init__` function.

    Base class: [`OmDataEventHandler`][om.data_retrieval_layer.base.OmDataSource]
    """

    def __init__(
        self,
        *,
        data_source_name: str,
        monitor_parameters: MonitorParams,
    ):
        """
        #TODO: docs

        Arguments:

            source_name: the name of the current data source, used to identify the
                source when needed (communication with the user, retrieval of
                initialization parameters.

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.
        """
        self._data_source_name = data_source_name
        self._monitor_parameters = monitor_parameters

    def initialize_data_source(self) -> None:
        """
        #TODO: Docs
        """
        self._value: float = self._monitor_parameters.get_parameter(
            group="data_retrieval_layer",
            parameter=f"{self._data_source_name}",
            required=True,
            parameter_type=float,
        )

    def get_data(self, *, event: Dict[str, Any]) -> float:
        """
        Retrieves an Epics variable from psana.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves the value of an Epics variable from psana.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The value of the Epics variable.
        """
        return self._value


class FrameIdZero(drl_base.OmDataSource):
    """
    See documentation of the `__init__` function.

    Base class: [`OmDataEventHandler`][om.data_retrieval_layer.base.OmDataSource]
    """

    def __init__(
        self,
        *,
        data_source_name: str,
        monitor_parameters: MonitorParams,
    ):
        """
        #TODO: docs

        Arguments:

            source_name: the name of the current data source, used to identify the
                source when needed (communication with the user, retrieval of
                initialization parameters.

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.
        """
        self._data_source_name = data_source_name
        self._monitor_parameters = monitor_parameters

    def initialize_data_source(self) -> None:
        """
        #TODO: Docs
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> Any:
        """
        Retrieves an Epics variable from psana.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves the value of an Epics variable from psana.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The value of the Epics variable.
        """
        return "0"
