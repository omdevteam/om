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

file_extensions = di.import_list_from_layer('file_extensions', de_layer)


class MasterWorker(object):
    NOMORE = 998
    DIETAG = 999
    DEADTAG = 1000
    
    def send_exit_announcement(self):
        print('Sending exit announcement')
        self.query.stop()


    def __init__(self, map_func, reduce_func, source):

        self.mpi_rank = MPI.COMM_WORLD.Get_rank()
        self.mpi_size = MPI.COMM_WORLD.Get_size()
        if self.mpi_rank == 0:
            self.role = 'master'
        else:
            self.role = 'worker'

        self.map = map_func
        self.reduce = reduce_func
        self.extract_data = extract

        self.hostname = socket.gethostname()
        self.sender_hostname = source
        self.base_port = op.param('PetraIIIDataParallelizationLayer', 'base_port', int, required=True)
        self.priority = 1

        self.targets = [['', '', 1]]

        for node_rank in range(1, self.mpi_size):
            target_entry = [self.hostname,
                            str(self.base_port + node_rank),
                            str(self.priority),
                            file_extensions]
            self.targets.append(target_entry)

        if self.role == 'master':
            self.num_nomore = 0
            self.num_reduced_events = 0

            print('Announcing OnDA to sender.')
            sys.stdout.flush()

            self.query = Transfer('QUERY_NEXT', self.sender_hostname, use_log=False)
            self.query.initiate(self.targets[1:])

            signal.signal(signal.SIGTERM, self.send_exit_announcement)

        if self.role == 'worker':
            self.shots_to_proc = op.param('PetraIIIDataParallelizationLayer', 'images_per_file_to_process', int,
                                          required=True)

            self._buffer = None

            self.query = Transfer('QUERY_NEXT', self.sender_hostname, use_log=None)
            self.worker_port = self.targets[self.mpi_rank][1]

            print('Worker', self.mpi_rank, 'listening at port', self.worker_port)
            sys.stdout.flush()

            self.query.start(self.targets[self.mpi_rank][1])

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

                [metadata, data] = self.query.get()
                relative_filepath = os.path.join(metadata['relative_path'], metadata['filename'])

                if MPI.COMM_WORLD.Iprobe(source=0, tag=self.DIETAG):
                    self.shutdown('Shutting down RANK: {0}.'.format(self.mpi_rank))

                evt['filename'] = relative_filepath
                try:
                    evt['filehandle'] = open_file(data)
                    evt['filectime'] = datetime.datetime.fromtimestamp(metadata['file_create_time'])
                    evt['filesize'] = metadata['filesize']
                    evt['num_events'] = num_events(evt)
                except (IOError, OSError):
                    print('Cannot read file: {0}'.format(relative_filepath))
                    continue

                if int(evt['num_events']) < self.shots_to_proc:
                    self.shots_to_proc = int(evt['num_events'])

                for shot_offset in range(-self.shots_to_proc, 0, 1):

                    evt['shot_offset'] = shot_offset

                    self.extract_data(evt, self)

                    if self.raw_data is None:
                        continue

                    result = self.map()

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
                        self.num_nomore += 1
                        if self.num_nomore == self.mpi_size - 1:
                            print('All workers have run out of events.')
                            print('Shutting down.')
                            sys.stdout.flush()
                            self.end_processing()
                            MPI.Finalize()
                            exit(0)
                        continue

                    self.reduce(buffer_data)
                    self.num_reduced_events += 1

                except KeyboardInterrupt as excp:
                    print('Recieved keyboard sigterm...')
                    print(str(excp))
                    print('shutting down MPI.')
                    self.shutdown()
                    print('---> execution finished.')
                    sys.stdout.flush()
                    exit(0)

        return

    def end_processing(self):
        print('Processing finished. Processed', self.num_reduced_events, 'events in total.')
        sys.stdout.flush()
        pass
