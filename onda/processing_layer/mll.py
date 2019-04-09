# This file is part of OnDA.
#
# OnDA is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# OnDA is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with OnDA.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2014-2018 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
OnDA Monitor for serial x-ray crystallography.

An OnDA real-time monitor for serial x-ray crystallography experiments.
"""
from __future__ import absolute_import, division, print_function

import os.path
import sys
import time

import numpy
from future.utils import raise_from

from onda.algorithms import calibration_algorithms as calib_algs
from onda.algorithms import generic_algorithms as gen_algs
from onda.parallelization_layer import mpi
from onda.utils import zmq as onda_zmq


def _make_mll_mask(centre, size, shape):
    # Creates masks for the calculation of STXM and DPC

    mask = numpy.zeros(shape, dtype=numpy.int)

    i, j = numpy.indices(mask.shape)
    left_ss = (i > (centre[0] - size[0])) * (i < centre[0])
    left_fs = (j > (centre[1] - size[1])) * (j < centre[1])
    right_ss = (i > centre[0]) * (i < centre[0] + size[0])
    right_fs = (j > centre[1]) * (j < centre[1] + size[1])
    mask[left_ss * left_fs] = 1
    mask[left_ss * right_fs] = 2
    mask[right_ss * left_fs] = 3
    mask[right_ss * right_fs] = 4
    return mask


class OndaMonitor(mpi.ParallelizationEngine):
    """
    An OnDA real-time monitor for multi-layer lens experiments.

    This monitor assembles images from 1-d and 2-d scans.

    TODO: Describe the monitor.

    The monitor broadcasts STXM and DPC assembled images for the whole scan for
    visualization.
    """

    def __init__(self, source, monitor_parameters):
        """
        Initializes the OndaMonitor class.

        Args:

            source (str): A string describing the data source. The exact format of the
                string depends on the data recovery layer used by the monitor (e.g:
                the string could be a psana experiment descriptor at the LCLS
                facility, information on where HiDRA is running at the Petra III
                facility, etc.).

            monitor_params (MonitorParams): a
                :obj:`~onda.utils.parameters.MonitorParams` object
                containing the monitor parameters from the configuration file.
        """
        super(OndaMonitor, self).__init__(
            process_func=self.process_data,
            collect_func=self.collect_data,
            source=source,
            monitor_params=monitor_parameters,
        )

        if self.role == "worker":
            requested_calib_alg = monitor_parameters.get_param(
                section="DetectorCalibration",
                parameter="calibration_algorithm",
                type_=str,
            )
            if requested_calib_alg is not None:
                calibration_alg_class = getattr(calib_algs, requested_calib_alg)

                self._calibration_alg = calibration_alg_class(
                    calibration_file=monitor_parameters.get_param(
                        section="DetectorCalibration",
                        parameter="calibration_file",
                        type_=str,
                        required=True,
                    )
                )
            else:
                # If no calibration is required, stores None in the 'calibration_alg'
                # attribute.
                self._calibration_alg = None

            # Initializes the non_hit_frame_sending_counter and the
            # hit_frame_sending_counter to keep track of how often the detector frame
            # data needs to be sent to the master worker.
            self._hit_frame_sending_counter = 0
            self._non_hit_frame_sending_counter = 0

            # Reads from the configuration file all the parameters needed to
            # instantiate the dark calibration correction algorithm, then instatiates
            # the algorithm.
            dark_cal_fname = monitor_parameters.get_param(
                section="DarkCalCorrection",
                parameter="filename",
                type_=str,
                required=True,
            )
            dark_cal_hdf5_pth = monitor_parameters.get_param(
                section="DarkCalCorrection",
                parameter="hdf5_path",
                type_=str,
                required=True,
            )
            dark_cal_mask_fname = monitor_parameters.get_param(
                section="DarkCalCorrection", parameter="mask_filename", type_=str
            )
            dark_cal_mask_hdf5_pth = monitor_parameters.get_param(
                section="DarkCalCorrection", parameter="mask_hdf5_path", type_=str
            )
            dark_cal_gain_map_fname = monitor_parameters.get_param(
                section="DarkCalCorrection", parameter="gain_map_filename", type_=str
            )
            dark_cal_gain_map_hdf5_pth = monitor_parameters.get_param(
                section="DarkCalCorrection", parameter="gain_map_hdf5_path", type_=str
            )
            self._dark_cal_corr_alg = gen_algs.DarkCalCorrection(
                darkcal_filename=dark_cal_fname,
                darkcal_hdf5_path=dark_cal_hdf5_pth,
                mask_filename=dark_cal_mask_fname,
                mask_hdf5_path=dark_cal_mask_hdf5_pth,
                gain_map_filename=dark_cal_gain_map_fname,
                gain_map_hdf5_path=dark_cal_gain_map_hdf5_pth,
            )

            mask_shape = (
                monitor_parameters.get_param(
                    section="MLL", parameter="mask_size_ss", type_=int, required=True
                ),
                monitor_parameters.get_param(
                    section="MLL", parameter="mask_size_fs", type_=int, required=True
                ),
            )
            mask_center = (
                monitor_parameters.get_param(
                    section="MLL", parameter="mask_center_ss", type_=int, required=True
                ),
                monitor_parameters.get_param(
                    section="MLL", parameter="mask_center_fs", type_=int, required=True
                ),
            )
            mask_size = (
                monitor_parameters.get_param(
                    section="MLL", parameter="mask_edge_ss", type_=int, required=True
                ),
                monitor_parameters.get_param(
                    section="MLL", parameter="mask_edge_fs", type_=int, required=True
                ),
            )
            self._mask = _make_mll_mask(mask_center, mask_size, mask_shape)

            print("Starting worker: {0}.".format(self.rank))
            sys.stdout.flush()

        if self.role == "master":

            # Reads information about the scan from a log file
            source_parts = source.split(":")
            self._log_file_path = source_parts[1]

            try:
                with open(self._log_file_path, "r") as fhandle:
                    log_file_lines = fhandle.readlines()
            except (IOError, OSError):
                raise_from(
                    exc=RuntimeError("Error reading the {0} log file.".format(source)),
                    cause=None,
                )

            scan_template_lines = tuple(
                line
                for line in log_file_lines
                if line.lower().startswith("# scan template")
            )
            if "2d" in scan_template_lines[-1].lower():
                self._scan_type = 2
            elif "1d" in scan_template_lines[-1].lower():
                self._scan_type = 1
            else:
                raise_from(
                    exc=RuntimeError("Unknown scan template (not 1D or 2D)"), cause=None
                )
            print("Log file: {0}".format(self._log_file_path))

            points_count_lines = (
                line
                for line in log_file_lines
                if line.lower().startswith("# steps count")
            )
            try:
                self._points_count = tuple(
                    int(line.split(":")[1]) + 1 for line in points_count_lines
                )
            except ValueError:
                raise_from(
                    exc=RuntimeError("Error reading point counts from log file."),
                    cause=None,
                )

            if self._scan_type == 2:
                print(
                    "2D scan, {0}x{1} points.".format(
                        self._points_count[0], self._points_count[1]
                    )
                )
                sys.stdout.flush()
            else:
                print("1D scan, {0} points.".format(self._points_count[0]))
                sys.stdout.flush()

            device_lines = (
                line for line in log_file_lines if line.lower().startswith("# device")
            )

            try:
                self._devices = tuple(line.split(":")[1] for line in device_lines)
            except ValueError:
                raise_from(
                    exc=RuntimeError("Error reading step sizes from log file."),
                    cause=None,
                )

            start_point_lines = (
                line
                for line in log_file_lines
                if line.lower().startswith("# start point")
            )

            try:
                self._start_points = tuple(
                    float(line.split(":")[1].strip().split(" ")[0])
                    for line in start_point_lines
                )
            except ValueError:
                raise_from(
                    exc=RuntimeError("Error reading start points from log file."),
                    cause=None,
                )

            end_point_lines = (
                line
                for line in log_file_lines
                if line.lower().startswith("# end point")
            )
            try:
                self._end_points = tuple(
                    float(line.split(":")[1].strip().split(" ")[0])
                    for line in end_point_lines
                )
            except ValueError:
                raise_from(
                    exc=RuntimeError("Error reading end points from log file."),
                    cause=None,
                )

            self._speed_report_interval = monitor_parameters.get_param(
                section="General",
                parameter="speed_report_interval",
                type_=int,
                required=True,
            )

            self._stxm = None
            self._dpc = None

            self._fs_integr_image = None
            self._ss_integr_image = None

            self._num_events = 0
            self._old_time = time.time()
            self._time = None

            broadcast_socket_ip = monitor_parameters.get_param(
                section="General", parameter="publish_ip", type_=str
            )
            broadcast_socket_port = monitor_parameters.get_param(
                section="General", parameter="publish_port", type_=int
            )

            self._data_broadcast_socket = onda_zmq.DataBroadcaster(
                publish_ip=broadcast_socket_ip, publish_port=broadcast_socket_port
            )

            print("Starting the monitor...")
            sys.stdout.flush()

    def process_data(self, data):
        """
        Processes frame data.

        Performs detector and dark calibration corrections. If the current scan is a
        2d scan, calculates STXM and DPC data for the frame. If the scan is instead
        1d, computes integrals along the two dimention of the frame.

        Args:

            data (Dict): a dictionary containing the frame raw data. Keys in the
                dictionary correspond to entries in the required_data list in the
                configuration file (e.g.: 'detector_distance', 'beam_energy',
                'detector_data', etc.).

        Returns:

            Tuple: a tuple where the first field is a dictionary containing the data
            that should be sent to the master node, and the second is the rank of the
            current worker.
        """
        results_dict = {}
        if self._calibration_alg is not None:
            calib_det_data = self._calibration_alg.apply_calibration(
                calibration_file_name=data["detector_data"]
            )
        else:
            calib_det_data = data["detector_data"]

        corr_det_data = self._dark_cal_corr_alg.apply_darkcal_correction(
            data=calib_det_data
        )

        sum1 = corr_det_data[self._mask == 1].sum()
        sum2 = corr_det_data[self._mask == 2].sum()
        sum3 = corr_det_data[self._mask == 3].sum()
        sum4 = corr_det_data[self._mask == 4].sum()

        stxm = sum1 + sum2 + sum3 + sum4

        dpc = 0

        if (
            numpy.count_nonzero(sum1) != 0
            and numpy.count_nonzero(sum2) != 0
            and numpy.count_nonzero(sum3) != 0
            and numpy.count_nonzero(sum4) != 0
        ):
            dpc = numpy.sqrt(
                ((sum1 + sum3 - sum2 - sum4) ** 2 + (sum1 + sum2 - sum3 - sum4) ** 2)
                / (sum1 ** 2 + sum2 ** 2 + sum3 ** 2 + sum4 ** 2)
            )

        integr_ss = corr_det_data.sum(axis=0)
        integr_fs = corr_det_data.sum(axis=1)

        results_dict["stxm"] = stxm
        results_dict["dpc"] = dpc
        results_dict["integr_ss"] = integr_ss
        results_dict["integr_fs"] = integr_fs
        results_dict["motor_positions"] = data["motor_positions"]
        results_dict["index_in_scan"] = data["index_in_scan"]
        results_dict["timestamp"] = data["timestamp"]

        return results_dict, self.rank

    def collect_data(self, data):
        """
        Assembles data for a scan and broacasts it for visualization.

        TODO: Description.

        Args:

            data (Tuple): a tuple where the first field is a dictionary containing the
                data received from a worker node, and the second is the rank of the
                worker node sending the data.
        """
        results_dict, _ = data
        self._num_events += 1

        if self._stxm is None and self._fs_integr_image is None:

            if self._scan_type == 2:
                self._stxm = numpy.zeros(self._points_count)
                self._dpc = numpy.zeros(self._points_count)
            else:
                self._fs_integr_image = numpy.zeros(
                    (results_dict["integr_fs"].shape[0], self._points_count[0])
                )
                self._ss_integr_image = numpy.zeros(
                    (results_dict["integr_ss"].shape[0], self._points_count[0])
                )

        collected_data = {}

        if self._scan_type == 2:

            y_in_grid, x_in_grid = numpy.unravel_index(
                results_dict["index_in_scan"], self._points_count
            )
            self._stxm[y_in_grid, x_in_grid] += results_dict["stxm"]
            self._dpc[y_in_grid, x_in_grid] += results_dict["dpc"]

            collected_data["scan_type"] = 2
            collected_data["stxm"] = self._stxm
            collected_data["dpc"] = self._dpc
            collected_data["ss_start"] = self._start_points[0]
            collected_data["fs_start"] = self._start_points[1]
            collected_data["ss_end"] = self._end_points[0]
            collected_data["fs_end"] = self._end_points[1]
            collected_data["ss_name"] = self._devices[0]
            collected_data["fs_name"] = self._devices[1]
            collected_data["fs_steps"] = self._points_count[1]
            collected_data["ss_steps"] = self._points_count[0]
            collected_data["timestamp"] = results_dict["timestamp"]
            collected_data["num_run"] = int(
                os.path.basename(self._log_file_path).split("_")[1].split(".")[0]
            )

        elif self._scan_type == 1:

            self._fs_integr_image[:, results_dict["index_in_scan"]] += results_dict[
                "integr_fs"
            ]
            self._ss_integr_image[:, results_dict["index_in_scan"]] += results_dict[
                "integr_ss"
            ]

            collected_data["scan_type"] = 1
            collected_data["ss_integr_image"] = self._ss_integr_image
            collected_data["fs_integr_image"] = self._fs_integr_image
            collected_data["fs_start"] = self._start_points[0]
            collected_data["fs_end"] = self._end_points[0]
            collected_data["fs_name"] = self._devices[0]
            collected_data["fs_steps"] = self._points_count[0]
            collected_data["timestamp"] = results_dict["timestamp"]
            collected_data["num_run"] = int(
                os.path.basename(self._log_file_path).split("_")[1].split(".")[0]
            )

        self._data_broadcast_socket.send_data(
            tag=u"ondadata", message=(collected_data,)
        )

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
