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
OnDA Crystallography.

This module implements an OnDA real-time monitor for serial x-ray
crystallography experiments.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import collections
import sys
import time
from builtins import str  # pylint: disable=W0622

from onda.algorithms import calibration_algorithms as calib_algs
from onda.algorithms import crystallography_algorithms as cryst_algs
from onda.algorithms import generic_algorithms as gen_algs
from onda.cfelpyutils import crystfel_utils, geometry_utils
from onda.parallelization_layer import mpi
from onda.utils import zmq as onda_zmq
from onda.utils import named_tuples
from onda.utils.dynamic_import import get_peakfinder8_info


class OndaMonitor(mpi.ParallelizationEngine):
    """
    An OnDA real-time monitor for serial crystallography experiments.

    An OnDA monitor for x-ray crystallography experiments. Provide real
    time hit and saturation rate information, plus a virtual powder
    pattern-style plot of the processed data. Optionally, apply
    detector calibration, dark calibration and gain map correction to
    each frame. Support also broadcasting of corrected frame data for
    visualization.

    Carry out the peak finding using the peakfinder8 algorithm from the
    Cheetah software package:

    A. Barty, R. A. Kirian, F. R. N. C. Maia, M. Hantke, C. H. Yoon,
    T. A. White, and H. N. Chapman, "Cheetah: software for
    high-throughput reduction and analysis of serial femtosecond X-ray
    diffraction data," J Appl Crystallogr, vol. 47,
    pp. 1118-1131 (2014).
    """
    def __init__(self,
                 source,
                 monitor_parameters):
        """
        Initialize the OndaMonitor class.

        Args:

            source (str): A string describing the data source. The
                exact format of the string depends on the data recovery
                layer used by the monitor (e.g: a psana experiment
                descriptor at the LCLS facility, a description of the
                machine where HiDRA is running at the Petra III
                facility, etc.)

            monitor_params (:obj:`onda.utils.parameters.MonitorParams`):
                a MonitorParams object containing the monitor
                parameters from the configuration file.
        """
        # Call the parent class's cunstructor.
        super(OndaMonitor, self).__init__(
            process_func=self.process_data,
            collect_func=self.collect_data,
            source=source,
            monitor_params=monitor_parameters
        )

        if self.role == 'worker':

            # Check in the configuration file if calibration is
            # requested.
            requested_calib_alg = monitor_parameters.get_param(
                section='DetectorCalibration',
                parameter='calibration_algorithm',
                type_=str
            )

            if requested_calib_alg is not None:
                # If it is, read from the configuration file which
                # algorithm should be used.
                calibration_alg_class = getattr(
                    calib_algs,
                    requested_calib_alg
                )

                # Instantiate the calibration algorithm and store it in
                # an attribute, so it can be called later.
                self._calibration_alg = calibration_alg_class(
                    calibration_file=monitor_parameters.get_param(
                        section='DetectorCalibration',
                        parameter='calibration_file',
                        type_=str,
                        required=True
                    )
                )
            else:

                # If no calibration is required store None in the
                # 'calibration_alg' attribute.
                self._calibration_alg = None

            # Initialize the hit_sending_counter to keep track of how
            # often the detector frame data needs to be sent to the
            # master worker.
            self._hit_sending_counter = 0

            # Read from the configuration file all the parameters
            # needed to instantiate the dark calibration correction
            # algorithm.
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

            # Instantiate the algorithm and store it in an attribute so
            # that it can be applied later.
            self._dark_cal_corr_alg = gen_algs.DarkCalCorrection(
                darkcal_filename=dark_cal_fname,
                darkcal_hdf5_path=dark_cal_hdf5_pth,
                mask_filename=dark_cal_mask_fname,
                mask_hdf5_path=dark_cal_mask_hdf5_pth,
                gain_map_filename=dark_cal_gain_map_fname,
                gain_map_hdf5_path=dark_cal_gain_map_hdf5_pth
            )

            # Load the geometry data and compute the pixel maps.
            geometry_filename = monitor_parameters.get_param(
                section='General',
                parameter='geometry_file',
                type_=str,
                required=True
            )

            geometry = crystfel_utils.load_crystfel_geometry(geometry_filename)
            pixelmaps = geometry_utils.compute_pix_maps(geometry)
            radius_pixel_map = pixelmaps.r

            # Read from the configuration file all the parameters
            # needed to instantiate the peakfinder8 algorithm.
            pf8_max_num_peaks = monitor_parameters.get_param(
                section='Peakfinder8PeakDetection',
                parameter='max_num_peaks',
                type_=int,
                required=True
            )

            pf8_adc_threshold = monitor_parameters.get_param(
                section='Peakfinder8PeakDetection',
                parameter='adc_threshold',
                type_=float,
                required=True
            )

            pf8_minimum_snr = monitor_parameters.get_param(
                section='Peakfinder8PeakDetection',
                parameter='minimum_snr',
                type_=float,
                required=True
            )

            pf8_min_pixel_count = monitor_parameters.get_param(
                section='Peakfinder8PeakDetection',
                parameter='min_pixel_count',
                type_=int,
                required=True
            )

            pf8_max_pixel_count = monitor_parameters.get_param(
                section='Peakfinder8PeakDetection',
                parameter='max_pixel_count',
                type_=int,
                required=True
            )

            pf8_local_bg_radius = monitor_parameters.get_param(
                section='Peakfinder8PeakDetection',
                parameter='local_bg_radius',
                type_=int,
                required=True
            )

            pf8_min_res = monitor_parameters.get_param(
                section='Peakfinder8PeakDetection',
                parameter='min_res',
                type_=int,
                required=True
            )

            pf8_max_res = monitor_parameters.get_param(
                section='Peakfinder8PeakDetection',
                parameter='max_res',
                type_=int,
                required=True
            )

            pf8_bad_pixel_map_fname = monitor_parameters.get_param(
                section='Peakfinder8PeakDetection',
                parameter='bad_pixel_map_filename',
                type_=str,
                required=True
            )

            pf8_bad_pixel_map_hdf5_path = monitor_parameters.get_param(
                section='Peakfinder8PeakDetection',
                parameter='bad_pixel_map_hdf5_path',
                type_=str,
                required=True
            )

            # Recovers the peakfinder8 information for the detector
            # being used.
            pf8_detector_info = get_peakfinder8_info(
                monitor_params=self._mon_params,
                detector='detector_data',
            )

            # Instantiate the peakfinder8 algorithm and store it in an
            # attribute.
            self._peakfinder8_peak_det = cryst_algs.Peakfinder8PeakDetection(
                max_num_peaks=pf8_max_num_peaks,
                asic_nx=pf8_detector_info.asic_nx,
                asic_ny=pf8_detector_info.asic_ny,
                nasics_x=pf8_detector_info.nasics_x,
                nasics_y=pf8_detector_info.nasics_y,
                adc_threshold=pf8_adc_threshold,
                minimum_snr=pf8_minimum_snr,
                min_pixel_count=pf8_min_pixel_count,
                max_pixel_count=pf8_max_pixel_count,
                local_bg_radius=pf8_local_bg_radius,
                min_res=pf8_min_res,
                max_res=pf8_max_res,
                bad_pixel_map_filename=pf8_bad_pixel_map_fname,
                bad_pixel_map_hdf5_path=pf8_bad_pixel_map_hdf5_path,
                radius_pixel_map=radius_pixel_map
            )

            # Read some additional peak-finding parameters from the
            # configuration file and save them to attributes.
            self._max_saturated_peaks = monitor_parameters.get_param(
                section='General',
                parameter='max_saturated_peaks',
                type_=int,
                required=True
            )

            self._min_num_peaks_for_hit = monitor_parameters.get_param(
                section='General',
                parameter='min_num_peaks_for_hit',
                type_=int,
                required=True
            )

            self._max_num_peaks_for_hit = monitor_parameters.get_param(
                section='General',
                parameter='max_num_peaks_for_hit',
                type_=int,
                required=True
            )

            # Read from the configuration file the ADC threshold value
            # above which a pixel should be considered saturated.
            self._saturation_value = monitor_parameters.get_param(
                section='General',
                parameter='saturation_value',
                type_=int,
                required=True
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

            # Notify the user that the worker node is starting.
            print("Starting worker: {0}.".format(self.rank))
            sys.stdout.flush()

        if self.role == 'master':

            # Read from the configuration file how often (in events)
            # the master node should print the estimated processing
            # speed.
            self._speed_report_interval = monitor_parameters.get_param(
                section='General',
                parameter='speed_report_interval',
                type_=int,
                required=True
            )

            # Read from the configuration file if the geometry is
            # optimized or not.
            self._optimized_geometry = monitor_parameters.get_param(
                section='General',
                parameter='geometry_is_optimized',
                type_=bool,
                required=True
            )

            # Read from the configuration file how many events should
            # be accumulated by the master node before broadcasting the
            # acccumulated data.
            pa_num_events_to_accumulate = monitor_parameters.get_param(
                section='PeakAccumulator',
                parameter='num_events_to_accumulate',
                type_=int,
                required=True
            )

            # Instantiate the peak accumulator algorithm and assign it
            # to an attribute.
            self._accumulator = cryst_algs.PeakAccumulator(
                num_events_to_accumulate=pa_num_events_to_accumulate
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
            # saturation_rate should be.
            self._run_avg_wdw_size = monitor_parameters.get_param(
                section='General',
                parameter='running_average_size',
                type_=int,
                required=True
            )

            # Initalize the running windows and the averages.
            self._hit_rate_run_wdw = collections.deque(
                [0.0] * self._run_avg_wdw_size,
                maxlen=self._run_avg_wdw_size
            )

            self._saturation_rate_run_wdw = collections.deque(
                [0.0] * self._run_avg_wdw_size,
                maxlen=self._run_avg_wdw_size
            )

            self._avg_hit_rate = 0
            self._avg_sat_rate = 0

            # Read from the configuration file which IP and port should
            # be used for the data broadcasting socket.
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

            # Initialize the ZMQ socket.
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
        peak information and evaluate the extracted data. Return a
        dictionary with the data to be sent to the master node.

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
        # Initialize the dictionary that will store the data to be
        # sent to the master.
        results_dict = {}

        # Apply the calibration algorithm if it has been requested.
        if self._calibration_alg is not None:
            calib_det_data = self._calibration_alg.apply_calibration(
                calibration_file_name=data['detector_data']
            )
        else:
            calib_det_data = data['detector_data']

        # Apply the dark cal correction algorithm.
        corr_det_data = self._dark_cal_corr_alg.apply_darkcal_correction(
            data=calib_det_data
        )

        # Apply the peakfinder8 algorithm.
        peak_list = self._peakfinder8_peak_det.find_peaks(corr_det_data)

        # Determine if the the frame should be labelled as 'saturated'.
        sat = len(
            [x for x in peak_list.intensity if x > self._saturation_value]
        ) > self._max_saturated_peaks

        # Determine if the the frame should be labelled as a 'hit'.
        hit = (
            self._min_num_peaks_for_hit <
            len(peak_list.intensity) <
            self._max_num_peaks_for_hit
        )

        # Store in the 'result_dict' dictionary the data that must be
        # sent to the master node.
        results_dict['timestamp'] = data['timestamp']
        if not hit:
            results_dict['peak_list'] = named_tuples.PeakList([], [], [])
        else:
            results_dict['peak_list'] = peak_list
        results_dict['saturation_flag'] = sat
        results_dict['hit_flag'] = hit
        results_dict['detector_distance'] = data['detector_distance']
        results_dict['beam_energy'] = data['beam_energy']
        results_dict['native_data_shape'] = data['detector_data'].shape

        if hit:
            self._hit_sending_counter += 1
            if (
                    (
                        self._hit_sending_interval < 0
                    ) or (
                        self._hit_sending_counter ==
                        abs(self._hit_sending_interval)
                    )
            ):
                # If the frame is a hit, and if the
                # 'hit_sending_interval' attribute says we should send
                # the detector frame data to the master node, add it to
                # the dictionary (and reset the counter).
                results_dict['detector_data'] = corr_det_data
                self._hit_sending_counter = 0

        # Return the dictionary to be sent to the master node, together
        # with information about the worker node that is sending the
        # data.
        return results_dict, self.rank

    def collect_data(self, data):
        """
        Compute aggregated data statistics and broadcast the data.

        Accumulate data received from the worker nodes and compute
        statistics on the aggregated data (e.g.: hit rate,
        saturation_rate). Finally, broadcast the data.

        Args:

            data (tuple): a tuple where the first field is a dictionary
                containing the data received from a worker node, and
                the second is the rank of the worker node sending the
                data.
        """

        # Create two dictionary that will hold data to be sent to
        # data to broadcast (the reducted data and the detector frame
        # data respectively).
        collected_data = {}
        collected_framedata = {}

        # Recover the dictionary that stores the data sent by the
        # worker node.
        results_dict, _ = data

        # Mark the event as collected, increasing the counter.
        self._num_events += 1

        # Update the windows used to compute the running average, then
        # compute the new average hit and saturation rates.
        self._hit_rate_run_wdw.append(
            float(
                results_dict['hit_flag']
            )
        )

        self._saturation_rate_run_wdw.append(
            float(
                results_dict['saturation_flag']
                )
        )
        self._saturation_rate_run_wdw.popleft()
        self._avg_hit_rate = (
            sum(self._hit_rate_run_wdw) /
            self._run_avg_wdw_size
        )

        self._avg_sat_rate = (
            sum(self._saturation_rate_run_wdw) /
            self._run_avg_wdw_size
        )

        # Add the detected peaks to the peak accumulator algorithm.
        collected_peaks = self._accumulator.accumulate_peaks(
            results_dict['peak_list']
        )
        if collected_peaks is not None:

            # If the peak accumulator algorithm returned some data (not
            # None), the accumulator has been reset: add the returned
            # data to the 'collected_data' dictionary.
            collected_data['peak_list'] = collected_peaks
            collected_data['timestamp'] = results_dict['timestamp']
            collected_data['hit_rate'] = self._avg_hit_rate
            collected_data['saturation_rate'] = self._avg_sat_rate
            collected_data['detector_distance'] = (
                results_dict['detector_distance']
            )
            collected_data['beam_energy'] = results_dict['beam_energy']
            collected_data['optimized_geometry'] = self._optimized_geometry
            collected_data['native_data_shape'] = (
                results_dict['native_data_shape']
            )

            # Broadcast the data.
            self._zmq_pub_socket.send_data('ondadata', collected_data)

        if 'detector_data' in results_dict:

            # If detector frame data is found in the data received from
            # a worker node, it must be broadcast: add it to the
            # 'collected_framedata' dictionary, together with the peak
            # and timestamp information.
            collected_framedata['detector_data'] = (
                results_dict['detector_data']
            )
            collected_framedata['peak_list'] = results_dict['peak_list']
            collected_framedata['timestamp'] = results_dict['timestamp']

            # Broadcast the detector frame data.
            self._zmq_pub_socket.send_data('ondarawdata', collected_framedata)

        if self._num_events % self._speed_report_interval == 0:

            # If the 'speed_report_interval' attribute says that the
            # estimated speed should be reported to the user, use the
            # time elapsed since the last message to compute the
            # processing speed.
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

            # Report everthing to the user.
            print(speed_report_msg)
            sys.stdout.flush()
            self._old_time = now_time
