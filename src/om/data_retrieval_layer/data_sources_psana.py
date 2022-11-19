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
software framework (used at the LCLS facility).
"""
from typing import Any, Callable, Dict, List, Tuple, Union, cast

import numpy
from numpy.typing import NDArray

from om.abcs.data_retrieval_layer import OmDataSourceBase
from om.data_retrieval_layer.data_sources_generic import get_calibration_request
from om.library.exceptions import (
    OmDataExtractionError,
    OmMissingDependencyError,
    OmWrongParameterTypeError,
)
from om.library.parameters import MonitorParameters

try:
    import psana  # type: ignore
except ImportError:
    raise OmMissingDependencyError(
        "The following required module cannot be imported: psana"
    )


def _get_psana_epics_name(
    *, source_protocols_name: str, monitor_parameters: MonitorParameters
) -> str:
    # Helper function that retrieves an epics variable's name from the monitor
    # configuration parameters or from the source base name, if the name begins with
    # the string "psana-"".
    if source_protocols_name.startswith("psana-"):
        detector_name: str = source_protocols_name.split("psana-")[1]
    else:
        detector_name = monitor_parameters.get_parameter(
            group="data_retrieval_layer",
            parameter=f"psana_{source_protocols_name}_epics_name",
            parameter_type=str,
        )
    return detector_name


def _get_psana_detector_name(
    *, source_protocols_name: str, monitor_parameters: MonitorParameters
) -> str:
    # Helper function that retrieves a detector's name from the monitor configuration
    # parameters or from the source base name, if the name begins with the string
    # "psana-"
    if source_protocols_name.startswith("psana-"):
        detector_name: str = source_protocols_name.split("psana-")[1]
    else:
        detector_name = monitor_parameters.get_parameter(
            group="data_retrieval_layer",
            parameter=f"psana_{source_protocols_name}_name",
            required=True,
            parameter_type=str,
        )
    return detector_name


def _get_psana_data_retrieval_function(
    # Helper function that  picks the right psana data retrieval function
    # (raw or calib) depending on what is required.
    *,
    source_protocols_name: str,
    monitor_parameters: MonitorParameters,
) -> Callable[[Any], Any]:
    detector_name: str = _get_psana_detector_name(
        source_protocols_name=source_protocols_name,
        monitor_parameters=monitor_parameters,
    )
    detector_interface: Any = psana.Detector(detector_name)
    calibrated_data_required: bool = get_calibration_request(
        source_protocols_name=source_protocols_name,
        monitor_parameters=monitor_parameters,
    )
    if calibrated_data_required:
        data_retrieval_function: Callable[[Any], Any] = detector_interface.calib
    else:
        data_retrieval_function = detector_interface.raw
    return data_retrieval_function


class CspadPsana(OmDataSourceBase):
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
        CSPAD detector data frames at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of a CSPAD detector data frame from the
        psana software framework. Data is normally retrieved for the detector whose
        psana name matches the `psana_{source_protocols_name}_name` entry in OM's
        `data_retrieval_layer` configuration parameter group. However, it is also
        possible to provide the psana name of the detector directly in the
        `source_protocols_name` argument, by prefixing it with the string "psana-". The
        detector data frame can be retrieved in calibrated or non-calibrated form,
        depending on the value of the `{source_protocols_name}_calibration` entry in the
        `data_retrieval_layer` parameter group.

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
        Initializes the psana CSPAD detector frame data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the psana Detector interface for the detector
        whose psana name matches the entry `psana_{source_protocols_name}_name` in OM's
        `data_retrieval_layer` configuration parameter group, or for the detector with
        a given psana name, if the `source_protocols_name` argument has the format
        `psana-{psana detector name}`.
        """
        self._data_retrieval_function: Callable[
            [Any], Any
        ] = _get_psana_data_retrieval_function(
            source_protocols_name=self._data_source_name,
            monitor_parameters=self._monitor_parameters,
        )

    def get_data(self, *, event: Dict[str, Any]) -> NDArray[numpy.float_ | numpy.int_]:
        """
        Retrieves a CSPAD detector data frame from psana.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves from psana the detector data frame associated with the
        provided event. It returns the frame as a 2D array storing pixel information.
        Data is retrieved in calibrated or non-calibrated form depending on the
        value of the `{source_protocols_name}_calibration` entry in OM's
        `data_retrieval_layer` configuration parameter group.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            One detector data frame.
        """
        cspad_psana: Union[
            NDArray[numpy.float_], NDArray[numpy.int_]
        ] = self._data_retrieval_function(event["data"])
        if cspad_psana is None:
            raise OmDataExtractionError("Could not retrieve detector data from psana.")

        # Rearranges the data into 'slab' format.
        cspad_reshaped: Union[
            NDArray[numpy.float_], NDArray[numpy.int_]
        ] = cspad_psana.reshape((4, 8, 185, 388))
        cspad_slab: NDArray[numpy.float_ | numpy.int_] = numpy.zeros(
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


class Epix10kaPsana(OmDataSourceBase):
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
        Epix10KA 2M detector data frames at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of an Epix10KA 2M detector data frame from
        the psana software framework. Data is normally retrieved for the detector whose
        psana name matches the `psana_{source_protocols_name}_name` entry in OM's
        `data_retrieval_layer` configuration parameter group. However, it is also
        possible to provide the psana name of the detector directly in the
        `source_protocols_name` argument, by prefixing it with the string "psana-". The
        detector data frame can be retrieved in calibrated or non-calibrated form,
        depending on the value of the `{source_protocols_name}_calibration` entry in the
        `data_retrieval_layer` parameter group.

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
        Initializes the Epix10KA 2M detector frame data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the psana Detector interface for the detector
        whose psana name matches the `psana_{source_protocols_name}_name` entry in OM's
        `data_retrieval_layer` configuration parameter group, or for the detector with
        a given psana name, if the `source_protocols_name` argument has the format
        `psana-{psana detector name}`.
        """
        self._data_retrieval_function: Callable[
            [Any], Any
        ] = _get_psana_data_retrieval_function(
            source_protocols_name=self._data_source_name,
            monitor_parameters=self._monitor_parameters,
        )

    def get_data(
        self, *, event: Dict[str, Any]
    ) -> Union[NDArray[numpy.float_], NDArray[numpy.int_]]:
        """
        Retrieves a Epix10KA 2M detector data frame from psana.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves from psana the detector data frame associated with the
        provided event. It returns the frame as a 2D array storing pixel information.
        Data is retrieved in calibrated or non-calibrated form depending on the
        value of the `{source_protocols_name}_calibration` entry in OM's
        `data_retrieval_layer` configuration parameter group.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            One detector data frame.
        """
        epixka2m_psana: Union[
            NDArray[numpy.float_], NDArray[numpy.int_]
        ] = self._data_retrieval_function(event["data"])
        if epixka2m_psana is None:
            raise OmDataExtractionError("Could not retrieve detector data from psana.")

        # Rearranges the data into 'slab' format.
        epixka2m_reshaped: Union[
            NDArray[numpy.float_], NDArray[numpy.int_]
        ] = epixka2m_psana.reshape(16 * 352, 384)

        return epixka2m_reshaped


class Jungfrau4MPsana(OmDataSourceBase):
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
        Jungfrau 4M detector data frames at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of a Jungfrau 4M detector data frame from
        the psana software framework. Data is normally retrieved for the detector whose
        psana name matches the `psana_{source_protocols_name}_name` entry in OM's
        `data_retrieval_layer` configuration parameter group. However, it is also
        possible to provide the psana name of the detector directly in the
        `source_protocols_name` argument, by prefixing it with the string "psana-". The
        detector data frame can be retrieved in calibrated or non-calibrated form,
        depending on the value of the `{source_protocols_name}_calibration` entry in the
        `data_retrieval_layer` parameter group.

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
        Initializes the psana Jungfrau 4M detector frame data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the psana Detector interface for the detector
        whose psana name matches the `psana_{source_protocols_name}_name` entry in the
        OM's `data_retrieval_layer` configuration parameter group, or for the detector
        with a given psana name, if the `source_protocols_name` argument has the format
        `psana-{psana detector name}`.
        """
        self._data_retrieval_function: Callable[
            [Any], Any
        ] = _get_psana_data_retrieval_function(
            source_protocols_name=self._data_source_name,
            monitor_parameters=self._monitor_parameters,
        )

    def get_data(
        self, *, event: Dict[str, Any]
    ) -> Union[NDArray[numpy.float_], NDArray[numpy.int_]]:
        """
        Retrieves a Jungfrau 4M detector data frame from psana.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves from psana the detector data frame associated with the
        provided event. It returns the frame as a 2D array storing pixel information.
        Data is retrieved in calibrated or non-calibrated form depending on the
        value of the `{source_protocols_name}_calibration` entry in OM's
        `data_retrieval_layer` configuration parameter group..

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            One detector data frame.
        """
        jungfrau_psana: Union[
            NDArray[numpy.float_], NDArray[numpy.int_]
        ] = self._data_retrieval_function(event["data"])
        if jungfrau_psana is None:
            raise OmDataExtractionError("Could not retrieve detector data from psana.")

        # Rearranges the data into 'slab' format.
        jungfrau_reshaped: Union[
            NDArray[numpy.float_], NDArray[numpy.int_]
        ] = jungfrau_psana.reshape(8 * 512, 1024)

        return jungfrau_reshaped


class Epix100Psana(OmDataSourceBase):
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
        Epix100 detector data frames at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of an Epix100 detector data frame from the
        psana software framework. Data is normally retrieved for the detector whose
        psana name matches the `psana_{source_protocols_name}_name` entry in OM's
        `data_retrieval_layer` configuration parameter group. However, it is also
        possible to provide the psana name of the detector directly in the
        `source_protocols_name` argument, by prefixing it with the string "psana-". The
        detector data frame can be retrieved in calibrated or non-calibrated form,
        depending on the value of the `{source_protocols_name}_calibration` entry in the
        `data_retrieval_layer` parameter group.

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
        Initializes the psana Epix100 detector frame data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the psana Detector interface for the detector
        whose psana name matches the `psana_{source_protocols_name}_name` entry in OM's
        `data_retrieval_layer` configuration parameter group, or for the detector with
        a given psana name, if the `source_protocols_name` argument has the format
        `psana-{psana detector name}`.
        """
        self._data_retrieval_function: Callable[
            [Any], Any
        ] = _get_psana_data_retrieval_function(
            source_protocols_name=self._data_source_name,
            monitor_parameters=self._monitor_parameters,
        )

    def get_data(
        self, *, event: Dict[str, Any]
    ) -> Union[NDArray[numpy.float_], NDArray[numpy.int_]]:
        """
        Retrieves a Epix100 detector data frame from psana.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves from psana the detector data frame associated with the
        provided event. It returns the frame as a 2D array storing pixel information.
        Data is retrieved in calibrated or non-calibrated form depending on the
        value of the `{source_protocols_name}_calibration` entry in OM's
        `data_retrieval_layer` configuration parameter group.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            One detector data frame.
        """
        epix_psana: Union[
            NDArray[numpy.float_], NDArray[numpy.int_]
        ] = self._data_retrieval_function(event["data"])
        if epix_psana is None:
            raise OmDataExtractionError("Could not retrieve detector data from psana.")

        return epix_psana


class RayonixPsana(OmDataSourceBase):
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
        Rayonix detector data frames at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of a Rayonix detector data frame from the
        psana software framework. Data is normally retrieved for the detector whose
        psana name matches the `psana_{source_protocols_name}_name` entry in OM's
        `data_retrieval_layer` configuration parameter group. However, it is also
        possible to provide the psana name of the detector directly in the
        `source_protocols_name` argument, by prefixing it with the string "psana-".

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, in communications with the user or for the retrieval
                of a sensor's initialization parameters.

            monitor_parameters: An object storing OM'a configuration parameters.
        """

        self._data_source_name = data_source_name
        self._monitor_parameters = monitor_parameters

    def initialize_data_source(self) -> None:
        """
        Initializes the psana Rayonix detector frame data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the psana Detector interface for the detector
        whose psana name matches the `psana_{source_protocols_name}_name` entry in OM's
        `data_retrieval_layer` configuration parameter group, or for the detector with
        a given psana name, if the `source_protocols_name` argument has the format
        `psana-{psana detector name}`.
        """
        detector_name: str = _get_psana_detector_name(
            source_protocols_name=self._data_source_name,
            monitor_parameters=self._monitor_parameters,
        )
        self._detector_interface: Any = psana.Detector(detector_name)

    def get_data(self, *, event: Dict[str, Any]) -> NDArray[numpy.float_]:
        """
        Retrieves a Rayonix detector data frame from psana.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves from psana the detector data frame associated with the
        provided event. It returns the frame as a 2D array storing pixel information.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            One detector data frame.
        """
        rayonix_psana: NDArray[numpy.float_] = self._detector_interface.calib(
            event["data"]
        )
        if rayonix_psana is None:
            raise OmDataExtractionError("Could not retrieve detector data from psana.")

        return rayonix_psana


class OpalPsana(OmDataSourceBase):
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
        Opal camera data frames at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of an Opal camera data frame from the psana
        software framework. Data is normally retrieved for the camera whose psana name
        matches the `psana_{source_protocols_name}_name` entry in OM's
        `data_retrieval_layer` configuration parameter group. However, it is also
        possible to provide the psana name of the camera directly in the
        `source_protocols_name` argument, by prefixing it with the string "psana-".

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
        Initializes the psana Opal camera frame data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the psana Detector interface for the camera
        whose psana name matches the `psana_{source_protocols_name}_name` entry in OM's
        `data_retrieval_layer` configuration parameter group, or for the camera with
        a given psana name, if the `source_protocols_name` argument has the format
        `psana-{psana detector name}`.
        """
        detector_name: str = _get_psana_detector_name(
            source_protocols_name=self._data_source_name,
            monitor_parameters=self._monitor_parameters,
        )
        self._detector_interface: Any = psana.Detector(detector_name)

    def get_data(self, *, event: Dict[str, Any]) -> NDArray[numpy.float_]:
        """
        Retrieves an Opal camera data frame from psana.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves from psana the camera data frame associated with the
        provided event. It returns the frame as a 2D array storing pixel information.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            One camera data frame.
        """
        opal_psana: NDArray[numpy.float_] = self._detector_interface.calib(
            event["data"]
        )
        if opal_psana is None:
            raise OmDataExtractionError("Could not retrieve detector data from psana.")

        return opal_psana


class AcqirisPsana(OmDataSourceBase):
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
        Acqiris time/voltage waveform data at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of waveform data from an Acqiris
        time/voltage detector at the LCLS facility. Data is normally retrieved for the
        Acqiris detector whose psana name matches the
        `psana_{source_protocols_name}_name` entry in OM's `data_retrieval_layer`
        configuration parameter group. However, it is also possible to provide the
        psana name of the Acqiris detector directly in the `source_protocols_name`
        argument, by prefixing it with the string "psana-".

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
        Initializes the psana Acqiris waveform data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the psana Detector interface for the Acqiris detector
        whose psana name matches the `psana_{source_protocols_name}_name` entry in OM's
        `data_retrieval_layer` configuration parameter group, or for the detector with
        a given psana name, if the `source_protocols_name` argument has the format
        `psana-{psana detector name}`.
        """
        detector_name: str = _get_psana_detector_name(
            source_protocols_name=self._data_source_name,
            monitor_parameters=self._monitor_parameters,
        )
        self._detector_interface: Any = psana.Detector(detector_name)

    def get_data(
        self, *, event: Dict[str, Any]
    ) -> Tuple[NDArray[numpy.float_], NDArray[numpy.float_]]:
        """
        Retrieves Acqiris waveform data from psana.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves from psana the waveform data for the provided event.
        Data is retrieved for all of the detector's channels at the same time, and
        returned in the form of a tuple with two entries:

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

                * The first entry is a 1D numpy array storing the time points at which
                each waveform has been digitized. The size of this array matches the
                size of each waveform in the second entry.

                * The second entry is a 2D numpy array that stores the waveform
                information for all channels of the detector.

                    - The first axis corresponds to the channel number.

                    - The second axis stores, for each channel, the value of the
                    waveform data at the time points at which it has been digitized.
        """
        return cast(
            Tuple[NDArray[numpy.float_], NDArray[numpy.float_]],
            (
                self._detector_interface.wftime(event["data"]),
                self._detector_interface.waveform(event["data"]),
            ),
        )


class AssembledDetectorPsana(OmDataSourceBase):
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
        Assembled detector data frames at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of an assembled detector data frame from
        the psana software framework. It retrieves detector data to which geometry
        information has already been applied. The assembled data is normally retrieved
        for the detector whose psana name matches the
        `psana_{source_protocols_name}_name` entry in OM's `data_retrieval_layer`
        configuration parameter group. However, it is also possible to provide the
        psana name of the detector directly in the `source_protocols_name` argument,
        by prefixing it with the string "psana-".

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, in communications with the user or for the retrieval
                of a sensor's initialization parameters.

            monitor_parameters: An object storing OM'a configuration parameters.
        """
        self._data_source_name = data_source_name
        self._monitor_parameters = monitor_parameters

    def initialize_data_source(self) -> None:
        """
        Initializes the psana assembled detector frame data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the psana Detector interface for the detector
        whose psana name matches the `psana_{source_protocols_name}_name` entry in OM's
        `data_retrieval_layer` configuration parameter group, or for the detector with
        a given psana name, if the `source_protocols_name` argument has the format
        `psana-{psana detector name}`.
        """
        detector_name: str = _get_psana_detector_name(
            source_protocols_name=self._data_source_name,
            monitor_parameters=self._monitor_parameters,
        )
        self._detector_interface: Any = psana.Detector(detector_name)

    def get_data(self, *, event: Dict[str, Any]) -> NDArray[numpy.float_]:
        """
        Retrieves an assembled detector data frame from psana.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves from psana the assembled detector data frame associated
        with the provided event. It returns the frame as a 2D array storing pixel
        information.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            One detector data frame.
        """
        assembled_data: NDArray[numpy.float_] = self._detector_interface.image(
            event["data"]
        )
        if assembled_data is None:
            raise OmDataExtractionError(
                "Could not retrieve assembled detector data from psana."
            )

        return assembled_data


class Wave8Psana(OmDataSourceBase):
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
        Wave8 detector data at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of data from a Wave8 detector at the LCLS
        facility. Data is normally retrieved for the Wave8 detector whose psana name
        matches the `psana_{source_protocols_name}_name` entry in OM's
        `data_retrieval_layer` configuration parameter group. However, it is also
        possible to provide the psana name of the Wave8 detector directly in the
        `source_protocols_name` argument, by prefixing it with the string "psana-".

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
        Initializes the Wave8 data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the psana Detector interface for the Wave8 detector
        whose psana name matches the `psana_{source_protocols_name}_name` entry in OM's
        `data_retrieval_layer` configuration parameter group, or for the detector with
        a given psana name, if the `source_protocols_name` argument has the format
        `psana-{psana detector name}`.
        """
        detector_name: str = _get_psana_detector_name(
            source_protocols_name=self._data_source_name,
            monitor_parameters=self._monitor_parameters,
        )
        self._detector_interface: Any = psana.Detector(detector_name)

    def get_data(self, *, event: Dict[str, Any]) -> float:
        """
        Retrieves Wave8 total intensity data from psana.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves from psana the total intensity recorded by the detector
        for the provided event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The total intensity recorded by the Wave8 detector.
        """
        return cast(float, self._detector_interface())


class TimestampPsana(OmDataSourceBase):
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
        Timestamp information from psana at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of timestamp information from the psana
        software framework. Psana provides this information for each event with a
        nanosecond-level precision.

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

        This function retrieves from psana the timestamp information for the provided
        event.

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


class EventIdPsana(OmDataSourceBase):
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
        Data event identifier at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of a unique event identifier for
        psana-based data events. With psana, an OM's data event corresponds to the
        content of an individual psana event. The psana software framework provides
        timestamp information with nanosecond-level precision for each event, plus a
        specific fiducial string form more detailed identification. This class uses a
        combination of these two items to generate a unique event identifier with the
        following format:
        `{timestamp: seconds}-{timestamp: nanoseconds}-{fiducials}`.

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
        Initializes the psana event identifier data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        No initialization is required to retrieve an event identifier for a psana-based
        data event, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> str:
        """
        Retrieves an event identifier for a psana-based data event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves from psana a unique identifier for the provided event.
        The identifier is generated by combining the timestamp and fiducial information
        that psana provides for the event. It has the following format:
        `{timestamp: seconds}-{timestamp: nanoseconds}-{fiducials}`.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A unique event identifier.
        """
        psana_event_id: Any = event["data"].get(psana.EventId)
        timestamp_epoch_format: Any = psana_event_id.time()
        fiducials: Any = psana_event_id.fiducials()
        return f"{timestamp_epoch_format[0]}-{timestamp_epoch_format[1]}-{fiducials}"


class EpicsVariablePsana(OmDataSourceBase):
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
        Epics variable values at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of an Epics variable's value from the
        psana software framework. It retrieves the value of the variable whose psana
        name matches the `psana_{source_protocols_name}_name` entry in OM's
        `data_retrieval_layer` configuration parameter group. However, it is also
        possible to provide the psana name of the variable directly in the
        `source_protocols_name` argument, by prefixing it with the string "psana-".

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
        Initializes the psana Epics variable data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the psana Detector interface for the variable whose
        psana name matches the `psana_{source_protocols_name}_name` entry in the
        OM's `data_retrieval_layer` configuration parameter group, or for the Epics
        variable with a given psana name, if the `source_protocols_name` argument has
        the format `psana-{psana detector name}`.
        """
        epics_variable_name: str = _get_psana_epics_name(
            source_protocols_name=self._data_source_name,
            monitor_parameters=self._monitor_parameters,
        )
        if not epics_variable_name:
            epics_variable_name = _get_psana_detector_name(
                source_protocols_name=self._data_source_name,
                monitor_parameters=self._monitor_parameters,
            )
        self._detector_interface: Any = psana.Detector(epics_variable_name)

    def get_data(self, *, event: Dict[str, Any]) -> Any:
        """
        Retrieves an Epics variable's value from psana.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves from psana the Epics variable's value associated with
        the provided event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The value of the Epics variable.
        """
        return self._detector_interface()


class BeamEnergyPsana(OmDataSourceBase):
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
        Beam energy information at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of beam energy information at the LCLS
        facility. Psana provides this information for each event.

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, in communications with the user or for the retrieval
                of a sensor's initialization parameters.

            monitor_parameters: An object storing OM's configuration parameters.
        """
        del data_source_name
        del monitor_parameters

    def initialize_data_source(self) -> None:
        """
        Initializes the psana beam energy data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the psana Detector interface for the retrieval of
        beam energy information.
        """
        self._detector_interface: Any = psana.Detector("EBeam")

    def get_data(self, *, event: Dict[str, Any]) -> float:
        """
        Retrieves beam energy information from psana.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

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


class BeamEnergyFromEpicsVariablePsana(OmDataSourceBase):
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
        Beam energy information at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of beam energy information at the LCLS
        facility. It retrieves the information with a method that is different from
        how Psana usually provides this beam energy information: this class retrieves
        the information by reading an Epics variable.

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, in communications with the user or for the retrieval
                of a sensor's initialization parameters.

            monitor_parameters: An object storing OM's configuration parameters.
        """
        del data_source_name
        del monitor_parameters

    def initialize_data_source(self) -> None:
        """
        Initializes the psana beam energy data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the psana Detector interface for the Epics variable
        storing the beam energy information.
        """
        self._detector_interface: Any = psana.Detector("SIOC:SYS0:ML00:AO192")

    def get_data(self, *, event: Dict[str, Any]) -> float:
        """
        Retrieves beam energy information from psana.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves from an Epics variable the beam energy information for
        the provided event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The beam energy.
        """
        wavelength: Union[float, None] = self._detector_interface(event)
        if wavelength is None:
            raise OmDataExtractionError(
                "Could not retrieve beam energy information from psana."
            )
        h: float = 6.626070e-34  # J.m
        c: float = 2.99792458e8  # m/s
        joules_per_ev: float = 1.602176621e-19  # J/eV
        photon_energy: float = (h / joules_per_ev * c) / (wavelength * 1e-9)

        return photon_energy


class EvrCodesPsana(OmDataSourceBase):
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
        EVR event codes at the LCLS facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of EVR event codes at the LCLS facility.
        It gathers the information needed to determine if an EVR event code has been
        emitted by an EVR source for a specific event. This class checks the EVR code
        number corresponding to the value of the `{data_source_name}_evr_code` entry in
        OM's `data_retrieval_layer` configuration parameter group. The name of the EVR
        source is instead specified by the `psana_evr_source_name` entry in the same
        parameter group.

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
        Initializes the psana EVR event code data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function initializes the psana Detector interface for the EVR event source
        specified by the `psana_evr_source_name` entry in OM's `Data Retrieval Layer`
        configuration parameter group.
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

        This function checks if the event code associated with the data source class
        is emitted by the monitored EVR source for the provided event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            Whether the required event code has been emitted for the provided event.
        """
        current_evr_codes: Union[List[int], None] = self._detector_interface.eventCodes(
            event["data"]
        )
        if current_evr_codes is None:
            raise OmDataExtractionError("Could not retrieve event codes from psana.")

        return self._requested_event_code in current_evr_codes


class LclsExtraPsana(OmDataSourceBase):
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
        TODO: Documentation

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
        TODO: Documentation
        """

        lcls_extra_items: List[List[str]] = self._monitor_parameters.get_parameter(
            group="data_retrieval_layer",
            parameter="lcls_extra",
            parameter_type=list,
            required=True,
        )

        self._lcls_extra: Dict[str, Any] = {}

        data_item: List[str]
        for data_item in lcls_extra_items:
            if not isinstance(data_item, list) or len(data_item) != 3:
                raise OmWrongParameterTypeError(
                    "The 'lcls_extra' entry of the 'data_retrieval_layer' group "
                    "in the configuration file is not formatted correctly."
                )
            for entry in data_item:
                if not isinstance(entry, str):
                    raise OmWrongParameterTypeError(
                        "The 'lcls_extra' entry of the 'data_retrieval_layer' "
                        "group in the configuration file is not formatted "
                        "correctly."
                    )
                identifier: str
                name: str
                data_type, identifier, name = data_item
                if data_type == "acqiris_waveform":
                    self._lcls_extra[name] = AcqirisPsana(
                        data_source_name=f"psana-{identifier}",
                        monitor_parameters=self._monitor_parameters,
                    )
                elif data_type == "epics_pv":
                    self._lcls_extra[name] = EpicsVariablePsana(
                        data_source_name=f"psana-{identifier}",
                        monitor_parameters=self._monitor_parameters,
                    )
                elif data_type == "wave8_total_intensity":
                    self._lcls_extra[name] = Wave8Psana(
                        data_source_name=f"psana-{identifier}",
                        monitor_parameters=self._monitor_parameters,
                    )
                elif data_type == "opal_camera":
                    self._lcls_extra[name] = OpalPsana(
                        data_source_name=f"psana-{identifier}",
                        monitor_parameters=self._monitor_parameters,
                    )
                elif data_type == "assembled_detector_data":
                    self._lcls_extra[name] = AssembledDetectorPsana(
                        data_source_name=f"psana-{identifier}",
                        monitor_parameters=self._monitor_parameters,
                    )
                else:
                    raise OmWrongParameterTypeError(
                        f"The requested '{data_type}' LCLS-specific data type is "
                        "not supported."
                    )
                self._lcls_extra[name].initialize_data_source()

    def get_data(self, *, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        TODO: Documentation

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            Whether the required event code has been emitted for the provided event.
        """
        data: Dict[str, Any] = {}

        name: str
        for name in self._lcls_extra:
            data[name] = self._lcls_extra[name].get_data(event=event)

        return data
