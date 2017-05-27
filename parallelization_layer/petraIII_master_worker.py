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

from mpi4py import MPI
import datetime
import os.path
import signal
import socket
import sys

from hidra_api import Transfer
import ondautils.onda_dynamic_import_utils as di
import ondautils.onda_param_utils as op

de_layer = di.import_correct_layer_module('data_extraction_layer', op.monitor_params)
open_file = di.import_function_from_layer('open_file', de_layer)
close_file = di.import_function_from_layer('close_file', de_layer)
extract = di.import_function_from_layer('extract', de_layer)
num_events = di.import_function_from_layer('num_events', de_layer)

in_layer = di.import_correct_layer_module('instrument_layer', op.monitor_params)
file_extensions = di.import_list_from_layer('file_extensions', in_layer)


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
        self._extract_data = extract

        self._hostname = socket.gethostname()
        self._sender_hostname = source
        self._base_port = op.param('PetraIIIParallelizationLayer', 'base_port', int, required=True)
        self._priority = 1

        transfer_type = op.param('PetraIIIParallelizationLayer', 'transfer_type', required=True)
        if transfer_type == 'data':
            self._query_text = 'QUERY_NEXT'
            self._data_base_path = os.path.join(op.param('PetraIIIParallelizationLayer', 'data_base_path',
                                                         str, required=True))
            self._open_file = _open_file_data
        elif transfer_type == 'metadata':
            self._query_text = 'QUERY_METADATA'
            self._data_base_path = ''
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

            self._query = Transfer(self._query_text, self._sender_hostname, use_log=False)
            self._query.initiate(self._targets[1:])

            signal.signal(signal.SIGTERM, self.send_exit_announcement)

        if self.role == 'worker':
            self._max_shots_to_proc = op.param('PetraIIIMetadataParallelizationLayer', 'images_per_file_to_process',
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

            evt = {'monitor_params': op.monitor_params}

            while True:

                [metadata, data] = self._query.get()

                if MPI.COMM_WORLD.Iprobe(source=0, tag=self.DIETAG):
                    self.shutdown('Shutting down RANK: {0}.'.format(self.mpi_rank))

                relative_filepath = os.path.join(metadata['relative_path'], metadata['filename'])
                filepath = os.path.join(op.param(self._data_base_path, relative_filepath))

                evt['filename'] = filepath
                try:
                    evt['filehandle'] = self._open_file(data, filepath)
                    evt['filectime'] = datetime.datetime.fromtimestamp(metadata['file_create_time'])
                    evt['num_events'] = num_events(evt)
                except (IOError, OSError):
                    print('Cannot read file: {0}'.format(filepath))
                    continue

                shots_to_proc = self._max_shots_to_proc

                if int(evt['num_events']) < self._max_shots_to_proc:
                    shots_to_proc = int(evt['num_events'])

                for shot_offset in range(-shots_to_proc, 0, 1):

                    evt['shot_offset'] = shot_offset

                    self._extract_data(evt, self)

                    if self.raw_data is None:
                        continue

                    result = self._map()

                    if req:
                        req.Wait()
                    req = MPI.COMM_WORLD.isend(result, dest=0, tag=0)

                if req:
                    req.Wait()
                close_file(evt['filehandle'])

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
