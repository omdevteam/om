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
OM monitor for crystallography.

This module contains an OM monitor for serial x-ray crystallography experiments.
"""
from __future__ import absolute_import, division, print_function

import collections
import sys
import time
from typing import Any, Dict, Tuple

from om.algorithms import calibration_algorithms as calib_algs
from om.algorithms import crystallography_algorithms as cryst_algs
from om.algorithms import generic_algorithms as gen_algs
from om.parallelization_layer import mpi
from om.utils import (
    crystfel_geometry,
    dynamic_import,
    zmq_monitor,
    parameters,
)


class OndaMonitor(mpi.ParallelizationEngine):
    """
    See documentation for the '__init__' function.
    """

    def __init__(self, source, monitor_parameters):
        # type: (str, parameters.MonitorParams) -> None
        """
        An OM real-time monitor for serial x-ray crystallography experiments.

        This monitor processes detector data frames, optionally applying detector
        calibration, dark correction and gain correction. It detects Bragg peaks in
        each detector frame using the peakfinder8 algorithm from Cheetah. It provides
        information about the location and integrated intensity of each peak.
        Additionally, it calculates the evolution of the hit and saturation rates over
        time. It broadcasts all this information over a network socket for
        visualization by other programs. Optionally, it can also broadcast calibrated
        and corrected detector data frames.

        Arguments:

            source (str): a string describing the data source. The exact format of the
                string depends on the specific Data Recovery Layer currently being
                used. See the documentation of the relevant 'initialize_event_source'
                function.

            monitor_params (:class:`~om.utils.parameters.MonitorParams`): an object
                storing the OM monitor parameters from the configuration file.
        """
        super(OndaMonitor, self).__init__(
            process_func=self.process_data,
            collect_func=self.collect_data,
            source=source,
            monitor_params=monitor_parameters,
        )

        if self.role == "worker":
            requested_calibration_algorithm = monitor_parameters.get_param(
                group="calibration",
                parameter="calibration_algorithm",
                parameter_type=str,
            )
            if requested_calibration_algorithm is not None:
                calibration_alg = getattr(calib_algs, requested_calibration_algorithm)
                self._calibration = calibration_alg(
                    calibration_file=monitor_parameters.get_param(
                        group="calibration",
                        parameter="calibration_filename",
                        parameter_type=str,
                        required=True,
                    ),
                    cellid_list=monitor_parameters.get_param(
                        group="crystallography",
                        parameter="agipd_cellids_for_which_to_load_calibration_"
                        "parameters",
                        parameter_type=list,
                        required=True,
                    ),
                )

            else:
                # If no calibration is required, stores None in the 'calibration_alg'
                # attribute.
                self._calibration = None

            self._hit_frame_sending_counter = 0
            self._non_hit_frame_sending_counter = 0

            dark_data_filename = monitor_parameters.get_param(
                group="correction", parameter="dark_filename", parameter_type=str
            )
            dark_data_hdf5_path = monitor_parameters.get_param(
                group="correction", parameter="dark_hdf5_path", parameter_type=str
            )
            mask_filename = monitor_parameters.get_param(
                group="correction", parameter="mask_filename", parameter_type=str
            )
            mask_hdf5_path = monitor_parameters.get_param(
                group="correction", parameter="mask_hdf5_path", parameter_type=str
            )
            gain_map_filename = monitor_parameters.get_param(
                group="correction", parameter="gain_filename", parameter_type=str
            )
            gain_map_hdf5_path = monitor_parameters.get_param(
                group="correction", parameter="gain_hdf5_path", parameter_type=str
            )
            self._correction = gen_algs.Correction(
                dark_filename=dark_data_filename,
                dark_hdf5_path=dark_data_hdf5_path,
                mask_filename=mask_filename,
                mask_hdf5_path=mask_hdf5_path,
                gain_filename=gain_map_filename,
                gain_hdf5_path=gain_map_hdf5_path,
            )

            geometry_filename = monitor_parameters.get_param(
                group="crystallography",
                parameter="geometry_file",
                parameter_type=str,
                required=True,
            )
            geometry, _, _ = crystfel_geometry.load_crystfel_geometry(geometry_filename)
            pixelmaps = crystfel_geometry.compute_pix_maps(geometry)
            radius_pixel_map = pixelmaps["radius"]
            pf8_detector_info = dynamic_import.get_peakfinder8_info(
                monitor_params=monitor_parameters
            )
            pf8_max_num_peaks = monitor_parameters.get_param(
                group="peakfinder8",
                parameter="max_num_peaks",
                parameter_type=int,
                required=True,
            )
            pf8_adc_threshold = monitor_parameters.get_param(
                group="peakfinder8",
                parameter="adc_threshold",
                parameter_type=float,
                required=True,
            )
            pf8_minimum_snr = monitor_parameters.get_param(
                group="peakfinder8",
                parameter="minimum_snr",
                parameter_type=float,
                required=True,
            )
            pf8_min_pixel_count = monitor_parameters.get_param(
                group="peakfinder8",
                parameter="min_pixel_count",
                parameter_type=int,
                required=True,
            )
            pf8_max_pixel_count = monitor_parameters.get_param(
                group="peakfinder8",
                parameter="max_pixel_count",
                parameter_type=int,
                required=True,
            )
            pf8_local_bg_radius = monitor_parameters.get_param(
                group="peakfinder8",
                parameter="local_bg_radius",
                parameter_type=int,
                required=True,
            )
            pf8_min_res = monitor_parameters.get_param(
                group="peakfinder8",
                parameter="min_res",
                parameter_type=int,
                required=True,
            )
            pf8_max_res = monitor_parameters.get_param(
                group="peakfinder8",
                parameter="max_res",
                parameter_type=int,
                required=True,
            )
            pf8_bad_pixel_map_fname = monitor_parameters.get_param(
                group="peakfinder8",
                parameter="bad_pixel_map_filename",
                parameter_type=str,
            )
            if pf8_bad_pixel_map_fname is not None:
                pf8_bad_pixel_map_hdf5_path = monitor_parameters.get_param(
                    group="peakfinder8",
                    parameter="bad_pixel_map_hdf5_path",
                    parameter_type=str,
                    required=True,
                )
            else:
                pf8_bad_pixel_map_hdf5_path = None
            self._peak_detection = cryst_algs.Peakfinder8PeakDetection(
                max_num_peaks=pf8_max_num_peaks,
                asic_nx=pf8_detector_info["asic_nx"],
                asic_ny=pf8_detector_info["asic_ny"],
                nasics_x=pf8_detector_info["nasics_x"],
                nasics_y=pf8_detector_info["nasics_y"],
                adc_threshold=pf8_adc_threshold,
                minimum_snr=pf8_minimum_snr,
                min_pixel_count=pf8_min_pixel_count,
                max_pixel_count=pf8_max_pixel_count,
                local_bg_radius=pf8_local_bg_radius,
                min_res=pf8_min_res,
                max_res=pf8_max_res,
                bad_pixel_map_filename=pf8_bad_pixel_map_fname,
                bad_pixel_map_hdf5_path=pf8_bad_pixel_map_hdf5_path,
                radius_pixel_map=radius_pixel_map,
            )

            self._max_saturated_peaks = monitor_parameters.get_param(
                group="crystallography",
                parameter="max_saturated_peaks",
                parameter_type=int,
                required=True,
            )
            self._min_num_peaks_for_hit = monitor_parameters.get_param(
                group="crystallography",
                parameter="min_num_peaks_for_hit",
                parameter_type=int,
                required=True,
            )
            self._max_num_peaks_for_hit = monitor_parameters.get_param(
                group="crystallography",
                parameter="max_num_peaks_for_hit",
                parameter_type=int,
                required=True,
            )
            self._saturation_value = monitor_parameters.get_param(
                group="crystallography",
                parameter="saturation_value",
                parameter_type=int,
                required=True,
            )
            self._hit_frame_sending_interval = monitor_parameters.get_param(
                group="crystallography",
                parameter="hit_frame_sending_interval",
                parameter_type=int,
            )
            self._non_hit_frame_sending_interval = monitor_parameters.get_param(
                group="crystallography",
                parameter="non_hit_frame_sending_interval",
                parameter_type=int,
            )

            print("Starting worker: {0}.".format(self.rank))
            sys.stdout.flush()
        if self.role == "master":
            self._speed_report_interval = monitor_parameters.get_param(
                group="crystallography",
                parameter="speed_report_interval",
                parameter_type=int,
                required=True,
            )
            self._geometry_is_optimized = monitor_parameters.get_param(
                group="crystallography",
                parameter="geometry_is_optimized",
                parameter_type=bool,
                required=True,
            )
            num_events_to_accumulate = monitor_parameters.get_param(
                group="data_accumulator",
                parameter="num_events_to_accumulate",
                parameter_type=int,
                required=True,
            )
            self._data_accumulator = gen_algs.DataAccumulator(
                num_events_to_accumulate=num_events_to_accumulate
            )

            self._running_average_window_size = monitor_parameters.get_param(
                group="crystallography",
                parameter="running_average_window_size",
                parameter_type=int,
                required=True,
            )
            self._hit_rate_running_window = collections.deque(
                [0.0] * self._running_average_window_size,
                maxlen=self._running_average_window_size,
            )
            self._saturation_rate_running_window = collections.deque(
                [0.0] * self._running_average_window_size,
                maxlen=self._running_average_window_size,
            )
            self._avg_hit_rate = 0
            self._avg_sat_rate = 0

            broadcast_socket_ip = monitor_parameters.get_param(
                group="crystallography", parameter="broadcast_ip", parameter_type=str
            )
            broadcast_socket_port = monitor_parameters.get_param(
                group="crystallography", parameter="broadcast_port", parameter_type=int
            )
            self._data_broadcast_socket = zmq_monitor.ZmqDataBroadcaster(
                hostname=broadcast_socket_ip, port=broadcast_socket_port
            )

            self._num_events = 0
            self._old_time = time.time()
            self._time = None

            print("Starting the monitor...")
            sys.stdout.flush()

    def process_data(self, data):
        # type: (Dict[str, Any]) -> Dict[str, Any]
        """
        Processes a detector data frame.

        This function performs calibration and correction of a detector data frame and
        extracts Bragg peak information. Finally, it prepares the Bragg peak data (and
        optionally, the detector frame data) for transmission to to the master node.

        Arguments:

            data(Dict[str, Any]): a dictionary containing the data retrieved by
                OM for the frame being processed.

                * The dictionary keys must match the entries in the 'required_data'
                  list found in the 'Onda' configuration parameter group.

                * The corresponding dictionary values must store the retrieved data.

        Returns:

            Dict[str, Any]: a named tuple storing the processed data and some
            information about the node that processed it.
        """
        processed_data = {}
        if self._calibration is not None:
            calibrated_detector_data = self._calibration.apply_calibration(
                {
                    "data": data["detector_data"],
                    "info": {
                        "gain": data["detector_gain"],
                        "cell": int(data["frame_id"]),
                    },
                }
            )
        else:
            calibrated_detector_data = data["detector_data"]
        corrected_detector_data = self._correction.apply_correction(
            data=calibrated_detector_data
        )
        peak_list = self._peak_detection.find_peaks(corrected_detector_data)
        frame_is_saturated = (
            len([x for x in peak_list["intensity"] if x > self._saturation_value])
            > self._max_saturated_peaks
        )
        frame_is_hit = (
            self._min_num_peaks_for_hit
            < len(peak_list["intensity"])
            < self._max_num_peaks_for_hit
        )

        processed_data["timestamp"] = data["timestamp"]
        processed_data["frame_is_saturated"] = frame_is_saturated
        processed_data["frame_is_hit"] = frame_is_hit
        processed_data["detector_distance"] = data["detector_distance"]
        processed_data["beam_energy"] = data["beam_energy"]
        processed_data["native_data_shape"] = data["detector_data"].shape
        if frame_is_hit:
            processed_data["peak_list"] = peak_list
            if self._hit_frame_sending_interval is not None:
                self._hit_frame_sending_counter += 1
                if self._hit_frame_sending_counter == self._hit_frame_sending_interval:
                    # If the frame is a hit, and if the 'hit_sending_interval'
                    # attribute says that the detector frame data should be sent to
                    # the master node, adds the data to the 'processed_dat' dictionary
                    # (and resets the counter).
                    processed_data["detector_data"] = corrected_detector_data
                    self._hit_frame_sending_counter = 0
        else:
            # If the frame is not a hit, sends an empty peak list.
            processed_data["peak_list"] = {"fs": [], "ss": [], "intensity": []}
            if self._non_hit_frame_sending_interval is not None:
                self._non_hit_frame_sending_counter += 1
                if (
                    self._non_hit_frame_sending_counter
                    == self._non_hit_frame_sending_interval
                ):
                    # If the frame is a not a hit, and if the 'hit_sending_interval'
                    # attribute says that the detector frame data should be sent to
                    # the master node, adds the data to the 'results_dict' dictionary
                    # (and resets the counter).
                    processed_data["detector_data"] = corrected_detector_data
                    self._non_hit_frame_sending_counter = 0

        return {"data": processed_data, "worker_rank": self.rank}

    def collect_data(self, processed_data):
        # type: (Dict[str, Any]) -> None
        """
        Computes statistics on aggregated data and broadcasts them via a network socket.

        This function computes aggregated statistics on data received from the worker
        nodes. It then broadcasts the results via a network socket (for visualization
        by other programs) using the MessagePack protocol.

        Arguments:

            processed_data(Dict[str, Any]): a named tuple storing the processed data
                and some information about the node that processed it.
        """
        received_data = processed_data["data"]
        self._num_events += 1

        self._hit_rate_running_window.append(float(received_data["frame_is_hit"]))
        self._saturation_rate_running_window.append(
            float(received_data["frame_is_saturated"])
        )
        avg_hit_rate = (
            sum(self._hit_rate_running_window) / self._running_average_window_size
        )
        avg_sat_rate = (
            sum(self._saturation_rate_running_window)
            / self._running_average_window_size
        )
        received_data["hit_rate"] = avg_hit_rate
        received_data["saturation_rate"] = avg_sat_rate
        received_data["geometry_is_optimized"] = self._geometry_is_optimized

        # Since the data will be sent out of the master node using msgpack, NamedTuple
        # structures will not be preserved. The peak list is converted here to a
        # dictionary, which suvives the msgpack conversion and allows introspection on
        # the receiver side.
        received_data["peak_list"] = {
            "fs": received_data["peak_list"]["fs"],
            "ss": received_data["peak_list"]["ss"],
            "intensity": received_data["peak_list"]["intensity"],
        }

        if "detector_data" in received_data:
            # If detector frame data is found in the data received from the worker
            # node, it must be broadcasted to visualization programs. The frame is
            # wrapped into a list because the receiving programs usually expect lists
            # of aggregated events as opposed to single events.
            self._data_broadcast_socket.send_data(
                tag=u"omframedata", message=[received_data]
            )
        # After it has been broadcasted, it removes the detector frame data from the
        # 'received_data' dictionary (the frame data is not needed anymore, so we
        # remove it for efficiency reasons).
        if "detector_data" in received_data:
            del received_data["detector_data"]

        collected_data = self._data_accumulator.add_data(data=received_data)
        if collected_data is not None:
            self._data_broadcast_socket.send_data(tag=u"omdata", message=collected_data)

        if self._num_events % self._speed_report_interval == 0:
            now_time = time.time()
            speed_report_msg = "Processed: {0} in {1:.2f} seconds ({2:.2f} Hz)".format(
                self._num_events,
                now_time - self._old_time,
                (float(self._speed_report_interval) / float(now_time - self._old_time)),
            )

            print(speed_report_msg)
            sys.stdout.flush()
            self._old_time = now_time
