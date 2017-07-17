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
from future.utils import raise_from

import os.path
import signal
import socket
import sys
from builtins import str
from collections import namedtuple

from mpi4py import MPI

import ondautils.onda_dynamic_import_utils as di
import ondautils.onda_param_utils as op
from facility_layer.hidra_api.transfer import CommunicationFailed
from facility_layer.hidra_api import Transfer
from ondautils.onda_exception_utils import MissingDataExtractionFunction, HidraAPIError, DataExtractionError

EventData = namedtuple('EventData', ['filehandle', 'filename', 'filectime', 'num_events', 'shot_offset',
                                     'monitor_params'])


def _extract(event, monitor):
    for entry in data_extraction_funcs:
        try:
            setattr(monitor, entry, globals()['_'+entry](event))
        except Exception as e:
            raise DataExtractionError('OnDA Warning: Error extracting {0}: {1}'.format(entry, e))


def _open_file_data(data, _):
    return open_file(data)


def _open_file_metadata(_, filepath):
    return open_file(filepath)


class MasterWorker(object):
    NOMORE = 998
    DIETAG = 999
    DEADTAG = 1000

    def send_exit_announcement(self):
        print('Sending exit announcement')
        self._query.stop()

    def __init__(self, map_func, reduce_func, source):

        self.mpi_rank = MPI.COMM_WORLD.Get_rank()
        self.mpi_size = MPI.COMM_WORLD.Get_size()

        if self.mpi_rank == 0:
            self.role = 'master'
        else:
            self.role = 'worker'

        self._map = map_func
        self._reduce = reduce_func
        self._extract_data = _extract

        self._hostname = socket.gethostname()
        self._sender_hostname = source
        self._base_port = op.param('PetraIIIParallelizationLayer', 'base_port', int, required=True)
        self._priority = 1

        transfer_type = op.param('PetraIIIParallelizationLayer', 'transfer_type', required=True)
        if transfer_type == 'data':
            self._query_text = 'QUERY_NEXT'
            self._data_base_path = ''
            self._open_file = _open_file_data
        elif transfer_type == 'metadata':
            self._query_text = 'QUERY_METADATA'
            self._data_base_path = os.path.join(op.param('PetraIIIParallelizationLayer', 'data_base_path',
                                                         str, required=True))
            self._open_file = _open_file_metadata
        else:
            raise RuntimeError('Unrecognized transfer type for PetraIII parallelization layer.')

        self._targets = [['', '', 1]]

        for node_rank in range(1, self.mpi_size):
            target_entry = [self._hostname,
                            str(self._base_port + node_rank),
                            str(self._priority),
                            file_extensions]
            self._targets.append(target_entry)

        if self.role == 'master':
            self._num_nomore = 0
            self._num_reduced_events = 0

            print('Announcing OnDA to sender.')
            sys.stdout.flush()

            try:
                self._query = Transfer(self._query_text, self._sender_hostname, use_log=False)
                self._query.initiate(self._targets[1:])
            except CommunicationFailed as e:
                raise_from(HidraAPIError('Failed to contact HiDRA: {0}'.format(e)), None)

            signal.signal(signal.SIGTERM, self.send_exit_announcement)

        if self.role == 'worker':
            self._max_shots_to_proc = op.param('PetraIIIParallelizationLayer', 'images_per_file_to_process',
                                               int, required=True)

            self._buffer = None

            self._query = Transfer(self._query_text, self._sender_hostname, use_log=None)
            self._worker_port = self._targets[self.mpi_rank][1]

            print('Worker', self.mpi_rank, 'listening at port', self._worker_port)
            sys.stdout.flush()

            self._query.start(self._targets[self.mpi_rank][1])

        return

    def shutdown(self, msg='Reason not provided.'):

        print('Shutting down:', msg)
        sys.stdout.flush()

        if self.role == 'worker':
            self._buffer = MPI.COMM_WORLD.send(dest=0, tag=self.DEADTAG)
            MPI.Finalize()
            exit(0)

        if self.role == 'master':

            try:
                for nod_num in range(1, self.mpi_size()):
                    MPI.COMM_WORLD.isend(0, dest=nod_num,
                                         tag=self.DIETAG)
                num_shutdown_confirm = 0
                while True:
                    if MPI.COMM_WORLD.Iprobe(source=MPI.ANY_SOURCE, tag=0):
                        self._buffer = MPI.COMM_WORLD.recv(source=MPI.ANY_SOURCE, tag=0)
                    if MPI.COMM_WORLD.Iprobe(source=MPI.ANY_SOURCE, tag=self.DEADTAG):
                        num_shutdown_confirm += 1
                    if num_shutdown_confirm == self.mpi_size() - 1:
                        break
                MPI.Finalize()
            except Exception:
                MPI.COMM_WORLD.Abort(0)
            exit(0)
        return

    def start(self, verbose=False):

        if self.role == 'worker':

            req = None

            while True:

                [metadata, data] = self._query.get()

                if MPI.COMM_WORLD.Iprobe(source=0, tag=self.DIETAG):
                    self.shutdown('Shutting down RANK: {0}.'.format(self.mpi_rank))

                relative_filepath = os.path.join(metadata['relative_path'], metadata['filename'])
                filepath = os.path.join(self._data_base_path, relative_filepath)

                filename = filepath

                try:
                    filehandle = self._open_file(data, filepath)
                    filectime = metadata['file_create_time']
                    num_events = num_events_in_file(filehandle)
                except (IOError, OSError) as e:
                    print('>>>>> OnDA WARNING: Cannot read file {0}: {1}. Skipping.... <<<<<'.format(
                        filepath.strip(), e))
                    continue

                shots_to_proc = self._max_shots_to_proc

                if num_events < self._max_shots_to_proc:
                    shots_to_proc = num_events

                for shot_offset in range(-shots_to_proc, 0, 1):

                    event = EventData(filehandle, filename, filectime, num_events, shot_offset,
                                      op.monitor_params)

                    try:
                        self._extract_data(event, self)
                    except DataExtractionError as e:
                        print('OnDA Warning: Cannot interpret some event data: {}. Skipping event....'.format(e))
                        continue

                    result = self._map()

                    if req:
                        req.Wait()
                    req = MPI.COMM_WORLD.isend(result, dest=0, tag=0)

                if req:
                    req.Wait()
                close_file(filehandle)

            end_dict = {'end': True}
            if req:
                req.Wait()
            MPI.COMM_WORLD.isend((end_dict, self.mpi_rank), dest=0, tag=0)
            MPI.Finalize()
            exit(0)

        elif self.role == 'master':

            if verbose:
                print('Starting master.')
                sys.stdout.flush()

            while True:

                try:

                    buffer_data = MPI.COMM_WORLD.recv(source=MPI.ANY_SOURCE, tag=0)
                    if 'end' in buffer_data[0].keys():
                        print('Finalizing', buffer_data[1])
                        self._num_nomore += 1
                        if self._num_nomore == self.mpi_size - 1:
                            print('All workers have run out of events.')
                            print('Shutting down.')
                            sys.stdout.flush()
                            self.end_processing()
                            MPI.Finalize()
                            exit(0)
                        continue

                    self._reduce(buffer_data)
                    self._num_reduced_events += 1

                except KeyboardInterrupt as excp:
                    print('Recieved keyboprd sigterm...')
                    print(str(excp))
                    print('shutting down MPI.')
                    self.shutdown()
                    print('---> execution finished.')
                    sys.stdout.flush()
                    exit(0)

        return

    def end_processing(self):
        print('Processing finished. Processed', self._num_reduced_events, 'events in total.')
        sys.stdout.flush()
        pass


in_layer = di.import_correct_layer_module('detector_layer', op.monitor_params)

open_file = di.import_function_from_layer('open_file', in_layer)
close_file = di.import_function_from_layer('close_file', in_layer)
num_events_in_file = di.import_function_from_layer('num_events_in_file', in_layer)
file_extensions = di.import_list_from_layer('file_extensions', in_layer)

data_extraction_funcs = [x.strip() for x in op.param('Onda', 'required_data', list, required=True)]
for func in data_extraction_funcs:
    try:
        globals()[func] = getattr(in_layer, func)
    except AttributeError:
        if func not in globals():
            raise_from(MissingDataExtractionFunction('Data extraction function not defined for the following '
                                                     'data type: {0}'.format(func)), None)
