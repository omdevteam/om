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
from collections import namedtuple

import numpy
from future.utils import raise_from
from mpi4py import MPI

import ondautils.onda_dynamic_import_utils as di
import ondautils.onda_param_utils as op
from ondautils.onda_exception_utils import (DataExtractionError,
                                            MissingDataExtractionFunction)

EventData = namedtuple('EventData', ['filehandle', 'filename', 'filectime', 'num_events', 'shot_offset',
                                     'monitor_params'])


def _extract(event, monitor):
    for entry in data_extraction_funcs:
        try:
            setattr(monitor, entry, globals()['_' + entry](event))
        except Exception as e:
            raise DataExtractionError('Error extracting {0}: {1}'.format(entry, e))


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
        self._extract_data = _extract

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

            mylength = int(numpy.ceil(len(self._filelist) / float(self.mpi_size - 1)))
            myfiles = self._filelist[(self.mpi_rank - 1) * mylength:self.mpi_rank * mylength]

            for filepath in myfiles:

                if MPI.COMM_WORLD.Iprobe(source=0, tag=self.DIETAG):
                    self.shutdown('Shutting down RANK: {0}.'.format(self.mpi_rank))

                extension_match = [filepath.strip().endswith(extension) for extension in file_extensions]
                if not any(extension_match) is True:
                    continue

                filename = filepath.strip()

                try:
                    filehandle = open_file(filepath.strip())
                    filectime = os.path.getctime(filepath.strip())
                    num_events = num_events_in_file(filehandle)
                except (IOError, OSError) as e:
                    print('OnDA Warning: Cannot read file {0}: {1}. Skipping file...'.format(filepath.strip(), e))
                    continue

                if num_events < self._shots_to_proc:
                    self._shots_to_proc = num_events

                for shot_offset in range(-self._shots_to_proc, 0, 1):

                    event = EventData(filehandle, filename, filectime, num_events_in_file, shot_offset,
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


in_layer = di.import_correct_layer_module('detector_layer', op.monitor_params)

open_file = di.import_function_from_layer('open_file', in_layer)
close_file = di.import_function_from_layer('close_file', in_layer)
num_events_in_file = di.import_function_from_layer('num_events_in_file', in_layer)
file_extensions = di.import_list_from_layer('file_extensions', in_layer)

data_extraction_funcs = [x.strip() for x in op.param('Onda', 'required_data', list, required=True)]
for func in data_extraction_funcs:
    try:
        globals()['_' + func] = getattr(in_layer, func)
    except AttributeError:
        if func not in globals():
            raise_from(MissingDataExtractionFunction('Data extraction function not defined for the following '
                                                     'data type: {0}'.format(func)), None)
