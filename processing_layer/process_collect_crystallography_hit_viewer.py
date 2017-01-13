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

import collections
import sys
import time

import cfelpyutils.cfel_geom as cgm
import parallelization_layer.utils.onda_dynamic_import as di
import parallelization_layer.utils.onda_params as oa
import parallelization_layer.utils.onda_zmq_monitor_utils as zut
import processing_layer.algorithms.cheetah_algorithms as calg
import processing_layer.algorithms.generic_algorithms as galg


par_layer = di.import_correct_layer_module('parallelization_layer', oa.monitor_params)
MasterWorker = di.import_class_from_layer('MasterWorker', par_layer)


class Onda(MasterWorker):
    def __init__(self, source):

        super(Onda, self).__init__(map_func=self.process_data,
                                   reduce_func=self.collect_data,
                                   source=source)

        if self.role == 'worker':

            _, _, pixelmap_radius = cgm.pixel_maps_from_geometry_file(oa.param('General', 'geometry_file', str))

            self.dark_cal_correction = galg.DarkCalCorrection(oa.param('DarkCalCorrection', 'filename', str),
                                                              oa.param('DarkCalCorrection', 'hdf5_group', str),
                                                              oa.param('DarkCalCorrection', 'apply_mask', bool),
                                                              oa.param('DarkCalCorrection', 'mask_filename', str),
                                                              oa.param('DarkCalCorrection', 'mask_hdf5_group', str),
                                                              oa.param('DarkCalCorrection', 'gain_map_correction',
                                                                       bool),
                                                              oa.param('DarkCalCorrection', 'gain_map_filename', str),
                                                              oa.param('DarkCalCorrection', 'gain_map_hdf5_group', str))

            self.peakfinder8_peak_det = calg.Peakfinder8PeakDetection(
                oa.param('Peakfinder8PeakDetection', 'max_num_peaks', int),
                oa.param('Peakfinder8PeakDetection', 'asics_nx', int),
                oa.param('Peakfinder8PeakDetection', 'asics_ny', int),
                oa.param('Peakfinder8PeakDetection', 'nasics_x', int),
                oa.param('Peakfinder8PeakDetection', 'nasics_y', int),
                oa.param('Peakfinder8PeakDetection', 'adc_threshold', float),
                oa.param('Peakfinder8PeakDetection', 'minimum_snr', float),
                oa.param('Peakfinder8PeakDetection', 'min_pixel_count', int),
                oa.param('Peakfinder8PeakDetection', 'max_pixel_count', int),
                oa.param('Peakfinder8PeakDetection', 'local_bg_radius', int),
                oa.param('Peakfinder8PeakDetection', 'min_res', int),
                oa.param('Peakfinder8PeakDetection', 'max_res', int),
                oa.param('Peakfinder8PeakDetection', 'mask_filename', str),
                oa.param('Peakfinder8PeakDetection', 'mask_hdf5_path', str),
                pixelmap_radius
            )

            self.max_saturated_peaks = oa.param('General', 'max_saturated_peaks', int)
            self.min_num_peaks_for_hit = oa.param('General', 'min_num_peaks_for_hit', int)
            self.max_num_peaks_for_hit = oa.param('General', 'max_num_peaks_for_hit', int)
            self.saturation_value = oa.param('General', 'saturation_value', int)
            self.hit_sending_interval = oa.param('General', 'hit_sending_interval', int)

            self.hit_sending_counter = 0

            print('Starting worker: {0}.'.format(self.mpi_rank))
            sys.stdout.flush()

        if self.role == 'master':

            print('accumulated_shots', oa.param('General', 'accumulated_shots', int))

            self.accumulator = galg.PeakAccumulator(oa.param('PeakAccumulator', 'accumulated_shots', int))

            self.num_events = 0
            self.old_time = time.time()

            self.time = None

            self.speed_report_interval = oa.param('General', 'speed_report_interval', int)
            self.optimized_geometry = oa.param('General', 'geometry_is_optimized', bool)

            self.hit_rate_running_w = collections.deque([0.0] * oa.param('General', 'running_average_size', int))
            self.saturation_rate_running_w = collections.deque([0.0] * oa.param('General', 'running_average_size', int))

            print('Starting the monitor...')
            sys.stdout.flush()

            self.sending_socket = zut.zmq_onda_publisher_socket(oa.param('General', 'publish_ip', str),
                                                                oa.param('General', 'publish_port', int))

            self.hit_rate = 0
            self.sat_rate = 0

    def process_data(self):

        results_dict = {}

        corr_raw_data = self.dark_cal_correction.apply_darkcal_correction(self.raw_data)
        peak_list = self.peakfinder8_peak_det.find_peaks(corr_raw_data)

        sat = len([x for x in peak_list[2] if x > self.saturation_value]) > self.max_saturated_peaks
        hit = self.min_num_peaks_for_hit < len(peak_list[2]) < self.max_num_peaks_for_hit

        results_dict['timestamp'] = self.timestamp
        results_dict['peak_list'] = peak_list
        results_dict['sat_flag'] = sat
        results_dict['hit_flag'] = hit
        results_dict['detector_distance'] = self.detector_distance
        results_dict['beam_energy'] = self.beam_energy

        if not hit:
            results_dict['peak_list'] = ([], [], [])

        if hit or self.hit_sending_interval < 0:
            self.hit_sending_counter += 1
            if self.hit_sending_counter == abs(self.hit_sending_interval):
                results_dict['raw_data'] = corr_raw_data
                self.hit_sending_counter = 0

        return results_dict, self.mpi_rank

    def collect_data(self, new):

        collected_data = {}
        collected_rawdata = {}

        results_dict, _ = new
        self.num_events += 1

        self.hit_rate_running_w.append(float(results_dict['hit_flag']))
        self.hit_rate_running_w.popleft()
        self.saturation_rate_running_w.append(float(results_dict['sat_flag']))
        self.saturation_rate_running_w.popleft()

        self.hit_rate = sum(self.hit_rate_running_w) / len(self.hit_rate_running_w)
        self.sat_rate = sum(self.saturation_rate_running_w) / len(self.saturation_rate_running_w)

        collected_peaks = self.accumulator.accumulate_peaks(results_dict['peak_list'])

        if collected_peaks is not None:
            collected_data['peak_list'] = collected_peaks
            collected_data['timestamp'] = results_dict['timestamp']
            collected_data['hit_rate'] = self.hit_rate
            collected_data['sat_rate'] = self.sat_rate
            collected_data['detector_distance'] = results_dict['detector_distance']
            collected_data['beam_energy'] = results_dict['beam_energy']
            collected_data['optimized_geometry'] = self.optimized_geometry

            self.sending_socket.send_data('ondadata', collected_data)

        if 'raw_data' in results_dict:
            collected_rawdata['raw_data'] = results_dict['raw_data']
            collected_rawdata['peak_list'] = results_dict['peak_list']

            self.sending_socket.send_data('ondarawdata', collected_rawdata)

        if self.num_events % self.speed_report_interval == 0:
            now_time = time.time()
            print('Processed: {0} in {1:.2f} seconds ({2:.2f} Hz)'.format(
                self.num_events,
                now_time - self.old_time,
                float(self.speed_report_interval) / float(now_time - self.old_time)))
            sys.stdout.flush()
            self.old_time = now_time
