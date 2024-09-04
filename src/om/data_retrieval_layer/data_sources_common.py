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
from typing import Any, Dict, List, Type, TypeVar, Union, cast

import numpy
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
from typing_extensions import Self

from om.algorithms.calibration import Jungfrau1MCalibration
from om.lib.exceptions import OmConfigurationFileSyntaxError
from om.typing import OmDataSourceProtocol

T = TypeVar("T")


class _Jungfrau1MFilesParameters(BaseModel):
    calibration: bool = Field(default=True)
    dark_filenames: List[str]
    gain_filenames: List[str]
    photon_energy_kev: float

    @model_validator(mode="after")
    def check_calibration_parameters(self) -> Self:
        if self.calibration and (
            self.dark_filenames is None
            or self.gain_filenames is None
            or self.photon_energy_kev is None
        ):
            raise ValueError(
                "If calibration is requested for a Jungfrau1M detector, the "
                "following entries must be present in the set of parameters "
                "related to the detector, and cannot values of None: "
                "dark_filenames, gain_filenames, photon_energy_kev"
            )
        return self


class _FloatEntryParameters(BaseModel):
    value: float

    @field_validator("value")
    def check_value(cls: Self, v: Union[float, None]) -> float:
        if v is None:
            raise ValueError(
                "The following entry must be present in the set of OM monitor "
                "parameters for every data source of type "
                "FloatValueFromConfiguration: value",
            )
        return v


class OmJungfrau1MDataSourceMixin:
    """
    See documentation of the `__init__` function.
    """

    def __new__(cls: Type[T], *args: Any, **kwargs: Any) -> T:
        if cls is OmJungfrau1MDataSourceMixin:
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
        Detector data frames from Jungfrau 1M HDF5 files.

        This class deals with the retrieval of Jungfrau 1M detector data frame from
        files written by the detector in HDF5 format.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, in communications with the user or for the retrieval
                of a sensor's initialization parameters.

            parameters: An object storing OM's configuration parameters.
        """

        if data_source_name not in parameters:
            raise AttributeError(
                "The following section must be present in the configuration file: "
                f"data retrieval_layer/{data_source_name}"
            )

        try:
            self._parameters: _Jungfrau1MFilesParameters = (
                _Jungfrau1MFilesParameters.model_validate(parameters[data_source_name])
            )
        except ValidationError as exception:
            raise OmConfigurationFileSyntaxError(
                "Error parsing the following section of OM's configuration parameters: "
                f"data_retrieval_layer/{data_source_name} "
                f"{exception}"
            )

        self._calibrated_data_required: bool = self._parameters.calibration
        self._dark_filenames: List[str] = self._parameters.dark_filenames
        self._gain_filenames: List[str] = self._parameters.gain_filenames
        self._photon_energy_kev: float = self._parameters.photon_energy_kev

    def initialize_data_source(self) -> None:
        """
        Initializes the HDF5 file-based Jungfrau 1M detector data frame source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves from OM's configuration parameters all the information
        needed to initialize the data source. It looks at the
        `{data_source_name}_calibration` entry in OM's `data retrieval layer`
        configuration parameter group to determine if calibrated data needs to be
        retrieved. In the affirmative case, it reads the names of the files containing
        the required calibration constants from the entries `dark_filenames` and
        `gain_filenames` in the `calibration` parameter group.
        """
        if self._calibrated_data_required:
            self._calibration = Jungfrau1MCalibration(
                dark_filenames=self._dark_filenames,
                gain_filenames=self._gain_filenames,
                photon_energy_kev=self._photon_energy_kev,
            )


class TimestampFromEvent(OmDataSourceProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        data_source_name: str,
        parameters: Dict[str, Any],
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

            parameters: An object storing OM's configuration parameters.
        """
        del parameters
        del data_source_name

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


class FloatValueFromConfiguration(OmDataSourceProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        data_source_name: str,
        parameters: Dict[str, Any],
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

        if data_source_name not in parameters:
            raise AttributeError(
                "The following section must be present in the configuration file: "
                f"data retrieval_layer/{data_source_name}"
            )

        try:
            self._parameters: _FloatEntryParameters = (
                _FloatEntryParameters.model_validate(parameters[data_source_name])
            )
        except ValidationError as exception:
            raise OmConfigurationFileSyntaxError(
                "Error parsing the following section of OM's configuration parameters: "
                f"data_retrieval_layer/{data_source_name} "
                f"{exception}"
            )

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
        pass

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
        return self._parameters.value
