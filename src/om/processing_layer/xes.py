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
OnDA Monitor for X-ray Emission Spectroscopy.

This module contains an OnDA Monitor for x-ray emission spectroscopy experiments.
"""
from __future__ import absolute_import, division, print_function

import sys
from typing import Any, Dict, Tuple, Union

import numpy
from numpy.typing import NDArray

from om.algorithms.xes import EnergySpectrumRetrieval
from om.lib.event_management import EventCounter
from om.lib.geometry import GeometryInformation
from om.lib.parameters import MonitorParameters
from om.lib.rich_console import console, get_current_timestamp
from om.lib.xes import XesAnalysisAndPlots
from om.lib.zmq import ZmqDataBroadcaster, ZmqResponder
from om.protocols.processing_layer import OmProcessingProtocol


class XesProcessing(OmProcessingProtocol):
    """
    See documentation for the `__init__` function.
    """

    def __init__(self, *, monitor_parameters: MonitorParameters) -> None:
        """
        OnDA Monitor for X-ray Emission Spectroscopy.

        This Processing class implements and OnDA Monitor for X-ray Emission
        Spectroscopy experiments. The monitor processes camera data frames,extracting
        an energy spectrum from each of the data frames. The monitor computes smoothed
        and averaged spectral data information and broadcasts it to
        external programs (like [OM's XES GUI][om.graphical_interfaces.xes_gui.XesGui],
        for visualization. In time resolved experiments, the monitor can process
        spectra for pumped and dark events separately, and compute their difference.

        This monitor is designed to work with cameras or simple single-module
        detectors. It will not work with a segmented detector.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        Arguments:

            monitor_parameters: An object storing OM's configuration parameters.
        """
        # Parameters
        self._monitor_params: MonitorParameters = monitor_parameters

        # Geometry
        self._geometry_information = GeometryInformation.from_file(
            geometry_filename=self._monitor_params.get_parameter(
                group="xes",
                parameter="geometry_file",
                parameter_type=str,
                required=True,
            ),
        )

        # Pump probe
        self._time_resolved: bool = self._monitor_params.get_parameter(
            group="xes",
            parameter="time_resolved",
            parameter_type=bool,
            required=True,
        )

    def initialize_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes the processing nodes for the XES Monitor.

        This function initializes the the spectrum extraction algorithm, plus some
        internal counters.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        # Frame sending
        self._send_hit_frame: bool = False
        self._send_non_hit_frame: bool = False

        self._energy_spectrum_retrieval: EnergySpectrumRetrieval = (
            EnergySpectrumRetrieval(
                parameters=self._monitor_params.get_parameter_group(group="xes"),
            )
        )

        # Console
        console.print(f"{get_current_timestamp()} Processing node {node_rank} starting")
        sys.stdout.flush()

    def initialize_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes the collecting node for the XES Monitor.

        This function initializes the data accumulation algorithms and the storage
        buffers used to compute statistics on the aggregated spectral data.
        Additionally, it prepares all the necessary network sockets.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        self._time_resolved = self._monitor_params.get_parameter(
            group="xes",
            parameter="time_resolved",
            parameter_type=bool,
            required=True,
        )

        # Plots
        self._plots = XesAnalysisAndPlots(
            parameters=self._monitor_params.get_parameter_group(group="xes"),
            time_resolved=self._time_resolved,
        )

        # Data broadcast
        self._data_broadcast_socket: ZmqDataBroadcaster = ZmqDataBroadcaster(
            parameters=self._monitor_params.get_parameter_group(group="crystallography")
        )

        # Responding socket
        self._responding_socket: ZmqResponder = ZmqResponder(
            parameters=self._monitor_params.get_parameter_group(group="crystallography")
        )

        # Event counting
        self._event_counter: EventCounter = EventCounter(
            om_parameters=self._monitor_params.get_parameter_group(
                group="crystallography"
            ),
            node_pool_size=node_pool_size,
        )

        # Console
        console.print(f"{get_current_timestamp()} Starting the monitor...")
        sys.stdout.flush()

    def process_data(
        self, *, node_rank: int, node_pool_size: int, data: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], int]:
        """
        Processes a detector data frame and extracts spectrum information.

        This function processes retrieved data events, extracting an energy spectrum
        from each of them. It additionally prepares the spectral data for transmission
        to to the collecting node.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

            data: A dictionary containing the data that OM retrieved for the detector
                data frame being processed.

                * The dictionary keys describe the Data Sources for which OM has
                  retrieved data. The keys must match the source names listed in the
                  `required_data` entry of OM's `om` configuration parameter group.

                * The corresponding dictionary values must store the the data that OM
                  retrieved for each of the Data Sources.

        Returns:

            A tuple with two entries. The first entry is a dictionary storing the
                processed data that should be sent to the collecting node. The second
                entry is the OM rank number of the node that processed the information.
        """
        processed_data: Dict[str, Any] = {}
        camera_data: NDArray[numpy.float_] = data["detector_data"]

        # Mask the camera edges
        camera_data[camera_data.shape[0] // 2 - 1 : camera_data.shape[0] // 2 + 1] = 0
        camera_data[
            :,
            camera_data.shape[1] // 2 - 1 : camera_data.shape[1] // 2 + 1,
        ] = 0

        xes: Dict[
            str, NDArray[numpy.float_]
        ] = self._energy_spectrum_retrieval.calculate_spectrum(data=camera_data)

        processed_data["timestamp"] = data["timestamp"]
        processed_data["spectrum"] = xes["spectrum"]
        processed_data["beam_energy"] = data["beam_energy"]
        processed_data["data_shape"] = data["detector_data"].shape
        processed_data["detector_data"] = camera_data
        if self._time_resolved:
            processed_data["optical_laser_active"] = data["optical_laser_active"]
        else:
            processed_data["optical_laser_active"] = False
        return (processed_data, node_rank)

    def wait_for_data(
        self,
        *,
        node_rank: int,
        node_pool_size: int,
    ) -> None:
        """
        Receives and handles requests from external programs.

        This function receives requests from external programs over a network socket
        and reacts according to the nature of the request, sending data back to the
        source of the request or modifying the internal behavior of the monitor.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        """
        pass

    def collect_data(
        self,
        *,
        node_rank: int,
        node_pool_size: int,
        processed_data: Tuple[Dict[str, Any], int],
    ) -> Union[Dict[int, Dict[str, Any]], None]:
        """
        Computes statistics on aggregated spectrum data and broadcasts them.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function computes aggregated statistics on spectral data received from the
        processing nodes. It then broadcasts the aggregated information to external
        programs for visualization.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

            processed_data (Tuple[Dict, int]): A tuple whose first entry is a
                dictionary storing the data received from a processing node, and whose
                second entry is the OM rank number of the node that processed the
                information.
        """
        del node_rank
        del node_pool_size
        received_data: Dict[str, Any] = processed_data[0]
        return_dict: Dict[int, Dict[str, Any]] = {}

        spectrum_for_gui = received_data["spectrum"]

        spectra_cumulative_sum: Union[NDArray[numpy.float_], NDArray[numpy.int_], None]
        spectra_cumulative_sum_smoothed: Union[NDArray[numpy.float_], None]
        cumulative_2d: Union[NDArray[numpy.float_], NDArray[numpy.int_], None]
        spectra_cumulative_sum_pumped: Union[NDArray[numpy.float_], None]
        spectra_cumulative_sum_dark: Union[NDArray[numpy.float_], None]
        spectra_cumulative_sum_difference: Union[NDArray[numpy.float_], None]
        (
            spectra_cumulative_sum,
            spectra_cumulative_sum_smoothed,
            cumulative_2d,
            spectra_cumulative_sum_pumped,
            spectra_cumulative_sum_dark,
            spectra_cumulative_sum_difference,
        ) = self._plots.update_plots(
            detector_data=received_data["detector_data"],
            optical_laser_active=received_data["optical_laser_active"],
        )

        if self._event_counter.should_broadcast_data():
            message: Dict[str, Any] = {
                "timestamp": received_data["timestamp"],
                "detector_data": cumulative_2d,
                "spectrum": spectrum_for_gui,
                "spectra_sum": spectra_cumulative_sum,
                "spectra_sum_smoothed": spectra_cumulative_sum_smoothed,
                "beam_energy": received_data["beam_energy"],
            }
            if self._time_resolved:
                message["spectra_sum_pumped"] = spectra_cumulative_sum_pumped
                message["spectra_sum_dark"] = spectra_cumulative_sum_dark
                message["spectra_sum_difference"] = spectra_cumulative_sum_difference

            self._data_broadcast_socket.send_data(
                tag="omdata",
                message=message,
            )

        self._event_counter.report_speed()

        if return_dict:
            return return_dict
        return None

    def end_processing_on_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> Union[Dict[str, Any], None]:
        """
        Ends processing on the processing nodes for the XES Monitor.

        This function prints a message on the console and ends the processing.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        Returns:

            Usually nothing. Optionally, a dictionary storing information to be sent to
                the processing node.
        """
        console.print(
            f"{get_current_timestamp()} Processing node {node_rank} shutting down."
        )
        sys.stdout.flush()
        return None

    def end_processing_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Ends processing on the collecting node for the XES Monitor.

        This function prints a message on the console and ends the processing.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node, which is an integer that
                unambiguously identifies the current node in the OM node pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        console.print(
            f"{get_current_timestamp()} Processing finished. OM has processed "
            f"{self._event_counter.get_num_events()} events in total."
        )
        sys.stdout.flush()
