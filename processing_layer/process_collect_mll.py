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

import numpy
from os.path import basename, join
from sys import stdout
from time import time

from cfelpyutils.cfel_hdf5 import load_nparray_from_hdf5_file
from parallelization_layer.utils.onda_dynamic_import import import_correct_layer_module
from parallelization_layer.utils.onda_params import monitor_params, param
from parallelization_layer.utils.onda_zmq_monitor_utils import zmq_onda_publisher_socket
from processing_layer.utils.onda_mll_log_file_utils import read_mll_logfile

par_layer = import_correct_layer_module('parallelization_layer', monitor_params)
MasterWorker = getattr(par_layer, 'MasterWorker')


def make_mll_mask(centre, size, shape):
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


class Onda(MasterWorker):
    def __init__(self, source):

        super(Onda, self).__init__(map_func=self.process_data,
                                   reduce_func=self.collect_data,
                                   source=source)

        if self.role == 'worker':

            mask_shape = (param('General', 'mask_size_ss', int), param('General', 'mask_size_fs', int))
            mask_center = (param('General', 'mask_center_ss', int), param('General', 'mask_center_fs', int))
            mask_size = (param('General', 'mask_edge_ss', int) / 2, param('General', 'mask_edge_fs', int) / 2)

            self.mask = make_mll_mask(mask_center, mask_size, mask_shape)

            self.bad_pixel_mask = load_nparray_from_hdf5_file(param('General', 'bad_pixel_mask_filename', str),
                                                              param('General', 'bad_pixel_mask_hdf5_group', str))

            if param('General', 'whitefield_subtraction', bool) is True:
                self.whitefield = load_nparray_from_hdf5_file(param('General', 'whitefield_filename', str),
                                                              param('General', 'whitefield_hdf5_group', str))
                self.whitefiled[self.whitefield == 0] = 1
            else:
                self.whitefield = True

            self.new_scan = False

            self.hit_sending_counter = 0

            print('Starting worker: {0}.'.format(self.mpi_rank))
            stdout.flush()

        if self.role == 'master':
            self.num_events = 0
            self.old_time = time()

            self.current_run_num = 0

            self.num_accumulated_shots = 0

            self.speed_report_interval = param('General', 'speed_report_interval', int)
            self.num_shots_to_accumulate = param('General', 'accumulated_shots', int)

            self.log_dir = param('General', 'log_base_path', str)
            self.data_dir = param('General', 'data_base_path', str)

            self.scan_type = 0

            self.ss_start = 0
            self.ss_end = 0
            self.ss_name = 0
            self.ss_steps = 0

            self.fs_start = 0
            self.fs_end = 0
            self.fs_name = 0
            self.fs_steps = 0

            self.stxm = numpy.zeros((0, 0))
            self.dpc = numpy.zeros((0, 0))

            self.fs_integr_image = numpy.zeros((0, 0))
            self.ss_integr_image = numpy.zeros((0, 0))

            print('Starting the monitor...')
            stdout.flush()


            self.sending_socket = zmq_onda_publisher_socket(param('General', 'publish_ip'),
                                                            param('General', 'publish_port'))

            self.hit_rate = 0
            self.sat_rate = 0

    def process_data(self):

        results_dict = {}

        corrected_data = self.raw_data * self.bad_pixel_mask / self.whitefield

        sum1 = corrected_data[self.mask == 1].sum()
        sum2 = corrected_data[self.mask == 2].sum()
        sum3 = corrected_data[self.mask == 3].sum()
        sum4 = corrected_data[self.mask == 4].sum()

        stxm = sum1 + sum2 + sum3 + sum4

        dpc = numpy.sqrt(
            ((sum1 + sum3 - sum2 - sum4) ** 2 + (sum1 + sum2 - sum3 - sum4) ** 2) /
            (sum1 ** 2 + sum2 ** 2 + sum3 ** 2 + sum4 ** 2)
        )

        integr_ss = corrected_data.sum(axis=0)
        integr_fs = corrected_data.sum(axis=1)

        results_dict['timestamp'] = self.event_timestamp
        results_dict['stxm'] = stxm
        results_dict['dpc'] = dpc
        results_dict['integr_ss'] = integr_ss
        results_dict['integr_fs'] = integr_fs
        results_dict['filename'] = self.filename
        results_dict['event'] = self.event

        return results_dict, self.mpi_rank

    def collect_data(self, new):

        collected_data = {}

        results_dict, _ = new
        self.num_events += 1

        filename_parts = (basename(results_dict['filename']).split('_'))

        if 'Frame' in results_dict['filename']:
            return
        try:
            num_run = int(filename_parts[1])
            num_file = int(filename_parts[2].split('.')[0])
            num_event = int(results_dict['event'])
        except ValueError:
            return

        if num_run < self.current_run_num:
            return

        if num_run > self.current_run_num:
            log_file_name = '{0}.dat'.format('_'.join(filename_parts[0:2]))
            log_class = read_mll_logfile(join(self.log_dir, log_file_name))

            self.grid = tuple(log_class.log['Grid'])
            self.physical_grid_axes = tuple(log_class.log['Physical_grid_axes'])

            if len(self.physical_grid_axes) == 2:

                print('New 2D scan. Log file:', log_file_name + '.')
                stdout.flush()

                self.scan_type = 2

                self.ss_start = log_class.log['Slow axis']['Start position']
                self.ss_end = log_class.log['Slow axis']['End position']
                self.ss_name = log_class.log['Slow axis']['name']
                self.ss_steps = log_class.log['Slow axis']['Steps']

                self.fs_start = log_class.log['Fast axis']['Start position']
                self.fs_end = log_class.log['Fast axis']['End position']
                self.fs_name = log_class.log['Fast axis']['name']
                self.fs_steps = log_class.log['Fast axis']['Steps']

                self.stxm = numpy.zeros((self.ss_steps, self.fs_steps))
                self.dpc = numpy.zeros((self.ss_steps, self.fs_steps))

            elif len(self.physical_grid_axes) == 1:

                print('New 1D scan. Log file:', log_file_name + '.')
                stdout.flush()

                self.scan_type = 1

                self.fs_start = log_class.log['Fast axis']['Start position']
                self.fs_end = log_class.log['Fast axis']['End position']
                self.fs_steps = log_class.log['Fast axis']['Steps']
                self.fs_name = log_class.log['Fast axis']['name']

                self.fs_integr_image = numpy.zeros((results_dict['integr_fs'].shape[0], self.fs_steps))
                self.ss_integr_image = numpy.zeros((results_dict['integr_ss'].shape[0], self.fs_steps))
            
            else: 

                print('New 0D scan. Log file:', log_file_name + '.')
                stdout.flush()

                self.scan_type = 0

        if self.scan_type == 2:

            ind = numpy.unravel_index(num_file + num_event, self.grid)

            self.stxm[ind[self.physical_grid_axes[0]], ind[self.physical_grid_axes[1]]] += results_dict['stxm']
            self.dpc[ind[self.physical_grid_axes[0]], ind[self.physical_grid_axes[1]]] += results_dict['dpc']

            self.num_accumulated_shots += 1
            
            collected_data['scan_type'] = 2
            collected_data['stxm'] = self.stxm.transpose()
            collected_data['dpc'] = self.dpc.transpose()
            collected_data['fs_start'] = self.fs_start
            collected_data['fs_end'] = self.fs_end
            collected_data['ss_start'] = self.ss_start
            collected_data['ss_end'] = self.ss_end
            collected_data['fs_name'] = self.fs_name
            collected_data['ss_name'] = self.ss_name
            collected_data['fs_steps'] = self.fs_steps
            collected_data['ss_steps'] = self.ss_steps
            collected_data['timestamp'] = results_dict['timestamp']
            collected_data['num_run'] = num_run

        elif self.scan_type == 1:

            ind = numpy.unravel_index(num_file + num_event, self.grid)

            self.fs_integr_image[:, ind[self.physical_grid_axes[0]]] += results_dict['integr_fs']
            self.ss_integr_image[:, ind[self.physical_grid_axes[0]]] += results_dict['integr_ss']

            self.num_accumulated_shots += 1

            collected_data['scan_type'] = 1
            collected_data['fs_start'] = self.fs_start
            collected_data['fs_end'] = self.fs_end
            collected_data['fs_steps'] = self.fs_steps
            collected_data['fs_name'] = self.fs_name
            collected_data['ss_integr_image'] = self.ss_integr_image
            collected_data['fs_integr_image'] = self.fs_integr_image
            collected_data['timestamp'] = results_dict['timestamp']
            collected_data['num_run'] = num_run

        else:

           print('Data from 0D scan, not processed.')


        self.current_run_num = num_run
        self.new_scan = False

        if self.num_accumulated_shots == self.num_shots_to_accumulate:
            self.sending_socket.send_data('ondadata', collected_data)
            self.num_accumulated_shots = 0

        if self.num_events % self.speed_report_interval == 0:
            now_time = time()
            print('Processed: {0} in {1:.2f} seconds ({2:.2f} Hz)'.format(
                self.num_events,
                now_time - self.old_time,
                float(self.speed_report_interval) / float(now_time - self.old_time)))
            stdout.flush()
            self.old_time = now_time
