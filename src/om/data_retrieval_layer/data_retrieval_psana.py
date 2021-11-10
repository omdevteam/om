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
Retrieval and handling of data from psana.

This module contains Data Event Handlers And Data Retrieval classes that deal with data
retrieved from the psana software framework (used at the LCLS facility).
"""
import sys
from typing import Any, Dict, Generator, List, Union

import numpy  # type: ignore

from om.data_retrieval_layer import base as drl_base
from om.data_retrieval_layer import data_sources_generic as ds_generic
from om.data_retrieval_layer import data_sources_psana as ds_psana
from om.utils import exceptions, parameters

try:
    import psana  # type: ignore
except ImportError:
    raise exceptions.OmMissingDependencyError(
        "The following required module cannot be imported: psana"
    )


def _psana_offline_event_generator(
    *, psana_source: Any, node_rank: int, mpi_pool_size: int
) -> Any:
    # Computes how many events the current processing node should process. Splits the
    # events as equally as possible amongst the processing nodes. If the number of
    # events cannot be exactly divided by the number of processing nodes, an additional
    # processing node is assigned the residual events.
    run: Any
    for run in psana_source.runs():
        times: Any = run.times()
        num_events_curr_node: int = int(
            numpy.ceil(len(times) / float(mpi_pool_size - 1))
        )
        events_curr_node: Any = times[
            (node_rank - 1) * num_events_curr_node : node_rank * num_events_curr_node
        ]
        evt: Any
        for evt in events_curr_node:

            yield run.event(evt)


class _PsanaDataEventHandler(drl_base.OmDataEventHandler):
    """
    See documentation of the `__init__` function.

    Base class: [`OmDataEventHandler`][om.data_retrieval_layer.base.OmDataEventHandler]
    """

    def __init__(
        self,
        *,
        source: str,
        data_sources: Dict[str, drl_base.OmDataSource],
        monitor_parameters: parameters.MonitorParams,
    ) -> None:
        """
        Data Event Handler for psana events.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class handles data events retrieved from the psana software framework at
        the LCLS facility. It is a subclass of the
        [OmDataEventHandler][om.data_retrieval_layer.base.OmDataEventHandler] class.

        The source string for this Data Event Handler is a string of the type used by
        psana to identify specific runs, experiments, or live data streams.

        Arguments:

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.

            source: A string describing the data source.
        """

        self._source: str = source
        self._monitor_params: parameters.MonitorParams = monitor_parameters
        self._data_sources: Dict[str, drl_base.OmDataSource] = data_sources

    def initialize_event_handling_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> Any:
        """
        Initializes psana event handling on the collecting node.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        The psana data source does not need to be initialized on the collecting node,
        so this function actually does nothing.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        Returns:

            An optional initialization token.
        """
        pass

    def initialize_event_handling_on_processing_node(
        self, node_rank: int, node_pool_size: int
    ) -> Any:
        """
        Initializes psana event handling on the processing nodes.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        Returns:

            An optional initialization token.
        """
        required_data: List[str] = self._monitor_params.get_parameter(
            group="data_retrieval_layer",
            parameter="required_data",
            parameter_type=list,
            required=True,
        )

        self._required_data_sources = drl_base.filter_data_sources(
            data_sources=self._data_sources,
            required_data=required_data,
        )

        lcls_extra_entry: List[List[str]] = self._monitor_params.get_parameter(
            group="data_retrieval_layer",
            parameter="lcls_extra",
            parameter_type=list,
        )

        if lcls_extra_entry:
            self._lcls_extra: Union[Dict[str, Any], None] = {}

            data_item: list[str]
            for data_item in lcls_extra_entry:
                if not isinstance(data_item, list) or len(data_item) != 3:
                    raise exceptions.OmWrongParameterTypeError(
                        "The 'lcls_extra' entry of the 'data_retrieval_layer' group "
                        "in the configuration file is not formatted correctly."
                    )
                for entry in data_item:
                    if not isinstance(entry, str):
                        raise exceptions.OmWrongParameterTypeError(
                            "The 'lcls_extra' entry of the 'data_retrieval_layer' "
                            "group in the configuration file is not formatted "
                            "correctly."
                        )
                    identifier: str
                    name: str
                    data_type, identifier, name = data_item
                    if data_type == "acqiris_waveform":
                        self._lcls_extra[name] = ds_psana.AcqirisDetector(
                            data_source_name=f"psana-{identifier}",
                            monitor_parameters=self._monitor_params,
                        )
                    elif data_type == "epics_pv":
                        self._lcls_extra[name] = ds_psana.EpicsVariablePsana(
                            data_source_name=f"psana-{identifier}",
                            monitor_parameters=self._monitor_params,
                        )
                    elif data_type == "wave8_total_intensity":
                        self._lcls_extra[name] = ds_psana.Wave8Detector(
                            data_source_name=f"psana-{identifier}",
                            monitor_parameters=self._monitor_params,
                        )
                    else:
                        raise exceptions.OmWrongParameterTypeError(
                            "The requested '{}' LCLS-specific data type is not "
                            "supported.".format(data_type)
                        )
        else:
            self._lcls_extra = None

    def event_generator(
        self,
        *,
        node_rank: int,
        node_pool_size: int,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Retrieves psana events.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        When OM runs in shared memory mode (the usual way to retrieve real-time data at
        the LCLS facility), each processing node retrieves data from a shared memory
        server operated by the facility. The memory server must be running on the same
        machine as the processing node. When instead OM uses the psana framework to
        read offline data, this Data Event Handler distributes the data events as
        evenly as possible across all the processing nodes. Each node ideally
        retrieves the same number of events from psana. Only the last node might
        retrieve fewer events, depending on how evenly the total number can be split.

        Each retrieved psana event contains a single detector frame, along with all the
        data whose timestamp matches the timestamp of the frame. This is also true for
        data that is is updated at a slower rate than the frame itself. For this kind
        of  data, the last reported value at the time the frame is collected is
        associated with it.

        This generator function yields a dictionary storing the data for the current
        event.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        # TODO: Check types of Generator
        # Detects if data is being read from an online or offline source.
        if "shmem" in self._source:
            offline: bool = False
        else:
            offline = True
        if offline and not self._source[-4:] == ":idx":
            self._source += ":idx"

        # If the psana calibration directory is provided in the configuration file, it
        # is added as an option to psana before the DataSource is set.
        psana_calib_dir: str = self._monitor_params.get_parameter(
            group="data_retrieval_layer",
            parameter="psana_calibration_directory",
            parameter_type=str,
        )
        if psana_calib_dir is not None:
            psana.setOption("psana.calib-dir", psana_calib_dir)
        else:
            print("OM Warning: Calibration directory not provided or not found.")

        psana_source = psana.DataSource(self._source)

        self._data_sources["timestamp"].initialize_data_source()
        source_name: str
        for source_name in self._required_data_sources:
            self._data_sources[source_name].initialize_data_source()

        data_event: Dict[str, Dict[str, Any]] = {}
        data_event["additional_info"] = {}

        # Initializes the psana event source and starts retrieving events.
        if offline:
            psana_events: Any = _psana_offline_event_generator(
                psana_source=psana_source,
                node_rank=node_rank,
                mpi_pool_size=node_pool_size,
            )
        else:
            psana_events = psana_source.events()

        psana_event: Any
        for psana_event in psana_events:
            data_event["data"] = psana_event

            # Recovers the timestamp from the psana event (as seconds from the Epoch)
            # and stores it in the event dictionary to be retrieved later.
            data_event["additional_info"]["timestamp"] = self._data_sources[
                "timestamp"
            ].get_data(event=data_event)

            yield data_event

    def open_event(self, *, event: Dict[str, Any]) -> None:
        """
        Opens a psana event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Psana events do not need to be opened, so this function actually does nothing.

        Arguments:

            event: a dictionary storing the event data.
        """
        pass

    def close_event(self, *, event: Dict[str, Any]) -> None:
        """
        Closes a psana event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Psana events do not need to be closed, so this function actually does nothing.

        Arguments:

            event: a dictionary storing the event data.
        """
        pass

    def get_num_frames_in_event(self, *, event: Dict[str, Any]) -> int:
        """
        Gets the number of frames in a psana event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Each psana event stores data associated with a single detector frame, so this
        function always returns 1.

        Arguments:

            event: a dictionary storing the event data.

        Returns:

            int: the number of frames in the event.
        """
        return 1

    def extract_data(
        self,
        *,
        event: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extracts data from a psana data event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A dictionary storing the data returned by the Data Extraction Functions.

            * Each dictionary key identifies the Data Extraction Function used to
              extract the data.

            * The corresponding dictionary value stores the data returned by the
              function.
        """
        data: Dict[str, Any] = {}
        f_name: str
        data["timestamp"] = event["additional_info"]["timestamp"]
        for source_name in self._required_data_sources:
            try:
                data[source_name] = self._data_sources[source_name].get_data(
                    event=event
                )
            # One should never do the following, but it is not possible to anticipate
            # every possible error raised by the facility frameworks.
            except Exception:
                exc_type, exc_value = sys.exc_info()[:2]
                if exc_type is not None:
                    raise exceptions.OmDataExtractionError(
                        f"OM Warning: Cannot interpret {source_name} event data due "
                        "to the following error: {exc_type.__name__}: {exc_value}"
                    )

        if self._lcls_extra:
            data["lcls_extra"] = {}
            name: str
            for name in self._lcls_extra:
                data["lcls_extra"][name] = self._lcls_extra[name].get_data(event)

        return data


class CxiLclsDataRetrieval(drl_base.OmDataRetrieval):
    """
    See documentation of the `__init__` function.

    Base class: [`OmDataRetrieval`][om.data_retrieval_layer.base.OmDataRetrieval]
    """

    def __init__(self, *, monitor_parameters: parameters.MonitorParams, source: str):
        """
        Data Retrieval from psana at the CXI beamline (LCLS).

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class implements the operations needed to retrieve data at the CXI
        beamline of the LCLS facility, using the Jungfrau 4M x-ray detector, currently
        the main detector used at the CXI beamline.

        This class considers an individual data event as equivalent to the content of a
        psana event, which stores data related to a single detector frame. Psana
        provides timestamp, beam energy and detector distance data for each event,
        retrieved from various sensors in the system.

        The source string for this Data Retrieval class is a string of the type used by
        psana to identify specific runs, experiments, or live data streams.

        Arguments:

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.

            source: A string describing the data source.
        """
        data_sources: Dict[str, drl_base.OmDataSource] = {
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
            # "lcls_extra": functions_psana.lcls_extra,
        }

        self._data_event_handler: drl_base.OmDataEventHandler = _PsanaDataEventHandler(
            source=source,
            monitor_parameters=monitor_parameters,
            data_sources=data_sources,
        )

    @property
    def data_event_handler(self) -> drl_base.OmDataEventHandler:
        return self._data_event_handler


class CxiLclsCspadDataRetrieval(drl_base.OmDataRetrieval):
    """
    See documentation of the `__init__` function.

    Base class: [`OmDataRetrieval`][om.data_retrieval_layer.base.OmDataRetrieval]
    """

    def __init__(self, *, monitor_parameters: parameters.MonitorParams, source: str):
        """
        Data Retrieval from psana at the CXI beamline (LCLS), with the CSPAD detector.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class implements the operations needed to retrieve data at the CXI
        beamline of the LCLS facility, using the CSPAD x-ray detector. This detector
        was used at the beamline until early 2020.

        This class considers an individual data event as equivalent to the content of a
        psana event, which stores data related to a single detector frame. Psana
        provides timestamp, beam energy and detector distance data for each event,
        retrieved from various sensors in the system.

        The source string for this Data Retrieval class is a string of the type used by
        psana to identify specific runs, experiments, or live data streams.

        Arguments:

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.

            source: A string describing the data source.
        """
        data_sources: Dict[str, drl_base.OmDataSource] = {
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
            # "lcls_extra": functions_psana.lcls_extra,
        }

        self._data_event_handler: drl_base.OmDataEventHandler = _PsanaDataEventHandler(
            source=source,
            monitor_parameters=monitor_parameters,
            data_sources=data_sources,
        )

    @property
    def data_event_handler(self) -> drl_base.OmDataEventHandler:
        return self._data_event_handler


class CxiLclsEpix100DataRetrieval(drl_base.OmDataRetrieval):
    """
    See documentation of the `__init__` function.

    Base class: [`OmDataRetrieval`][om.data_retrieval_layer.base.OmDataRetrieval]
    """

    def __init__(self, *, monitor_parameters: parameters.MonitorParams, source: str):
        """
        Data Retrieval from psana at the CXI beamline (LCLS), with the ePix100 detector.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class implements the operations needed to retrieve data at the CXI
        beamline of the LCLS facility, using the ePix100 x-ray detector. This detector
        is often used for XES experiments.

        This class considers an individual data event as equivalent to the content of a
        psana event, which stores data related to a single detector frame. Psana
        provides timestamp, beam energy and detector distance data for each event,
        retrieved from various sensors in the system.

        The source string for this Data Retrieval class is a string of the type used by
        psana to identify specific runs, experiments, or live data streams.

        Arguments:

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.

            source: A string describing the data source.
        """
        data_sources: Dict[str, drl_base.OmDataSource] = {
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
            # "lcls_extra": functions_psana.lcls_extra,
        }

        self._data_event_handler: drl_base.OmDataEventHandler = _PsanaDataEventHandler(
            source=source,
            monitor_parameters=monitor_parameters,
            data_sources=data_sources,
        )

    @property
    def data_event_handler(self) -> drl_base.OmDataEventHandler:
        return self._data_event_handler


class MfxLclsDataRetrieval(drl_base.OmDataRetrieval):
    """
    See documentation of the `__init__` function.

    Base class: [`OmDataRetrieval`][om.data_retrieval_layer.base.OmDataRetrieval]
    """

    def __init__(self, *, monitor_parameters: parameters.MonitorParams, source: str):
        """
        Data Retrieval from psana at the MFX beamline (LCLS).

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class implements the operations needed to retrieve data at the MFX
        beamline of the LCLS facility using the Epix10KA 2M x-ray-detector, currently
        the main detector used at the MFX beamline.

        This class considers an individual data event as equivalent to the content of a
        psana event, which stores data related to a single detector frame. Psana
        provides timestamp, beam energy and detector distance data for each event,
        retrieved from various sensors in the system.

        The source string for this Data Retrieval class is a string of the type used by
        psana to identify specific runs, experiments, or live data streams.

        Arguments:

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.

            source: A string describing the data source.
        """
        data_sources: Dict[str, drl_base.OmDataSource] = {
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
            # "lcls_extra": functions_psana.lcls_extra,
        }

        self._data_event_handler: drl_base.OmDataEventHandler = _PsanaDataEventHandler(
            source=source,
            monitor_parameters=monitor_parameters,
            data_sources=data_sources,
        )

    @property
    def data_event_handler(self) -> drl_base.OmDataEventHandler:
        return self._data_event_handler


class MfxLclsRayonixDataRetrieval(drl_base.OmDataRetrieval):
    """
    See documentation of the `__init__` function.

    Base class: [`OmDataRetrieval`][om.data_retrieval_layer.base.OmDataRetrieval]
    """

    def __init__(self, *, monitor_parameters: parameters.MonitorParams, source: str):
        """
        Data Retrieval for events retrieved from psana at MFX (LCLS) with Rayonix.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class implements the operations needed to retrieve data at the MFX
        beamline of the LCLS facility using the Rayonix x-ray detector.

        This class considers an individual data event as equivalent to the content of a
        psana event, which stores data related to a single detector frame. Psana
        provides timestamp, beam energy and detector distance data for each event,
        retrieved from various sensors in the system.

        The source string for this Data Retrieval class is a string of the type used by
        psana to identify specific runs, experiments, or live data streams.

        Arguments:

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.

            source: A string describing the data source.
        """
        data_sources: Dict[str, drl_base.OmDataSource] = {
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
            # "lcls_extra": functions_psana.lcls_extra,
        }

        self._data_event_handler: drl_base.OmDataEventHandler = _PsanaDataEventHandler(
            source=source,
            monitor_parameters=monitor_parameters,
            data_sources=data_sources,
        )

    @property
    def data_event_handler(self) -> drl_base.OmDataEventHandler:
        return self._data_event_handler
