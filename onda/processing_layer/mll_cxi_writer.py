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

import h5py
import numpy
from scipy import constants
from future.utils import raise_from

from onda.algorithms import calibration_algorithms as calib_algs
from onda.algorithms import generic_algorithms as gen_algs
from onda.parallelization_layer import mpi


class OndaMonitor(mpi.ParallelizationEngine):
    """
    An OnDA data collector for multi-layer lens experiments.

    This monitor collects images from 1-d and 2-d scans and saves them, together with
    other relevant data (motor positions, etc.) in a HDF5 file.

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

            print("Starting worker: {0}.".format(self.rank))
            sys.stdout.flush()

        if self.role == "master":

            # Reads information about the scan from a log file
            source_parts = source.split(":")
            self._log_file_path = source_parts[1]

            print("Reading log file: {0}".format(self._log_file_path))

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

            # Reads from the configuration file the base path for the output file.
            self._hdf5_base_path = monitor_parameters.get_param(
                section="MLL", parameter="hdf5_base_path", type_=str, required=True
            )

            # Reads from the configuration file the basis vectors, and stores them in
            # an attribute.
            self._basis_ss_vector = monitor_parameters.get_param(
                section="MLL", parameter="ss_basis_vector", type_=list, required=True
            )
            self._basis_fs_vector = monitor_parameters.get_param(
                section="MLL", parameter="fs_basis_vector", type_=list, required=True
            )
            self._basis_vectors = numpy.array(
                [self._basis_ss_vector, self._basis_fs_vector]
            )

            # Looks in the configuration file for the path to a file containing a mask
            # that will be saved in the output HDF5 file, and for the internal HDF5
            # path to the mask in the file. If this information is provided, loads the
            # mask from the file and stores it as a property.
            mask_filename = monitor_parameters.get_param(
                section="MLL", parameter="mask_file_name", type_=str
            )
            if mask_filename:
                mask_hdf5_path = monitor_parameters.get_param(
                    section="MLL", parameter="mask_hdf5_path", type_=str, required=True
                )
                try:
                    with h5py.File(name=mask_filename, mode="r") as fhandle:
                        self._mask = fhandle[mask_hdf5_path]
                except OSError:
                    raise_from(
                        exc=RuntimeError(
                            "Error reading the {} HDF5 file.".format(mask_filename)
                        ),
                        cause=None,
                    )
            else:
                self._mask = None

            # Reads from the configuration file the size of a pixel of the detector.
            self._pixel_size = monitor_parameters.get_param(
                section="MLL", parameter="pixel_size", type_=float, required=True
            )

            self._speed_report_interval = monitor_parameters.get_param(
                section="General",
                parameter="speed_report_interval",
                type_=int,
                required=True,
            )

            self._num_events = 0
            self._old_time = time.time()
            self._time = None

            self._hdf5_file_handle = None

            print("Starting the monitor...")
            sys.stdout.flush()

    def process_data(self, data):
        """
        Processes frame data.

        Performs detector and dark calibration corrections.

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

        results_dict["motor_positions"] = tuple(
            float(mot_pos) * 10e-9 for mot_pos in data["motor_positions"]
        )

        results_dict["corrected_detector_data"] = corr_det_data
        results_dict["index_in_scan"] = data["index_in_scan"]
        results_dict["detector_distance"] = data["detector_distance"]
        results_dict["beam_energy"] = data["beam_energy"]
        results_dict["timestamp"] = data["timestamp"]

        return results_dict, self.rank

    def collect_data(self, data):
        """
        Assembles data for a scan and saves it to an HDF5 file.

        Args:

            data (Tuple): a tuple where the first field is a dictionary containing the
                data received from a worker node, and the second is the rank of the
                worker node sending the data.
        """
        results_dict, _ = data

        if not self._hdf5_file_handle:
            # If the file is not already open, opens the file and create its internal
            # structure.
            hdf5_file_name = "{0}.cxi".format(
                os.path.basename(self._log_file_path).split(".")[0]
            )
            hdf5_full_path = "{0}".format(
                os.path.join(self._hdf5_base_path, hdf5_file_name)
            )
            print("ONDA: Writing file {0}.".format(hdf5_full_path))
            self._hdf5_file_handle = h5py.File(hdf5_full_path, "w")

            if self._scan_type == 2:
                num_frames = self._points_count[0] * self._points_count[1]
            else:
                num_frames = self._points_count[0]

            image_shape = results_dict["corrected_detector_data"].shape
            image_dtype = results_dict["corrected_detector_data"].dtype

            # Creates the dataset that will store the detector data.
            self._hdf5_file_handle.create_dataset(
                "/entry_1/data_1/data",
                shape=(num_frames,) + image_shape,
                dtype=image_dtype,
            )

            # Creates a dataset that stores the basis vectors.
            basis_vectors_array = numpy.zeros((num_frames, 2, 3))
            for frame_idx in range(0, num_frames):
                basis_vectors_array[frame_idx] = self._basis_vectors
            self._hdf5_file_handle.create_dataset(
                "/instrument_1/detector_1/basis_vectors", data=basis_vectors_array
            )

            # Creates the dataset that stores the detector distance.
            self._hdf5_file_handle.create_dataset(
                "/instrument_1/detector_1/distance",
                data=results_dict["detector_distance"],
            )

            # Creates the dataset that stores a bad pixel mask. If a mask was
            # previousy loaded from a file, uses that one. If not, creates an
            # all-pass mask of the appropriate size.
            if not self._mask:
                self._mask = numpy.ones(results_dict["corrected_detector_data"].shape)
            self._hdf5_file_handle.create_dataset(
                "/mask_maker/mask", data=self._mask.astype(numpy.bool)
            )

            # Creates the datasets that store the pixel size.
            self._hdf5_file_handle.create_dataset(
                "/instrument_1/detector_1/x_pixel_size", data=self._pixel_size
            )
            self._hdf5_file_handle.create_dataset(
                "/instrument_1/detector_1/y_pixel_size", data=self._pixel_size
            )

            # Creates the datasets that store the beam energy and wavelength.
            energy = results_dict["beam_energy"] * constants.e
            wavelength = (constants.h * constants.c) / energy
            self._hdf5_file_handle.create_dataset(
                "/instrument_1/source_1/wavelength", data=wavelength
            )
            self._hdf5_file_handle.create_dataset(
                "/instrument_1/source_1/energy", data=energy
            )

            # Creates the dataset that will store the motor positions.
            if self._scan_type == 2:
                self._hdf5_file_handle.create_dataset(
                    "/entry_1/sample_3/geometry/translation",
                    data=numpy.zeros((num_frames, 3)),
                )
            else:
                self._hdf5_file_handle.create_dataset(
                    "/entry_1/sample_3/geometry/translation",
                    data=numpy.zeros((num_frames, 3)),
                )

            # Creates the dataset that will store the list of good frames.
            self._hdf5_file_handle.create_dataset(
                "/frame_selector/good_frames", data=numpy.arange(0, num_frames)
            )

        # Writes the detector and motor position data of each frame.
        self._hdf5_file_handle["/entry_1/data_1/data"][
            self._num_events, ...
        ] = results_dict["corrected_detector_data"]

        self._hdf5_file_handle["/entry_1/sample_3/geometry/translation"][
            self._num_events, 0:self._scan_type
        ] = results_dict["motor_positions"]

        self._num_events += 1

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

    def end_processing(self):
        """
        Cleans up after the processing is finished.

        Closes the file and notifies the user about the end of the processing.
        """
        print("ONDA: Closing file.")
        self._hdf5_file_handle.close()
        print("ONDA: Done.")
