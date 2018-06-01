#    This file is part of OnDA.
#
#    OnDA is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    OnDA is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with OnDA.  If not, see <http://www.gnu.org/licenses/>.
"""
An OnDA online monitor for crystallography experiments.

Exports:

    Classes:

        OndaMonitor: an OnDA monitor for x-ray crystallography
        experiments.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import collections
import sys
import time
from builtins import str  # pylint: disable=W0622

from onda.algorithms import calibration_algorithms as calib_algs
from onda.algorithms import generic_algorithms as gen_algs
from onda.parallelization_layer import mpi
from onda.utils import zmq as onda_zmq


class OndaMonitor(mpi.ParallelizationEngine):
    """
    An OnDA online monitor for fiber diffraction experiments.

    A monitor for x-ray fiber diffraction experiments. Ususe a simple
    hit detection mechanism based on the intensity of the signal on
    a x-ray detector. Provides real time hit rate information, plus
    real time information on the total intensity observed on the
    detector. In addition to the normal GUI, an additional viewer,
    which shows raw detecor data for a selection of the processed
    frames, is also supported.
    """
    def __init__(self,
                 source,
                 monitor_parameters):
        """
        Initialize the OndaMonitor class.

        Args:

            source (str): A string describing the data source. The
                format of the string depends on the Data Recovery layer
                that the monitor uses (e.g: the string represents a
                psana experiment descriptor for the psana backend, the
                IP address where HiDRA is running for the Petra III
                backend, etc.)

            monitor_params (MonitorParams): a MonitorParams object
                containing the monitor parameters from the
                configuration file.
        """
        # Call the constructor of the parent class
        # (mpi.ParallelizationEngine).
        super(OndaMonitor, self).__init__(
            map_func=self.process_data,
            reduce_func=self.collect_data,
            source=source,
            monitor_params=monitor_parameters
        )
        if self.role == 'worker':
            # Check if calibration is requested, and if it is, read
            # which algorithm should be used. Instantiate the
            # calibration algorithm and store it in an attribute, so it
            # can be called later. If no calibration has been store
            # None in the same attribute.
            requested_calib_alg = monitor_parameters.get_param(
                section='DetectorCalibration',
                parameter='calibration_algorithm',
                type_=str
            )
            if requested_calib_alg is not None:
                calibration_alg_class = getattr(
                    calib_algs,
                    requested_calib_alg
                )

                self._calibration_alg_class = calibration_alg_class(
                    calibration_file=monitor_parameters.get_param(
                        section='DetectorCalibration',
                        parameter='calibration_file',
                        type_=str,
                        required=True
                    )
                )
            else:
                self._calibration_alg = None

            # Initialize the hit_sending_counter to keep track of how
            # often the detector frame data needs to be sent to the
            # master worker.
            self._hit_sending_counter = 0

            # Read from the configuration file all the parameters
            # needed to instantiate the dark calibration correction
            # algorithm, then instantiate the algorithm and store it in
            # an attribute so that it can be applied later.
            dark_cal_fname = monitor_parameters.get_param(
                section='DarkCalCorrection',
                parameter='filename',
                type_=str,
                required=True
            )

            dark_cal_hdf5_pth = monitor_parameters.get_param(
                section='DarkCalCorrection',
                parameter='hdf5_path',
                type_=str,
                required=True
            )

            dark_cal_mask_fname = monitor_parameters.get_param(
                section='DarkCalCorrection',
                parameter='mask_filename',
                type_=str
            )

            dark_cal_mask_hdf5_pth = monitor_parameters.get_param(
                section='DarkCalCorrection',
                parameter='mask_hdf5_path',
                type_=str
            )

            dark_cal_gain_map_fname = monitor_parameters.get_param(
                section='DarkCalCorrection',
                parameter='gain_map_filename',
                type_=str
            )

            dark_cal_gain_map_hdf5_pth = monitor_parameters.get_param(
                section='DarkCalCorrection',
                parameter='gain_map_hdf5_path',
                type_=str
            )

            self._dark_cal_corr_alg = gen_algs.DarkCalCorrection(
                darkcal_filename=dark_cal_fname,
                darkcal_hdf5_path=dark_cal_hdf5_pth,
                mask_filename=dark_cal_mask_fname,
                mask_hdf5_path=dark_cal_mask_hdf5_pth,
                gain_map_filename=dark_cal_gain_map_fname,
                gain_map_hdf5_path=dark_cal_gain_map_hdf5_pth
            )

            # Read from the configuration file the interval (in events
            # labelled as 'hits') at which the full frame detector data
            # should be sent to the master node.
            self._hit_sending_interval = monitor_parameters.get_param(
                section='General',
                parameter='hit_sending_interval',
                type_=int,
                required=True
            )

            # Read from the configuration file the threshold used
            # when computing the total intensity on the detector.
            self._sum_threshold_detector_data = monitor_parameters.get_param(
                section='General',
                parameter='sum_threshold_detector_data',
                type_=int,
                required=True
            )

            # Read from the configuration file the threshold used to determine
            # if the intensity on the detector.corresponds to a hit.
            self._hit_threshold_detector_data = monitor_parameters.get_param(
                section='General',
                parameter='hit_threshold_detector_data',
                type_=int,
                required=True
            )

            print("Starting worker: {0}.".format(self.rank))
            sys.stdout.flush()

        if self.role == 'master':
            # Read from the configuration file how often the master
            # node should print to the console the estimated processing
            # speed.
            self._speed_report_interval = monitor_parameters.get_param(
                section='General',
                parameter='speed_report_interval',
                type_=int,
                required=True
            )

            # Read from the configuration file how many events should
            # be accumulated by the master node before sending the data
            # to the GUI.
            self._num_events_to_accumulate = monitor_parameters.get_param(
                section='General',
                parameter='num_events_to_accumulate',
                type_=int,
                required=True
            )

            # Initialize the num_events counter to keep track of the
            # number of processed events.
            self._num_events = 0

            # Initialize the attributes used to keep track of how long
            # it took to process events.
            self._old_time = time.time()
            self._time = None

            # Read from the configuration file how large (in number of
            # events) the running average windows for hit_rate and
            # saturation_rate should be, then initalize the windows and
            # the averages.
            self._run_avg_wdw_size = monitor_parameters.get_param(
                section='General',
                parameter='running_average_size',
                type_=int,
                required=True
            )

            self._hit_rate_run_wdw = collections.deque(
                [0.0] * self._run_avg_wdw_size,
                maxlen=self._run_avg_wdw_size
            )

            self._avg_hit_rate = 0

            # Initialize the lists that will contain the accumulated
            # total intensity data from the detector.
            self._accumulated_sum_detector = []

            # Initialize the lists that will contain the accumulated
            # hit rate from the detector.
            self._accumulated_hit_rate = []

            # Read from the configuration file which IP and port should
            # be used for the socket that broadcasts data to the
            # GUI(s), then initialize the ZMQ socket.
            publisher_socket_ip = monitor_parameters.get_param(
                section='General',
                parameter='publish_ip',
                type_=str
            )

            publisher_socket_port = monitor_parameters.get_param(
                section='General',
                parameter='publish_port',
                type_=int
            )

            self._zmq_pub_socket = onda_zmq.ZMQOndaPublisherSocket(
                publish_ip=publisher_socket_ip,
                publish_port=publisher_socket_port
            )

            print("Starting the monitor...")
            sys.stdout.flush()

    def process_data(self, data):
        """
        Process frame information.

        Perform detector and dark calibration corrections, extract the
        peak information and evalute the extracted data. Discard the
        raw data and prepare the reduced data to be sent to the master
        node.

        Args:

            data (dict): a dictionary containing the frame raw data.
                Keys in the dictionary correspond to entries in the
                required_data list in the configuration file (e.g.:
                'detector_distance', 'beam_energy', 'detector_data',
                etc.).

        Returns:

            tuple: a tuple where the first field is a dictionary
            containing the data that should be sent to the master node,
            and the second is the rank of the worker node sending the
            data.
        """
        results_dict = {}

        # Apply the calibration algorithm if it has been requested.
        # Then apply the dark cal correction algorithm, then perform
        # the peak finding.
        if self._calibration_alg is not None:
            calib_det_data = self._calibration_alg.apply_calibration(
                calibration_file_name=data['detector_data']
            )
        else:
            calib_det_data = data['detector_data']

        corr_det_data = self._dark_cal_corr_alg.apply_darkcal_correction(
            data=calib_det_data
        )

        # Compute sum of intensity on the detector. Only pixels whose
        # intensity surpasses a certain threshold, defined separately
        # for each detector, are included in the sum.
        sum_detector = (
            data['detector_data'] > self._sum_threshold_detector_data
        ).sum()

        hit = sum_detector > self._hit_threshold_detector_data

        # Store in the 'result_dict' dictionary the data that must be
        # sent to the master node.
        results_dict['timestamp'] = data['timestamp']
        results_dict['detector_distance'] = data['detector_distance']
        results_dict['beam_energy'] = data['beam_energy']
        results_dict['hit_flag'] = hit
        results_dict['sum_detector'] = sum_detector
        results_dict['native_data_shape'] = corr_det_data.shape

        # If the frame is a hit, and if the 'hit_sending_interval'
        # attribute says we should send the raw detector data of the
        # frame to the master node, add it to the dictionary. If the
        # 'hit_sending_interval' has a negative value, add the raw data
        # to the dictionary unconditionally.
        if hit or self._hit_sending_interval < 0:
            self._hit_sending_counter += 1
            if self._hit_sending_counter == abs(self._hit_sending_interval):
                results_dict['detector_data'] = corr_det_data
                self._hit_sending_counter = 0

        # Return the dictionary to be sent to the master node, together
        # with information about the worker node that is sending the
        # data.
        return results_dict, self.rank

    def collect_data(self, data):
        """
        Compute aggregated data statistics and send data to the GUI.

        Accumulate data received from the worker nodes and compute
        statistics on the aggregated data (e.g.: hit rate,
        saturation_rate). Finally, send the data to the GUI for
        visualization (at intervals determined by the user).

        Args:

            data (tuple): a tuple where the first field is a dictionary
                containing the data received from a worker node, and
                the second is the rank of the worker node sending the
                data.
        """

        # Create the two dictionary that will hold data to be sent to
        # the GUI and the 'raw data' GUI respectively.
        collected_data = {}
        collected_rawdata = {}

        # Recover the dictionary that stores the data sent by the
        # worker node, and mark the event as collected, increasing the
        # counter.
        results_dict, _ = data
        self._num_events += 1

        # Update the windows used to compute the running average, then
        # compute the new average hit and saturation rates.
        self._hit_rate_run_wdw.append(
            float(
                results_dict['hit_flag']
            )
        )

        avg_hit_rate = (
            sum(self._hit_rate_run_wdw) /
            self._run_avg_wdw_size
        )

        # If intensity sum data can be found in the data received from
        # the worker, accumulate it. When the data has been
        # accumulated for the number of times requested in the
        # configuration file, send the data to the GUI.
        if 'sum_detector' in results_dict:
            self._accumulated_sum_detector.append(results_dict['sum_detector'])
            self._accumulated_hit_rate.append(avg_hit_rate)
            if (
                    len(self._accumulated_sum_detector) ==
                    self._num_events_to_accumulate
            ):
                collected_data['accumulated_sum_detector'] = (
                    self._accumulated_sum_detector
                )
                collected_data['accumulated_hit_rate'] = (
                    self._accumulated_hit_rate
                )
                collected_data['timestamp'] = results_dict['timestamp']

                self._zmq_pub_socket.send_data(
                    tag='ondadata',
                    message=collected_data
                )
                self._accumulated_sum_detector = []
                self._accumulated_hit_rate = []

        # If raw frame data can be found in the data received from a
        # worker node, it must be sent to the 'raw data' GUI: add it to
        # the 'collected_rawdata' dictionary, and send the dictionary
        # to the 'raw data' GUI.
        if 'detector_data' in results_dict:
            collected_rawdata['detector_data'] = results_dict['detector_data']
            collected_rawdata['timestamp'] = results_dict['timestamp']
            self._zmq_pub_socket.send_data('ondarawdata', collected_rawdata)

        # If the 'speed_report_interval' attribute says that the
        # estimated speed should be reported to the user, use the time
        # elapsed since the last message  to compute the speed, and
        # report everything to the user.
        if self._num_events % self._speed_report_interval == 0:
            now_time = time.time()
            speed_report_msg = (
                "Processed: {0} in {1:.2f} seconds {2:.2f} Hz)".format(
                    self._num_events,
                    now_time - self._old_time,
                    (
                        float(self._speed_report_interval) /
                        float(now_time - self._old_time)
                    )
                )
            )
            print(speed_report_msg)
            sys.stdout.flush()
            self._old_time = now_time
