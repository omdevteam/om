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


from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os.path
import sys
import time
from builtins import str

import numpy

import cfelpyutils.cfel_hdf5 as ch5
import ondautils.onda_dynamic_import_utils as di
import ondautils.onda_mll_log_file_utils as mlu
import ondautils.onda_param_utils as op
import ondautils.onda_zmq_monitor_utils as zut
from ondautils.onda_exception_utils import MLLLogFleParsingError


par_layer = di.import_correct_layer_module('facility_layer', op.monitor_params)
MasterWorker = di.import_class_from_layer('MasterWorker', par_layer)


def _make_mll_mask(centre, size, shape):
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

        if self._role == 'worker':

            mask_shape = (
                op.param('General', 'mask_size_ss', int, required=True),
                op.param('General', 'mask_size_fs', int, required=True)
            )
            mask_center = (
                op.param('General', 'mask_center_ss', int, required=True),
                op.param('General', 'mask_center_fs', int, required=True)
            )
            mask_size = (
                op.param('General', 'mask_edge_ss', int, required=True) / 2,
                op.param('General', 'mask_edge_fs', int, required=True) / 2
            )

            self._mask = _make_mll_mask(mask_center, mask_size, mask_shape)

            self._bad_pixel_mask = ch5.load_nparray_from_hdf5_file(
                op.param('General', 'bad_pixel_mask_filename', str, required=True),
                op.param('General', 'bad_pixel_mask_hdf5_group', str, required=True)
            )

            if op.param('General', 'whitefield_subtraction', bool) is True:
                self._whitefield = ch5.load_nparray_from_hdf5_file(
                    op.param('General', 'whitefield_filename', str, required=True),
                    op.param('General', 'whitefield_hdf5_group', str, required=True)
                )
                self._whitefield[self._whitefield == 0] = 1
            else:
                self._whitefield = True

            self._new_scan = False

            self._hit_sending_counter = 0

            print('Starting worker: {0}.'.format(self.mpi_rank))
            sys.stdout.flush()

        if self._role == 'master':

            self._num_events = 0
            self._old_time = time.time()

            self._current_run_num = 0

            self._num_accumulated_shots = 0

            self._speed_report_interval = op.param('General', 'speed_report_interval', int, required=True)
            self._num_shots_to_accumulate = op.param('General', 'accumulated_shots', int, required=True)

            self._log_dir = op.param('General', 'log_base_path', str, required=True)
            self._data_dir = op.param('General', 'data_base_path', str, required=True)

            self._scan_type = 0

            self._scan_data = []
            self.grid = ()
            self.physical_grid_axes = ()

            self._stxm = numpy.zeros((0, 0))
            self._dpc = numpy.zeros((0, 0))

            self._fs_integr_image = numpy.zeros((0, 0))
            self._ss_integr_image = numpy.zeros((0, 0))

            print('Starting the monitor...')
            sys.stdout.flush()

            self._sending_socket = zut.ZMQOndaPublisherSocket(op.param('General', 'publish_ip', str),
                                                              op.param('General', 'publish_port', int))

            self._hit_rate = 0
            self._sat_rate = 0

    def process_data(self):

        results_dict = {}

        corrected_data = self.raw_data * self._bad_pixel_mask / self._whitefield

        sum1 = corrected_data[self._mask == 1].sum()
        sum2 = corrected_data[self._mask == 2].sum()
        sum3 = corrected_data[self._mask == 3].sum()
        sum4 = corrected_data[self._mask == 4].sum()

        stxm = sum1 + sum2 + sum3 + sum4

        dpc = 0

        if (
                numpy.count_nonzero(sum1) != 0 and numpy.count_nonzero(sum2) != 0 and
                numpy.count_nonzero(sum3) != 0 and numpy.count_nonzero(sum4) != 0
        ):
            dpc = numpy.sqrt(
                ((sum1 + sum3 - sum2 - sum4) ** 2 + (sum1 + sum2 - sum3 - sum4) ** 2) /
                (sum1 ** 2 + sum2 ** 2 + sum3 ** 2 + sum4 ** 2)
            )

        integr_ss = corrected_data.sum(axis=0)
        integr_fs = corrected_data.sum(axis=1)

        if 'Frame' in self.filename:
            results_dict['raw_data'] = corrected_data
            print('Received single frame.')

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
        self._num_events += 1

        filename_parts = (os.path.basename(results_dict['filename']).split('_'))

        if 'Frame' in results_dict['filename']:
            print('Sending Frame to MLL Frame Viewer.')
            self._sending_socket.send_data('ondarawdata', results_dict)
        try:
            num_run = int(filename_parts[1])
            num_file = int(filename_parts[2].split('.')[0])
            num_event = int(results_dict['event'])
        except ValueError as e:
            raise MLLLogFleParsingError('Error parsing the log file {0}: {1}'.format(results_dict['filename'], e))

        if num_run < self._current_run_num:
            return

        if num_run > self._current_run_num:
            log_file_name = '{0}.dat'.format('_'.join(filename_parts[0:2]))
            log_class = mlu.read_mll_logfile(os.path.join(self._log_dir, log_file_name))

            self.grid = tuple(log_class.log['Grid'])
            self.physical_grid_axes = tuple(log_class.log['Physical_grid_axes'])

            self._scan_data = []

            if 'Slower axis' in log_class.log:
                slower_data = {'start': 1e6 * log_class.log['Slower axis']['Start position'],
                               'end': 1e6 * log_class.log['Slower axis']['End position'],
                               'name': log_class.log['Slower axis']['name'],
                               'steps': log_class.log['Slower axis']['Steps']}
                self._scan_data.append(slower_data)

            if 'Slow axis' in log_class.log:
                slow_data = {'start': 1e6 * log_class.log['Slow axis']['Start position'],
                             'end': 1e6 * log_class.log['Slow axis']['End position'],
                             'name': log_class.log['Slow axis']['name'], 'steps': log_class.log['Slow axis']['Steps']}
                self._scan_data.append(slow_data)

            if 'Fast axis' in log_class.log:
                fast_data = {'start': 1e6 * log_class.log['Fast axis']['Start position'],
                             'end': 1e6 * log_class.log['Fast axis']['End position'],
                             'name': log_class.log['Fast axis']['name'], 'steps': log_class.log['Fast axis']['Steps']}
                self._scan_data.append(fast_data)

                if (
                        'StayStill hack' in log_class.log['Fast axis'] and
                        log_class.log['Fast axis']['StayStill hack'] is True
                ):
                    self._scan_data.pop()

            if len(self.physical_grid_axes) == 2:

                print('New 2D scan. Log file:', log_file_name + '.')
                sys.stdout.flush()

                self._scan_type = 2

                self._stxm = numpy.zeros((self.grid[self.physical_grid_axes[0]], self.grid[self.physical_grid_axes[1]]))
                self._dpc = numpy.zeros((self.grid[self.physical_grid_axes[0]], self.grid[self.physical_grid_axes[1]]))

            elif len(self.physical_grid_axes) == 1:

                print('New 1D scan. Log file:', log_file_name + '.')
                sys.stdout.flush()

                self._scan_type = 1

                self._fs_integr_image = numpy.zeros((results_dict['integr_fs'].shape[0],
                                                     self.grid[self.physical_grid_axes[0]]))
                self._ss_integr_image = numpy.zeros((results_dict['integr_ss'].shape[0],
                                                     self.grid[self.physical_grid_axes[0]]))

            else:

                print('New 0D scan. Log file:', log_file_name + '.')
                sys.stdout.flush()

                self._scan_type = 0

        if self._scan_type == 2:

            ind = numpy.unravel_index(num_file + num_event, self.grid)

            self._stxm[ind[self.physical_grid_axes[0]], ind[self.physical_grid_axes[1]]] += results_dict['stxm']
            self._dpc[ind[self.physical_grid_axes[0]], ind[self.physical_grid_axes[1]]] += results_dict['dpc']

            self._num_accumulated_shots += 1

            collected_data['scan_type'] = 2
            collected_data['stxm'] = self._stxm.transpose()
            collected_data['dpc'] = self._dpc.transpose()
            collected_data['fs_start'] = self._scan_data[-1]['start']
            collected_data['fs_end'] = self._scan_data[-1]['end']
            collected_data['ss_start'] = self._scan_data[-2]['start']
            collected_data['ss_end'] = self._scan_data[-2]['end']
            collected_data['fs_name'] = self._scan_data[-1]['name']
            collected_data['ss_name'] = self._scan_data[-2]['name']
            collected_data['fs_steps'] = self._scan_data[-1]['steps']
            collected_data['ss_steps'] = self._scan_data[-2]['steps']
            collected_data['timestamp'] = results_dict['timestamp']
            collected_data['num_run'] = num_run

        elif self._scan_type == 1:

            ind = numpy.unravel_index(num_file + num_event, self.grid)

            self._fs_integr_image[:, ind[self.physical_grid_axes[0]]] += results_dict['integr_fs']
            self._ss_integr_image[:, ind[self.physical_grid_axes[0]]] += results_dict['integr_ss']

            self._num_accumulated_shots += 1

            collected_data['scan_type'] = 1
            collected_data['scan_data'] = self._scan_data
            collected_data['fs_start'] = self._scan_data[-1]['start']
            collected_data['fs_end'] = self._scan_data[-1]['end']
            collected_data['fs_name'] = self._scan_data[-1]['name']
            collected_data['fs_steps'] = self._scan_data[-1]['steps']
            collected_data['ss_integr_image'] = self._ss_integr_image
            collected_data['fs_integr_image'] = self._fs_integr_image
            collected_data['timestamp'] = results_dict['timestamp']
            collected_data['num_run'] = num_run

        else:

            print('Data from 0D scan, not processed.')

        self._current_run_num = num_run
        self._new_scan = False

        if self._num_accumulated_shots == self._num_shots_to_accumulate:
            self._sending_socket.send_data('ondadata', collected_data)
            self._num_accumulated_shots = 0

        if self._num_events % self._speed_report_interval == 0:
            now_time = time.time()
            print('Processed: {0} in {1:.2f} seconds ({2:.2f} Hz)'.format(
                self._num_events,
                now_time - self._old_time,
                float(self._speed_report_interval) / float(now_time - self._old_time)))
            sys.stdout.flush()
            self._old_time = now_time
