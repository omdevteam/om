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
# Copyright 2020 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Retrieval and handling of data events from psana.

This module contains classes that retrieve and process data events from the psana
framework.
"""
from __future__ import absolute_import, division, print_function

from typing import Any, Callable, Dict, Generator, List

import numpy  # type: ignore
from future.utils import iteritems, raise_from  # type: ignore

import psana  # type: ignore
from om.data_retrieval_layer import base as drl_base
from om.data_retrieval_layer import (
    functions_cspad,
    functions_epix10ka,
    functions_jungfrau,
    functions_psana,
)
from om.utils import exceptions, parameters


def _psana_offline_event_generator(psana_source, node_rank, mpi_pool_size):
    # type: (Any, int, int) -> Any
    # Computes how many events the current processing node should process. Splits the
    # events as equally as possible amongst the processing nodes. If the number of
    # events cannot be exactly divided by the number of processing nodes, an additional
    # processing node is assigned the residual events.
    for run in psana_source.runs():
        times = run.times()
        num_events_curr_node = int(
            numpy.ceil(len(times) / float(mpi_pool_size - 1))
        )  # type: int
        events_curr_node = times[
            (node_rank - 1) * num_events_curr_node : node_rank * num_events_curr_node
        ]
        for evt in events_curr_node:

            yield run.event(evt)


class LclsBaseDataEventHandler(drl_base.OmDataEventHandler):
    """
    See documentation of the __init__ function.
    """

    def __init__(
        self,
        monitor_parameters,  # type: parameters.MonitorParams
        source,  # type: str
    ):
        # type: (...) -> None
        """
        Data event handler for events recovered psana (LCLS).

        See documentation of the constructor of the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.__init.py__` .

        This class handles detector events recovered from psana at the LCLS facility.
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
                }
            },
        )

    def initialize_event_handling_on_collecting_node(self, node_rank, node_pool_size):
        # type: (int, int) -> Any
        """
        Initializes event handling on the collecting node with psana.

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.\
initialize_event_source`.

        There is no need to initialize the psana event source, so this function
        actually does nothing.
        """
        del node_rank
        del node_pool_size

    def initialize_event_handling_on_processing_node(self, node_rank, node_pool_size):
        # type: (int, int) -> Any
        """
        Initializes event handling on the processing nodes with psana.

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.\
initialize_event_source`.
        """
        required_data = self._monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="required_data",
            parameter_type=list,
            required=True,
        )  # type: List[str]

        self._required_data_extraction_funcs = drl_base.filter_data_extraction_funcs(
            self.data_extraction_funcs, required_data
        )

        self._required_psana_detector_init_funcs = (
            {}
        )  # type: Dict[str, Callable[[parameters.MonitorParams],Any]]

        for func_name in required_data:
            try:
                self._required_psana_detector_init_funcs[
                    "{0}_init".format(func_name)
                ] = self._additional_info["psana_detector_init_funcs"][
                    "{0}_init".format(func_name)
                ]
            except KeyError as exc:
                raise_from(
                    exc=exceptions.OmMissingDataExtractionFunctionError(
                        "Psana Detector initialization function {0}_init not "
                        "defined".format(func_name)
                    ),
                    cause=exc,
                )

        self._event_info_to_append = {}  # type: Dict[str, Any]

        calibration = self._monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="calibration",
            parameter_type=bool,
            required=True,
        )
        self._event_info_to_append["calibration"] = calibration

    def event_generator(
        self,
        node_rank,  # type: int
        node_pool_size,  # type: int
    ):
        # type: (...) -> Generator[Dict[str, Any], None, None]
        """
        Retrieves events to process from psana at the LCLS facility.

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.event_generator`.

        Raises:

            :class:`~om.utils.exceptions.OmHidraAPIError`: if the initial connection to
                HiDRA fails.
        """
        # Detects if data is being read from an online or offline source.
        if "shmem" in self._source:
            offline = False  # type: bool
        else:
            offline = True
        if offline and not self._source[-4:] == ":idx":
            self._source += ":idx"

        # If the psana calibration directory is provided in the configuration file, it
        # is added as an option to psana before the DataSource is set.
        psana_calib_dir = self._monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="psana_calibration_directory",
            parameter_type=str,
        )  # type: str
        if psana_calib_dir is not None:
            psana.setOption("psana.calib-dir", psana_calib_dir)
        else:
            print("OM Warning: Calibration directory not provided or not found.")

        psana_source = psana.DataSource(self._source)

        data_event = {}  # type: Dict[str, Dict[str, Any]]
        data_event["data_extraction_funcs"] = self._required_data_extraction_funcs
        data_event["additional_info"] = {}

        # Calls all the required psana detector interface initialization functions and
        # stores the returned objects in a dictionary.
        data_event["additional_info"]["psana_detector_interface"] = {}
        for f_name, func in iteritems(self._required_psana_detector_init_funcs):
            data_event["additional_info"]["psana_detector_interface"][
                f_name.split("_init")[0]
            ] = func(self._monitor_params)

        # Initializes the psana event source and starts retrieving events.
        if offline:
            psana_events = _psana_offline_event_generator(
                psana_source=psana_source,
                node_rank=node_rank,
                mpi_pool_size=node_pool_size,
            )
        else:
            psana_events = psana_source.events()
        for psana_event in psana_events:
            data_event["data"] = psana_event

            # Recovers the timestamp from the psana event (as seconds from the Epoch)
            # and stores it in the event dictionary to be retrieved later.
            timestamp_epoch_format = psana_event.get(psana.EventId).time()
            data_event["additional_info"]["timestamp"] = numpy.float64(
                str(timestamp_epoch_format[0]) + "." + str(timestamp_epoch_format[1])
            )

            yield data_event

    def open_event(self, event):
        # type: (Dict[str, Any]) -> None
        """
        Opens an event retrieved from psana at the LCLS facility.

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.open_event` .

        Psana events do not need to be opened, so this function actually does nothing.

        Arguments:

            event (Dict[str, Any]): a dictionary storing the event data.
        """
        del event

    def close_event(self, event):
        # type: (Dict[str, Any]) -> None
        """
        Closes an event retrieved from psana at the LCLS facility.

        See documentation of the constructor of the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.close_event` .

        Psana events do not need to be closed, so this function actually does nothing.
        """
        del event

    def get_num_frames_in_event(self, event):
        # type: (Dict[str, Any]) -> int
        """
        Gets the number of frames in an event retrieved from psana at the LCLS facility.

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.\
get_num_frames_in_event` .

        Psana events are frame-based, and always contain just one frame. This function
        always returns 1.

        Returns:

            int: the number of frames in the event.
        """
        del event

        return 1


class CxiLclsCspadDataEventHandler(LclsBaseDataEventHandler):
    """
    See documentation of the __init__ function.
    """

    def __init__(self, monitor_parameters, source):
        # type: (parameters.MonitorParams, str) -> None
        """
        Data event handler for events recovered at CXI (LCLS) before 2020.

        See documentation of the function in the base class:
        :func:`~LclsBaseDataEventHandler.__init.py__` .

        This class handles detector events recovered from psana at the LCLS facility.
        """
        super(CxiLclsCspadDataEventHandler, self).__init__(
            monitor_parameters=monitor_parameters, source=source,
        )

    @property
    def data_extraction_funcs(self):
        # type: () -> Dict[str, Callable[[Dict[str, Dict[str, Any]]], Any]]
        """
        Retrieves the Data Extraction Functions for CXI (LCLS) before 2020.

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.\
data_extraction_funcs`.

        This function retrieves the Data Extraction Functions available for the CXI
        beamline at the LCLS facility, when data was collected before 2020 (using
        the CSPAD detector).
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
        }


class CxiLclsDataEventHandler(LclsBaseDataEventHandler):
    """
    See documentation of the __init__ function.
    """

    def __init__(self, monitor_parameters, source):
        # type: (parameters.MonitorParams, str) -> None
        """
        Data event handler for events recovered at CXI (LCLS).

        See documentation of the function in the base class:
        :func:`~PsanaDataEventHandler.__init.py__` .

        This class handles detector events recovered from psana at the LCLS facility.
        """
        super(CxiLclsDataEventHandler, self).__init__(
            monitor_parameters=monitor_parameters, source=source
        )

    @property
    def data_extraction_funcs(self):
        # type: () -> Dict[str, Callable[[Dict[str, Dict[str, Any]]], Any]]
        """
        Retrieves the Data Extraction Functions for CXI (LCLS).

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.\
data_extraction_funcs`.

        This function retrieves the Data Extraction Functions available for the CXI
        beamline at the LCLS facility, when data was collected after 2020 (using
        the Jungfrau4M detector).
        """
        return {
            "timestamp": functions_psana.timestamp,
            "detector_data": functions_jungfrau.detector_data,
            "beam_energy": functions_psana.beam_energy,
            "detector_distance": functions_psana.detector_distance,
            "timetool_data": functions_psana.timetool_data,
            "digitizer_data": functions_psana.digitizer_data,
            "opal_data": functions_psana.opal_data,
            "optical_laser_active": functions_psana.optical_laser_active,
            "xrays_active": functions_psana.xrays_active,
        }


class MfxLclsDataEventHandler(LclsBaseDataEventHandler):
    """
    See documentation of the __init__ function.
    """

    def __init__(self, monitor_parameters, source):
        # type: (parameters.MonitorParams, str) -> None
        """
        Data event handler for events recovered at CXI (LCLS).

        See documentation of the function in the base class:
        :func:`~PsanaDataEventHandler.__init.py__` .

        This class handles detector events recovered from psana at the LCLS facility.
        """
        super(MfxLclsDataEventHandler, self).__init__(
            monitor_parameters=monitor_parameters, source=source
        )

    @property
    def data_extraction_funcs(self):
        # type: () -> Dict[str, Callable[[Dict[str, Dict[str, Any]]], Any]]
        """
        Retrieves the Data Extraction Functions for CXI (LCLS).

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.\
data_extraction_funcs`.

        This function retrieves the Data Extraction Functions available for the CXI
        beamline at the LCLS facility, when data was collected after 2020 (using
        the Jungfrau4M detector).
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
        }
