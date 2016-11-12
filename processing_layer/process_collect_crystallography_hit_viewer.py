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

from collections import deque
from sys import stdout
from time import time

from cfelpyutils.cfel_geom import pixel_maps_from_geometry_file
from parallelization_layer.utils.onda_params import monitor_params, param
from parallelization_layer.utils.onda_dynamic_import import import_correct_layer_module

from parallelization_layer.utils.onda_zmq_monitor_utils import zmq_onda_publisher_socket
from processing_layer.algorithms.generic_algorithms import DarkCalCorrection
from processing_layer.algorithms.cheetah_algorithms import Peakfinder8PeakDetection

par_layer = import_correct_layer_module('parallelization_layer', monitor_params)
MasterWorker = getattr(par_layer, 'MasterWorker')


class Onda(MasterWorker):
    def __init__(self, source):

        super(Onda, self).__init__(map_func=self.process_data,
                                   reduce_func=self.collect_data,
                                   source=source)

        _, _, pixelmap_radius = pixel_maps_from_geometry_file(param('General', 'geometry_file'))

        self.dark_cal_correction = DarkCalCorrection(self.role,
                                                     param('DarkCalCorrection', 'filename', str),
                                                     param('DarkCalCorrection', 'hdf5_group', str),
                                                     param('DarkCalCorrection', 'apply_mask', bool),
                                                     param('DarkCalCorrection', 'mask_filename', str),
                                                     param('DarkCalCorrection', 'mask_hdf5_group', str),
                                                     param('DarkCalCorrection', 'gain_map_correction', bool),
                                                     param('DarkCalCorrection', 'gain_map_filename', str),
                                                     param('DarkCalCorrection', 'gain_map_hdf5_group', str))

        self.peakfinder8_peak_det = Peakfinder8PeakDetection(self.role,
                                                             param('Peakfinder8PeakDetection', 'max_num_peaks', int),
                                                             param('Peakfinder8PeakDetection', 'asics_nx', int),
                                                             param('Peakfinder8PeakDetection', 'asics_ny', int),
                                                             param('Peakfinder8PeakDetection', 'nasics_x', int),
                                                             param('Peakfinder8PeakDetection', 'nasics_y', int),
                                                             param('Peakfinder8PeakDetection', 'adc_threshold', float),
                                                             param('Peakfinder8PeakDetection', 'minimum_snr', float),
                                                             param('Peakfinder8PeakDetection', 'min_pixel_count', int),
                                                             param('Peakfinder8PeakDetection', 'max_pixel_count', int),
                                                             param('Peakfinder8PeakDetection', 'local_bg_radius', int),
                                                             param('Peakfinder8PeakDetection', 'accumulated_shots',
                                                                   int),
                                                             param('Peakfinder8PeakDetection', 'min_res', int),
                                                             param('Peakfinder8PeakDetection', 'max_res', int),
                                                             param('Peakfinder8PeakDetection', 'mask_filename',
                                                                   str),
                                                             param('Peakfinder8PeakDetection', 'mask_hdf5_path',
                                                                   str),
                                                             pixelmap_radius)

        if self.role == 'worker':
            self.max_saturated_peaks = param('General', 'max_saturated_peaks', int)
            self.min_num_peaks_for_hit = param('General', 'min_num_peaks_for_hit', int)
            self.max_num_peaks_for_hit = param('General', 'max_num_peaks_for_hit', int)
            self.saturation_value = param('General', 'saturation_value', int)
            self.hit_sending_interval = param('General', 'hit_sending_interval', int)

            self.hit_sending_counter = 0

            print('Starting worker: {0}.'.format(self.mpi_rank))
            stdout.flush()

        if self.role == 'master':
            self.num_events = 0
            self.old_time = time()

            self.time = None

            self.speed_report_interval = param('General', 'speed_report_interval', int)
            self.optimized_geometry = param('General', 'geometry_is_optimized', bool)

            self.hit_rate_running_w = deque([0.0] * param('General', 'running_average_size', int))
            self.saturation_rate_running_w = deque([0.0] * param('General', 'running_average_size', int))

            print('Starting the monitor...')
            stdout.flush()

            self.sending_socket = zmq_onda_publisher_socket(param('General', 'publish_ip', str),
                                                            param('General', 'publish_port', int))

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

        collected_peaks = self.peakfinder8_peak_det.accumulate_peaks(results_dict['peak_list'])

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
            now_time = time()
            print('Processed: {0} in {1:.2f} seconds ({2:.2f} Hz)'.format(
                self.num_events,
                now_time - self.old_time,
                float(self.speed_report_interval) / float(now_time - self.old_time)))
            stdout.flush()
            self.old_time = now_time
