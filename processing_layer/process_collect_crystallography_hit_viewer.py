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


import time
import sys
import zmq

from cfelpyutils.cfelgeom import pixel_maps_from_geometry_file

from parallelization_layer.utils import (
    global_params as gp,
    zmq_monitor_utils as zmq_mon,
    dynamic_import as dyn_imp
)
from processing_layer.algorithms.generic_algorithms import (
    DarkCalCorrection
)
from processing_layer.algorithms.cheetah_algorithms import (
    Peakfinder8PeakDetection
)

par_layer = dyn_imp.import_layer_module('parallelization_layer', gp.monitor_params)

MasterWorker = getattr(par_layer, 'MasterWorker')


class Onda(MasterWorker):

    def __init__(self, source, monitor_params):

        super(Onda, self).__init__(map_func=self.process_data,
                                   reduce_func=self.collect_data,
                                   source=source, monitor_params=monitor_params)

        gen_params = monitor_params['General']
        p8pd_params = monitor_params['Peakfinder8PeakDetection']
        dkc_params = monitor_params['DarkCalCorrection']

        self.max_saturated_peaks = gen_params['max_saturated_peaks']
        self.min_num_peaks_for_hit = gen_params['min_num_peaks_for_hit']
        self.max_num_peaks_for_hit = gen_params['max_num_peaks_for_hit']
        self.saturation_value = gen_params['saturation_value']
        self.optimized_geometry = gen_params['geometry_is_optimized']
        self.hit_sending_interval = gen_params['hit_sending_interval']

        self.p8pd_max_num_peaks = p8pd_params['max_num_peaks']
        self.p8pd_asic_nx = p8pd_params['asics_nx']
        self.p8pd_asic_ny = p8pd_params['asics_ny']
        self.p8pd_nasics_x = p8pd_params['nasics_x']
        self.p8pd_nasics_y = p8pd_params['nasics_y']
        self.p8pd_adc_thresh = p8pd_params['adc_threshold']
        self.p8pd_minimum_snr = p8pd_params['minimum_snr']
        self.p8pd_min_pixel_count = p8pd_params['min_pixel_count']
        self.p8pd_max_pixel_count = p8pd_params['max_pixel_count']
        self.p8pd_local_bg_radius = p8pd_params['local_bg_radius']
        self.p8pd_mask_filename = p8pd_params['mask_filename']
        self.p8pd_mask_hdf5_path = p8pd_params['mask_hdf5_path']
        self.p8pd_accumulated_shots = p8pd_params['accumulated_shots']
        self.p8pd_min_res = p8pd_params['min_res']
        self.p8pd_max_res = p8pd_params['max_res']

        self.dkc_filename = dkc_params['filename']
        self.dkc_hdf5_group = dkc_params['hdf5_group']

        pix_maps = pixel_maps_from_geometry_file(gen_params['geometry_file'])

        self.pixelmap_radius = pix_maps[2]

        self.dkc_apply_mask = 'mask' in dkc_params.keys() and dkc_params['mask'] is True

        self.dkc_mask_filename = None
        self.dkc_mask_hdf5_group = None
        if self.dkc_apply_mask is True:
            if 'mask_filename' in dkc_params.keys():
                self.dkc_mask_filename = dkc_params['mask_filename']

        if self.dkc_apply_mask is True:
            if 'mask_hdf5_group' in dkc_params.keys():
                self.dkc_mask_hdf5_group = dkc_params['mask_hdf5_group']

        self.dkc_gain_map_correction = 'gain_map' in dkc_params.keys() and dkc_params['gain_map'] is True

        self.dkc_gain_map_filename = None
        self.dkc_gain_map_hdf5_group = None
        if self.dkc_gain_map_correction is True:
            if 'gain_map_filename' in dkc_params.keys():
                self.dkc_gain_map_filename = dkc_params['gain_map_filename']

        if self.dkc_gain_map_correction is True:
            if 'gain_map_hdf5_group' in dkc_params.keys():
                self.dkc_gain_map_hdf5_group = dkc_params['gain_map_hdf5_group']

        self.dark_cal_correction = DarkCalCorrection(self.role,
                                                     self.dkc_filename,
                                                     self.dkc_hdf5_group,
                                                     self.dkc_apply_mask,
                                                     self.dkc_mask_filename,
                                                     self.dkc_mask_hdf5_group,
                                                     self.dkc_gain_map_correction,
                                                     self.dkc_gain_map_filename,
                                                     self.dkc_gain_map_hdf5_group)

        self.peakfinder8_peak_det = Peakfinder8PeakDetection(self.role,
                                                             self.p8pd_max_num_peaks,
                                                             self.p8pd_asic_nx,
                                                             self.p8pd_asic_ny,
                                                             self.p8pd_nasics_x,
                                                             self.p8pd_nasics_y,
                                                             self.p8pd_adc_thresh,
                                                             self.p8pd_minimum_snr,
                                                             self.p8pd_min_pixel_count,
                                                             self.p8pd_max_pixel_count,
                                                             self.p8pd_local_bg_radius,
                                                             self.p8pd_accumulated_shots,
                                                             self.p8pd_min_res,
                                                             self.p8pd_max_res,
                                                             self.p8pd_mask_filename,
                                                             self.p8pd_mask_hdf5_path,
                                                             self.pixelmap_radius)

        if self.role == 'master':

            self.collected_data = {}
            self.publish_ip = gen_params['publish_ip']
            self.publish_port = gen_params['publish_port']
            self.speed_rep_int = gen_params['speed_report_interval']

            running_win_size = gen_params['running_average_size']

            self.hit_rate_running_w = [0.0] * running_win_size
            self.saturation_rate_running_w = [0.0] * running_win_size

            print('Starting the monitor...')
            sys.stdout.flush()

            zmq_mon.init_zmq_to_gui(self, self.publish_ip, self.publish_port)

            self.num_events = 0
            self.old_time = time.time()

            self.time = None
            self.hit_rate = 0
            self.sat_rate = 0

        if self.role == 'worker':

            self.results_dict = {}

            self.hit_sending_counter = 0

            print('Starting worker: {0}.'.format(self.mpi_rank))
            sys.stdout.flush()

        return

    def process_data(self):

        self.results_dict = {}

        corr_raw_data = self.dark_cal_correction.apply_darkcal_correction(self.raw_data)
        peak_list = self.peakfinder8_peak_det.find_peaks(corr_raw_data)

        sat = len([ x for x in peak_list[2] if x > self.saturation_value]) > self.max_saturated_peaks
        hit = len(peak_list[2]) > self.min_num_peaks_for_hit and len(peak_list[2]) < self.max_num_peaks_for_hit
        self.results_dict['timestamp'] = self.event_timestamp
        self.results_dict['peak_list'] = peak_list
        self.results_dict['sat_flag'] = sat
        self.results_dict['hit_flag'] = hit
        self.results_dict['detector_distance'] = self.detector_distance
        self.results_dict['beam_energy'] = self.beam_energy


        if not hit:
            self.results_dict['peak_list'] = ([], [], [])
        
        if hit or self.hit_sending_interval < 0:
            self.hit_sending_counter += 1
            if self.hit_sending_counter == abs(self.hit_sending_interval):
                self.results_dict['raw_data'] = corr_raw_data
                self.hit_sending_counter = 0

        return self.results_dict, self.mpi_rank

    def collect_data(self, new):

        self.collected_data = {}
        self.collected_rawdata = {}

        self.results_dict, _ = new
        self.num_events += 1

        self.hit_rate_running_w.append(float(self.results_dict['hit_flag']))
        self.hit_rate_running_w.pop(0)
        self.saturation_rate_running_w.append(float(self.results_dict['sat_flag']))
        self.saturation_rate_running_w.pop(0)

        self.hit_rate = sum(self.hit_rate_running_w) / len(self.hit_rate_running_w)
        self.sat_rate = sum(self.saturation_rate_running_w) / len(self.saturation_rate_running_w)

        collected_peaks = self.peakfinder8_peak_det.accumulate_peaks(self.results_dict['peak_list'])

        if collected_peaks is not None:

            self.collected_data['peak_list'] = collected_peaks
            self.collected_data['timestamp'] = self.results_dict['timestamp']
            self.collected_data['hit_rate'] = self.hit_rate
            self.collected_data['sat_rate'] = self.sat_rate
            self.collected_data['detector_distance'] = self.results_dict['detector_distance']
            self.collected_data['beam_energy'] = self.results_dict['beam_energy']
            self.collected_data['optimized_geometry'] = self.optimized_geometry

            self.zmq_publish.send(b'ondadata', zmq.SNDMORE)
            self.zmq_publish.send_pyobj(self.collected_data)

        if 'raw_data' in self.results_dict.keys():
            self.collected_rawdata['raw_data'] = self.results_dict['raw_data']
            self.collected_rawdata['peak_list'] = self.results_dict['peak_list']

            self.zmq_publish.send(b'ondarawdata', zmq.SNDMORE)
            self.zmq_publish.send_pyobj(self.collected_rawdata)

        if self.num_events % self.speed_rep_int == 0:
            self.time = time.time()
            print('Processed: {0} in {1:.2f} seconds ({2:.2f} Hz)'.format(
                self.num_events,
                self.time - self.old_time,
                float(self.speed_rep_int)/float(self.time-self.old_time)))
            sys.stdout.flush()
            self.old_time = self.time

        return
