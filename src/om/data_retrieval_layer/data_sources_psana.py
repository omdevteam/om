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
from typing import Any, Callable, Dict, List, Tuple, Type, TypeVar, Union, cast

import numpy
from numpy.typing import NDArray
from pydantic import BaseModel, Field, ValidationError

from om.lib.exceptions import (
    OmConfigurationFileSyntaxError,
    OmDataExtractionError,
    OmMissingDependencyError,
    OmWrongParameterTypeError,
)
from om.typing import OmDataSourceProtocol

try:
    import psana  # type: ignore
except ImportError:
    raise OmMissingDependencyError(
        "The following required module cannot be imported: psana"
    )


T = TypeVar("T")


class _DetectorInterfacePsanaParameters(BaseModel):
    psana_name: str


class _AreaDetectorPsanaParameters(BaseModel):
    psana_name: str
    calibration: bool = Field(default=True)


class _CspadPsanaParameters(BaseModel):
    psana_name: str
    calibration: bool = Field(default=True)


class _EvrCodesPsanaParameters(BaseModel):
    evr_source: str
    event_code: int


class _LclsExtraPsanaParameters(BaseModel):
    data: List[Tuple[str, str, str]]


class OmDetectorInterfacePsanaDataSourceMixin:
    """
    See documentation of the `__init__` function.
    """

    def __new__(cls: Type[T], *args: Any, **kwargs: Any) -> T:
        if cls is OmDetectorInterfacePsanaDataSourceMixin:
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

        if data_source_name not in parameters:
            raise AttributeError(
                "The following section must be present in the configuration file: "
                f"data retrieval_layer/{data_source_name}"
            )

        try:
            self._parameters: _DetectorInterfacePsanaParameters = (
                _DetectorInterfacePsanaParameters.model_validate(
                    parameters[data_source_name]
                )
            )
        except ValidationError as exception:
            raise OmConfigurationFileSyntaxError(
                "Error parsing the following section of OM's configuration parameters: "
                f"data_retrieval_layer/{data_source_name} "
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
        self._detector_interface: Any = psana.Detector(self._parameters.psana_name)


class RayonixPsana(OmDetectorInterfacePsanaDataSourceMixin, OmDataSourceProtocol):
    """
    See documentation of the `__init__` function.
    """

    def get_data(self, *, event: Dict[str, Any]) -> NDArray[numpy.float_]:
        """
        Retrieves a Rayonix detector data frame from psana.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves from psana the detector data frame associated with the
        provided event. It returns the frame as a 2D array storing pixel information.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A detector data frame.

        Raises:

            OmDataExtractionError: Raised when data cannot be retrieved from psana.
        """
        rayonix_psana: Union[NDArray[numpy.float_], None] = self._detector_interface(
            event["data"]
        )
        if rayonix_psana is None:
            raise OmDataExtractionError(
                "Could not retrieve data from psana for the following data source: "
                f"{self._parameters.psana_name}"
            )
        return rayonix_psana


class OpalPsana(OmDetectorInterfacePsanaDataSourceMixin, OmDataSourceProtocol):
    """
    See documentation of the `__init__` function.
    """

    def get_data(self, *, event: Dict[str, Any]) -> NDArray[numpy.float_]:
        """
        Retrieves an Opal camera data frame from psana.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves from psana the camera data frame associated with the
        provided event. It returns the frame as a 2D array storing pixel information.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A camera data frame.

        Raises:

            OmDataExtractionError: Raised when data cannot be retrieved from psana.
        """
        opal_psana: Union[NDArray[numpy.float_], None] = self._detector_interface(
            event["data"]
        )
        if opal_psana is None:
            raise OmDataExtractionError(
                "Could not retrieve data from psana for the following data source: "
                f"{self._parameters.psana_name}"
            )
        return opal_psana


class AcqirisPsana(OmDetectorInterfacePsanaDataSourceMixin, OmDataSourceProtocol):
    """
    See documentation of the `__init__` function.
    """

    def get_data(
        self, *, event: Dict[str, Any]
    ) -> Tuple[NDArray[numpy.float_], NDArray[numpy.float_]]:
        """
        Retrieves Acqiris waveform data from psana.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves from psana the waveform data for the provided event.
        The Acqiris data is retrieved for all of the detector's channels at the same
        time, and returned in the form of a tuple with two entries:

        * The first entry in the tuple is a 1D array storing information about the time
        points at which the waveform data has been digitized. The size of this array
        matches the size of each waveform in the second entry.

        * The second entry is a 2D array that stores the waveform information from all
        the channels. The first axis of the array corresponds to the channel number,
        the second one stores, for each channel, the digitized waveform data.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A tuple, with two entries, storing the digitized waveform data from the
                Acqiris detector.
        """
        wftime: Union[NDArray[numpy.float_], None] = self._detector_interface.wftime(
            event["data"]
        )
        waveform: Union[NDArray[numpy.float_], None] = (
            self._detector_interface.waveform(event["data"])
        )

        if wftime is None or waveform is None:
            raise OmDataExtractionError(
                "Could not retrieve data from psana for the following data source: "
                f"{self._parameters.psana_name}"
            )

        return (wftime, waveform)


class AssembledDetectorPsana(
    OmDetectorInterfacePsanaDataSourceMixin, OmDataSourceProtocol
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
        assembled_data: Union[NDArray[numpy.float_], None] = (
            self._detector_interface.image(event["data"])
        )
        if assembled_data is None:
            raise OmDataExtractionError(
                "Could not retrieve data from psana for the following data source: "
                f"{self._parameters.psana_name}"
            )

        return assembled_data


class Wave8TotalIntensityPsana(
    OmDetectorInterfacePsanaDataSourceMixin, OmDataSourceProtocol
):
    """
    See documentation of the `__init__` function.
    """

    def get_data(self, *, event: Dict[str, Any]) -> float:
        """
        Retrieves Wave8 intensity data from psana.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves from psana the total intensity recorded by the detector
        for the provided event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The total intensity recorded by the Wave8 detector.
        """

        wave8_total_intensity_data: Union[float, None] = self._detector_interface.image(
            event["data"]
        )
        if wave8_total_intensity_data is None:
            raise OmDataExtractionError(
                "Could not retrieve data from psana for the following data source: "
                f"{self._parameters.psana_name}"
            )

        return wave8_total_intensity_data


class EpicsVariablePsana(OmDetectorInterfacePsanaDataSourceMixin, OmDataSourceProtocol):
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
        return self._detector_interface()


class DiodeTotalIntensityPsana(
    OmDetectorInterfacePsanaDataSourceMixin, OmDataSourceProtocol
):
    """
    See documentation of the `__init__` function.
    """

    def get_data(self, *, event: Dict[str, Any]) -> float:
        """
        Retrieves diode intensity data from psana.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves from psana the total intensity recorded by the diode
        for the provided event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The total intensity recorded by the diode.

        """
        return cast(float, self._detector_interface.get(event["data"]).TotalIntensity())


class BeamEnergyFromEpicsVariablePsana(
    OmDetectorInterfacePsanaDataSourceMixin, OmDataSourceProtocol
):
    """
    See documentation of the `__init__` function.
    """

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
        wavelength: Union[float, None] = self._detector_interface(event["data"])
        if wavelength is None:
            raise OmDataExtractionError(
                "Could not retrieve beam energy information from psana via the "
                f"{self._parameters.psana_name} data source."
            )
        h: float = 6.626070e-34  # J.m
        c: float = 2.99792458e8  # m/s
        joules_per_ev: float = 1.602176621e-19  # J/eV
        photon_energy: float = (h / joules_per_ev * c) / (wavelength * 1e-9)

        return photon_energy


class AreaDetectorPsana(OmDataSourceProtocol):
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

        if data_source_name not in parameters:
            raise AttributeError(
                "The following section must be present in the configuration file: "
                f"data retrieval_layer/{data_source_name}"
            )
        try:
            self._parameters: _AreaDetectorPsanaParameters = (
                _AreaDetectorPsanaParameters.model_validate(
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
        detector_interface: Any = psana.Detector(self._parameters.psana_name)

        if self._parameters.calibration:
            self._data_retrieval_function: Callable[[Any], Any] = (
                detector_interface.calib
            )
        else:
            self._data_retrieval_function = detector_interface.raw

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
        psana_data: Union[NDArray[numpy.float_], NDArray[numpy.int_], None] = (
            self._data_retrieval_function(event["data"])
        )
        if psana_data is None:
            raise OmDataExtractionError(
                "Could not retrieve data from psana for the following data source: "
                f"{self._parameters.psana_name}"
            )

        # Rearranges the data into 'slab' format.
        psana_data_shape: Tuple[int, ...] = psana_data.shape
        psana_data_reshaped: Union[NDArray[numpy.float_], NDArray[numpy.int_]] = (
            psana_data.reshape(
                psana_data_shape[0] * psana_data_shape[1], psana_data_shape[2]
            )
        )

        return psana_data_reshaped


class CspadPsana(OmDataSourceProtocol):
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

        if data_source_name not in parameters:
            raise AttributeError(
                "The following section must be present in the configuration file: "
                f"data retrieval_layer/{data_source_name}"
            )

        try:
            self._parameters: _CspadPsanaParameters = (
                _CspadPsanaParameters.model_validate(parameters[data_source_name])
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
        detector_interface: Any = psana.Detector(self._parameters.psana_name)

        if self._parameters.calibration:
            self._data_retrieval_function: Callable[[Any], Any] = (
                detector_interface.calib
            )
        else:
            self._data_retrieval_function = detector_interface.raw

    def get_data(
        self, *, event: Dict[str, Any]
    ) -> Union[NDArray[numpy.float_], NDArray[numpy.int_]]:
        """
        Retrieves a CSPAD detector data frame from psana.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves from psana the detector data frame associated with the
        provided event. It returns the frame as a 2D array storing pixel information.
        Data is retrieved in calibrated or non-calibrated form depending on the
        value of the `{source_protocols_name}_calibration` entry in OM's
        `data_retrieval_layer` configuration parameter group.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A detector data frame.

        Raises:

            OmDataExtractionError: Raised when data cannot be retrieved from psana.
        """
        cspad_psana: Union[NDArray[numpy.float_], NDArray[numpy.int_], None] = (
            self._data_retrieval_function(event["data"])
        )
        if cspad_psana is None:
            raise OmDataExtractionError(
                "Could not retrieve data from psana for the following data source: "
                f"{self._parameters.psana_name}"
            )

        # Rearranges the data into 'slab' format.
        cspad_reshaped: Union[NDArray[numpy.float_], NDArray[numpy.int_]] = (
            cspad_psana.reshape((4, 8, 185, 388))
        )
        cspad_slab: Union[NDArray[numpy.float_], NDArray[numpy.int_]] = cast(
            Union[NDArray[numpy.float_], NDArray[numpy.int_]],
            numpy.zeros(shape=(1480, 1552), dtype=cspad_reshaped.dtype),
        )
        index: int
        for index in range(cspad_reshaped.shape[0]):
            cspad_slab[
                :,
                index * cspad_reshaped.shape[3] : (index + 1) * cspad_reshaped.shape[3],
            ] = cspad_reshaped[index].reshape(
                (
                    cspad_reshaped.shape[1] * cspad_reshaped.shape[2],
                    cspad_reshaped.shape[3],
                )
            )

        return cspad_slab


class TimestampPsana(OmDataSourceProtocol):
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

    def initialize_data_source(self) -> None:
        """
        Initializes the psana timestamp data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        No initialization is needed to retrieve timestamp information from psana,
        so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> numpy.float64:
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
        psana_event_id: Any = event["data"].get(
            psana.EventId  # pyright: ignore[reportAttributeAccessIssue]
        )
        timestamp_epoch_format: Any = psana_event_id.time()
        return numpy.float64(
            str(timestamp_epoch_format[0]) + "." + str(timestamp_epoch_format[1])
        )


class EventIdPsana(OmDataSourceProtocol):
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
        psana_event_id: Any = event["data"].get(
            psana.EventId  # pyright: ignore[reportAttributeAccessIssue]
        )
        timestamp_epoch_format: Any = psana_event_id.time()
        fiducials: Any = psana_event_id.fiducials()
        return f"{timestamp_epoch_format[0]}-{timestamp_epoch_format[1]}-{fiducials}"


class BeamEnergyPsana(OmDataSourceProtocol):
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

    def initialize_data_source(self) -> None:
        """
        Initializes the psana beam energy data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function initializes the psana Detector interface for the retrieval of
        beam energy information.
        """
        self._detector_interface: Any = psana.Detector("EBeam")

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
            float, self._detector_interface.get(event["data"]).ebeamPhotonEnergy()
        )


class EvrCodesPsana(OmDataSourceProtocol):
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

        if data_source_name not in parameters:
            raise AttributeError(
                "The following section must be present in the configuration file: "
                f"data retrieval_layer/{data_source_name}"
            )

        try:
            self._parameters: _EvrCodesPsanaParameters = (
                _EvrCodesPsanaParameters.model_validate(parameters[data_source_name])
            )
        except ValidationError as exception:
            raise OmConfigurationFileSyntaxError(
                "Error parsing the following section of OM's configuration parameters: "
                f"data_retrieval_layer/{data_source_name}"
                f"{exception}"
            )

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
        self._detector_interface: Any = psana.Detector(self._parameters.evr_source)

    def get_data(self, *, event: Dict[str, Any]) -> bool:
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
        current_evr_codes: Union[List[int], None] = self._detector_interface.eventCodes(
            event["data"]
        )
        if current_evr_codes is None:
            raise OmDataExtractionError("Could not retrieve event codes from psana.")

        return self._parameters.event_code in current_evr_codes


class LclsExtraPsana(OmDataSourceProtocol):
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
        Additional facility-specific information from psana at the LCLS facility.

        This class deals with the retrieval of information that is specific to the LCLS
        facility. Due to its non-generic nature, the nature of the information that can
        be collected is limited to a few predefined types. The collected information,
        due to its specific nature, should not be processed by OM at all, but only
        saved to a storage media, or passed to a facility-specific downstream
        application.

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
            self._parameters: _LclsExtraPsanaParameters = (
                _LclsExtraPsanaParameters.model_validate(parameters[data_source_name])
            )
        except ValidationError as exception:
            raise OmConfigurationFileSyntaxError(
                "Error parsing the following section of OM's configuration parameters: "
                f"data_retrieval_layer/{data_source_name}"
                f"{exception}"
            )

    def initialize_data_source(self) -> None:
        """
        Initializes the psana LCLS-specific information data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function initializes the data retrieval for the LCLS-specific information
        defined by the `lcls_extra` entry in the OM's `data_retrieval_layer`
        configuration parameter group. The entry must have the
        format of a list of tuples. Each tuple must be made up of three elements:

        * The first entry must be a string that defines the nature of the information
          to retrieve. Currently, only the following types of information are
          supported:

          - `acqiris_waveform`: A waveform from an Acqiris detector. For a description
             of the format of the data, Please refer to the documentation of the
             [`get_data`][om.data_retrieval_layer.data_sources_psana.AcqirisPsana.get_data]
             function of the `AcqirisPsana` class.

          - `epics_pv`: The value of an Epics variable. For a description
             of the format of the data, Please refer to the documentation of the
             [`get_data`][om.data_retrieval_layer.data_sources_psana.EpicsVariablePsana.get_data]
             function of the `EpicsVariablePsana` class.

          - `wave8_total_intensity`: The total intensity recorded by a Wave8 detector
            (expressed as a float number).

          - `opal_camera`: An data frame collected by an Opal camera. For a description
             of the format of the data, Please refer to the documentation of the
             [`get_data`][om.data_retrieval_layer.data_sources_psana.OpalPsana.get_data]
             function of the `OpalPsana` class.

          -  `assembled_detector_data`: A detector data frame with geometry applied, as
             generated by the psana software framework. The data must have the format
             of a 2D array storing pixel information.

        * The second entry must be a string identifying the source of the retrieved
          information.

          - This is the name, in the psana software framework, of the detector
            generating the data to be retrieved.

          - For the `epics_pv` data type, this is the Epics name of the variable to
            retrieve.

        * The third entry is string that assigns an identifying name to data. This is
          only used by OM, and only within the set of retrieved LCLS-specific data.

        Raises:

            OmWrongParameterTypeError: Raised when the `lcls_extra` entry in OM's
                configuration parameters is not formatted correctly, or it requests
                data that is not supported yet.
        """

        self._lcls_extra: Dict[str, Any] = {}
        lcls_extra_index: int = 0

        data_item: Tuple[str, str, str]
        for data_item in self._parameters.data:
            data_type, identifier, name = data_item
            if data_type == "acqiris_waveform":
                self._lcls_extra[name] = AcqirisPsana(
                    data_source_name=f"lcls_extra_{lcls_extra_index}",
                    parameters={f"lcls_extra_{lcls_extra_index}": {"name": identifier}},
                )
                lcls_extra_index += 1
            elif data_type == "epics_pv":
                self._lcls_extra[name] = EpicsVariablePsana(
                    data_source_name=f"lcls_extra_{lcls_extra_index}",
                    parameters={f"lcls_extra_{lcls_extra_index}": {"name": identifier}},
                )
                lcls_extra_index += 1
            elif data_type == "wave8_total_intensity":
                self._lcls_extra[name] = Wave8TotalIntensityPsana(
                    data_source_name=f"lcls_extra_{lcls_extra_index}",
                    parameters={f"lcls_extra_{lcls_extra_index}": {"name": identifier}},
                )
                lcls_extra_index += 1
            elif data_type == "opal_camera":
                self._lcls_extra[name] = OpalPsana(
                    data_source_name=f"lcls_extra_{lcls_extra_index}",
                    parameters={f"lcls_extra_{lcls_extra_index}": {"name": identifier}},
                )
                lcls_extra_index += 1
            elif data_type == "assembled_detector_data":
                self._lcls_extra[name] = AssembledDetectorPsana(
                    data_source_name=f"lcls_extra_{lcls_extra_index}",
                    parameters={f"lcls_extra_{lcls_extra_index}": {"name": identifier}},
                )
                lcls_extra_index += 1
            else:
                raise OmWrongParameterTypeError(
                    f"The requested '{data_type}' LCLS-specific data type is "
                    "not supported."
                )
            self._lcls_extra[name].initialize_data_source()

    def get_data(self, *, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieves LCLS-specific information from psana.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves from psana the LCLS-specific information associated
        with the provided event. It returns the data in the format of a dictionary.

        * The keys in the dictionary match the OM identifiers assigned to each data
          entry.

        * The corresponding dictionary values the retrieved information for each
          required data element.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A dictionary storing the retrieved LCLS-specific information for the
            provided event.
        """
        data: Dict[str, Any] = {}

        name: str
        for name in self._lcls_extra:
            data[name] = self._lcls_extra[name].get_data(event=event)

        return data
