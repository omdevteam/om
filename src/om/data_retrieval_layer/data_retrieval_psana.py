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
Retrieval of data from psana.

This module contains Data Retrieval classes that deal with the psana software framework
(used at the LCLS facility).
"""
from typing import Dict

from om.protocols import data_extraction_layer as drl_protocols
from om.data_retrieval_layer import data_event_handlers_psana as deh_psana
from om.data_retrieval_layer import data_sources_generic as ds_generic
from om.data_retrieval_layer import data_sources_psana as ds_psana
from om.utils import parameters


class CxiLclsDataRetrieval(drl_protocols.OmDataRetrieval):
    """
    See documentation of the `__init__` function.
    """

    def __init__(self, *, monitor_parameters: parameters.MonitorParams, source: str):
        """
        Data Retrieval from psana at the CXI beamline (LCLS).

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class implements OM's Data Retrieval Layer for the CXI beamline of the
        LCLS facility, using the Jungfrau 4M x-ray detector, currently the main
        detector used at this beamline.

        * This class considers an individual data event as equivalent to the content of
          a psana event, which stores data related to a single detector frame.

        * Psana provides timestamp, beam energy and detector distance information for
          each event, retrieved from various sensors in the system.

        * The source string required by this Data Retrieval class is a string of the
          type used by psana to identify specific runs, experiments, or live data
          streams.

        Arguments:

            monitor_parameters: An object storing OM's configuration parameters.
            source: A string describing the data event source.
        """
        data_sources: Dict[str, drl_protocols.OmDataSource] = {
            "timestamp": ds_psana.TimestampPsana(
                data_source_name="timestamp", monitor_parameters=monitor_parameters
            ),
            "event_id": ds_psana.EventIdPsana(
                data_source_name="eventid", monitor_parameters=monitor_parameters
            ),
            "frame_id": ds_generic.FrameIdZero(
                data_source_name="frameid", monitor_parameters=monitor_parameters
            ),
            "detector_data": ds_psana.Jungfrau4MPsana(
                data_source_name="detector", monitor_parameters=monitor_parameters
            ),
            "beam_energy": ds_psana.BeamEnergyPsana(
                data_source_name="beam_energy", monitor_parameters=monitor_parameters
            ),
            "detector_distance": ds_psana.EpicsVariablePsana(
                data_source_name="detector_distance",
                monitor_parameters=monitor_parameters,
            ),
            "timetool_data": ds_psana.EpicsVariablePsana(
                data_source_name="timetool", monitor_parameters=monitor_parameters
            ),
            "optical_laser_active": ds_psana.EvrCodesPsana(
                data_source_name="active_optical_laser",
                monitor_parameters=monitor_parameters,
            ),
            "xrays_active": ds_psana.EvrCodesPsana(
                data_source_name="active_optical_laser",
                monitor_parameters=monitor_parameters,
            ),
            "lcls_extra": ds_psana.LclsExtraPsana(
                data_source_name="lcls_extra",
                monitor_parameters=monitor_parameters,
            ),
        }

        self._data_event_handler: drl_protocols.OmDataEventHandler = (
            deh_psana.PsanaDataEventHandler(
                source=source,
                monitor_parameters=monitor_parameters,
                data_sources=data_sources,
            )
        )

    def get_data_event_handler(self) -> drl_protocols.OmDataEventHandler:
        """
        Retrieves the Data Event Handler used by the class.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Returns:

            The Data Event Handler used by the Data Retrieval class.
        """
        return self._data_event_handler


class CxiLclsCspadDataRetrieval(drl_protocols.OmDataRetrieval):
    """
    See documentation of the `__init__` function.
    """

    def __init__(self, *, monitor_parameters: parameters.MonitorParams, source: str):
        """
        Data Retrieval from psana at the CXI beamline (LCLS), with the CSPAD detector.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class implements OM's Data Retrieval Layer for the CXI beamline of the
        LCLS facility, using the CSPAD x-ray detector. This detector was used at the
        beamline until early 2020.

        * This class considers an individual data event as equivalent to the content of
          a psana event, which stores data related to a single detector frame.

        * Psana provides timestamp, beam energy and detector distance data for each
          event, retrieved from various sensors in the system.

        * The source string required by this Data Retrieval class is a string of the
          type used by psana to identify specific runs, experiments, or live data
          streams.

        Arguments:

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.

            source: A string describing the data event source.
        """
        data_sources: Dict[str, drl_protocols.OmDataSource] = {
            "timestamp": ds_psana.TimestampPsana(
                data_source_name="timestamp", monitor_parameters=monitor_parameters
            ),
            "event_id": ds_psana.EventIdPsana(
                data_source_name="eventid", monitor_parameters=monitor_parameters
            ),
            "frame_id": ds_generic.FrameIdZero(
                data_source_name="frameid", monitor_parameters=monitor_parameters
            ),
            "detector_data": ds_psana.CspadPsana(
                data_source_name="detector", monitor_parameters=monitor_parameters
            ),
            "beam_energy": ds_psana.BeamEnergyPsana(
                data_source_name="beam_energy", monitor_parameters=monitor_parameters
            ),
            "detector_distance": ds_psana.EpicsVariablePsana(
                data_source_name="detector_distance",
                monitor_parameters=monitor_parameters,
            ),
            "timetool_data": ds_psana.EpicsVariablePsana(
                data_source_name="timetool", monitor_parameters=monitor_parameters
            ),
            "optical_laser_active": ds_psana.EvrCodesPsana(
                data_source_name="active_optical_laser",
                monitor_parameters=monitor_parameters,
            ),
            "xrays_active": ds_psana.EvrCodesPsana(
                data_source_name="active_optical_laser",
                monitor_parameters=monitor_parameters,
            ),
            "lcls_extra": ds_psana.LclsExtraPsana(
                data_source_name="lcls_extra",
                monitor_parameters=monitor_parameters,
            ),
        }

        self._data_event_handler: drl_protocols.OmDataEventHandler = (
            deh_psana.PsanaDataEventHandler(
                source=source,
                monitor_parameters=monitor_parameters,
                data_sources=data_sources,
            )
        )

    def get_data_event_handler(self) -> drl_protocols.OmDataEventHandler:
        """
        Retrieves the Data Event Handler used by the class.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Returns:

            The Data Event Handler used by the Data Retrieval class.
        """
        return self._data_event_handler


class CxiLclsEpix100DataRetrieval(drl_protocols.OmDataRetrieval):
    """
    See documentation of the `__init__` function.
    """

    def __init__(self, *, monitor_parameters: parameters.MonitorParams, source: str):
        """
        Data Retrieval from psana at the CXI beamline (LCLS), with the ePix100 detector.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class implements OM's Data Retrieval Layer for the CXI beamline of the
        LCLS facility, using the ePix100 x-ray detector. This detector is often used
        to record beam energy spectrum information in XES experiments.

        * This class considers an individual data event as equivalent to the content of
          a psana event, which stores data related to a single detector frame.

        * Psana provides timestamp, beam energy and detector distance data for each
          event, retrieved from various sensors in the system.

        * The source string required by this Data Retrieval class is a string of the
          type used by psana to identify specific runs, experiments, or live data
          streams.

        Arguments:

            monitor_parameters: An object storing OM's configuration parameters.
            source: A string describing the data event source.
        """
        data_sources: Dict[str, drl_protocols.OmDataSource] = {
            "timestamp": ds_psana.TimestampPsana(
                data_source_name="timestamp", monitor_parameters=monitor_parameters
            ),
            "event_id": ds_psana.EventIdPsana(
                data_source_name="eventid", monitor_parameters=monitor_parameters
            ),
            "frame_id": ds_generic.FrameIdZero(
                data_source_name="frameid", monitor_parameters=monitor_parameters
            ),
            "detector_data": ds_psana.Epix100Psana(
                data_source_name="detector", monitor_parameters=monitor_parameters
            ),
            "beam_energy": ds_psana.BeamEnergyPsana(
                data_source_name="beam_energy", monitor_parameters=monitor_parameters
            ),
            "detector_distance": ds_psana.EpicsVariablePsana(
                data_source_name="detector_distance",
                monitor_parameters=monitor_parameters,
            ),
            "timetool_data": ds_psana.EpicsVariablePsana(
                data_source_name="timetool", monitor_parameters=monitor_parameters
            ),
            "optical_laser_active": ds_psana.EvrCodesPsana(
                data_source_name="active_optical_laser",
                monitor_parameters=monitor_parameters,
            ),
            "xrays_active": ds_psana.EvrCodesPsana(
                data_source_name="active_optical_laser",
                monitor_parameters=monitor_parameters,
            ),
            "lcls_extra": ds_psana.LclsExtraPsana(
                data_source_name="lcls_extra",
                monitor_parameters=monitor_parameters,
            ),
        }

        self._data_event_handler: drl_protocols.OmDataEventHandler = (
            deh_psana.PsanaDataEventHandler(
                source=source,
                monitor_parameters=monitor_parameters,
                data_sources=data_sources,
            )
        )

    def get_data_event_handler(self) -> drl_protocols.OmDataEventHandler:
        """
        Retrieves the Data Event Handler used by the class.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Returns:

            The Data Event Handler used by the Data Retrieval class.
        """
        return self._data_event_handler


class MfxLclsDataRetrieval(drl_protocols.OmDataRetrieval):
    """
    See documentation of the `__init__` function.
    """

    def __init__(self, *, monitor_parameters: parameters.MonitorParams, source: str):
        """
        Data Retrieval from psana at the MFX beamline (LCLS).

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class implements OM's Data Retrieval Layer for the MFX beamline of the
        LCLS facility, using the Epix10KA 2M x-ray detector, currently the main
        detector used at this beamline.

        * This class considers an individual data event as equivalent to the content of
          a psana event, which stores data related to a single detector frame.

        * Psana provides timestamp, beam energy and detector distance data for each
          event, retrieved from various sensors in the system.

        * The source string required by this Data Retrieval class is a string of the
          type used by psana to identify specific runs, experiments, or live data
          streams.

        Arguments:

            monitor_parameters: An object storing OM's configuration parameters.
            source: A string describing the data event source.
        """
        data_sources: Dict[str, drl_protocols.OmDataSource] = {
            "timestamp": ds_psana.TimestampPsana(
                data_source_name="timestamp", monitor_parameters=monitor_parameters
            ),
            "event_id": ds_psana.EventIdPsana(
                data_source_name="eventid", monitor_parameters=monitor_parameters
            ),
            "frame_id": ds_generic.FrameIdZero(
                data_source_name="frameid", monitor_parameters=monitor_parameters
            ),
            "detector_data": ds_psana.Epix10kaPsana(
                data_source_name="detector", monitor_parameters=monitor_parameters
            ),
            "beam_energy": ds_psana.BeamEnergyPsana(
                data_source_name="beam_energy", monitor_parameters=monitor_parameters
            ),
            "detector_distance": ds_psana.EpicsVariablePsana(
                data_source_name="detector_distance",
                monitor_parameters=monitor_parameters,
            ),
            "timetool_data": ds_psana.EpicsVariablePsana(
                data_source_name="timetool", monitor_parameters=monitor_parameters
            ),
            "optical_laser_active": ds_psana.EvrCodesPsana(
                data_source_name="active_optical_laser",
                monitor_parameters=monitor_parameters,
            ),
            "xrays_active": ds_psana.EvrCodesPsana(
                data_source_name="active_optical_laser",
                monitor_parameters=monitor_parameters,
            ),
            "lcls_extra": ds_psana.LclsExtraPsana(
                data_source_name="lcls_extra",
                monitor_parameters=monitor_parameters,
            ),
        }

        self._data_event_handler: drl_protocols.OmDataEventHandler = (
            deh_psana.PsanaDataEventHandler(
                source=source,
                monitor_parameters=monitor_parameters,
                data_sources=data_sources,
            )
        )

    def get_data_event_handler(self) -> drl_protocols.OmDataEventHandler:
        """
        Retrieves the Data Event Handler used by the class.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Returns:

            The Data Event Handler used by the Data Retrieval class.
        """
        return self._data_event_handler


class MfxLclsRayonixDataRetrieval(drl_protocols.OmDataRetrieval):
    """
    See documentation of the `__init__` function.
    """

    def __init__(self, *, monitor_parameters: parameters.MonitorParams, source: str):
        """
        Data Retrieval for events retrieved from psana at MFX (LCLS) with Rayonix.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class implements OM's Data Retrieval Layer for the MFX beamline of the
        LCLS facility, using the Rayonix x-ray detector.

        * This class considers an individual data event as equivalent to the content of
          a psana event, which stores data related to a single detector frame.

        * Psana provides timestamp, beam energy and detector distance data for each
          event, retrieved from various sensors in the system.

        * The source string required by this Data Retrieval class is a string of the
          type used by psana to identify specific runs, experiments, or live data
          streams.

        Arguments:

            monitor_parameters: An object storing OM's configuration parameters.
            source: A string describing the data event source.
        """
        data_sources: Dict[str, drl_protocols.OmDataSource] = {
            "timestamp": ds_psana.TimestampPsana(
                data_source_name="timestamp", monitor_parameters=monitor_parameters
            ),
            "event_id": ds_psana.EventIdPsana(
                data_source_name="eventid", monitor_parameters=monitor_parameters
            ),
            "frame_id": ds_generic.FrameIdZero(
                data_source_name="frameid", monitor_parameters=monitor_parameters
            ),
            "detector_data": ds_psana.RayonixPsana(
                data_source_name="detector", monitor_parameters=monitor_parameters
            ),
            "beam_energy": ds_psana.BeamEnergyPsana(
                data_source_name="beam_energy", monitor_parameters=monitor_parameters
            ),
            "detector_distance": ds_psana.EpicsVariablePsana(
                data_source_name="detector_distance",
                monitor_parameters=monitor_parameters,
            ),
            "timetool_data": ds_psana.EpicsVariablePsana(
                data_source_name="timetool", monitor_parameters=monitor_parameters
            ),
            "optical_laser_active": ds_psana.EvrCodesPsana(
                data_source_name="active_optical_laser",
                monitor_parameters=monitor_parameters,
            ),
            "xrays_active": ds_psana.EvrCodesPsana(
                data_source_name="active_optical_laser",
                monitor_parameters=monitor_parameters,
            ),
            "lcls_extra": ds_psana.LclsExtraPsana(
                data_source_name="lcls_extra",
                monitor_parameters=monitor_parameters,
            ),
        }

        self._data_event_handler: drl_protocols.OmDataEventHandler = (
            deh_psana.PsanaDataEventHandler(
                source=source,
                monitor_parameters=monitor_parameters,
                data_sources=data_sources,
            )
        )

    def get_data_event_handler(self) -> drl_protocols.OmDataEventHandler:
        """
        Retrieves the Data Event Handler used by the class.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Returns:

            The Data Event Handler used by the Data Retrieval class.
        """
        return self._data_event_handler
