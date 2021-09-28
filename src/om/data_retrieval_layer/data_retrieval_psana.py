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
Retrieval and handling of data events from psana.

This module contains Data Event Handlers for events retrieved from the psana software
framework (used at the LCLS facility).
"""
import sys
from typing import Any, Dict, Generator, List

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


class _LclsBaseDataEventHandler(drl_base.OmDataEventHandler):
    """
    See documentation of the `__init__` function.

    Base class: [`OmDataEventHandler`][om.data_retrieval_layer.base.OmDataEventHandler]
    """

    def __init__(
        self,
        *,
        source: str,
        data_extraction_functions: Dict[str, drl_base.OmDataSource],
        monitor_parameters: parameters.MonitorParams,
    ) -> None:
        """
        Base Data Event Handler for events recovered from psana at LCLS.

        This is the base class for Data Event Handlers that deal with events retrieved
        from the psana software framework at the LCLS facility. It is a subclass of the
        more generic [OmDataEventHandler]
        [om.data_retrieval_layer.base.OmDataEventHandler] base class and should in turn
        be subclassed to work with specific detectors or beamlines.

        The source string for this Data Event Handler is a string of the type used by
        the psana framework to identify specific runs, experiments, or live data
        streams.

        Arguments:

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.

            source: A string describing the data source.
        """

        self._source: str = source
        self._monitor_params: parameters.MonitorParams = monitor_parameters
        self._data_extraction_functions: Dict[
            str, drl_base.OmDataSource
        ] = data_extraction_functions

    def initialize_event_handling_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> Any:
        """
        Initializes psana event handling on the collecting node.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        The psana data source does not need to be initialized on the collecting node,
        therefore this function actually does nothing.

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

        This function prepares the processing node to retrieve events from psana,
        initializing all the members of the psana Detector interface according to the
        instructions specified in OM's configuration file. Please refer to the
        documentation of the each Detector interface initialization function for a
        description of the relevant configuration parameters.

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

        self._required_data_extraction_funcs = drl_base.filter_data_extraction_funcs(
            data_extraction_funcs=self._data_extraction_functions,
            required_data=required_data,
        )

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
        machine as the processing node.

        When instead OM uses the psana framework to read offline data, this Data Event
        Handler distributes the data events as evenly as possible across all the
        processing nodes. Each node ideally retrieves the same number of events from
        psana. Only the last node might retrieve fewer events, depending on how evenly
        the total number can be split.

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

        func_name: str
        self._data_extraction_functions["timestamp"].initialize_data_source()
        for func_name in self._required_data_extraction_funcs:
            self._data_extraction_functions[func_name].initialize_data_source()

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
            data_event["additional_info"][
                "timestamp"
            ] = self._data_extraction_functions["timestamp"].get_data(event=data_event)

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

        Each psana event stores data related to a single detector frame, so this
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
        Extracts data from a frame stored in an event.

        This function extracts data from a frame stored in an event. It works by
        calling, one after the other, all the Data Extraction Functions associated
        with the event, passing the event itself as input to each of them. The data
        extracted by each function is collected and returned to the caller.

        After retrieving a data event, OM calls this function on each frame in the
        event in sequence. The function is invoked each time on the full event: an
        internal flag keeps track of which frame should be processed in any given call.

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
        for f_name in self._required_data_extraction_funcs:
            try:
                data[f_name] = self._data_extraction_functions[f_name].get_data(
                    event=event
                )
            # One should never do the following, but it is not possible to anticipate
            # every possible error raised by the facility frameworks.
            except Exception:
                exc_type, exc_value = sys.exc_info()[:2]
                if exc_type is not None:
                    raise exceptions.OmDataExtractionError(
                        f"OM Warning: Cannot interpret {f_name} event data due to the "
                        "following error: {exc_type.__name__}: {exc_value}"
                    )

        return data


class CxiLclsCspadDataRetrieval(drl_base.OmDataRetrieval):
    """
    See documentation of the `__init__` function.

    TODO: Docs
    """

    def __init__(self, *, monitor_parameters: parameters.MonitorParams, source: str):
        """
        Data Event Handler for events retrieved from psana at CXI (LCLS).

        TODO: Docs

        Arguments:

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.

            source: A string describing the data source.
        """

        data_extraction_funcs: Dict[str, drl_base.OmDataSource] = {
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

        self._data_event_handler: drl_base.OmDataEventHandler = (
            _LclsBaseDataEventHandler(
                source=source,
                monitor_parameters=monitor_parameters,
                data_extraction_functions=data_extraction_funcs,
            )
        )

    @property
    def data_event_handler(self) -> drl_base.OmDataEventHandler:
        return self._data_event_handler


class CxiLclsDataRetrieval(drl_base.OmDataRetrieval):
    """
    See documentation of the `__init__` function.

    TODO: docs
    """

    def __init__(self, *, monitor_parameters: parameters.MonitorParams, source: str):
        """
        Data Event Handler for events retrieved from psana at CXI with CSPAD (LCLS).

        TODO: Docs

        Arguments:

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.

            source: A string describing the data source.
        """

        data_extraction_funcs: Dict[str, drl_base.OmDataSource] = {
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

        self._data_event_handler: drl_base.OmDataEventHandler = (
            _LclsBaseDataEventHandler(
                source=source,
                monitor_parameters=monitor_parameters,
                data_extraction_functions=data_extraction_funcs,
            )
        )

    @property
    def data_event_handler(self) -> drl_base.OmDataEventHandler:
        return self._data_event_handler


class MfxLclsDataRetrieval(drl_base.OmDataRetrieval):
    """
    See documentation of the `__init__` function.

    TODO: docs
    """

    def __init__(self, *, monitor_parameters: parameters.MonitorParams, source: str):
        """
        Data Event Handler for events retrieved from psana at MFX (LCLS).

        TODO: Docs

        Arguments:

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.

            source: A string describing the data source.
        """

        data_extraction_funcs: Dict[str, drl_base.OmDataSource] = {
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

        self._data_event_handler: drl_base.OmDataEventHandler = (
            _LclsBaseDataEventHandler(
                source=source,
                monitor_parameters=monitor_parameters,
                data_extraction_functions=data_extraction_funcs,
            )
        )

    @property
    def data_event_handler(self) -> drl_base.OmDataEventHandler:
        return self._data_event_handler


class MfxLclsRayonixDataRetrieval(drl_base.OmDataRetrieval):
    """
    See documentation of the `__init__` function.

    TODO: docs
    """

    def __init__(self, *, monitor_parameters: parameters.MonitorParams, source: str):
        """
        Data Event Handler for events retrieved from psana at MFX (LCLS).

        TODO: Docs

        Arguments:

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.

            source: A string describing the data source.
        """

        data_extraction_funcs: Dict[str, drl_base.OmDataSource] = {
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

        self._data_event_handler: drl_base.OmDataEventHandler = (
            _LclsBaseDataEventHandler(
                source=source,
                monitor_parameters=monitor_parameters,
                data_extraction_functions=data_extraction_funcs,
            )
        )

    @property
    def data_event_handler(self) -> drl_base.OmDataEventHandler:
        return self._data_event_handler
