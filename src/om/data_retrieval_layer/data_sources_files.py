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
File-based data sources.

This module contains Data Source classes that deal with data stored in files.
"""
from typing import Any, BinaryIO, Dict, List, Tuple, Union, cast

import h5py  # type: ignore
import numpy  # type: ignore

from om.data_retrieval_layer import base as drl_base
from om.data_retrieval_layer import data_sources_generic as ds_generic
from om.utils.parameters import MonitorParams


class PilatusSingleFrameFiles(drl_base.OmDataSource):
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
        Detector frame data from Pilatus single-frame files.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of detector frame data from single-frame
        files written by a Pilatus detector in CBF format. It is a subclass of the
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
        Initializes the Pilatus single-frame file data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        No initialization is needed to retrieve data from Pilatus single-frame files,
        so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> numpy.ndarray:
        """
        Retrieves a Pilatus detector data frame.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function extracts the detector frame information from the content of the
        CBF file attached to the data event. It returns it as a 2D array storing pixel
        data.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            One frame of detector data.
        """
        return event["data"].data


class Jungfrau1MFiles(drl_base.OmDataSource):
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
        Detector frame data from Jungfrau 1M HDF5 files.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of Jungfrau 1M detector frame data from
        files written by the detector in HDF5 format. It is a subclass of the
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
        Initializes the Jungfrau 1M HDF5 data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves from OM's configuration parameters all the information
        needed to initialize the data source. It looks at the parameter
        `{data_source_name}_calibration` in the `data retrieval layer` parameter group
        to determine if calibrated data needs to be retrieved from the Jungfrau 1M. In
        the affirmative case, it reads the names of the files containing the required
        calibration constants from the entries `dark_filenames` and `gain_filenames`
        in the `calibration` parameter group.
        """
        self._calibrated_data_required: bool = ds_generic.get_calibration_request(
            source_base_name=self._data_source_name,
            monitor_parameters=self._monitor_parameters,
        )
        if self._calibrated_data_required:
            dark_filenames: Union[
                List[str], None
            ] = self._monitor_parameters.get_parameter(
                group="calibration",
                parameter="dark_filenames",
                parameter_type=list,
            )
            gain_filenames: Union[
                List[str], None
            ] = self._monitor_parameters.get_parameter(
                group="calibration",
                parameter="gain_filenames",
                parameter_type=list,
            )

            # TODO: Energy should be in eV
            photon_energy_kev: Union[
                float, None
            ] = self._monitor_parameters.get_parameter(
                group="calibration",
                parameter="photon_energy_kev",
                parameter_type=float,
            )

            if (
                dark_filenames is None
                or gain_filenames is None
                or photon_energy_kev is None
            ):
                self._calbration_available: bool = False
            else:
                self._calbration_available = True
                # 2 for Jungfrau 1M
                num_panels: int = len(dark_filenames)

                self._dark: numpy.ndarray = numpy.ndarray(
                    (3, 512 * num_panels, 1024), dtype=numpy.float32
                )
                self._gain: numpy.ndarray = numpy.ndarray(
                    (3, 512 * num_panels, 1024), dtype=numpy.float64
                )
                panel_id: int
                for panel_id in range(num_panels):
                    gain_file: BinaryIO = open(gain_filenames[panel_id], "rb")
                    dark_file: Any = h5py.File(dark_filenames[panel_id], "r")
                    gain: int
                    for gain in range(3):
                        self._dark[
                            gain, 512 * panel_id : 512 * (panel_id + 1), :
                        ] = dark_file["gain%d" % gain][:]
                        self._gain[
                            gain, 512 * panel_id : 512 * (panel_id + 1), :
                        ] = numpy.fromfile(
                            gain_file, dtype=numpy.float64, count=1024 * 512
                        ).reshape(
                            (512, 1024)
                        )
                    gain_file.close()
                    dark_file.close()

                self._photon_energy_kev: float = photon_energy_kev

    def get_data(self, *, event: Dict[str, Any]) -> numpy.ndarray:
        """
        Retrieves a Jungfrau 1M  detector data frame.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function extracts the detector frame information from the content of the
        data event, and returns the it as a 2D array storing pixel data.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            One frame of detector data.
        """
        h5files: Tuple[Any, Any] = event["additional_info"]["h5files"]
        h5_data_path: str = event["additional_info"]["h5_data_path"]
        index: Tuple[int, int] = event["additional_info"]["index"]

        data: numpy.ndarray = numpy.concatenate(
            [h5files[i][h5_data_path][index[i]] for i in range(len(h5files))]
        )

        if self._calibrated_data_required:

            calibrated_data: numpy.ndarray = data.astype(numpy.float32)

            where_gain: List[numpy.ndarray] = [
                numpy.where(data & 2 ** 14 == 0),
                numpy.where((data & (2 ** 14) > 0) & (data & 2 ** 15 == 0)),
                numpy.where(data & 2 ** 15 > 0),
            ]

            gain: int
            for gain in range(3):
                calibrated_data[where_gain[gain]] -= self._dark[gain][where_gain[gain]]
                calibrated_data[where_gain[gain]] /= (
                    self._gain[gain][where_gain[gain]] * self._photon_energy_kev
                )

            return calibrated_data
        else:
            return data


class Eiger16MFiles(drl_base.OmDataSource):
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
        Detector frame data from Eiger 16M HDF5 files.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of Eiger 16M detector frame data from
        files written by the detector in HDF5 format. It is a subclass of the
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
        Initializes the Eiger 16M single-frame file data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        No initialization is needed to retrieve data from Eiger single-frame files,
        so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> numpy.ndarray:
        """
        Retrieves a Eiger 16M detector data frame.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function extracts the detector frame information from the content of the
        HDF5 file attached to the data event. It returns it as a 2D array storing pixel
        data.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            One frame of detector data.
        """
        return event["additional_info"]["h5file"]["entry/data/data"][event["additional_info"]["index"]]


class TimestampFromFileModificationTime(drl_base.OmDataSource):
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
        Timestamp information from the modification date of files.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of timestamp information for data files
        which do not contain any timestamp information provided by a detector. It works
        on the assumption that the modification date of the file is a good first
        approximation of the timestamp of the data stored in it. This class is a
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
        Initializes the modification date timestamp data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        No initialization is needed to retrieve timestamp data from the modification
        date of a file, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> numpy.float64:
        """
        Retrieves timestamp information from the modification date of a file.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves the timestamp information for a file attached to an
        event by extracing the file modification date as recorded by OM when the
        event was opened.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The timestamp of the file-based data event.
        """
        return event["additional_info"]["file_modification_time"]


class TimestampJungfrau1MFiles(drl_base.OmDataSource):
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
        Timestamp information for Jungfrau 1M data files.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of timestamp information for Jungfrau 1M
        data files. The files written by this detector do not record any absolute
        timestamp information. However, they store the readout of the internal detector
        clock for every frame they contain. As a first approximation, this class takes
        the modification time of the whole data file as the timestamp of the first
        frame in it, and computes the timestamp of all other frames according to the
        recorded internal clock time difference. This class is a subclass of the
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
        Initializes the Jungfrau 1M file timestamp data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        No initialization is needed to retrieve timestamp data for a Jungfrau 1M data
        file, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> numpy.float64:
        """
        Retrieves timestamp information for a Jungfrau 1M data event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves the timestamp information for a Jungfrau 1M detector
        data frame attached to an event, based on the file modification date and the
        internal clock reading associated with the frame. Both values are recorded by
        OM when the data event is opened.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The timestamp of the Jungfrau 1M data event.
        """

        file_creation_time: float = event["additional_info"]["file_creation_time"]
        jf_clock_value: int = event["additional_info"]["jf_internal_clock"]
        # Jungfrau internal clock frequency in Hz
        jf_clock_frequency: int = 10000000
        return file_creation_time + jf_clock_value / jf_clock_frequency


class EventIdFromFilePath(drl_base.OmDataSource):
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
        Event identifier from a file's full path.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of a unique event identifier for file-based
        data events that do not provide this information in any other way. It takes as
        identifier the full path to the data file attached to the event. This class
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
        Initializes the full path event identifier data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        No initialization is needed to retrieve an event identifier from a full
        file path, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> str:
        """
        Retrieves the event identifier from the full path of a file.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves a unique event identifier from the full path to the
        file attached to a data event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A unique event identifier.
        """
        return cast(str, event["additional_info"]["full_path"])


class EventIdJungfrau1MFiles(drl_base.OmDataSource):
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
        Event identifier for Jungfrau 1M data events.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of a unique event identifier for
        Jungfrau 1M data events. For this detector one event is equivalent to a single
        stored in an HDF5 file. The combination of the full path to the data file
        and the index of the frame within the file itself is used to generate an event
        identifier. This class is a subclass of the
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
        Initializes the Jungfrau 1M event identifier data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        No initialization is needed to retrieve an event identifier for Jungfrau 1M
        event data, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> str:
        """
        Retrieves an event identifier for a Jungfrau 1M data event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function constructs the event identifier for an event by joining the
        following elements in a single string:

        - The full path to the file containing the data for the first panel of the
          detector data frame (d0) .

        - The index of the current frame within the file itself.

        The two parts of the are separated by the "//" symbol.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A unique event identifier.
        """
        filename: str = event["additional_info"]["h5files"][0].filename
        index: str = event["additional_info"]["index"][0]
        return f"{filename} // {index:04d}"


class EventIdEiger16MFiles(drl_base.OmDataSource):
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
        Event identifier for Eiger 16M data events.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of a unique event identifier for
        Eiger 16M data events. For this detector one event is equivalent to a single
        stored in an HDF5 file. The combination of the full path to the data file
        and the index of the frame within the file itself is used to generate an event
        identifier. This class is a subclass of the
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
        Initializes the Eiger 16M event identifier data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        No initialization is needed to retrieve an event identifier for Eiger 16M
        event data, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> str:
        """
        Retrieves an event identifier for a Eiger 16M data event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function constructs the event identifier for an event by joining the
        following elements in a single string:

        - The full path to the file.

        - The index of the current frame within the file itself.

        The two parts of the are separated by the "//" symbol.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A unique event identifier.
        """
        filename: str = event["additional_info"]["full_path"]
        index: str = event["additional_info"]["index"]
        return f"{filename} // {index:04d}"
