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

import importlib
import sys

from mpi4py import MPI

import onda.utils.parameters as op
from future.utils import raise_from
from onda.utils.exceptions import (DataExtractionError,
                                   MissingDataExtractionFunction)


fa_layer = importlib.import_module(
    'onda.facility_layer.{0}'.format(
        op.param('OnDA', 'facility_layer', str, required=True)
    )
)
de_layer = importlib.import_module(
    'onda.instrument_layer.{0}'.format(
        op.param('OnDA', 'instrument_layer', str, required=True)
    )
)
open_event = getattr(de_layer, 'open_event')
close_event = getattr(de_layer, 'close_event')
num_frames_in_event = getattr(de_layer, 'num_frames_in_event')
filter_event = getattr(de_layer, 'filter_event')
data_extraction_funcs = [x.strip() 
                         for x in op.param(
                             'Onda', 'required_data', list, required=True
                        )]

for func in data_extraction_funcs:
    try:
        globals()['_' + func] = getattr(fa_layer, func)
    except AttributeError:
        try:
            globals()['_' + func] = getattr(de_layer, func)
        except AttributeError as e:
            raise MissingDataExtractionFunction(
                'The {0} data extraction function is not defined'.format(func)
            )


def _extract(event, monitor):
    for entry in data_extraction_funcs:
        try:
            setattr(monitor, entry, globals()['_' + entry](event))
        except Exception as e:
            raise DataExtractionError(
                'Error extracting {0}: {1}'.format(entry, e)
            )


class ParallelizationEngine(object):
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
            self._shots_to_proc = op.param(
                'FilelistParallelizationLayer', 'images_per_file_to_process',
                int, required=True
            )
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

            events = event_generator()

            for event in events:

                if MPI.COMM_WORLD.Iprobe(source=0, tag=self.DIETAG):
                    self.shutdown('Shutting down RANK: {0}.'.format(self.mpi_rank))

                if reject_filter(event):
                    continue

                n_events = num_events(event)

                if n_events < self._shots_to_proc:
                    self._shots_to_proc = n_events

                opened_event = open_event(event)

                for shot_offset in range(-self._shots_to_proc, 0, 1):

                    event_data = create_event_data(event)

                    try:
                        self._extract_data(event_data, self)
                    except DataExtractionError as e:
                        print('OnDA Warning: Cannot interpret some event data: {}. Skipping event....'.format(e))
                        continue

                    result = self._map()

                    if req:
                        req.Wait()
                    req = MPI.COMM_WORLD.isend(result, dest=0, tag=0)

                if req:
                    req.Wait()

                close_event(event)

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
