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
from typing import Any, Callable, Dict, Generator, List

import numpy  # type: ignore
from om.data_retrieval_layer import base as drl_base
from om.data_retrieval_layer import (
    functions_cspad,
    functions_epix10ka,
    functions_jungfrau4M,
    functions_psana,
    functions_rayonix,
)
from om.utils import exceptions, parameters

try:
    import psana  # type: ignore
except ImportError:
    raise exceptions.OmMissingDependencyError(
        "The following required module cannot be imported: psana"
    )


def _psana_offline_event_generator(
    psana_source: Any, node_rank: int, mpi_pool_size: int
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


class LclsBaseDataEventHandler(drl_base.OmDataEventHandler):
    """
    See documentation of the `__init__` function.

    Base class: [`OmDataEventHandler`][om.data_retrieval_layer.base.OmDataEventHandler]
    """

    def __init__(
        self,
        monitor_parameters: parameters.MonitorParams,
        source: str,
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
        super(LclsBaseDataEventHandler, self).__init__(
            monitor_parameters=monitor_parameters,
            source=source,
            additional_info={
                "psana_detector_init_funcs": {
                    "timestamp_init": functions_psana.timestamp_init,
                    "detector_data_init": functions_psana.detector_data_init,
                    "beam_energy_init": functions_psana.beam_energy_init,
                    "detector_distance_init": functions_psana.detector_distance_init,
                    "timetool_data_init": functions_psana.timetool_data_init,
                    "digitizer_data_init": functions_psana.digitizer_data_init,
                    "opal_data_init": functions_psana.opal_data_init,
                    "optical_laser_active_init": (
                        functions_psana.optical_laser_active_init
                    ),
                    "xrays_active_init": functions_psana.xrays_active_init,
                    "event_id_init": functions_psana.event_id_init,
                    "frame_id_init": functions_psana.frame_id_init,
                }
            },
        )

    def initialize_event_handling_on_collecting_node(
        self, node_rank: int, node_pool_size: int
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
        required_data: List[str] = self._monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="required_data",
            parameter_type=list,
            required=True,
        )

        self._required_data_extraction_funcs = drl_base.filter_data_extraction_funcs(
            self.data_extraction_funcs, required_data
        )

        self._required_psana_detector_init_funcs: Dict[
            str, Callable[[parameters.MonitorParams], Any]
        ] = {}

        func_name: str
        for func_name in required_data:
            try:
                self._required_psana_detector_init_funcs[
                    "{0}_init".format(func_name)
                ] = self._additional_info["psana_detector_init_funcs"][
                    "{0}_init".format(func_name)
                ]
            except KeyError as exc:
                raise exceptions.OmMissingDataExtractionFunctionError(
                    "Psana Detector initialization function {0}_init not "
                    "defined".format(func_name)
                ) from exc

        # Fills the event info dictionary with static data that will be retrieved
        # later.
        self._event_info_to_append: Dict[str, Any] = {}
        if "optical_laser_active" in required_data:
            self._event_info_to_append[
                "active_optical_laser_evr_code"
            ] = self._monitor_params.get_param(
                group="data_retrieval_layer",
                parameter="active_optical_laser_evr_code",
                parameter_type=int,
                required=True,
            )
        if "xray_active" in required_data:
            self._event_info_to_append[
                "active_xray_evr_code"
            ] = self._monitor_params.get_param(
                group="data_retrieval_layer",
                parameter="active_xray_evr_code",
                parameter_type=int,
                required=True,
            )

    def event_generator(
        self,
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
        psana_calib_dir: str = self._monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="psana_calibration_directory",
            parameter_type=str,
        )
        if psana_calib_dir is not None:
            psana.setOption("psana.calib-dir", psana_calib_dir)
        else:
            print("OM Warning: Calibration directory not provided or not found.")

        psana_source = psana.DataSource(self._source)

        data_event: Dict[str, Dict[str, Any]] = {}
        data_event["data_extraction_funcs"] = self._required_data_extraction_funcs
        data_event["additional_info"] = {}
        data_event["additional_info"].update(self._event_info_to_append)

        # Calls all the required psana detector interface initialization functions and
        # stores the returned objects in a dictionary.
        data_event["additional_info"]["psana_detector_interface"] = {}
        f_name: str
        func: Callable[[parameters.MonitorParams], Any]
        for f_name, func in self._required_psana_detector_init_funcs.items():
            data_event["additional_info"]["psana_detector_interface"][
                f_name.split("_init")[0]
            ] = func(self._monitor_params)

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
            timestamp_epoch_format: Any = psana_event.get(psana.EventId).time()
            data_event["additional_info"]["timestamp"] = numpy.float64(
                str(timestamp_epoch_format[0]) + "." + str(timestamp_epoch_format[1])
            )

            yield data_event

    def open_event(self, event: Dict[str, Any]) -> None:
        """
        Opens a psana event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Psana events do not need to be opened, so this function actually does nothing.

        Arguments:

            event: a dictionary storing the event data.
        """
        pass

    def close_event(self, event: Dict[str, Any]) -> None:
        """
        Closes a psana event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Psana events do not need to be closed, so this function actually does nothing.

        Arguments:

            event: a dictionary storing the event data.
        """
        pass

    def get_num_frames_in_event(self, event: Dict[str, Any]) -> int:
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


class CxiLclsCspadDataEventHandler(LclsBaseDataEventHandler):
    """
    See documentation of the `__init__` function.

    Base class: [`LclsBaseDataEventHandler`]
    [om.data_retrieval_layer.data_handlers_psana.LclsBaseDataEventHandler]
    """

    def __init__(self, monitor_parameters: parameters.MonitorParams, source: str):
        """
        Data Event Handler for events retrieved from psana at CXI with CSPAD (LCLS).

        This Data Event Handler deals with events retrieved from psana at the CXI
        beamline of the LCLS facility before 2020, when a CSPAD was the main x-ray
        detector. Is is a subclass of the  [LclsBaseDataEventHandler]
        [om.data_retrieval_layer.data_handlers_psana.LclsBaseDataEventHandler] class.

        Arguments:

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.

            source: A string describing the data source.
        """
        super(CxiLclsCspadDataEventHandler, self).__init__(
            monitor_parameters=monitor_parameters,
            source=source,
        )

    @property
    def data_extraction_funcs(
        self,
    ) -> Dict[str, Callable[[Dict[str, Dict[str, Any]]], Any]]:
        """
        Retrieves the Data Extraction Functions for CXI psana events (CSPAD).

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Returns:

            A dictionary storing the implementations of the Data Extraction functions
            available to the current DataEventHandler.

            * Each dictionary key defines the name of a function.

            * The corresponding dictionary value stores the function implementation.
        """
        return {
            "timestamp": functions_psana.timestamp,
            "detector_data": functions_cspad.detector_data,
            "beam_energy": functions_psana.beam_energy,
            "detector_distance": functions_psana.detector_distance,
            "timetool_data": functions_psana.timetool_data,
            "digitizer_data": functions_psana.digitizer_data,
            "opal_data": functions_psana.opal_data,
            "optical_laser_active": functions_psana.optical_laser_active,
            "xrays_active": functions_psana.xrays_active,
            "event_id": functions_psana.event_id,
            "frame_id": functions_psana.frame_id,
        }


class CxiLclsDataEventHandler(LclsBaseDataEventHandler):
    """
    See documentation of the `__init__` function.

    Base class: [`LclsBaseDataEventHandler`]
    [om.data_retrieval_layer.data_handlers_psana.LclsBaseDataEventHandler]
    """

    def __init__(
        self, monitor_parameters: parameters.MonitorParams, source: str
    ) -> None:
        """
        Data Event Handler for events retrieved from psana at CXI (LCLS).

        This Data Event Handler deals with events retrieved from psana at the CXI
        beamline of the LCLS facility from 2020, with a Jungfrau 4M as the main x-ray
        detector. Is is a subclass of the [LclsBaseDataEventHandler]
        [om.data_retrieval_layer.data_handlers_psana.LclsBaseDataEventHandler] class.

        Arguments:

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.

            source: A string describing the data source.
        """
        super(CxiLclsDataEventHandler, self).__init__(
            monitor_parameters=monitor_parameters, source=source
        )

    @property
    def data_extraction_funcs(self) -> Dict[str, Callable[[Dict[str, Any]], Any]]:
        """
        Retrieves the Data Extraction Functions for CXI psana events.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Returns:

            A dictionary storing the Data Extraction functions available to the current
            Data Event Handler.

            * Each dictionary key defines the name of a function.

            * The corresponding dictionary value stores the function implementation.
        """
        return {
            "timestamp": functions_psana.timestamp,
            "detector_data": functions_jungfrau4M.detector_data,
            "beam_energy": functions_psana.beam_energy,
            "detector_distance": functions_psana.detector_distance,
            "timetool_data": functions_psana.timetool_data,
            "digitizer_data": functions_psana.digitizer_data,
            "opal_data": functions_psana.opal_data,
            "optical_laser_active": functions_psana.optical_laser_active,
            "xrays_active": functions_psana.xrays_active,
            "event_id": functions_psana.event_id,
            "frame_id": functions_psana.frame_id,
        }


class MfxLclsDataEventHandler(LclsBaseDataEventHandler):
    """
    See documentation of the `__init__` function.

    Base class: [`LclsBaseDataEventHandler`]
    [om.data_retrieval_layer.data_handlers_psana.LclsBaseDataEventHandler]
    """

    def __init__(
        self, monitor_parameters: parameters.MonitorParams, source: str
    ) -> None:
        """
        Data Event Handler for events retrieved from psana at MFX (LCLS).

        This Data Event Handler deals with events retrieved from psana at the MFX
        beamline of the LCLS facility, with an Epix10KA as the main x-ray detector. It
        is a subclass of the [LclsBaseDataEventHandler]
        [om.data_retrieval_layer.data_handlers_psana.LclsBaseDataEventHandler] class.

        Arguments:

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.

            source: A string describing the data source.
        """
        super(MfxLclsDataEventHandler, self).__init__(
            monitor_parameters=monitor_parameters, source=source
        )

    @property
    def data_extraction_funcs(self) -> Dict[str, Callable[[Dict[str, Any]], Any]]:
        """
        Retrieves the Data Extraction Functions for MFX psana events.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Returns:

            A dictionary storing the implementations of the Data Extraction functions
            available to the current DataEventHandler.

            * Each dictionary key defines the name of a function.

            * The corresponding dictionary value stores the function implementation.
        """
        return {
            "timestamp": functions_psana.timestamp,
            "detector_data": functions_epix10ka.epixka2m_detector_data,
            "beam_energy": functions_psana.beam_energy,
            "detector_distance": functions_psana.detector_distance,
            "timetool_data": functions_psana.timetool_data,
            "digitizer_data": functions_psana.digitizer_data,
            "opal_data": functions_psana.opal_data,
            "optical_laser_active": functions_psana.optical_laser_active,
            "xrays_active": functions_psana.xrays_active,
            "event_id": functions_psana.event_id,
            "frame_id": functions_psana.frame_id,
        }


class MfxLclsRayonixDataEventHandler(LclsBaseDataEventHandler):
    """
    See documentation of the `__init__` function.

    Base class: [`LclsBaseDataEventHandler`]
    [om.data_retrieval_layer.data_handlers_psana.LclsBaseDataEventHandler]
    """

    def __init__(
        self, monitor_parameters: parameters.MonitorParams, source: str
    ) -> None:
        """
        Data Event Handler for events retrieved from psana at MFX with Rayonix (LCLS).

        This Data Event Handler deals with events retrieved from psana at the MFX
        beamline of the LCLS facility, with a Rayonix as the main x-ray detector. It
        is a subclass of the [LclsBaseDataEventHandler]
        [om.data_retrieval_layer.data_handlers_psana.LclsBaseDataEventHandler] class.

        Arguments:

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.

            source: A string describing the data source.
        """
        super(MfxLclsRayonixDataEventHandler, self).__init__(
            monitor_parameters=monitor_parameters, source=source
        )

    @property
    def data_extraction_funcs(self) -> Dict[str, Callable[[Dict[str, Any]], Any]]:
        """
        Retrieves the Data Extraction Functions for MFX psana events.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Returns:

            A dictionary storing the implementations of the Data Extraction functions
            available to the current DataEventHandler.

            * Each dictionary key defines the name of a function.

            * The corresponding dictionary value stores the function implementation.
        """
        return {
            "timestamp": functions_psana.timestamp,
            "detector_data": functions_rayonix.detector_data,
            "beam_energy": functions_psana.beam_energy,
            "detector_distance": functions_psana.detector_distance,
            "timetool_data": functions_psana.timetool_data,
            "digitizer_data": functions_psana.digitizer_data,
            "opal_data": functions_psana.opal_data,
            "optical_laser_active": functions_psana.optical_laser_active,
            "xrays_active": functions_psana.xrays_active,
            "event_id": functions_psana.event_id,
            "frame_id": functions_psana.frame_id,
        }
