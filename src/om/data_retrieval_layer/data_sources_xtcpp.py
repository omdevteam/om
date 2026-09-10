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
Psana-related data sources.

This module contains Data Source classes that deal with data retrieved from the ASAP::O
software framework (used at the PETRA III facility).

This module contains Data Source classes that deal with data retrieved from  the psana
software framework (used at the LCLS facility).
"""

from pathlib import Path
from typing import (
    Any,
    Callable,
    cast,
)

import numpy
from numpy.typing import NDArray

from om.lib.exceptions import (
    OmDataExtractionError,
    OmMissingDependencyError,
)
from om.lib.files import load_hdf5_data
from om.lib.layer_management import import_data_source_class
from om.lib.logging import log_error_and_exit
from om.lib.parameters import DataSourceParameters
from om.lib.protocols import OmDataSourceProtocol

try:
    import _xtcpp  # type: ignore[import-untyped]
except ImportError:
    raise OmMissingDependencyError(
        "The following required module cannot be imported: _xtcpp"
    )


class AreaDetectorXtcpp:
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
        Area data frames from psana at the LCLS facility.

        This class deals with the retrieval of area detector data frames from the psana
        software framework. Classes dealing with the retrieval of data frames from
        specific area detector should inherit from this base class

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, in communications with the user or for the retrieval
                of a sensor's initialization parameters.

            parameters: An object storing OM's configuration parameters.
        """
        self._xtcpp_data_source: Any = additional_info["data_source"]

        self._gain_map_filename: Path = Path("")
        self._gain_map_hdf5_path: str = ""

        extra_parameters: dict[str, Any] | None = parameters.__pydantic_extra__

        if extra_parameters is None:
            log_error_and_exit(
                f"Entries needed by the {data_source_name} data source are not defined"
            )
            return  # For the type checker
        if "name" not in extra_parameters:
            log_error_and_exit(
                f"Entry 'name' is not defined for data source {data_source_name}"
            )
        if "calibration" not in extra_parameters:
            log_error_and_exit(
                f"Entry 'calibration' is not defined for data source {data_source_name}"
            )
        if "gain_map_filename" in extra_parameters:
            if "gain_map_hdf5_path" not in extra_parameters:
                log_error_and_exit(
                    "Entry 'gain_map_filename' is defined for data source "
                    f"{data_source_name}, but entry 'gain_map_hdf5_path' is not"
                )
            self._gain_map_filename = extra_parameters["gain_map_filename"]
            self._gain_map_hdf5_path = extra_parameters["gain_map_hdf5_path"]
        self._name: str = extra_parameters["name"]
        self._calibration: bool = extra_parameters["calibration"]

    def initialize_data_source(self) -> None:
        """
        Initializes the psana event identifier data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        No initialization is required to retrieve event identifiers for psana-based
        data events, so this function actually does nothing.
        """
        detector_wrapper: _xtcpp.DetectorWrapper = self._xtcpp_data_source.detector(
            self._name
        )

        if self._calibration:
            self._data_retrieval_function: Callable[[Any], Any] = (
                detector_wrapper.raw.calib  # pyright: ignore[reportUnknownMemberType]
            )
        else:
            self._data_retrieval_function = (
                detector_wrapper.raw.raw  # pyright: ignore[reportUnknownMemberType]
            )

        if self._gain_map_filename != Path("") and self._gain_map_hdf5_path != "":
            self._gain_map: NDArray[numpy.floating[Any]] | None = cast(
                NDArray[numpy.floating[Any]] | None,
                load_hdf5_data(
                    hdf5_filename=self._gain_map_filename,
                    hdf5_path=self._gain_map_hdf5_path,
                ),
            )
        else:
            self._gain_map = None

    def get_data(
        self, *, event: dict[str, Any]
    ) -> NDArray[numpy.floating[Any] | numpy.signedinteger[Any]]:
        """
        Retrieves a Jungfrau 4M detector data frame from psana.
        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves from psana the detector data frame associated with the
        provided event. It returns the frame as a 2D array storing pixel information.
        Data is retrieved in calibrated or non-calibrated form depending on the
        value of the `{source_protocols_name}_calibration` entry in OM's
        `data_retrieval_layer` configuration parameter group..

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A detector data frame.

        Raises:

            OmDataExtractionError: Raised when data cannot be retrieved from psana.
        """

        data: NDArray[numpy.floating[Any] | numpy.signedinteger[Any]] | None = (
            self._data_retrieval_function(event["data"])
        )

        if data is None:
            raise OmDataExtractionError(
                "Could not retrieve data from psana for the following data source: "
                f"{self._name}"
            )

        # Rearranges the data into 'slab' format.
        data_shape: tuple[int, ...] = data.shape
        if len(data_shape) == 2:
            data_reshaped: NDArray[numpy.floating[Any] | numpy.signedinteger[Any]] = (
                data
            )
        else:
            data_reshaped = data.reshape(data_shape[0] * data_shape[1], data_shape[2])

        if self._gain_map is not None:
            data_reshaped = data_reshaped * self._gain_map

        return data_reshaped


class EpicsVariableXtcpp(OmDataSourceProtocol):
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
        Timestamp information from psana at the LCLS facility.

        This class deals with the retrieval of timestamp information from the psana
        software framework.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, in communications with the user or for the retrieval
                of a sensor's initialization parameters.

            monitor_parameters: An object storing OM's configuration parameters.
        """
        self._xtcpp_data_source: Any = additional_info["data_source"]
        extra_parameters: dict[str, Any] | None = parameters.__pydantic_extra__
        if extra_parameters is None:
            log_error_and_exit(
                f"Entries needed by the {data_source_name} data source are not defined"
            )
            return  # For the type checker
        if "name" not in extra_parameters:
            log_error_and_exit(
                f"Entry 'name' is not defined for data source {data_source_name}"
            )
        self._name: str = extra_parameters["name"]

    def initialize_data_source(self) -> None:
        """
        Initializes the psana timestamp data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        No initialization is needed to retrieve timestamp information from psana,
        so this function actually does nothing.
        """
        self._epics_wrapper: _xtcpp.DetectorWrapper = self._xtcpp_data_source.detector(
            self._name
        )

    def get_data(self, *, event: dict[str, Any]) -> Any:
        """
        Retrieves an Epics variable's value from psana.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves from psana the value of the requested Epics variable
        associated with the provided event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The value of the Epics variable.
        """
        return self._epics_wrapper.get(event["data"])


class BeamEnergyFromEpicsVariableXtcpp(OmDataSourceProtocol):
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
        Beam energy information from psana at the LCLS facility.

        This class deals with the retrieval of beam energy information from the psana
        software framework.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, in communications with the user or for the retrieval
                of a sensor's initialization parameters.

            monitor_parameters: An object storing OM's configuration parameters.
        """
        self._xtcpp_data_source: Any = additional_info["data_source"]
        del data_source_name
        del parameters

    def initialize_data_source(self) -> None:
        """
        Initializes the psana beam energy data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function initializes the psana Detector interface for the retrieval of
        beam energy information.
        """
        self._epics_wrapper: _xtcpp.DetectorWrapper = self._xtcpp_data_source.detector(
            "photonBeam_Wavelength"
        )

    def get_data(self, *, event: dict[str, Any]) -> float:
        """
        Retrieves beam energy information from psana using an Epics variable.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves from psana the value of the beam energy associated to
        the provided event. It calculates the beam energy from the value of the
        SIOC:SYS0:ML00:AO192 Epics variable attached to the event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The beam energy in eV.

        Raises:

            OmDataExtractionError: Raised when data cannot be retrieved from psana.
        """
        wavelength: float | None = self._epics_wrapper.get(event["data"])
        if wavelength is None:
            raise OmDataExtractionError(
                "Could not retrieve beam energy information from XTCPP via the "
                "SIOC:SYS0:ML00:AO192 PV."
            )
        h: float = 6.626070e-34  # J.m
        c: float = 2.99792458e8  # m/s
        joules_per_ev: float = 1.602176621e-19  # J/eV
        photon_energy: float = (h / joules_per_ev * c) / (wavelength * 1e-9)

        return photon_energy


class TimestampXtcpp(OmDataSourceProtocol):
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
        Timestamp information from psana at the LCLS facility.

        This class deals with the retrieval of timestamp information from the psana
        software framework.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, in communications with the user or for the retrieval
                of a sensor's initialization parameters.

            monitor_parameters: An object storing OM's configuration parameters.
        """
        self._xtcpp_data_source: Any = additional_info["data_source"]

        del data_source_name
        del parameters

    def initialize_data_source(self) -> None:
        """
        Initializes the psana timestamp data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        No initialization is needed to retrieve timestamp information from psana,
        so this function actually does nothing.
        """
        self._timing_wrapper: _xtcpp.DetectorWrapper = self._xtcpp_data_source.detector(
            "jungfrau"
        )

    def get_data(self, *, event: dict[str, Any]) -> numpy.float64:
        """
        Retrieves timestamp information from psana.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves from psana the timestamp information for the provided
        event. Psana provides this information with nanosecond precision.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The timestamp for the data event.
        """
        # timing: list[numpy.int64] = self._timing_wrapper.raw.timeStamp(event["data"])
        ts_s: numpy.int_ = self._timing_wrapper.time_seconds()
        ts_ns: numpy.int = self._timing_wrapper.time_nanoseconds()

        timestamp: numpy.float64 = numpy.float64(ts_s) + numpy.float64(ts_ns) / 1e9
        return timestamp


class EvrCodesXtcpp(OmDataSourceProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        data_source_name: str,
        parameters: DataSourceParameters,
        additional_info: dict[str, Any] = {},
    ):
        """
        EVR event codes from psana at the LCLS facility.

        This class deals with the retrieval EVR event codes from the psana software
        framework.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, in communications with the user or for the retrieval
                of a sensor's initialization parameters.

            monitor_parameters: An object storing OM's configuration parameters.
        """
        self._xtcpp_data_source: Any = additional_info["data_source"]

        extra_parameters: dict[str, Any] | None = parameters.__pydantic_extra__

        if extra_parameters is None:
            log_error_and_exit(
                f"Entries needed by the {data_source_name} data source are not defined"
            )
            return  # For the type checker
        self._event_code: int = extra_parameters["event_code"]

    def initialize_data_source(self) -> None:
        """
        Initializes the psana EVR event code data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function initializes the data retrieval for the EVR event code number
        specified  by the `{data_source_name}_evr_code` entry in OM's
        `Data Retrieval Layer` configuration parameter group. The EVR event source
        to monitor for the emission of the event is instead determined by the
        `psana_evr_source_name` entry in the same parameter group.
        """
        self._timing_wrapper: Any = self._xtcpp_data_source.detector(  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
            "timing"
        )

    def get_data(self, *, event: dict[str, Any]) -> bool:
        """
        Retrieves EVR events code information from psana.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function checks whether the event code attached to the Data Source has
        been emitted, for the provided event, by the monitored EVR source.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            Whether the required event code has been emitted for the provided event.

        Raises:

            OmDataExtractionError: Raised when data cannot be retrieved from psana.
        """
        sequenceValues: Any = self._timing_wrapper.raw.seqenceValue(event["data"])
        if sequenceValues is None:
            raise OmDataExtractionError("Could not retrieve event codes from XTCPP.")

        index: int
        current_evr_codes = [
            int((sequenceValues[index >> 4] >> (index & 0xF)) & 1)
            for index in range(288)
        ]

        return self._event_code in current_evr_codes


class EvrCodelistXtcpp(OmDataSourceProtocol):
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
        EVR event codes from psana at the LCLS facility.

        This class deals with the retrieval EVR event codes from the psana software
        framework.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, in communications with the user or for the retrieval
                of a sensor's initialization parameters.

            monitor_parameters: An object storing OM's configuration parameters.
        """
        del data_source_name
        del parameters

        self._xtcpp_data_source: Any = additional_info["data_source"]

    def initialize_data_source(self) -> None:
        """
        Initializes the psana EVR event code data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function initializes the data retrieval for the EVR event code number
        specified  by the `{data_source_name}_evr_code` entry in OM's
        `Data Retrieval Layer` configuration parameter group. The EVR event source
        to monitor for the emission of the event is instead determined by the
        `psana_evr_source_name` entry in the same parameter group.
        """
        self._timing_wrapper: Any = self._xtcpp_data_source.detector(  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
            "timing"
        )

    def get_data(self, *, event: dict[str, Any]) -> NDArray[numpy.int_]:
        """
        Retrieves EVR events code information from psana.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function checks whether the event code attached to the Data Source has
        been emitted, for the provided event, by the monitored EVR source.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            Whether the required event code has been emitted for the provided event.

        Raises:

            OmDataExtractionError: Raised when data cannot be retrieved from psana.
        """
        sequenceValues: Any = self._timing_wrapper.raw.seqenceValue(event["data"])
        if sequenceValues is None:
            raise OmDataExtractionError("Could not retrieve event codes from XTCPP.")

        index: int
        current_evr_codes = [
            int((sequenceValues[index >> 4] >> (index & 0xF)) & 1)
            for index in range(288)
        ]

        numpy_evr_codes = numpy.pad(
            numpy.array(current_evr_codes),
            pad_width=(0, 256 - len(current_evr_codes)),
            constant_values=0,
        )
        return numpy_evr_codes


class EventIdXtcpp(OmDataSourceProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        data_source_name: str,
        parameters: dict[str, Any],
        additional_info: dict[str, Any],
    ):
        """
        Data event identifiers from psana at the LCLS facility.

        This class deals with the retrieval of unique event identifiers for
        psana-based data events.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, in communications with the user or for the retrieval
                of a sensor's initialization parameters.

            monitor_parameters: An object storing OM's configuration parameters.
        """
        del data_source_name
        del parameters
        del additional_info

    def initialize_data_source(self) -> None:
        """
        Initializes the psana event identifier data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        No initialization is required to retrieve event identifiers for psana-based
        data events, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: dict[str, Any]) -> str:
        """
        Retrieves an event identifier from psana.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves from psana a unique identifier for the provided event.
        The psana software framework provides timestamp information with
        nanosecond-level precision for each event, plus a specific fiducial string for
        more detailed identification. The identifier is generated by combining the
        timestamp and fiducial information that psana provides for the event. It has
        the following format:
        `{timestamp: seconds}-{timestamp: nanoseconds}-{fiducial_string}`.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A unique event identifier.
        """
        return f"{event['additional_info']['timestamp']}"
