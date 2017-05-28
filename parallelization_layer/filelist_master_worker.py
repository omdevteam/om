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
import numpy
import os.path
import sys

import ondautils.onda_dynamic_import_utils as di
import ondautils.onda_param_utils as op


de_layer = di.import_correct_layer_module('data_extraction_layer', op.monitor_params)
open_file = di.import_function_from_layer('open_file', de_layer)
close_file = di.import_function_from_layer('close_file', de_layer)
extract = di.import_function_from_layer('extract', de_layer)
num_events = di.import_function_from_layer('num_events', de_layer)

in_layer = di.import_correct_layer_module('instrument_layer', op.monitor_params)
try:
    file_extensions = di.import_list_from_layer('file_extensions', in_layer)
except RuntimeError:
    try:
        file_extensions = di.import_str_from_layer('file_extensions', in_layer)
    except RuntimeError:
        raise RuntimeError('Could not import file extensions from the instrument layer.')


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

        filelist_filename = source

        self._map = map_func
        self._reduce = reduce_func
        self._extract_data = extract

        with open(filelist_filename, 'r') as fh:
            self._filelist = fh.readlines()

        if self.role == 'master':
            self._num_nomore = 0
            self._num_reduced_events = 0

        if self.role == 'worker':
            self._shots_to_proc = op.param('FilelistParallelizationLayer', 'images_per_file_to_process', int,
                                           required=True)
            self._buffer = None

        return

    def shutdown(self, msg='Reason not provided.'):
        """Shuts down of the data processor.
        """
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
            except RuntimeError:
                MPI.COMM_WORLD.Abort(0)
            exit(0)
        return

    def start(self, verbose=False):

        if self.role == 'worker':

            req = None

            evt = {'monitor_params': op.monitor_params}

            mylength = int(numpy.ceil(len(self._filelist) / float(self.mpi_size - 1)))
            myfiles = self._filelist[(self.mpi_rank - 1) * mylength:self.mpi_rank * mylength]

            for filepath in myfiles:

                if MPI.COMM_WORLD.Iprobe(source=0, tag=self.DIETAG):
                    self.shutdown('Shutting down RANK: {0}.'.format(self.mpi_rank))

                extension_match = [filepath.strip().endswith(x) for x in file_extensions]
                if not any(extension_match) is True:
                    continue

                evt['filename'] = filepath.strip()

                try:
                    evt['filehandle'] = open_file(filepath.strip())
                    evt['filectime'] = datetime.datetime.fromtimestamp(os.path.getctime(filepath.strip()))
                    evt['num_events'] = num_events(evt)
                except (IOError, OSError):
                    print('Cannot read file: {0}'.format(filepath.strip()))
                    continue

                if int(evt['num_events']) < self._shots_to_proc:
                    self._shots_to_proc = int(evt['num_events'])

                for shot_offset in range(-self._shots_to_proc, 0, 1):

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

        # The following is executed on the master
        elif self.role == 'master':

            if verbose:
                print('Starting master.')
                sys.stdout.flush()

            self._num_reduced_events = 0

            # Loops continuously waiting for processed data from workers
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

                except KeyboardInterrupt as e:
                    print('Recieved keyboard sigterm...')
                    print(str(e))
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
