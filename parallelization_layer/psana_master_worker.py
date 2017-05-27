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

from datetime import datetime
from mpi4py import MPI
from numpy import ceil
from sys import exit, stdout
from time import strptime, mktime

import psana
from cfelpyutils.cfel_psana import dirname_from_source_runs
from ondautils.onda_param_utils import monitor_params, param
from ondautils.onda_dynamic_import_utils import import_correct_layer_module, import_function_from_layer

de_layer = import_correct_layer_module('data_extraction_layer', monitor_params)
initialize = import_function_from_layer('initialize', de_layer)
extract = import_function_from_layer('extract', de_layer)


class MasterWorker(object):
    NOMORE = 998
    DIETAG = 999
    DEADTAG = 1000

    def __init__(self, map_func, reduce_func, source):

        debug = False

        self._psana_source = None
        self._buffer = None
        self._event_timestamp = None

        self.mpi_rank = MPI.COMM_WORLD.Get_rank()
        self.mpi_size = MPI.COMM_WORLD.Get_size()

        if self.mpi_rank == 0:
            self.role = 'master'
        else:
            self.role = 'worker'

        self._event_rejection_threshold = 10000000000
        self._offline = False
        self._source = source

        # Set offline mode depending on source
        if 'shmem' not in self._source and debug is False:
            self._offline = True
            if not self._source[-4:] == ':idx':
                self._source += ':idx'

        # Set event_rejection threshold
        rej_thr = param('PsanaParallelizationLayer', 'event_rejection_threshold')
        if rej_thr is not None:
            self._event_rejection_threshold = rej_thr

        # Set map,reduce and extract functions
        self._map = map_func
        self._reduce = reduce_func
        self._extract_data = extract
        self._initialize_data_extraction = initialize

        if self.role == 'worker':
            self._psana_calib_dir = param('PsanaParallelizationLayer', 'psana_calib_dir', str, required=True)

        # The following is executed only on the master node
        if self.role == 'master':

            self._num_reduced_events = 0
            self._num_nomore = 0

            if self._offline is True:
                self._source_runs_dirname = dirname_from_source_runs(source)

        return

    def shutdown(self, msg='Reason not provided.'):

        print('Shutting down:', msg)

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

            psana.setOption('psana.calib-dir'.encode('ascii'), self._psana_calib_dir.encode('ascii'))
            self._psana_source = psana.DataSource(self._source.encode('ascii'))

            if self._offline is False:
                psana_events = self._psana_source.events()
            else:
                def psana_events_generator():
                    for r in self._psana_source.runs():
                        times = r.times()
                        mylength = int(ceil(len(times) / float(self.mpi_size - 1)))
                        mytimes = times[(self.mpi_rank - 1) * mylength: self.mpi_rank * mylength]
                        for mt in mytimes:
                            yield r.event(mt)

                psana_events = psana_events_generator()

            event = {'monitor_params': monitor_params, 'det': {}}
            self._initialize_data_extraction(event['det'])

            # Loop over events and process
            for evt in psana_events:

                if evt is None:
                    continue

                # Reject events above the rejection threshold
                event_id = str(evt.get(psana.EventId))
                timestring = event_id.split('time=')[1].split(',')[0]
                timestamp = strptime(timestring[:-6], '%Y-%m-%d %H:%M:%S.%f')
                timestamp = datetime.fromtimestamp(mktime(timestamp))
                timenow = datetime.now()

                if (timenow - timestamp).total_seconds() > self._event_rejection_threshold:
                    continue

                event['det']['timestamp'] = timestamp

                # Check if a shutdown message is coming from the server
                if MPI.COMM_WORLD.Iprobe(source=0, tag=self.DIETAG):
                    self.shutdown('Shutting down RANK: {0}'.format(self.mpi_rank))

                event['evt'] = evt

                self._extract_data(event, self)

                if self.raw_data is None:
                    continue

                result = self._map()

                # send the mapped event data to the master process
                if req:
                    req.Wait()  # be sure we're not still sending something
                req = MPI.COMM_WORLD.isend(result, dest=0, tag=0)

            # When all events have been processed, send the master a
            # dictionary with an 'end' flag and die
            end_dict = {'end': True}
            if req:
                req.Wait()  # be sure we're not still sending something
            MPI.COMM_WORLD.isend((end_dict, self.mpi_rank), dest=0, tag=0)
            MPI.Finalize()
            exit(0)

        # The following is executed on the master
        elif self.role == 'master':

            if verbose:
                print('Starting master.')

            # Loops continuously waiting for processed data from workers
            while True:

                try:

                    buffer_data = MPI.COMM_WORLD.recv(
                        source=MPI.ANY_SOURCE,
                        tag=0)
                    if 'end' in buffer_data[0].keys():
                        print('Finalizing', buffer_data[1])
                        self._num_nomore += 1
                        if self._num_nomore == self.mpi_size - 1:
                            print('All workers have run out of events.')
                            print('Shutting down.')
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
                    exit(0)

        return

    def end_processing(self):
        print('Processing finished. Processed', self._num_reduced_events, 'events in total.')
        stdout.flush()
        pass
