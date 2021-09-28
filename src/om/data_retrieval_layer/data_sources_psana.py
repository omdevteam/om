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
from typing import Any, Callable, cast, Dict, List, Union

import numpy  # type: ignore
import psana  # type: ignore

from om.data_retrieval_layer import base as drl_base
from om.data_retrieval_layer import data_sources_generic as ds_generic
from om.utils import exceptions
from om.utils.parameters import MonitorParams


def _get_psana_epics_name(
    *, source_base_name: str, monitor_parameters: MonitorParams
) -> str:
    # Helper function to retrieve an epics variable's name from the monitor
    # configuration parameters.
    detector_name: str = monitor_parameters.get_parameter(
        group="data_retrieval_layer",
        parameter=f"psana_{source_base_name}_epics_name",
        required=True,
        parameter_type=str,
    )
    return detector_name


def _get_psana_detector_name(
    *, source_base_name: str, monitor_parameters: MonitorParams
) -> str:
    # Helper function to retrieve a detector's name from the monitor configuration
    # parameters.
    detector_name: str = monitor_parameters.get_parameter(
        group="data_retrieval_layer",
        parameter=f"psana_{source_base_name}_name",
        required=True,
        parameter_type=str,
    )
    return detector_name


def _get_psana_data_retrieval_function(
    *, source_base_name: str, monitor_parameters: MonitorParams
) -> Callable[[Any], Any]:
    detector_name: str = _get_psana_detector_name(
        source_base_name=source_base_name, monitor_parameters=monitor_parameters
    )
    detector_interface: Any = psana.Detector(detector_name)
    calibrated_data_required: bool = ds_generic.get_calibration_request(
        source_base_name=source_base_name, monitor_parameters=monitor_parameters
    )
    if calibrated_data_required:
        data_retrieval_function: Callable[[Any], Any] = detector_interface.calib
    else:
        detector_interface.raw
    return data_retrieval_function


class CspadPsana(drl_base.OmDataSource):
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
        CSPAD Detector at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the CSPAD x-ray detector as used at the LCLS facility.
        It is a subclass of the generic
        [OmDataSource][om.data_retrieval_layer.base.OmDataSource] base class.

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
        self._data_retrieval_function: Callable[
            [Any], Any
        ] = _get_psana_data_retrieval_function(
            source_base_name=self._data_source_name,
            monitor_parameters=self._monitor_parameters,
        )

    def get_data(self, *, event: Dict[str, Any]) -> numpy.ndarray:
        """
        Retrieves a calibrated CSPAD detector data frame from psana.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves a single calibrated CSPAD detector frame from psana. It
        returns the frame as a 2D array storing pixel data.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            One frame of detector data.
        """
        cspad_psana: numpy.ndarray = self._data_retrieval_function(event["data"])
        if cspad_psana is None:
            raise exceptions.OmDataExtractionError(
                "Could not retrieve detector data from psana."
            )

        # Rearranges the data into 'slab' format.
        cspad_reshaped: numpy.ndarray = cspad_psana.reshape((4, 8, 185, 388))
        cspad_slab: numpy.ndarray = numpy.zeros(
            shape=(1480, 1552), dtype=cspad_reshaped.dtype
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


class Epix10kaPsana(drl_base.OmDataSource):
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
        Epix10KA 2M Detector at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        It is a subclass of the generic
        [OmDataSource][om.data_retrieval_layer.base.OmDataSource] base class.

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
        self._data_retrieval_function: Callable[
            [Any], Any
        ] = _get_psana_data_retrieval_function(
            source_base_name=self._data_source_name,
            monitor_parameters=self._monitor_parameters,
        )

    def get_data(self, *, event: Dict[str, Any]) -> numpy.ndarray:
        """
        Retrieves a calibrated Epix10KA 2M detector data frame from psana.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves a single calibrated Epix10KA 2M detector frame from
        psana. It returns the frame as a 2D array storing pixel data.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            One frame of detector data.
        """
        epixka2m_psana: numpy.ndarray = self._data_retrieval_function(event["data"])
        if epixka2m_psana is None:
            raise exceptions.OmDataExtractionError(
                "Could not retrieve detector data from psana."
            )

        # Rearranges the data into 'slab' format.
        epixka2m_reshaped: numpy.ndarray = epixka2m_psana.reshape(16 * 352, 384)

        return epixka2m_reshaped


class Jungfrau4MPsana(drl_base.OmDataSource):
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
        Jungfrau 4M Detector at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the Jungfrau 4M x-ray detector as used at the LCLS
        facility. It is a subclass of the generic
        [OmDataSource][om.data_retrieval_layer.base.OmDataSource] base class.

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
        self._data_retrieval_function: Callable[
            [Any], Any
        ] = _get_psana_data_retrieval_function(
            source_base_name=self._data_source_name,
            monitor_parameters=self._monitor_parameters,
        )

    def get_data(self, *, event: Dict[str, Any]) -> numpy.ndarray:
        """
        Retrieves a calibrated Jungfrau 4M detector data frame from psana.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves a single calibrated  Jungfrau 4M detector frame from
        psana. It returns the frame as a 2D array storing pixel data.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            One frame of detector data.
        """
        jungfrau_psana: numpy.ndarray = self._data_retrieval_function(event["data"])
        if jungfrau_psana is None:
            raise exceptions.OmDataExtractionError(
                "Could not retrieve detector data from psana."
            )

        # Rearranges the data into 'slab' format.
        jungfrau_reshaped: numpy.ndarray = jungfrau_psana.reshape(8 * 512, 1024)

        return jungfrau_reshaped


class RayonixPsana(drl_base.OmDataSource):
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
        Rayonix Detector at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the Rayonix x-ray detector as used at the LCLS facility.
        It is a subclass of the generic
        [OmDataSource][om.data_retrieval_layer.base.OmDataSource] base class.

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
        self._data_retrieval_function: Callable[
            [Any], Any
        ] = _get_psana_data_retrieval_function(
            source_base_name=self._data_source_name,
            monitor_parameters=self._monitor_parameters,
        )

    def get_data(self, *, event: Dict[str, Any]) -> numpy.ndarray:
        """
        Retrieves a calibrated Rayonix data frame from psana.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves a single calibrated  Rayonix 4M detector frame from
        psana. It returns the frame as a 2D array storing pixel data.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            One frame of detector data.
        """
        rayonix_psana: numpy.ndarray = self._data_retrieval_function(event["data"])
        if rayonix_psana is None:
            raise exceptions.OmDataExtractionError(
                "Could not retrieve detector data from psana."
            )

        return rayonix_psana


class OpalPsana(drl_base.OmDataSource):
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
        Opal Camera at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the Opal camera as used at the LCLS facility. It is a
        subclass of the generic
        [OmDataSource][om.data_retrieval_layer.base.OmDataSource]
        base class.

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
        self._data_retrieval_function: Callable[
            [Any], Any
        ] = _get_psana_data_retrieval_function(
            source_base_name=self._data_source_name,
            monitor_parameters=self._monitor_parameters,
        )

    def get_data(self, *, event: Dict[str, Any]) -> numpy.ndarray:
        """
        Retrieves an Opal camera data frame from psana.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves a single Opal camera frame from psana. It returns the
        frame as a 2D array storing pixel data.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            One frame of detector data.
        """
        opal_psana: numpy.ndarray = self._data_retrieval_function(event["data"])
        if opal_psana is None:
            raise exceptions.OmDataExtractionError(
                "Could not retrieve detector data from psana."
            )

        return opal_psana


class TimestampPsana(drl_base.OmDataSource):
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
        psana_event_id: Any = event["data"].get(psana.EventId)
        timestamp_epoch_format: Any = psana_event_id.time()
        return numpy.float64(
            str(timestamp_epoch_format[0]) + "." + str(timestamp_epoch_format[1])
        )


class EventIdPsana(drl_base.OmDataSource):
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
        psana_event_id: Any = event["data"].get(psana.EventId)
        timestamp_epoch_format: Any = psana_event_id.time()
        fiducials: Any = psana_event_id.fiducials()
        return f"{timestamp_epoch_format[0]}-{timestamp_epoch_format[1]}-{fiducials}"


class EpicsVariablePsana(drl_base.OmDataSource):
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
        An Epics variable at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with Epics variables are retrieved at the LCLS facility. It is
        a subclass of the generic
        [OmDataSource][om.data_retrieval_layer.base.OmDataSource]
        base class.

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
        epics_variable_name: str = _get_psana_epics_name(
            source_base_name=self._data_source_name,
            monitor_parameters=self._monitor_parameters,
        )
        self._detector_interface: Any = psana.Detector(epics_variable_name)

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
        return self._detector_interface()


class BeamEnergyPsana(drl_base.OmDataSource):
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
        Beam energy at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of the beam energy information at the LCLS
        facility. It is a subclass of the generic
        [OmDataSource][om.data_retrieval_layer.base.OmDataSource]
        base class.

        Arguments:

            source_name: the name of the current data source, used to identify the
                source when needed (communication with the user, retrieval of
                initialization parameters.

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.
        """
        del data_source_name
        del monitor_parameters

    def initialize_data_source(self) -> None:
        """
        #TODO: Docs
        """
        self._detector_interface: Any = psana.Detector("EBeam")

    def get_data(self, *, event: Dict[str, Any]) -> float:
        """
        Retrieves the beam energy from psana.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves the value of the beam energy from psana by reading a
        multicast variable.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The beam energy.
        """
        return cast(
            float, self._detector_interface.get(event["data"]).ebeamPhotonEnergy()
        )


class EvrCodesPsana(drl_base.OmDataSource):
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
        EVR Event Codes at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval and detection of EVR event codes at the LCLS
        facility. It is a subclass of the generic
        [OmDataSource][om.data_retrieval_layer.base.OmDataSource]
        base class.

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
        evr_source_name: str = self._monitor_parameters.get_parameter(
            group="data_retrieval_layer",
            parameter="psana_evr_source_name",
            parameter_type=str,
            required=True,
        )
        self._detector_interface: Any = psana.Detector(evr_source_name)

        self._requested_event_code: int = self._monitor_parameters.get_parameter(
            group="data_retrieval_layer",
            parameter=f"{self._data_source_name}_evr_code",
            parameter_type=int,
            required=True,
        )

    def get_data(self, *, event: Dict[str, Any]) -> bool:
        """
        Checks for events codes in the current event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function checks the current events features a predefined EVR event code.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The beam energy.
        """
        current_evr_codes: Union[List[int], None] = self._detector_interface.eventCodes(
            event["data"]
        )
        if current_evr_codes is None:
            raise exceptions.OmDataExtractionError(
                "Could not retrieve event codes from psana."
            )

        return self._requested_event_code in current_evr_codes
