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

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy
from numpy.typing import NDArray

from om.algorithms.calibration import Jungfrau1MCalibration
from om.lib.files import load_hdf5_data
from om.lib.logging import log_error_and_exit
from om.lib.parameters import DataSourceParameters
from om.lib.protocols import OmDataSourceProtocol


@dataclass
class Jungfrau1MFrameInfo:
    # This typed dictionary is used internally to store additional information
    # required to retrieve Jungfrau 1M frame data.
    h5file: Any
    index: int
    file_timestamp: float


class OmJungfrau1MDataSourceMixin:
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        data_source_name: str,
        parameters: DataSourceParameters,
        additional_info: dict[str, Any],
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
        del additional_info
        self._calibration: bool = False
        self._dark_filenames: list[str] = []
        self._gain_filenames: list[str] = []
        self._photon_energy_kev: float = 0

        extra_parameters: dict[str, Any] | None = parameters.__pydantic_extra__
        if extra_parameters is not None:
            if "calibration" in extra_parameters:
                self._calibration = extra_parameters["calibration"]
            if "dark_filenames" in extra_parameters:
                self._dark_filenames = extra_parameters["dark_filenames"]
            if "gain_filenames" in extra_parameters:
                self._gain_filenames = extra_parameters["gain_filenames"]
            if "photon_energy_kev" in extra_parameters:
                self._photon_energy_kev = extra_parameters["photon_energy_kev"]

        if self._calibration is True:
            if len(self._dark_filenames) == 0:
                log_error_and_exit(
                    f"The entry 'dark_filenames' needed by the {data_source_name} "
                    "data source is not defined"
                )
            if len(self._gain_filenames) == 0:
                log_error_and_exit(
                    f"The entry 'gain_filenames' needed by the {data_source_name} "
                    "data source is not defined"
                )
            if self._photon_energy_kev == 0:
                log_error_and_exit(
                    f"The entry 'photon_energy_kev' needed by the {data_source_name} "
                    "data source is not defined"
                )

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
        if self._calibration is True:
            self._calibration_algorithm = Jungfrau1MCalibration(
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
        parameters: DataSourceParameters,
        additional_info: dict[str, Any],
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
        del data_source_name
        del parameters
        del additional_info

    def initialize_data_source(self) -> None:
        """
        Initializes the event timestamp data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        No initialization is needed to retrieve timestamp information from data events,
        so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: dict[str, Any]) -> numpy.float64:
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
        parameters: DataSourceParameters,
        additional_info: dict[str, Any],
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
        del additional_info

        extra_parameters: dict[str, Any] | None = parameters.__pydantic_extra__
        if extra_parameters is None:
            log_error_and_exit(
                f"Entries needed by the {data_source_name} data source are not defined"
            )
            return  # Fot the type checker
        if "value" not in extra_parameters:
            log_error_and_exit(
                f"Entry 'value' is not defined for data source {data_source_name}"
            )
        self._value: float = extra_parameters["value"]

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

    def get_data(self, *, event: dict[str, Any]) -> float:
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


class IntValueFromConfiguration(OmDataSourceProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        data_source_name: str,
        parameters: DataSourceParameters,
        additional_info: dict[str, Any],
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
        del additional_info

        extra_parameters: dict[str, Any] | None = parameters.__pydantic_extra__
        if extra_parameters is None:
            log_error_and_exit(
                f"Entries needed by the {data_source_name} data source are not defined"
            )
            return  # Fot the type checker
        if "value" not in extra_parameters:
            log_error_and_exit(
                f"Entry 'value' is not defined for data source {data_source_name}"
            )
        self._value: int = extra_parameters["value"]

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

    def get_data(self, *, event: dict[str, Any]) -> float:
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


class ArrayFromHdf5File(OmDataSourceProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        data_source_name: str,
        parameters: DataSourceParameters,
        additional_info: dict[str, Any],
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
        del additional_info

        extra_parameters: dict[str, Any] | None = parameters.__pydantic_extra__
        if extra_parameters is None:
            log_error_and_exit(
                f"Entries needed by the {data_source_name} data source are not defined"
            )
            return  # Fot the type checker
        if "hd5_filename" not in extra_parameters:
            log_error_and_exit(
                "Entry 'hdf5_filename' is not defined for data source "
                f"{data_source_name}"
            )
        if "hd5_path" not in extra_parameters:
            log_error_and_exit(
                "Entry 'hdf5_filename' is not defined for data source "
                f"{data_source_name}"
            )
        self._hdf5_filename: Path = Path(extra_parameters["hdf5_filename"])
        self._hdf5_path: str = extra_parameters["hdf5_path"]

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
        self._array: NDArray[numpy.floating[Any] | numpy.signedinteger[Any]] = (
            load_hdf5_data(
                hdf5_filename=self._hdf5_filename,
                hdf5_path=self._hdf5_path,
            )
        )

    def get_data(
        self, *, event: dict[str, Any]
    ) -> NDArray[numpy.floating[Any] | numpy.signedinteger[Any]]:
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
        return self._array
