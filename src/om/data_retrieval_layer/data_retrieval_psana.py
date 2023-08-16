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
Retrieval of data from psana.

This module contains Data Retrieval classes that deal with the psana software framework
(used at the LCLS facility).
"""
from typing import Dict

from om.data_retrieval_layer.data_event_handlers_psana import PsanaDataEventHandler
from om.data_retrieval_layer.data_sources_psana import (
    BeamEnergyFromEpicsVariablePsana,
    BeamEnergyPsana,
    CspadPsana,
    DiodeTotalIntensityPsana,
    EpicsVariablePsana,
    Epix10kaPsana,
    Epix100Psana,
    EventIdPsana,
    EvrCodesPsana,
    Jungfrau4MPsana,
    LclsExtraPsana,
    RayonixPsana,
    TimestampPsana,
)
from om.lib.parameters import MonitorParameters
from om.protocols.data_retrieval_layer import (
    OmDataEventHandlerProtocol,
    OmDataRetrievalProtocol,
    OmDataSourceProtocol,
)


class CxiLclsDataRetrieval(OmDataRetrievalProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(self, *, monitor_parameters: MonitorParameters, source: str):
        """
        Data Retrieval from psana at the CXI beamline of the LCLS facility.

        This class implements OM's Data Retrieval Layer for the CXI beamline of the
        LCLS facility, using the Jungfrau 4M x-ray detector. The Jungfrau 4M is
        currently the main detector used at the CXI beamline.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        * This class considers an individual data event as equivalent to the content of
          a psana event, which stores data related to a single detector frame.

        * A string combining psana's timestamp and fiducial information, with the
          following format:
          `{timestamp: seconds}-{timestamp: nanoseconds}-{fiducials}`, is used as event
          identifier.

        * Psana provides timestamp, beam energy and detector distance information for
          each event, retrieved from various sensors in the system.

        * The source string required by this Data Retrieval class is a string of the
          type used by psana to identify specific runs, experiments, or live data
          streams.

        Arguments:

            monitor_parameters: An object storing OM's configuration parameters.

            source: A string describing the data event source.
        """
        data_sources: Dict[str, OmDataSourceProtocol] = {
            "timestamp": TimestampPsana(
                data_source_name="timestamp", monitor_parameters=monitor_parameters
            ),
            "event_id": EventIdPsana(
                data_source_name="eventid", monitor_parameters=monitor_parameters
            ),
            "detector_data": Jungfrau4MPsana(
                data_source_name="detector", monitor_parameters=monitor_parameters
            ),
            "beam_energy": BeamEnergyFromEpicsVariablePsana(
                data_source_name="beam_energy", monitor_parameters=monitor_parameters
            ),
            "detector_distance": EpicsVariablePsana(
                data_source_name="detector_distance",
                monitor_parameters=monitor_parameters,
            ),
            "timetool_data": EpicsVariablePsana(
                data_source_name="timetool", monitor_parameters=monitor_parameters
            ),
            "optical_laser_active": EvrCodesPsana(
                data_source_name="active_optical_laser",
                monitor_parameters=monitor_parameters,
            ),
            "xrays_active": EvrCodesPsana(
                data_source_name="active_xrays",
                monitor_parameters=monitor_parameters,
            ),
            "post_sample_intensity": DiodeTotalIntensityPsana(
                data_source_name="post_sample_intensity",
                monitor_parameters=monitor_parameters,
            ),
            "lcls_extra": LclsExtraPsana(
                data_source_name="lcls_extra",
                monitor_parameters=monitor_parameters,
            ),
        }

        self._data_event_handler: OmDataEventHandlerProtocol = PsanaDataEventHandler(
            source=source,
            monitor_parameters=monitor_parameters,
            data_sources=data_sources,
        )

    def get_data_event_handler(self) -> OmDataEventHandlerProtocol:
        """
        Retrieves the Data Event Handler used by the Data Retrieval class.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Returns:

            The Data Event Handler used by the Data Retrieval class.
        """
        return self._data_event_handler


class CxiLclsCspadDataRetrieval(OmDataRetrievalProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(self, *, monitor_parameters: MonitorParameters, source: str):
        """
        Data Retrieval from psana at the CXI beamline of the LCLS facility (CSPAD).

        This class implements OM's Data Retrieval Layer for the CXI beamline of the
        LCLS facility, using the CSPAD x-ray detector. This detector was used at the
        beamline until early 2020.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        * This class considers an individual data event as equivalent to the content of
          a psana event, which stores data related to a single detector frame.

        * A string combining psana's timestamp and fiducial information, with the
          following format:
          `{timestamp: seconds}-{timestamp: nanoseconds}-{fiducials}`, is used as event
          identifier.

        * Psana provides timestamp, beam energy and detector distance data for each
          event, retrieved from various sensors in the system.

        * The source string required by this Data Retrieval class is a string of the
          type used by psana to identify specific runs, experiments, or live data
          streams.

        Arguments:

            monitor_parameters: An object OM's configuration parameters.

            source: A string describing the data event source.
        """
        data_sources: Dict[str, OmDataSourceProtocol] = {
            "timestamp": TimestampPsana(
                data_source_name="timestamp", monitor_parameters=monitor_parameters
            ),
            "event_id": EventIdPsana(
                data_source_name="eventid", monitor_parameters=monitor_parameters
            ),
            "detector_data": CspadPsana(
                data_source_name="detector", monitor_parameters=monitor_parameters
            ),
            "beam_energy": BeamEnergyPsana(
                data_source_name="beam_energy", monitor_parameters=monitor_parameters
            ),
            "detector_distance": EpicsVariablePsana(
                data_source_name="detector_distance",
                monitor_parameters=monitor_parameters,
            ),
            "timetool_data": EpicsVariablePsana(
                data_source_name="timetool", monitor_parameters=monitor_parameters
            ),
            "optical_laser_active": EvrCodesPsana(
                data_source_name="active_optical_laser",
                monitor_parameters=monitor_parameters,
            ),
            "xrays_active": EvrCodesPsana(
                data_source_name="active_xrays",
                monitor_parameters=monitor_parameters,
            ),
            "lcls_extra": LclsExtraPsana(
                data_source_name="lcls_extra",
                monitor_parameters=monitor_parameters,
            ),
        }

        self._data_event_handler: OmDataEventHandlerProtocol = PsanaDataEventHandler(
            source=source,
            monitor_parameters=monitor_parameters,
            data_sources=data_sources,
        )

    def get_data_event_handler(self) -> OmDataEventHandlerProtocol:
        """
        Retrieves the Data Event Handler used by the Data Retrieval class.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Returns:

            The Data Event Handler used by the Data Retrieval class.
        """
        return self._data_event_handler


class LclsEpix100DataRetrieval(OmDataRetrievalProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(self, *, monitor_parameters: MonitorParameters, source: str):
        """
        Data Retrieval from psana at the CXI beamline of the LCLS facility (ePix100).

        This class implements OM's Data Retrieval Layer for the CXI beamline of the
        LCLS facility, using the ePix100 x-ray detector. This detector is often used
        to record beam energy spectrum information in X-ray Emission Spectroscopy
        experiments.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        * This class considers an individual data event as equivalent to the content of
          a psana event, which stores data related to a single detector frame.

        * A string combining psana's timestamp and fiducial information, with the
          following format:
          `{timestamp: seconds}-{timestamp: nanoseconds}-{fiducials}`, is used as event
          identifier.

        * Psana provides timestamp, beam energy and detector distance data for each
          event, retrieved from various sensors in the system.

        * The source string required by this Data Retrieval class is a string of the
          type used by psana to identify specific runs, experiments, or live data
          streams.

        Arguments:

            monitor_parameters: An object storing OM's configuration
            source: A string describing the data event source.
        """
        data_sources: Dict[str, OmDataSourceProtocol] = {
            "timestamp": TimestampPsana(
                data_source_name="timestamp", monitor_parameters=monitor_parameters
            ),
            "event_id": EventIdPsana(
                data_source_name="eventid", monitor_parameters=monitor_parameters
            ),
            "detector_data": Epix100Psana(
                data_source_name="detector", monitor_parameters=monitor_parameters
            ),
            "beam_energy": BeamEnergyPsana(
                data_source_name="beam_energy", monitor_parameters=monitor_parameters
            ),
            "detector_distance": EpicsVariablePsana(
                data_source_name="detector_distance",
                monitor_parameters=monitor_parameters,
            ),
            "timetool_data": EpicsVariablePsana(
                data_source_name="timetool", monitor_parameters=monitor_parameters
            ),
            "optical_laser_active": EvrCodesPsana(
                data_source_name="active_optical_laser",
                monitor_parameters=monitor_parameters,
            ),
            "xrays_active": EvrCodesPsana(
                data_source_name="active_xrays",
                monitor_parameters=monitor_parameters,
            ),
            "lcls_extra": LclsExtraPsana(
                data_source_name="lcls_extra",
                monitor_parameters=monitor_parameters,
            ),
        }

        self._data_event_handler: OmDataEventHandlerProtocol = PsanaDataEventHandler(
            source=source,
            monitor_parameters=monitor_parameters,
            data_sources=data_sources,
        )

    def get_data_event_handler(self) -> OmDataEventHandlerProtocol:
        """
        Retrieves the Data Event Handler used by the Data Retrieval class.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Returns:

            The Data Event Handler used by the Data Retrieval class.
        """
        return self._data_event_handler


class MfxLclsDataRetrieval(OmDataRetrievalProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(self, *, monitor_parameters: MonitorParameters, source: str):
        """
        Data Retrieval from psana at the MFX beamline of the LCLS facility.

        This class implements OM's Data Retrieval Layer for the MFX beamline of the
        LCLS facility, using the Epix10KA 2M x-ray detector. The Epix10KA is currently
        the main detector used at the MFX beamline.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        * This class considers an individual data event as equivalent to the content of
          a psana event, which stores data related to a single detector frame.

        * A string combining psana's timestamp and fiducial information, with the
          following format:
          `{timestamp: seconds}-{timestamp: nanoseconds}-{fiducials}`, is used as event
          identifier.

        * Psana provides timestamp, beam energy and detector distance data for each
          event, retrieved from various sensors in the system.

        * The source string required by this Data Retrieval class is a string of the
          type used by psana to identify specific runs, experiments, or live data
          streams.

        Arguments:

            monitor_parameters: An object storing OM's configuration parameters.

            source: A string describing the data event source.
        """
        data_sources: Dict[str, OmDataSourceProtocol] = {
            "timestamp": TimestampPsana(
                data_source_name="timestamp", monitor_parameters=monitor_parameters
            ),
            "event_id": EventIdPsana(
                data_source_name="eventid", monitor_parameters=monitor_parameters
            ),
            "detector_data": Epix10kaPsana(
                data_source_name="detector", monitor_parameters=monitor_parameters
            ),
            "beam_energy": BeamEnergyFromEpicsVariablePsana(
                data_source_name="beam_energy", monitor_parameters=monitor_parameters
            ),
            "detector_distance": EpicsVariablePsana(
                data_source_name="detector_distance",
                monitor_parameters=monitor_parameters,
            ),
            "timetool_data": EpicsVariablePsana(
                data_source_name="timetool", monitor_parameters=monitor_parameters
            ),
            "optical_laser_active": EvrCodesPsana(
                data_source_name="active_optical_laser",
                monitor_parameters=monitor_parameters,
            ),
            "xrays_active": EvrCodesPsana(
                data_source_name="active_xrays",
                monitor_parameters=monitor_parameters,
            ),
            "lcls_extra": LclsExtraPsana(
                data_source_name="lcls_extra",
                monitor_parameters=monitor_parameters,
            ),
        }

        self._data_event_handler: OmDataEventHandlerProtocol = PsanaDataEventHandler(
            source=source,
            monitor_parameters=monitor_parameters,
            data_sources=data_sources,
        )

    def get_data_event_handler(self) -> OmDataEventHandlerProtocol:
        """
        Retrieves the Data Event Handler used by the Data Retrieval class.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Returns:

            The Data Event Handler used by the Data Retrieval class.
        """
        return self._data_event_handler


class MfxLclsRayonixDataRetrieval(OmDataRetrievalProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(self, *, monitor_parameters: MonitorParameters, source: str):
        """
        Data Retrieval from psana at MFX beamline of the LCLS facility (Rayonix).

        This class implements OM's Data Retrieval Layer for the MFX beamline of the
        LCLS facility, using the Rayonix x-ray detector.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        * This class considers an individual data event as equivalent to the content of
          a psana event, which stores data related to a single detector frame.

        * A string combining psana's timestamp and fiducial information, with the
          following format:
          `{timestamp: seconds}-{timestamp: nanoseconds}-{fiducials}`, is used as event
          identifier.

        * Psana provides timestamp, beam energy and detector distance data for each
          event, retrieved from various sensors in the system.

        * The source string required by this Data Retrieval class is a string of the
          type used by psana to identify specific runs, experiments, or live data
          streams.

        Arguments:

            monitor_parameters: An object storing OM's configuration parameters.

            source: A string describing the data event source.
        """
        data_sources: Dict[str, OmDataSourceProtocol] = {
            "timestamp": TimestampPsana(
                data_source_name="timestamp", monitor_parameters=monitor_parameters
            ),
            "event_id": EventIdPsana(
                data_source_name="eventid", monitor_parameters=monitor_parameters
            ),
            "detector_data": RayonixPsana(
                data_source_name="detector", monitor_parameters=monitor_parameters
            ),
            "beam_energy": BeamEnergyPsana(
                data_source_name="beam_energy", monitor_parameters=monitor_parameters
            ),
            "detector_distance": EpicsVariablePsana(
                data_source_name="detector_distance",
                monitor_parameters=monitor_parameters,
            ),
            "timetool_data": EpicsVariablePsana(
                data_source_name="timetool", monitor_parameters=monitor_parameters
            ),
            "optical_laser_active": EvrCodesPsana(
                data_source_name="active_optical_laser",
                monitor_parameters=monitor_parameters,
            ),
            "xrays_active": EvrCodesPsana(
                data_source_name="active_xrays",
                monitor_parameters=monitor_parameters,
            ),
            "lcls_extra": LclsExtraPsana(
                data_source_name="lcls_extra",
                monitor_parameters=monitor_parameters,
            ),
        }

        self._data_event_handler: OmDataEventHandlerProtocol = PsanaDataEventHandler(
            source=source,
            monitor_parameters=monitor_parameters,
            data_sources=data_sources,
        )

    def get_data_event_handler(self) -> OmDataEventHandlerProtocol:
        """
        Retrieves the Data Event Handler used by the Data Retrieval class.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Returns:

            The Data Event Handler used by the Data Retrieval class.
        """
        return self._data_event_handler
