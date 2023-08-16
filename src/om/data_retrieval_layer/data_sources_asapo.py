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
ASAP::O-related data sources.

This module contains Data Source classes that deal with data retrieved from the ASAP::O
software framework (used at the PETRA III facility).
"""
from typing import Any, Dict, Union, cast

import numpy
from numpy.typing import NDArray
from scipy import constants  # type: ignore

from om.lib.exceptions import OmMissingDependencyError
from om.lib.parameters import MonitorParameters
from om.protocols.data_retrieval_layer import OmDataSourceProtocol

try:
    import seedee  # type: ignore
except ImportError:
    raise OmMissingDependencyError(
        "The following required module cannot be imported: seedee"
    )


class EigerAsapo(OmDataSourceProtocol):
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
        Eiger 16M detector data frames from ASAP::O at the PETRA III facility.

        This class deals with the retrieval of EIGER 16M detector data frames from the
        ASAPO software framework, as used at the PETRA III facility.

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
        Initializes the ASAP::O Eiger 16M detector data frame source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        No initialization is needed to retrieve detector data frames from ASAP::O, so
        this function actually does nothing.
        """
        pass

    def get_data(
        self, *, event: Dict[str, Any]
    ) -> Union[NDArray[numpy.float_], NDArray[numpy.int_]]:
        """
        Retrieves an Eiger 16M detector data frame from ASAP::O.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves from ASAP::O the detector data frame associated with
        the provided event, and returns the detector frame as a 2D array storing pixel
        information.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A detector data frame.
        """
        # TODO: Fix type hinting
        return cast(
            Union[NDArray[numpy.float_], NDArray[numpy.int_]],
            seedee.deserialize(
                event["data"], event["metadata"]["meta"]["_data_format"]
            ),
        )


class TimestampAsapo(OmDataSourceProtocol):
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
        Timestamp information from ASAP::O at the PETRA III facility.

        This class deals with the retrieval of timestamp information from the ASAP::O
        software framework. ASAP::O provides this information for each event.

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
        Initializes the ASAP::O timestamp data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        No initialization is needed to retrieve timestamp information from ASAP::O,
        so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> numpy.float64:
        """
        Retrieves timestamp information from ASAP::O.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves from ASAP::O the timestamp information associated with
        the provided event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The timestamp for the data event.
        """
        return cast(numpy.float64, event["metadata"]["timestamp"] / 1e9)


class EventIdAsapo(OmDataSourceProtocol):
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
        Data event identifiers from ASAP::O at the PETRA III facility.

        This class deals with the retrieval of unique event identifiers for
        ASAP::O-based data events.

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
        Initializes the ASAP::O event identifier data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        No initialization is required to retrieve event identifiers for ASAP::O, so
        this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> str:
        """
        Retrieves an event identifier from ASAP::O.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves a unique event identifier for the provided event.
        Since an ASAP::O-based OM data event corresponds to the content of a single
        ASAP::O event, the function constructs the event identifier by joining the
        following elements in a single string, with the "//" symbol placed between
        them:

        * The name of the ASAP::O stream.

        * The ID of the ASAP::O event in the stream.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A unique event identifier.
        """
        return (
            f"{event['additional_info']['stream_name']} // {event['metadata']['_id']}"
        )


class BeamEnergyAsapo(OmDataSourceProtocol):
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
        Beam energy information from ASAP::O at the PETRA III facility.

        This class deals with the retrieval of beam energy information from ASAP::O.
        ASAP::O provides this information for each event.

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
        del monitor_parameters

    def initialize_data_source(self) -> None:
        """
        Initializes the ASAP::O beam energy data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        No initialization is required to retrieve beam energy information from ASAP::O,
        so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> float:
        """
        Retrieves beam energy information from ASAP::O.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves from ASAP::O the beam energy information associated
        with the provided event.

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


class DetectorDistanceAsapo(OmDataSourceProtocol):
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
        Detector distance information from ASAP::O at the PETRA III facility.

        This class deals with the retrieval of detector distance information from
        ASAP::O. ASAP::O provides this information for each event.

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
        del monitor_parameters

    def initialize_data_source(self) -> None:
        """
        Initializes the ASAP::O detector distance data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        No initialization is required to retrieve detector distance information from
        ASAP::O, so this function actually does nothing.
        """
        pass

    def get_data(self, *, event: Dict[str, Any]) -> float:
        """
        Retrieves detector distance information from ASAP::O.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves from ASAP::O the detector distance information\
        associated with the provided event.

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
