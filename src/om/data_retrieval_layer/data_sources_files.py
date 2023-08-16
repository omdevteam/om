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
File-based data sources.

This module contains Data Source classes that deal with data stored in files.
"""
from typing import Any, Dict, List, Tuple, Union, cast

import numpy
from numpy.typing import NDArray

from om.algorithms.calibration import Jungfrau1MCalibration
from om.data_retrieval_layer.data_sources_generic import get_calibration_request
from om.lib.exceptions import OmMissingDependencyError
from om.lib.parameters import MonitorParameters
from om.protocols.data_retrieval_layer import OmDataSourceProtocol

try:
    from PIL import Image  # type: ignore
except ImportError:
    raise OmMissingDependencyError(
        "The following required module cannot be imported: PIL.Image"
    )


class PilatusSingleFrameFiles(OmDataSourceProtocol):
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
        Detector data frames from Pilatus single-frame CBF files.

        This class deals with the retrieval of Pilatus detector data frames from
        single-frame files written by the detector in CBF format.

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
        Initializes CBF file-based Pilatus detector data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        No initialization is needed to retrieve detector data frames from single-frame
        CBF files, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> NDArray[numpy.float_]:
        """
        Retrieves a Pilatus detector data frame from a file-based event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves the detector data frame associated with the provided
        file-based event, and returns the detector frame as a 2D array storing pixel
        information.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            One detector data frame.
        """
        return cast(NDArray[numpy.float_], event["data"].data)


class Jungfrau1MFiles(OmDataSourceProtocol):
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

            monitor_parameters: An object storing OM's configuration parameters.
        """
        self._data_source_name = data_source_name
        self._monitor_parameters = monitor_parameters

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
        self._calibrated_data_required: bool = get_calibration_request(
            source_protocols_name=self._data_source_name,
            monitor_parameters=self._monitor_parameters,
        )
        if self._calibrated_data_required:
            dark_filenames: List[str] = self._monitor_parameters.get_parameter(
                group="data_retrieval_layer",
                parameter=f"{self._data_source_name}_dark_filenames",
                parameter_type=list,
                required=True,
            )
            gain_filenames: List[str] = self._monitor_parameters.get_parameter(
                group="data_retrieval_layer",
                parameter=f"{self._data_source_name}_gain_filenames",
                parameter_type=list,
                required=True,
            )

            photon_energy_kev: float = self._monitor_parameters.get_parameter(
                group="data_retrieval_layer",
                parameter=f"{self._data_source_name}_photon_energy_kev",
                parameter_type=float,
            )

            self._calibration = Jungfrau1MCalibration(
                dark_filenames=dark_filenames,
                gain_filenames=gain_filenames,
                photon_energy_kev=photon_energy_kev,
            )

    def get_data(
        self, *, event: Dict[str, Any]
    ) -> Union[NDArray[numpy.float_], NDArray[numpy.int_]]:
        """
        Retrieves a Jungfrau 1M detector data frame from a file-based event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves the detector data frame associated with the provided
        file-based event, and returns the detector frame as a 2D array storing pixel
        information. The data is retrieved in calibrated or non-calibrated form
        depending on the value of the `{source_protocols_name}_calibration` entry in
        OM's `data_retrieval_layer` configuration parameter group.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            One detector data frame.
        """
        data: NDArray[numpy.int_] = event["additional_info"]["h5file"][
            "/entry/data/data"
        ][event["additional_info"]["index"]]

        if self._calibrated_data_required:
            return self._calibration.apply_calibration(data=data)
        else:
            return data


class Eiger16MFiles(OmDataSourceProtocol):
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
        Detector data frames from Eiger 16M HDF5 files.

        This class deals with the retrieval of Eiger 16M detector data frames from
        files written by the detector in HDF5 format.

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
        Initializes the HDF5 file-based Eiger 16M detector data frame source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        No initialization is needed to retrieve detector data frames from files
        written by the Eiger 16M detector, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> NDArray[numpy.int_]:
        """
        Retrieves an Eiger 16M detector data frame from files.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves the detector data frame associated with the provided
        file-based event, and returns the detector frame as a 2D array storing pixel
        information.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A detector data frame.
        """
        return cast(
            NDArray[numpy.int_],
            event["additional_info"]["h5file"]["entry/data/data"][
                event["additional_info"]["index"]
            ],
        )


class RayonixMccdSingleFrameFiles(OmDataSourceProtocol):
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
        Detector data frames from Rayonix MX340-HS single-frame mccd files.

        This class deals with the retrieval of Rayonix detector data frames from
        single-frame files written by the detector in MCCD format.

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
        Initializes the mccd file-based Rayonix MX340-HS detector data frame source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        No initialization is needed to retrieve detector data frames from single-frame
        mccd files, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> NDArray[numpy.int_]:
        """
        Retrieves a Rayonix MX340-HS detector data frame from files.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves the detector data frame associated with the provided
        file-based event, and returns the detector frame as a 2D array storing pixel
        information.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A detector data frame.
        """
        img: Any
        with Image.open(event["additional_info"]["full_path"]) as img:
            data: NDArray[numpy.int_] = numpy.array(img)
        return data


class Lambda1M5Files(OmDataSourceProtocol):
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
        Detector data frames from Lambda 1.5M HDF5 files.

        This class deals with the retrieval of Lambda 1.5M detector data frames from
        files written by the detector in HDF5 format.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, in communications with the user or for the retrieval
                of a sensor's initialization parameters.

            monitor_parameters: An object storing OM's configuration parameters."""
        self._data_source_name = data_source_name
        self._monitor_parameters = monitor_parameters

    def initialize_data_source(self) -> None:
        """
        Initializes the HDF5 file-based Lambda 1.5M detector data frame source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        No initialization is needed to retrieve detector data frames from files
        written by the Lambda 1.5M detector, so this function actually does nothing.
        """
        pass

    def get_data(
        self, *, event: Dict[str, Any]
    ) -> Union[NDArray[numpy.float_], NDArray[numpy.int_]]:
        """
        Retrieves a Lambda 1.5M detector data frame from files.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves the detector data frame associated with the provided
        file-based event, and returns the detector frame as a 2D array storing pixel
        information.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            Detector data frame.
        """
        h5files: Tuple[Any, Any] = event["additional_info"]["h5files"]
        index: Tuple[int, int] = event["additional_info"]["index"]
        return cast(
            NDArray[numpy.int_],
            numpy.concatenate(
                [
                    h5files[i]["/entry/instrument/detector/data"][index[i]]
                    for i in range(len(h5files))
                ]
            ),
        )


class TimestampFromFileModificationTime(OmDataSourceProtocol):
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
        Timestamp information from the modification date of files.

        This class deals with the retrieval of timestamp information for file-based
        data events which do not provide any information of this kind. It assumes that
        the last modification date of a file is a good first approximation of the
        timestamp of the data stored in it.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, in communications with the user or for the retrieval
                of a sensor's initialization parameters.

            monitor_parameters: An object storing OM's configuration parameters."""
        self._data_source_name = data_source_name
        self._monitor_parameters = monitor_parameters

    def initialize_data_source(self) -> None:
        """
        Initializes the file modification date timestamp data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        No initialization is needed to retrieve timestamp information from the
        modification date of files, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> numpy.float64:
        """
        Retrieves timestamp information from the modification date of a file.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves the timestamp information associated with the provided
        file-based event. It uses as timestamp the last modification time of the file
        attached to the event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The timestamp of the data event.
        """
        return cast(numpy.float64, event["additional_info"]["file_modification_time"])


class TimestampJungfrau1MFiles(OmDataSourceProtocol):
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
        Timestamp information for Jungfrau 1M detector data events.

        This class deals with the retrieval of timestamp information for Jungfrau 1M
        data events. The files written by this detector do not record any absolute
        timestamp information. However, they store the readout of the internal detector
        clock for every frame they contain. As a first approximation, this class takes
        the modification time of a data file as the timestamp of the first frame stored
        in it, and computes the timestamp of all other frames according to the recorded
        internal clock time difference.

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
        Initializes the Jungfrau 1M timestamp data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        No initialization is needed to retrieve timestamp information for Jungfrau 1M
        data events, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> numpy.float64:
        """
        Retrieves the timestamp information for a Jungfrau 1M data event from files.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves the timestamp information associated with the provided
        file-based event. It computes the timestamp using the last modification time of
        the file attached to the event, modified by the internal clock reading of the
        frame associated to the event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The timestamp for the Jungfrau 1M data event.
        """

        file_timestamp: numpy.float64 = numpy.float64(
            event["additional_info"]["file_timestamp"]
        )
        jf_clock_value: int = (
            event["additional_info"]["h5file"]["/entry/data/timestamp"][
                event["additional_info"]["index"]
            ][0]
            - event["additional_info"]["h5file"]["/entry/data/timestamp"][0][0]
        )
        # Jungfrau internal clock frequency in Hz
        jf_clock_frequency: int = 10000000
        return file_timestamp + jf_clock_value / jf_clock_frequency


class EventIdFromFilePath(OmDataSourceProtocol):
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
        Event identifiers from full path of files.

        This class deals with the retrieval of unique event identifiers for file-based
        data events that do not provide this information in any other way. It takes the
        full path to the data file as event identifier.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, in communications with the user or for the retrieval
                of a sensor's initialization parameters.

            monitor_parameters: An object storing OM's configuration parameters."""
        self._data_source_name = data_source_name
        self._monitor_parameters = monitor_parameters

    def initialize_data_source(self) -> None:
        """
        Initializes the full file path event identifier data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        No initialization is needed to retrieve an event identifier from a full file
        path, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> str:
        """
        Retrieves the event identifier from the full path of a file.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves a unique event identifier for the provided file-based\
        event, using as identifier the full path of the file attached to the event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A unique event identifier.
        """
        return cast(str, event["additional_info"]["full_path"])


class EventIdJungfrau1MFiles(OmDataSourceProtocol):
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
        Event identifiers for Jungfrau 1M data events.

        This class deals with the retrieval of unique event identifiers for Jungfrau 1M
        file-based data events.

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
        Initializes the Jungfrau 1M event identifier data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        No initialization is needed to retrieve event identifiers for Jungfrau 1M
        data events, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> str:
        """
        Retrieves the event identifier for a Jungfrau 1M data event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function constructs the event identifier for the provided file-based event
        by joining the following elements in a single string, with the "//" symbol
        placed between them.

        * The full path to the HDF5 file attached to the event.

        * The index, within the file, of the frame being processed.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A unique event identifier.
        """
        filename: str = event["additional_info"]["h5file"].filename
        index: str = event["additional_info"]["index"]
        return f"{filename} // {index:05d}"


class EventIdEiger16MFiles(OmDataSourceProtocol):
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
        Event identifiers for Eiger 16M data events.

        This class deals with the retrieval of unique event identifiers for an Eiger
        16M file-based data events.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, in communications with the user or for the retrieval
                of a sensor's initialization parameters.

            monitor_parameters: An object storing OM's configuration parameters."""
        self._data_source_name = data_source_name
        self._monitor_parameters = monitor_parameters

    def initialize_data_source(self) -> None:
        """
        Initializes the Eiger 16M event identifier data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        No initialization is needed retrieve event identifiers for Eiger 16M data
        events, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> str:
        """
        Retrieves the event identifier for an Eiger 16M data event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function constructs the event identifier for the provided file-based event
        by joining the following elements in a single string, with the "//" symbol
        placed between them.

        * The full path to the HDF5 file attached to the provided event.

        * The index, within the file, of the frame being processed.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A unique event identifier.
        """
        filename: str = event["additional_info"]["full_path"]
        index: str = event["additional_info"]["index"]
        return f"{filename} // {index:04d}"


class EventIdLambda1M5Files(OmDataSourceProtocol):
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
        Event identifiers for Lambda 1.5M data events.

        This class deals with the retrieval of unique event identifiers for a Lambda
        1.5M data events.

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
        Initializes the Lambda 1.5M event identifier data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        No initialization is needed to retrieve event identifiers for Lambda 1.5M
        data events, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> str:
        """
        Retrieves the event identifier for an Lambda 1.5M data event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function constructs the event identifier for the provided file-based event
        by joining the following elements in a single string, with the "//" symbol
        placed between them.

        * The full path to the HDF5 file attached to the event and written by the first
          detector module,

        * The index, within the file, of the frame being processed.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A unique event identifier.
        """
        filename: str = event["additional_info"]["full_path"]
        index: str = event["additional_info"]["index"][0]
        return f"{filename} // {index:05d}"
