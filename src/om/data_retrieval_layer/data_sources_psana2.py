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
    Dict,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

import numpy
from numpy.typing import NDArray

from om.lib.exceptions import (
    OmConfigurationFileSyntaxError,
    OmDataExtractionError,
    OmMissingDependencyError,
)
from om.lib.files import load_hdf5_data
from om.lib.parameters import DataSourceParameters
from om.lib.protocols import OmDataSourceProtocol

try:
    import psana  # type: ignore
except ImportError:
    raise OmMissingDependencyError(
        "The following required module cannot be imported: psana"
    )


T = TypeVar("T")


class OmDetectorInterfacePsana2DataSourceMixin:
    """
    See documentation of the `__init__` function.
    """

    def __new__(cls: Type[T], *args: Any, **kwargs: Any) -> T:
        if cls is OmDetectorInterfacePsana2DataSourceMixin:
            raise TypeError(
                f"{cls.__name__} is a Mixin class and should not be instantiated"
            )
        return object.__new__(cls)

    def __init__(
        self,
        *,
        data_source_name: str,
        parameters: DataSourceParameters,
        additional_info: Dict[str, Any],
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
        self._run: Any = additional_info["run"]

    def initialize_data_source(self) -> None:
        """
        Initializes the psana event identifier data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        No initialization is required to retrieve event identifiers for psana-based
        data events, so this function actually does nothing.
        """
        self._detector_interface: Any = self._run.Detector(self._parameters.psana_name)


class AssembledDetectorPsana2(
    OmDetectorInterfacePsana2DataSourceMixin, OmDataSourceProtocol
):
    """
    See documentation of the `__init__` function.
    """

    def get_data(self, *, event: Dict[str, Any]) -> NDArray[numpy.float_]:
        """
        Retrieves an assembled detector data frame from psana.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves from psana the assembled detector data frame associated
        with the provided event. It returns the frame as a 2D array storing pixel
        information.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            An assembled detector data frame.

        Raises:

            OmDataExtractionError: Raised when data cannot be retrieved from psana.
        """
        assembled_data: Optional[NDArray[numpy.float_]] = (
            self._detector_interface.image(event["data"])
        )
        if assembled_data is None:
            raise OmDataExtractionError(
                "Could not retrieve data from psana for the following data source: "
                f"{self._parameters.psana_name}"
            )

        return assembled_data


class EpicsVariablePsana2(
    OmDetectorInterfacePsana2DataSourceMixin, OmDataSourceProtocol
):
    """
    See documentation of the `__init__` function.
    """

    def get_data(self, *, event: Dict[str, Any]) -> Any:
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
        return self._detector_interface(event["data"])


class BeamEnergyFromEpicsVariablePsana2(OmDataSourceProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        data_source_name: str,
        parameters: Dict[str, Any],
        additional_info: Dict[str, Any],
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
        del data_source_name
        del parameters

        self._run: Any = additional_info["run"]

    def initialize_data_source(self) -> None:
        """
        Initializes the psana beam energy data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function initializes the psana Detector interface for the retrieval of
        beam energy information.
        """
        self._detector_interface: Any = self._run.Detector("SIOC:SYS0:ML00:AO192")

    def get_data(self, *, event: Dict[str, Any]) -> float:
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
        wavelength: Optional[float] = self._detector_interface(event["data"])
        if wavelength is None:
            raise OmDataExtractionError(
                "Could not retrieve beam energy information from psana via the "
                "SIOC:SYS0:ML00:AO192 PV."
            )
        h: float = 6.626070e-34  # J.m
        c: float = 2.99792458e8  # m/s
        joules_per_ev: float = 1.602176621e-19  # J/eV
        photon_energy: float = (h / joules_per_ev * c) / (wavelength * 1e-9)

        return photon_energy


class AreaDetectorPsana2(OmDataSourceProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        data_source_name: str,
        parameters: Dict[str, Any],
        additional_info: Dict[str, Any],
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
        self._run: Any = additional_info["run"]

        if data_source_name not in parameters:
            raise AttributeError(
                "The following section must be present in the configuration file: "
                f"data retrieval_layer/{data_source_name}"
            )
        try:
            self._parameters: _AreaDetectorPsana2Parameters = (
                _AreaDetectorPsana2Parameters.model_validate(
                    parameters[data_source_name]
                )
            )
        except ValidationError as exception:
            raise OmConfigurationFileSyntaxError(
                "Error parsing the following section of OM's configuration parameters: "
                f"data_retrieval_layer/{data_source_name}"
                f"{exception}"
            )

    def initialize_data_source(self) -> None:
        """
        Initializes the psana event identifier data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        No initialization is required to retrieve event identifiers for psana-based
        data events, so this function actually does nothing.
        """
        detector_interface: Any = self._run.Detector(self._parameters.psana_name)

        if self._parameters.calibration:
            self._data_retrieval_function: Callable[[Any], Any] = (
                detector_interface.raw.calib
            )
        else:
            self._data_retrieval_function = detector_interface.raw.raw

        if (
            self._parameters.gain_map_filename is not None
            and self._parameters.gain_map_hdf5_path is not None
        ):
            self._gain_map: Optional[NDArray[numpy.float_]] = cast(
                Optional[NDArray[numpy.float_]],
                load_hdf5_data(
                    hdf5_filename=self._parameters.gain_map_filename,
                    hdf5_path=self._parameters.gain_map_hdf5_path,
                ),
            )
        else:
            self._gain_map = None

    def get_data(
        self, *, event: Dict[str, Any]
    ) -> Union[NDArray[numpy.float_], NDArray[numpy.int_]]:
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
        psana_data: Optional[Union[NDArray[numpy.float_], NDArray[numpy.int_]]] = (
            self._data_retrieval_function(event["data"])
        )
        if psana_data is None:
            raise OmDataExtractionError(
                "Could not retrieve data from psana for the following data source: "
                f"{self._parameters.psana_name}"
            )

        # Rearranges the data into 'slab' format.
        psana_data_shape: Tuple[int, ...] = psana_data.shape
        if len(psana_data_shape) == 2:
            psana_data_reshaped: Union[NDArray[numpy.float_], NDArray[numpy.int_]] = (
                psana_data
            )
        else:
            psana_data_reshaped = psana_data.reshape(
                psana_data_shape[0] * psana_data_shape[1], psana_data_shape[2]
            )

        if self._gain_map is not None:
            psana_data_reshaped = psana_data_reshaped * self._gain_map

        return psana_data_reshaped


class TimestampPsana2(OmDataSourceProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        data_source_name: str,
        parameters: Dict[str, Any],
        additional_info: Dict[str, Any],
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
        del data_source_name
        del parameters
        del additional_info

    def initialize_data_source(self) -> None:
        """
        Initializes the psana timestamp data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        No initialization is needed to retrieve timestamp information from psana,
        so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> int:
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
        timestamp: int = event["data"].timestamp
        return timestamp


class EventIdPsana2(OmDataSourceProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        data_source_name: str,
        parameters: Dict[str, Any],
        additional_info: Dict[str, Any],
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

    def get_data(self, *, event: Dict[str, Any]) -> str:
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
        return event["additional_info"]["timestamp"]


class BeamEnergyPsana2(OmDataSourceProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        data_source_name: str,
        parameters: Dict[str, Any],
        additional_info: Dict[str, Any],
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
        del data_source_name
        del parameters
        self._run: Any = additional_info["run"]

    def initialize_data_source(self) -> None:
        """
        Initializes the psana beam energy data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function initializes the psana Detector interface for the retrieval of
        beam energy information.
        """

        self._detector_interface: Any = self._run.Detector("ebeamh")

    def get_data(self, *, event: Dict[str, Any]) -> float:
        """
        Retrieves beam energy information from psana.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves from psana the beam energy information for the provided
        event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The beam energy.
        """
        return cast(
            float, self._detector_interface.raw.ebeamPhotonEnergy(event["data"])
        )
