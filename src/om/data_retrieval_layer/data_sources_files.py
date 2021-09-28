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
Retrieval of Jungfrau 1M detector data from files.

This module contains functions that retrieve Jungfrau 1M detector data from HDF5 files
written by the detector itself.
"""
from typing import Any, BinaryIO, cast, Dict, List, Tuple, Union

import h5py  # type: ignore
import numpy  # type: ignore

from om.data_retrieval_layer import base as drl_base
from om.data_retrieval_layer import data_sources_generic as ds_generic
from om.utils.parameters import MonitorParams


class PilatusSingleFrameFiles(drl_base.OmDataSource):
    def __init__(
        self,
        *,
        data_source_name: str,
        monitor_parameters: MonitorParams,
    ):
        """
        Jungfrau 1M detector data from files.

        This class deals with the Jungfrau 1M x-ray detector data, operated in such a
        way that data is written in HDF5 files. It is a subclass of the generic
        [OmDetector][om.data_retrieval_layer.base.OmDetector] base class.

        Arguments:

            detector_index: the index of the current detector in the list of detectors
                used by the monitor (used to determine the detector name).

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.

            additional_info: A dictionary storing any additional information needed for
                the initialization of the Data Event Handler.
        """
        self._data_source_name = data_source_name
        self._monitor_parameters = monitor_parameters

    def initialize_data_source(self) -> None:
        """
        # TODO: Docs
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> numpy.ndarray:
        """
        Retrieves a calibrated CSPAD detector data frame from psana.

        #TODO: docs

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            One frame of detector data.
        """
        return event["data"].data


class Jungfrau1MFiles(drl_base.OmDataSource):
    def __init__(
        self,
        *,
        data_source_name: str,
        monitor_parameters: MonitorParams,
    ):
        """
        Jungfrau 1M detector data from files.

        This class deals with the Jungfrau 1M x-ray detector data, operated in such a
        way that data is written in HDF5 files. It is a subclass of the generic
        [OmDetector][om.data_retrieval_layer.base.OmDetector] base class.

        Arguments:

            detector_index: the index of the current detector in the list of detectors
                used by the monitor (used to determine the detector name).

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.

            additional_info: A dictionary storing any additional information needed for
                the initialization of the Data Event Handler.
        """
        self._data_source_name = data_source_name
        self._monitor_parameters = monitor_parameters

    def initialize_data_source(self) -> None:
        """
        # TODO: Docs
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
        Retrieves a calibrated CSPAD detector data frame from psana.

        #TODO: docs

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


class TimestampFromFileModificationTime(drl_base.OmDataSource):
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

    def get_data(self, *, event: Dict[str, Any]) -> numpy.float64:
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
        return event["additional_info"]["file_modification_time"]


class EventIdJungfrau1MFiles(drl_base.OmDataSource):
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

    def get_data(self, *, event: Dict[str, Any]) -> str:
        """
        #TODO: docs

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A unique event identifier.
        """
        filename: str = event["additional_info"]["h5files"][0].filename
        index: str = event["additional_info"]["index"][0]
        return f"{filename} // {index:04d}"


class EventIdFromFilePath(drl_base.OmDataSource):
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

    def get_data(self, *, event: Dict[str, Any]) -> str:
        """
        #TODO: docs

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A unique event identifier.
        """
        return cast(str, event["additional_info"]["full_path"])


class TimestampJungfrau1MFiles(drl_base.OmDataSource):
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

    def get_data(self, *, event: Dict[str, Any]) -> numpy.float64:
        """
        Gets a unique identifier for an event retrieved from a Jungfrau 1M detector.

        This function returns a label that unambiguously identifies, within an
        experiment, the data event currently being processed.

        For the Jungfrau 1M detector, the label is constructed by joining the following
        elements:

        - The full path to the file containing the data for the first detector panel
          (d0)

        - The index of the current frame within the file itself.

        The two parts of the label are separated by the "//" symbol.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A unique event identifier.
        """
        file_creation_time: float = event["additional_info"]["file_creation_time"]
        jf_clock_value: int = event["additional_info"]["jf_internal_clock"]
        # Jungfrau internal clock frequency in Hz
        jf_clock_frequency: int = 10000000
        return file_creation_time + jf_clock_value / jf_clock_frequency
