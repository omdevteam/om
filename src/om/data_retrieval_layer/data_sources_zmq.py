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
ZMQ-based data sources.

This module contains Data Source classes that deal with data from ZMQ data streams.
"""
from typing import Any, BinaryIO, Dict, List, Tuple, Union, cast

import h5py  # type: ignore
import numpy
from numpy.typing import NDArray

from om.protocols import data_extraction_layer as drl_protocols
from om.data_retrieval_layer import data_sources_generic as ds_generic
from om.data_retrieval_layer import utils_generic as utils_gen
from om.utils.parameters import MonitorParams


class Jungfrau1MZmq(drl_protocols.OmDataSource):
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
        Detector data frames from a Jungfrau 1M ZMQ data stream.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of a Jungfrau 1M    detector data frame from
        a ZMQ stream broadcast by the detector. The detector data frame can be
        retrieved in calibrated or non-calibrated form, depending on the value of the
        `{source_protocols_name}_calibration` entry in the OM's `data_retrieval_layer`
        configuration parameter group.

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
        Initializes the Jungfrau 1M detector frame data source for ZMQ data streams.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves from OM's configuration parameters all the information
        needed to initialize the data source. It looks at the parameter
        `{data_source_name}_calibration` in OM's `data retrieval layer` configuration
        parameter group to determine if calibrated data needs to be retrieved. In the
        affirmative case, it reads the names of the files containing the required
        calibration constants from the entries `dark_filenames` and `gain_filenames`
        in the `calibration` parameter group.
        """
        self._calibrated_data_required: bool = ds_generic.get_calibration_request(
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

            self._calibration = utils_gen.Jungfrau1MCalibration(
                dark_filenames=dark_filenames,
                gain_filenames=gain_filenames,
                photon_energy_kev=photon_energy_kev,
            )

    def get_data(
        self, *, event: Dict[str, Any]
    ) -> Union[NDArray[numpy.float_], NDArray[numpy.int_]]:
        """
        Retrieves a Jungfrau 1M detector data frame from a ZMQ data stream.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves the detector data frame associated with the provided
        ZMQ-based event. It returns the frame as a 2D array storing pixel information.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            One detector data frame.
        """
        msg: Tuple[Dict[str, Any], Dict[str, Any]] = event["data"]
        data: NDArray[numpy.int_] = numpy.concatenate(
            [
                numpy.frombuffer(msg[i]["data"], dtype=numpy.int16).reshape((512, 1024))
                for i in range(2)
            ]
        )

        if self._calibrated_data_required:
            return self._calibration.apply_calibration(data=data)
        else:
            return data


class TimestampJungfrau1MZmq(drl_protocols.OmDataSource):
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
        Timestamp information for Jungfrau 1M ZMQ-based events.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of timestamp information for Jungfrau 1M
        data events originating from a ZMQ stream. For this detector, an individual
        data event corresponds to a single data frame. In the ZMQ stream, a frame
        timestamp is associated to each event. This class retrieves this timestamp
        information.

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, for communication with the user or retrieval of
                initialization parameters.

            monitor_parameters: A [MonitorParams] [om.utils.parameters.MonitorParams]
                object storing the OM monitor parameters from the configuration file.
        """
        self._data_source_name = data_source_name
        self._monitor_parameters = monitor_parameters

    def initialize_data_source(self) -> None:
        """
        Initializes the ZMQ Jungfrau 1M timestamp data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        No initialization is needed to retrieve timestamp information for Jungfrau 1M
        data events originating from a ZMQ stream, so this function actually does
        nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> numpy.float64:
        """
        Retrieves timestamp information for a Jungfrau 1M data event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function returns the timestamp information associated, in the ZMQ data
        stream, to the provided event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The timestamp of the Jungfrau 1M ZMQ data event.
        """

        return cast(numpy.float64, event["data"][0]["timestamp"])


class EventIdJungfrau1MZmq(drl_protocols.OmDataSource):
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
        Event identifier for Jungfrau 1M ZMQ-based events.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of a unique identifier for Jungfrau 1M
        data events originating from a ZMQ stream. For this detector, an individual
        data event corresponds to a single data frame. In the ZMQ stream, a frame
        number is used to label each event. This class uses the frame number as event
        identifier.

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
        Initializes the ZMQ Jungfrau 1M event identifier data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        No initialization is needed to retrieve an event identifier for Jungfrau 1M
        data events originating from a ZMQ stream, so this function actually does
        nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> str:
        """
        Retrieves an event identifier for a Jungfrau 1M data event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function returns the frame number associated, in the ZMQ data stream, to
        the provided event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A unique event identifier.
        """
        return str(event["data"][0]["frame_number"])
