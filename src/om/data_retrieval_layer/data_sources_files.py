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
    """

    def __init__(
        self,
        *,
        data_source_name: str,
        monitor_parameters: MonitorParams,
    ):
        """
        Detector data frames from Pilatus single-frame CBF files.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of a Pilatus detector data frame from
        single-frame files written by the detector in CBF format.

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
        Initializes the Pilatus detector frame data source for single-frame CBF files.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        No initialization is needed to retrieve a detector data frame from single-frame
        CBF files, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> numpy.ndarray:
        """
        Retrieves a Pilatus detector data frame from an event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function extracts a detector data frame from a CBF file attached to the
        provided data event. It returns the frame as a 2D array storing pixel
        information.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            One detector data frame.
        """
        return event["data"].data


class Jungfrau1MFiles(drl_base.OmDataSource):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        data_source_name: str,
        monitor_parameters: MonitorParams,
    ):
        """
        Detector data frames from Jungfrau 1M HDF5 files.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of a Jungfrau 1M detector data frame from
        files written by the detector in HDF5 format.  The frame can be retrieved in
        calibrated or non-calibrated form, depending on the value of the
        `{source_base_name}_calibration` entry in OM's `data_retrieval_layer`
        configuration parameter group.

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, in communications with the user or for the retrieval
                of a sensor's initialization parameters.

            monitor_parameters: An object storing OM's configuration parameters."""
        self._data_source_name = data_source_name
        self._monitor_parameters = monitor_parameters

    def initialize_data_source(self) -> None:
        """
        Initializes the Jungfrau 1M detector frame data source for files.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves from OM's configuration parameters all the information
        needed to initialize the data source. It looks at the
        `{data_source_name}_calibration` entry in OM's `data retrieval layer`
        configuration parameter group to determine if calibrated data needs to be
        retrieved. In the affirmative case, it reads the names of the files containing
        the required calibration constants from the entries `dark_filenames` and
        `gain_filenames` in the `calibration` parameter group.
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
                self._calibration_available: bool = False
            else:
                self._calibration_available = True
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

        This function extracts a detector data frame from an HDF5 file attached to the
        provided data event. It returns the frame as a 2D array storing pixel
        information. The data is retrieved in calibrated or non-calibrated form
        depending on the value of the `{source_base_name}_calibration` entry in OM's
        `data_retrieval_layer` configuration parameter group.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            One detector data frame.
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
    """

    def __init__(
        self,
        *,
        data_source_name: str,
        monitor_parameters: MonitorParams,
    ):
        """
        Detector data frames from Eiger 16M HDF5 files.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of an Eiger 16M detector data frame from
        files written by the detector in HDF5 format.

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, in communications with the user or for the retrieval
                of a sensor's initialization parameters.

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.
        """
        self._data_source_name = data_source_name
        self._monitor_parameters = monitor_parameters

    def initialize_data_source(self) -> None:
        """
        Initializes the Eiger 16M detector frame data source for files.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        No initialization is needed to retrieve a detector data frame from files
        written by the Eiger 16M detector, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> numpy.ndarray:
        """
        Retrieves a Eiger 16M detector data frame.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function extracts a detector data frame from an HDF5 file attached to the
        provided data event. It returns the frame as a 2D array storing pixel
        information.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            One detector data frame.
        """
        return event["additional_info"]["h5file"]["entry/data/data"][
            event["additional_info"]["index"]
        ]


class TimestampFromFileModificationTime(drl_base.OmDataSource):
    """
    See documentation of the `__init__` function.
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

        This class deals with the retrieval of timestamp information for file-based
        data events which do not provide any information of this kind. It assumes that
        the last modification date of a file is a good first approximation of the
        timestamp of the data stored in it.

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, in communications with the user or for the retrieval
                of a sensor's initialization parameters.

            monitor_parameters: An object storing OM's configuration parameters."""
        self._data_source_name = data_source_name
        self._monitor_parameters = monitor_parameters

    def initialize_data_source(self) -> None:
        """
        Initializes the modification date timestamp data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        No initialization is needed to retrieve timestamp information from the
        modification date of a file, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> numpy.float64:
        """
        Retrieves timestamp information from the modification date of a file.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves the timestamp information for a file attached to the
        provided event. It computes the timestamp using the last modification time of
        the file.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The timestamp of the data event.
        """
        return event["additional_info"]["file_modification_time"]


class TimestampJungfrau1MFiles(drl_base.OmDataSource):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        data_source_name: str,
        monitor_parameters: MonitorParams,
    ):
        """
        Timestamp information for Jungfrau 1M detector data frames.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of timestamp information for a Jungfrau 1M
        detector data frame. The files written by this detector do not record any
        absolute timestamp information. However, they store the readout of the internal
        detector clock for every frame they contain. As a first approximation, this
        class takes the modification time of a data file as the timestamp of the first
        frame stored in it, and computes the timestamp of all other frames according to
        the recorded internal clock time difference.

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

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        No initialization is needed to retrieve timestamp information for a Jungfrau 1M
        data frame, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> numpy.float64:
        """
        Retrieves timestamp information for a Jungfrau 1M data frame.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves the timestamp information for a Jungfrau 1M detector
        data frame. It computes the timestamp using the last modification time of the
        file attached to the provided event, plus the  internal clock reading
        associated with the frame being processed.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The timestamp of the Jungfrau 1M data frame.
        """

        file_creation_time: float = event["additional_info"]["file_creation_time"]
        jf_clock_value: int = event["additional_info"]["jf_internal_clock"]
        # Jungfrau internal clock frequency in Hz
        jf_clock_frequency: int = 10000000
        return file_creation_time + jf_clock_value / jf_clock_frequency


class EventIdFromFilePath(drl_base.OmDataSource):
    """
    See documentation of the `__init__` function.
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
        data events that do not provide this information in any other way. It takes the
        full path to the data file as event identifier.

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, in communications with the user or for the retrieval
                of a sensor's initialization parameters.

            monitor_parameters: An object storing OM's configuration parameters."""
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

        This function retrieves a unique event identifier from the full path of a file
        attached to the provided data event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A unique event identifier.
        """
        return cast(str, event["additional_info"]["full_path"])


class EventIdJungfrau1MFiles(drl_base.OmDataSource):
    """
    See documentation of the `__init__` function.
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

        This class deals with the retrieval of a unique event identifier for a
        Jungfrau 1M data event. For this detector, an individual event corresponds to
        a single frame stored in an HDF5 data file. The combination of the full path to
        the data file and the index of the frame within the file is used to generate
        an event identifier.

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, in communications with the user or for the retrieval
                of a sensor's initialization parameters.

            monitor_parameters: An object storing OM's configuration parameters."""
        self._data_source_name = data_source_name
        self._monitor_parameters = monitor_parameters

    def initialize_data_source(self) -> None:
        """
        Initializes the Jungfrau 1M event identifier data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        No initialization is needed to retrieve an event identifier for a Jungfrau 1M
        data event, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> str:
        """
        Retrieves an event identifier for a Jungfrau 1M data event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function constructs the event identifier for the provided event by joining
        the following elements in a single string, with the "//" symbol placed between
        them.

        * The full path to the HDF5 file attached to the event.

        * The index, within the file, of the frame being processed.

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

        This class deals with the retrieval of a unique event identifier for an
        Eiger 16M data event. For this detector, an individual event corresponds to a
        single frame stored in an HDF5 file. The combination of the full path to the
        data file and the index of the frame within the file is used to generate an
        event identifier.

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

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        No initialization is needed to retrieve an event identifier for an Eiger 16M
        data event, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> str:
        """
        Retrieves an event identifier for an Eiger 16M data event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function constructs the event identifier for the provided event by joining
        the following elements in a single string, with the "//" symbol placed between
        them.

        * The full path to the HDF5 file attached to the event.

        * The index, within the file, of the frame being processed.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A unique event identifier.
        """
        filename: str = event["additional_info"]["full_path"]
        index: str = event["additional_info"]["index"]
        return f"{filename} // {index:04d}"
