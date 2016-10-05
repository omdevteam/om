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

from datetime import datetime
from mpi4py import MPI
from numpy import ceil
from os.path import getctime
from sys import exit, stdout

from parallelization_layer.utils.onda_params import monitor_params, param
from parallelization_layer.utils.onda_dynamic_import import import_correct_layer_module, import_function_from_layer


de_layer = import_correct_layer_module('data_extraction_layer', monitor_params)
open_file = import_function_from_layer('open_file', de_layer)
close_file = import_function_from_layer('close_file', de_layer)
extract = import_function_from_layer('extract', de_layer)
num_events = import_function_from_layer('num_events', de_layer)


class MasterWorker(object):
    NOMORE = 998
    DIETAG = 999
    DEADTAG = 1000

    def __init__(self, map_func, reduce_func, source):

        self.mpi_rank = MPI.COMM_WORLD.Get_rank()
        self.mpi_size = MPI.COMM_WORLD.Get_size()
        if self.mpi_rank == 0:
            self.role = 'master'
        else:
            self.role = 'worker'

        self.filelist_filename = source

        self.map = map_func
        self.reduce = reduce_func

        self.extract_data = extract
        fh = open(self.filelist_filename, 'r')
        self.filelist = fh.readlines()
        fh.close()

        self.len_filelist = len(self.filelist)

        if self.role == 'master':
            self.num_nomore = 0
            self.num_reduced_events = 0

        if self.role == 'worker':
            self.shots_to_proc = param('FilelistParallelizationLayer', 'images_per_file_to_process')

            self._buffer = None

        return

    def shutdown(self, msg='Reason not provided.'):
        """Shuts down of the data processor.
        """
        print('Shutting down:', msg)
        stdout.flush()

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
            except RuntimeError:
                MPI.COMM_WORLD.Abort(0)
            exit(0)
        return

    def start(self, verbose=False):

        if self.role == 'worker':

            req = None

            evt = {'monitor_params': monitor_params}

            mylength = int(ceil(len(self.filelist) / float(self.mpi_size - 1)))
            myfiles = self.filelist[(self.mpi_rank - 1) * mylength:self.mpi_rank * mylength]

            for filepath in myfiles:

                if MPI.COMM_WORLD.Iprobe(source=0, tag=self.DIETAG):
                    self.shutdown('Shutting down RANK: {0}.'.format(self.mpi_rank))

                evt['filename'] = filepath.strip()

                try:
                    evt['filehandle'] = open_file(filepath.strip())
                    evt['filectime'] = datetime.fromtimestamp(getctime(filepath.strip()))
                    evt['num_events'] = num_events(evt)
                except RuntimeError:
                    print('Cannot read file', filepath)
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

        # The following is executed on the master
        elif self.role == 'master':

            if verbose:
                print('Starting master.')
                stdout.flush()

            self.num_reduced_events = 0

            # Loops continuously waiting for processed data from workers
            while True:

                try:

                    buffer_data = MPI.COMM_WORLD.recv(source=MPI.ANY_SOURCE, tag=0)
                    if 'end' in buffer_data[0].keys():
                        print('Finalizing', buffer_data[1])
                        self.num_nomore += 1
                        if self.num_nomore == self.mpi_size - 1:
                            print('All workers have run out of events.')
                            print('Shutting down.')
                            stdout.flush()
                            self.end_processing()
                            MPI.Finalize()
                            exit(0)
                        continue

                    self.reduce(buffer_data)
                    self.num_reduced_events += 1

                except KeyboardInterrupt as e:
                    print('Recieved keyboard sigterm...')
                    print(str(e))
                    print('shutting down MPI.')
                    self.shutdown()
                    print('---> execution finished.')
                    stdout.flush()
                    exit(0)

        return

    def end_processing(self):
        print('Processing finished. Processed', self.num_reduced_events, 'events in total.')
        stdout.flush()
        pass
