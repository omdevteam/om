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
ASAPO-related data sources.

This module contains Data Source classes that deal with data retrieved from the ASAPO
software framework (used at the PETRA III facility).
"""
from typing import Any, Callable, Dict, List, Tuple, Union, cast

import numpy
from numpy.typing import NDArray
from scipy import constants

from om.data_retrieval_layer import base as drl_base
from om.data_retrieval_layer import data_sources_generic as ds_generic
from om.utils import exceptions
from om.utils.parameters import MonitorParams

try:
    import ceedee  # type: ignore
except ImportError:
    raise exceptions.OmMissingDependencyError(
        "The following required module cannot be imported: ceedee"
    )


class EigerAsapo(drl_base.OmDataSource):
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
        Eiger 16M detector data frames from the ASAPO software framework at the PETRA
        III facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of a EIGER 16M detector data frame from the
        ASAPO software framework.

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
        Initializes the Eiger 16M detector frame data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        No initialization is needed to retrieve a detector data frame from ASAPO, so
        this function actually does nothing.
        """
        pass

    def get_data(
        self, *, event: Dict[str, Any]
    ) -> Union[NDArray[numpy.float_], NDArray[numpy.int_]]:
        """
        Retrieves an Eiger 16M detector data frame from ASAPO.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves from ASAPO the detector data frame associated with the
        provided event. It returns the frame as a 2D array storing pixel information.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            One detector data frame.
        """
        return ceedee.deserialize(
            event["data"], event["metadata"]["meta"]["_data_format"]
        )


class TimestampAsapo(drl_base.OmDataSource):
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
        Timestamp information from ASAPO at the PETRA III facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of timestamp information from the ASAPO
        software framework. ASAPO provides this information for each event.

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
        Initializes the ASAPO timestamp data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        No initialization is needed to retrieve timestamp information from ASAPO,
        so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> numpy.float64:
        """
        Retrieves timestamp information from ASAPO.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves from ASAPO the timestamp information for the provided
        event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The timestamp for the data event.
        """
        return cast(numpy.float64, event["metadata"]["timestamp"] / 1e9)


class EventIdAsapo(drl_base.OmDataSource):
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
        Data event identifier from the ASAPO software framework at the PETRA III
        facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of a unique event identifier for
        ASAPO-based data events. With ASAPO, an OM's data event corresponds to the
        content of an individual ASAPO event. The combination of ASAPO stream name and
        ASAPO event ID is used to generate an event identifier.

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
        Initializes the ASAPO event identifier data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        No initialization is required to retrieve an event identifier for a ASAPO-based
        data event, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> str:
        """
        Retrieves an event identifier for an ASAPO-based data event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function constructs the event identifier for the provided event by joining
        the following elements in a single string, with the "//" symbol placed between
        them.

        * The name of the ASAPO stream.

        * The ID of the event in the stream.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A unique event identifier.
        """
        return (
            f"{event['additional_info']['stream_name']} // {event['metadata']['_id']}"
        )


class BeamEnergyAsapo(drl_base.OmDataSource):
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
        Beam energy information from the ASAPO software framework at the PETRA III
        facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of beam energy information from ASAPO.
        ASAPO provides this information for each event.

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
        Initializes the ASAPO beam energy data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        No initialization is required to retrieve the beam energy for an ASAPO-based
        data event, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> float:
        """
        Retrieves beam energy information from ASAPO.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves from ASAPO the beam energy information for the provided
        event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The beam energy.
        """
        wavelength: float = (
            1e-10
            * event["additional_info"]["stream_metadata"]["entry"]["instrument"][
                "beam"
            ]["incident_wavelength"]["()"]
        )
        return cast(float, constants.h * constants.c / (wavelength * constants.e))


class DetectorDistanceAsapo(drl_base.OmDataSource):
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
        Detector distance information from the ASAPO software framework at the PETRA
        III facility.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class deals with the retrieval of detector distance information from
        ASAPO. ASAPO provides this information for each event.

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
        Initializes the ASAPO detector distance data source.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        No initialization is required to retrieve the detector distance for an
        ASAPO-based data event, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> float:
        """
        Retrieves detector distance information from ASAPO.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves from ASAPO the detector distance information for the
        provided event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The beam energy.
        """
        return cast(
            float,
            event["additional_info"]["stream_metadata"]["entry"]["instrument"][
                "detector"
            ]["distance"]["()"]
            * 1e3,
        )
