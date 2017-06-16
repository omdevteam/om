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


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from builtins import str
from collections import deque, namedtuple
import sys
import time

import cfelpyutils.cfel_geom as cgm
import ondautils.onda_dynamic_import_utils as di
import ondautils.onda_param_utils as op
import ondautils.onda_zmq_monitor_utils as zut
import algorithms.calibration_algorithms as calibalg
import algorithms.crystallography_algorithms as calg
import algorithms.generic_algorithms as galg


par_layer = di.import_correct_layer_module('parallelization_layer', op.monitor_params)
MasterWorker = di.import_class_from_layer('MasterWorker', par_layer)


class Onda(MasterWorker):
    def __init__(self, source):

        super(Onda, self).__init__(map_func=self.process_data,
                                   reduce_func=self.collect_data,
                                   source=source)

        if self.role == 'worker':

            pixelmap_radius = cgm.pixel_maps_from_geometry_file(op.param('General', 'geometry_file',
                                                                                         str, required=True)).r

            if op.param('DetectorCalibration', 'calibration_algorithm') is not None:

                detector_calibration_alg = di.import_class_from_module(op.param('DetectorCalibration',
                                                                                'calibration_algorithm', str,
                                                                                required=True), calibalg)
                detector_calibration = detector_calibration_alg(op.param('DetectorCalibration', 'calibration_file',
                                                                         str, required=True))
                self._apply_calibration = detector_calibration.apply_calibration
            else:
                self._apply_calibration = lambda x: x

            self._dark_cal_correction = galg.DarkCalCorrection(
                op.param('DarkCalCorrection', 'filename', str, required=True),
                op.param('DarkCalCorrection', 'hdf5_group', str, required=True),
                op.param('DarkCalCorrection', 'apply_mask', bool),
                op.param('DarkCalCorrection', 'mask_filename', str),
                op.param('DarkCalCorrection', 'mask_hdf5_group', str),
                op.param('DarkCalCorrection', 'gain_map_correction', bool),
                op.param('DarkCalCorrection', 'gain_map_filename', str),
                op.param('DarkCalCorrection', 'gain_map_hdf5_group', str)
            )

            self._peakfinder8_peak_det = calg.Peakfinder8PeakDetection(
                op.param('Peakfinder8PeakDetection', 'max_num_peaks', int, required=True),
                op.param('Peakfinder8PeakDetection', 'asics_nx', int, required=True),
                op.param('Peakfinder8PeakDetection', 'asics_ny', int, required=True),
                op.param('Peakfinder8PeakDetection', 'nasics_x', int, required=True),
                op.param('Peakfinder8PeakDetection', 'nasics_y', int, required=True),
                op.param('Peakfinder8PeakDetection', 'adc_threshold', float, required=True),
                op.param('Peakfinder8PeakDetection', 'minimum_snr', float, required=True),
                op.param('Peakfinder8PeakDetection', 'min_pixel_count', int, required=True),
                op.param('Peakfinder8PeakDetection', 'max_pixel_count', int, required=True),
                op.param('Peakfinder8PeakDetection', 'local_bg_radius', int, required=True),
                op.param('Peakfinder8PeakDetection', 'min_res', int, required=True),
                op.param('Peakfinder8PeakDetection', 'max_res', int, required=True),
                op.param('Peakfinder8PeakDetection', 'mask_filename', str, required=True),
                op.param('Peakfinder8PeakDetection', 'mask_hdf5_path', str, required=True),
                pixelmap_radius
            )

            self._max_saturated_peaks = op.param('General', 'max_saturated_peaks', int, required=True)
            self._min_num_peaks_for_hit = op.param('General', 'min_num_peaks_for_hit', int, required=True)
            self._max_num_peaks_for_hit = op.param('General', 'max_num_peaks_for_hit', int, required=True)
            self._saturation_value = op.param('General', 'saturation_value', int, required=True)
            self._hit_sending_interval = op.param('General', 'hit_sending_interval', int, required=True)

            self._hit_sending_counter = 0

            print('Starting worker: {0}.'.format(self.mpi_rank))
            sys.stdout.flush()

        if self.role == 'master':

            asdasdasdas


            self._accumulator = calg.PeakAccumulator(op.param('PeakAccumulator', 'accumulated_shots', int,
                                                              required=True))

            self._num_events = 0
            self._old_time = time.time()

            self._time = None

            self._speed_report_interval = op.param('General', 'speed_report_interval', int, required=True)
            self._optimized_geometry = op.param('General', 'geometry_is_optimized', bool, required=True)

            self._hit_rate_running_w = deque([0.0] * op.param('General', 'running_average_size', int,
                                                              required=True))
            self._saturation_rate_running_w = deque([0.0] * op.param('General', 'running_average_size', int,
                                                                      required=True))

            print('Starting the monitor...')
            sys.stdout.flush()

            self._sending_socket = zut.ZMQOndaPublisherSocket(op.param('General', 'publish_ip', str),
                                                              op.param('General', 'publish_port', int))

            self._hit_rate = 0
            self._sat_rate = 0

    def process_data(self):

        results_dict = {}

        calib_raw_data = self._apply_calibration(self.raw_data)

        corr_raw_data = self._dark_cal_correction.apply_darkcal_correction(calib_raw_data)
        peak_list = self._peakfinder8_peak_det.find_peaks(corr_raw_data)

        sat = len([x for x in peak_list.intensity if x > self._saturation_value]) > self._max_saturated_peaks
        hit = self._min_num_peaks_for_hit < len(peak_list.intensity) < self._max_num_peaks_for_hit

        results_dict['timestamp'] = self.timestamp
        results_dict['peak_list'] = peak_list
        results_dict['sat_flag'] = sat
        results_dict['hit_flag'] = hit
        results_dict['detector_distance'] = self.detector_distance
        results_dict['beam_energy'] = self.beam_energy
        results_dict['native_shape'] = corr_raw_data.shape

        if not hit:
            results_dict['peak_list'] = calg.PeakList([], [], [])

        if hit or self._hit_sending_interval < 0:
            self._hit_sending_counter += 1
            if self._hit_sending_counter == abs(self._hit_sending_interval):
                results_dict['raw_data'] = corr_raw_data
                self._hit_sending_counter = 0

        return results_dict, self.mpi_rank

    def collect_data(self, new):

        collected_data = {}
        collected_rawdata = {}

        results_dict, _ = new
        self._num_events += 1


        self._hit_rate_running_w.append(float(results_dict['hit_flag']))
        self._hit_rate_running_w.popleft()
        self._saturation_rate_running_w.append(float(results_dict['sat_flag']))
        self._saturation_rate_running_w.popleft()

        self._hit_rate = sum(self._hit_rate_running_w) / len(self._hit_rate_running_w)
        self._sat_rate = sum(self._saturation_rate_running_w) / len(self._saturation_rate_running_w)

        collected_peaks = self._accumulator.accumulate_peaks(results_dict['peak_list'])

        if collected_peaks is not None:
            collected_data['peak_list'] = collected_peaks
            collected_data['timestamp'] = results_dict['timestamp']
            collected_data['hit_rate'] = self._hit_rate
            collected_data['sat_rate'] = self._sat_rate
            collected_data['detector_distance'] = results_dict['detector_distance']
            collected_data['beam_energy'] = results_dict['beam_energy']
            collected_data['optimized_geometry'] = self._optimized_geometry
            collected_data['native_shape'] = results_dict['native_shape']

            self._sending_socket.send_data('ondadata', collected_data)

        if 'raw_data' in results_dict:
            collected_rawdata['raw_data'] = results_dict['raw_data']
            collected_rawdata['peak_list'] = results_dict['peak_list']

            self._sending_socket.send_data('ondarawdata', collected_rawdata)

        if self._num_events % self._speed_report_interval == 0:
            now_time = time.time()
            print('Processed: {0} in {1:.2f} seconds ({2:.2f} Hz)'.format(
                self._num_events,
                now_time - self._old_time,
                float(self._speed_report_interval) / float(now_time - self._old_time)))
            sys.stdout.flush()
            self._old_time = now_time
