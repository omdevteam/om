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
Psana-related data sources.

This module contains Data Source classes that deal with data retrieved from the psana
software framework used at the LCLS facility.
"""
from typing import Any, Callable, Dict, List, Tuple, Union, cast

import numpy  # type: ignore
import psana  # type: ignore

from om.data_retrieval_layer import base as drl_base
from om.data_retrieval_layer import data_sources_generic as ds_generic
from om.utils import exceptions
from om.utils.parameters import MonitorParams


def _get_psana_epics_name(
    *, source_base_name: str, monitor_parameters: MonitorParams
) -> str:
    # Helper function that retrieves an epics variable's name from the monitor
    # configuration parameters or from the source base name, if the name begins with
    # the string "psana-"".
    if source_base_name.startswith("psana-"):
        detector_name: str = source_base_name.split("psana-")[1]
    else:
        detector_name = monitor_parameters.get_parameter(
            group="data_retrieval_layer",
            parameter=f"psana_{source_base_name}_epics_name",
            parameter_type=str,
        )
    return detector_name


def _get_psana_detector_name(
    *, source_base_name: str, monitor_parameters: MonitorParams
) -> str:
    # Helper function that retrieves a detector's name from the monitor configuration
    # parameters or from the source base name, if the name begins with the string
    # "psana-"
    if source_base_name.startswith("psana-"):
        detector_name: str = source_base_name.split("psana-")[1]
    else:
        detector_name = monitor_parameters.get_parameter(
            group="data_retrieval_layer",
            parameter=f"psana_{source_base_name}_name",
            required=True,
            parameter_type=str,
        )
    return detector_name


def _get_psana_data_retrieval_function(
    # Helper function that  picks the right psana data retrieval function
    # (raw or calib) depending on what is required.
    *,
    source_base_name: str,
    monitor_parameters: MonitorParams,
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

    Base class: [`OmDataSource`][om.data_retrieval_layer.base.OmDataSource]
    """

    def __init__(
        self,
        *,
        data_source_name: str,
        monitor_parameters: MonitorParams,
    ):
        """
        CSPAD detector frame data at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of CSPAD detector frame data from the psana
        software framework. Data is normally retrieved for the detector whose psana
        name matches the entry `psana_{source_base_name}_name` in the
        `data_retrieval_layer` OM configuration parameter group. However, it is also
        possible to provide the psana name of the detector directly in the
        {source_base_name} argument, by prefixing it with the string "psana-". The
        detector frame data can be retrieved in calibrated or non-calibrated form,
        depending on the value of the `{source_base_name}_calibration` entry in the
        `data_retrieval_layer` parameter group. This class is a subclass of the
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
        Initializes the CSPAD detector frame data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the psana Detector interface for the detector
        whose psana name matches the entry `psana_{source_base_name}_name` in the
        `data_retrieval_layer` OM configuration group, or for the detector with
        a given psana name, if the {source_base_name} has the format
        `psana-{psana detector name}`.
        """
        self._data_retrieval_function: Callable[
            [Any], Any
        ] = _get_psana_data_retrieval_function(
            source_base_name=self._data_source_name,
            monitor_parameters=self._monitor_parameters,
        )

    def get_data(self, *, event: Dict[str, Any]) -> numpy.ndarray:
        """
        Retrieves a CSPAD detector data frame from psana.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves single detector data frame from psana. It returns the
        frame as a 2D array storing the pixel data. The data is retrieved in calibrated
        or non-calibrated form depending on the value of the
        `{source_base_name}_calibration` entry in the `data_retrieval_layer` OM
        configuration group.

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

    Base class: [`OmDataSource`][om.data_retrieval_layer.base.OmDataSource]
    """

    def __init__(
        self,
        *,
        data_source_name: str,
        monitor_parameters: MonitorParams,
    ):
        """
        Epix10KA 2M detector frame data at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of Epix10KA 2M detector frame data from the
        psana software framework. Data is normally retrieved for the detector whose
        psana name matches the entry `psana_{source_base_name}_name` in the
        `data_retrieval_layer` OM configuration parameter group. However, it is also
        possible to provide the psana name of the detector directly in the
        {source_base_name} argument, by prefixing it with the string "psana-". The
        detector frame data can be retrieved in calibrated or non-calibrated form,
        depending on the value of the `{source_base_name}_calibration` entry in the
        `data_retrieval_layer` parameter group. This class is a subclass of the
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
        Initializes the Epix10KA 2M detector frame data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the psana Detector interface for the detector
        whose psana name matches the entry `psana_{source_base_name}_name` in the
        `data_retrieval_layer` OM configuration group, or for the detector with
        a given psana name, if the {source_base_name} has the format
        `psana-{psana detector name}`.
        """
        self._data_retrieval_function: Callable[
            [Any], Any
        ] = _get_psana_data_retrieval_function(
            source_base_name=self._data_source_name,
            monitor_parameters=self._monitor_parameters,
        )

    def get_data(self, *, event: Dict[str, Any]) -> numpy.ndarray:
        """
        Retrieves a Epix10KA 2M detector data frame from psana.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves a single detector data frame from psana. It returns the
        frame as a 2D array storing the pixel data. The data is retrieved in calibrated
        or non-calibrated form depending on the value of the
        `{source_base_name}_calibration` entry in the `data_retrieval_layer` OM
        configuration group.

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

    Base class: [`OmDataSource`][om.data_retrieval_layer.base.OmDataSource]
    """

    def __init__(
        self,
        *,
        data_source_name: str,
        monitor_parameters: MonitorParams,
    ):
        """
        Jungfrau 4M detector frame data at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of Jungfrau 4M detector frame data from the
        psana software framework. Data is normally retrieved for the detector whose
        psana name matches the entry `psana_{source_base_name}_name` in the
        `data_retrieval_layer` OM configuration parameter group. However, it is also
        possible to provide the psana name of the detector directly in the
        {source_base_name} argument, by prefixing it with the string "psana-". The
        detector frame data can be retrieved in calibrated or non-calibrated form,
        depending on the value of the `{source_base_name}_calibration` entry in the
        `data_retrieval_layer` parameter group. This class is a subclass of the
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
        Initializes the Jungfrau 4M detector frame data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the psana Detector interface for the detector
        whose psana name matches the entry `psana_{source_base_name}_name` in the
        `data_retrieval_layer` OM configuration group, or for the detector with
        a given psana name, if the {source_base_name} has the format
        `psana-{psana detector name}`.
        """
        self._data_retrieval_function: Callable[
            [Any], Any
        ] = _get_psana_data_retrieval_function(
            source_base_name=self._data_source_name,
            monitor_parameters=self._monitor_parameters,
        )

    def get_data(self, *, event: Dict[str, Any]) -> numpy.ndarray:
        """
        Retrieves a Jungfrau 4M detector data frame from psana.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves a single detector data frame from psana. It returns the
        frame as a 2D array storing the pixel data. The data is retrieved in calibrated
        or non-calibrated form depending on the value of the
        `{source_base_name}_calibration` entry in the `data_retrieval_layer` OM
        configuration group.

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

    Base class: [`OmDataSource`][om.data_retrieval_layer.base.OmDataSource]
    """

    def __init__(
        self,
        *,
        data_source_name: str,
        monitor_parameters: MonitorParams,
    ):
        """
        Rayonix detector frame data at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of Rayonix frame data from the psana
        software framework. Data is normally retrieved for the detector whose psana
        name matches the entry `psana_{source_base_name}_name` in the
        `data_retrieval_layer` OM configuration parameter group. However, it is also
        possible to provide the psana name of the detector directly in the
        {source_base_name} argument, by prefixing it with the string "psana-". This
        class is a subclass of the
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
        Initializes the Rayonix detector frame data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the psana Detector interface for the detector
        whose psana name matches the entry `psana_{source_base_name}_name` in the
        `data_retrieval_layer` OM configuration group, or for the detector with
        a given psana name, if the {source_base_name} has the format
        `psana-{psana detector name}`.
        """
        detector_name: str = _get_psana_detector_name(
            source_base_name=self._data_source_name,
            monitor_parameters=self._monitor_parameters,
        )
        self._detector_interface: Any = psana.Detector(detector_name)

    def get_data(self, *, event: Dict[str, Any]) -> numpy.ndarray:
        """
        Retrieves a Rayonix detector data frame from psana.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves a single detector data frame from psana. It returns the
        frame as a 2D array storing the pixel data.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            One frame of detector data.
        """
        rayonix_psana: numpy.ndarray = self._detector_interface.calib(event["data"])
        if rayonix_psana is None:
            raise exceptions.OmDataExtractionError(
                "Could not retrieve detector data from psana."
            )

        return rayonix_psana


class OpalPsana(drl_base.OmDataSource):
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
        Opal camera frame data at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of Opal frame data from the psana software
        framework. Data is normally retrieved for the camera whose psana name matches
        the entry `psana_{source_base_name}_name` in the `data_retrieval_layer` OM
        configuration parameter group. However, it is also possible to provide the
        psana name of the camera directly in the {source_base_name} argument, by
        prefixing it with the string "psana-". This class is a subclass of the
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
        Initializes the Opal camera frame data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the psana Detector interface for the camera
        whose psana name matches the entry `psana_{source_base_name}_name` in the
        `data_retrieval_layer` OM configuration group, or for the camera with
        a given psana name, if the {source_base_name} has the format
        `psana-{psana detector name}`.
        """
        detector_name: str = _get_psana_detector_name(
            source_base_name=self._data_source_name,
            monitor_parameters=self._monitor_parameters,
        )
        self._detector_interface: Any = psana.Detector(detector_name)

    def get_data(self, *, event: Dict[str, Any]) -> numpy.ndarray:
        """
        Retrieves an Opal camera data frame from psana.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves a single camera data frame from psana. It returns the
        frame as a 2D array storing the pixel data.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            One frame of camera data.
        """
        opal_psana: numpy.ndarray = self._detector_interface.calib(event["data"])
        if opal_psana is None:
            raise exceptions.OmDataExtractionError(
                "Could not retrieve detector data from psana."
            )

        return opal_psana


class AcqirisDetector(drl_base.OmDataSource):
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
        Acqiris time/voltage waverform data at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of waveform data from an Acqiris
        time/voltage detector at the LCLS facility. Data is normally retrieved for the
        Acqiris detector whose psana name matches the entry
        `psana_{source_base_name}_name` in the `data_retrieval_layer` OM configuration
        parameter group. However, it is also possible to provide the psana name of the
        Acqiris detector directly in the {source_base_name} argument, by prefixing it
        with the string "psana-". This class is a subclass of the
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
        Initializes the Acqiris waveform data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the psana Detector interface for the Acqiris detector
        whose psana name matches the entry `psana_{source_base_name}_name` in the
        `data_retrieval_layer` OM configuration group, or for the detector with
        a given psana name, if the {source_base_name} has the format
        `psana-{psana detector name}`.
        """
        detector_name: str = _get_psana_detector_name(
            source_base_name=self._data_source_name,
            monitor_parameters=self._monitor_parameters,
        )
        self._detector_interface: Any = psana.Detector(detector_name)

    def get_data(self, *, event: Dict[str, Any]) -> Tuple[numpy.ndarray, numpy.ndarray]:
        """
        Retrieves Acqiris waveform data from psana.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves waveform data for all of the detector's channels at the
        same time. The data is retrieved in the format of a tuple with tho entries:

        - The first entry in the tuple is a numpy array storing information about the
          time points at which the waveform data was digitized.

        - The second entry is a 2D numpy array that stores the waveform information
          from the different channels. The first axis of the array encodes the
          channel number, the second one indexes the digitized data for each channel.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            Digitized waveform data from the Acqiris detector.
        """
        return (
            self._detector_interface.waveform(event["data"]),
            self._detector_interface.wftime(event["data"]),
        )


class Wave8Detector(drl_base.OmDataSource):
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
        Wave8 detector data at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of data from a Wave8 detector at the LCLS
        facility. Data is normally retrieved for the Wave8 detector whose psana name
        matches the entry `psana_{source_base_name}_name` in the `data_retrieval_layer`
        OM configuration parameter group. However, it is also possible to provide the
        psana name of the Wave8 detector directly in the {source_base_name} argument,
        by prefixing it with the string "psana-". It is a subclass of the
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
        Initializes the Wave8 data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the psana Detector interface for the Wave8 detector
        whose psana name matches the entry `psana_{source_base_name}_name` in the
        `data_retrieval_layer` OM configuration group, or for the detector with
        a given psana name, if the {source_base_name} has the format
        `psana-{psana detector name}`.
        """
        detector_name: str = _get_psana_detector_name(
            source_base_name=self._data_source_name,
            monitor_parameters=self._monitor_parameters,
        )
        self._detector_interface: Any = psana.Detector(detector_name)

    def get_data(self, *, event: Dict[str, Any]) -> float:
        """
        Retrieves Wave8 total intensity data from psana.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves the total intensity recorded by Wave8 the detector for
        an event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The total intensity recorded by the Wave detector.
        """
        return cast(float, self._detector_interface.get(event["data"]).TotalIntensity())


class TimestampPsana(drl_base.OmDataSource):
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
        Timestamp information from psana at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of timestamp information from the psana
        software framework, which provides this information for each event with a
        nanosecond-level precision. This class is a subclass of the
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
        Initializes the psana timestamp data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        No initialization is needed to retrieve timestamp information from psana,
        so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> numpy.float64:
        """
        Retrieves timestamp information from psana.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves the timestamp information provided for an event by
        psana.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The timestamp for the data event.
        """
        psana_event_id: Any = event["data"].get(psana.EventId)
        timestamp_epoch_format: Any = psana_event_id.time()
        return numpy.float64(
            str(timestamp_epoch_format[0]) + "." + str(timestamp_epoch_format[1])
        )


class EventIdPsana(drl_base.OmDataSource):
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
        Data event identifier at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of a unique event identifier for
        psana-based data events. In OM, a psana-based data event corresponds to the
        content of a single psana event. The psana software framework provides
        timestamp information with nanosecond-level precision for each event, plus a
        specific fiducial string form more detailed identification. This class uses a
        combination of these two items to generate a unique event identifier with the
        following format:
        `{timestamp: seconds}-{timestamp: nanoseconds}-{fiducials}`. This class
        is a subclass of the [OmDataSource][om.data_retrieval_layer.base.OmDataSource]
        class.

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
        Initializes the psana event identifier data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        No initialization is required to retrieve an event identifier for a psana-based
        data event, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> Any:
        """
        Retrieves the psana-based event identifier for an event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves a unique identifier for a psana-based data event. The
        identifier is generated by combining the timestamp and fiducial information
        that psana provides for the event. It has the following format:
        `{timestamp: seconds}-{timestamp: nanoseconds}-{fiducials}`.

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

    Base class: [`OmDataSource`][om.data_retrieval_layer.base.OmDataSource]
    """

    def __init__(
        self,
        *,
        data_source_name: str,
        monitor_parameters: MonitorParams,
    ):
        """
        Epics variable value at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of an Epics variable's value from the
        psana software framework. It retrieves the value of the variable whose psana
        name matches the entry `psana_{source_base_name}_name` in the
        `data_retrieval_layer` OM configuration parameter group. However, it is also
        possible to provide the psana name of the variable directly in the
        {source_base_name} argument, by prefixing it with the string "psana-". This
        class is a subclass of the
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
        Initializes the Epics variable value data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the psana Detector interface for the variable whose
        psana name matches the entry `psana_{source_base_name}_name` in the
        `data_retrieval_layer` OM configuration group, or for the Epics variable with
        a given psana name, if the {source_base_name} has the format
        `psana-{psana detector name}`.
        """
        epics_variable_name: str = _get_psana_epics_name(
            source_base_name=self._data_source_name,
            monitor_parameters=self._monitor_parameters,
        )
        if not epics_variable_name:
            epics_variable_name = _get_psana_detector_name(
                source_base_name=self._data_source_name,
                monitor_parameters=self._monitor_parameters,
            )
        self._detector_interface: Any = psana.Detector(epics_variable_name)

    def get_data(self, *, event: Dict[str, Any]) -> Any:
        """
        Retrieves an Epics variable's value from psana.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves from psana an Epics variable's value associated
        with a data event.

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
        Beam energy information at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of beam energy information at the LCLS
        facility. Psana provides this information for each event. This class is a
        subclass of the [OmDataSource][om.data_retrieval_layer.base.OmDataSource]
        class.

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, for communication with the user or retrieval of
                initialization parameters.

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.
        """
        del data_source_name
        del monitor_parameters

    def initialize_data_source(self) -> None:
        """
        Initializes the beam energy data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the psana Detector interface for the retrieval of
        the beam energy information.
        """
        self._detector_interface: Any = psana.Detector("EBeam")

    def get_data(self, *, event: Dict[str, Any]) -> float:
        """
        Retrieves beam energy information from psana.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves the beam energy information for an event, as provided
        by psana.

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

    Base class: [`OmDataSource`][om.data_retrieval_layer.base.OmDataSource]
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

        This class deals with the retrieval and detection of EVR events at the LCLS
        facility. It gathers the information needed to determine if the event code
        specified by the `{data_source_name}_evr_code` entry in the
        `data_retrieval_layer` has been emitted for a specific event by the EVR source
        specified by the `psana_evr_source_name` entry in the same group. It is a
        subclass of the [OmDataSource][om.data_retrieval_layer.base.OmDataSource]
        class.

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
        Initializes the EVR event code data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the psana Detector interface for the EVR event source
        specified by the `psana_evr_source_name` entry in the `Data Retrieval Layer`
        OM parameter group.
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
        Checks for EVR events codes in the current event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function checks if the event code specified by the
        `{data_source_name}_evr_code` entry in the `data_retrieval_layer` OM
        configuration group is present in the set of EVR Event codes attached to an
        event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            Whether the requested event code is amongst the ones attached to the
            current event.
        """
        current_evr_codes: Union[List[int], None] = self._detector_interface.eventCodes(
            event["data"]
        )
        if current_evr_codes is None:
            raise exceptions.OmDataExtractionError(
                "Could not retrieve event codes from psana."
            )

        return self._requested_event_code in current_evr_codes
