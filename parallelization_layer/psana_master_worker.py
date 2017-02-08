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
import numpy
import sys
import time

import psana
import cfelpyutils.cfel_psana as cps
import ondautils.onda_dynamic_import_utils as di
import ondautils.onda_param_utils as op

de_layer = di.import_correct_layer_module('data_extraction_layer', op.monitor_params)
initialize = di.import_function_from_layer('initialize', de_layer)
extract = di.import_function_from_layer('extract', de_layer)


class MasterWorker(object):
    NOMORE = 998
    DIETAG = 999
    DEADTAG = 1000

    def __init__(self, map_func, reduce_func, source):

        debug = False

        self.psana_source = None
        self._buffer = None
        self.event_timestamp = None

        self.mpi_rank = MPI.COMM_WORLD.Get_rank()
        self.mpi_size = MPI.COMM_WORLD.Get_size()
        if self.mpi_rank == 0:
            self.role = 'master'
        else:
            self.role = 'worker'

        self.event_rejection_threshold = 10000000000
        self.offline = False
        self.source = source

        # Set offline mode depending on source
        if 'shmem' not in self.source and debug is False:
            self.offline = True
            if not self.source[-4:] == ':idx':
                self.source += ':idx'

        # Set event_rejection threshold
        rej_thr = op.param('PsanaParallelizationLayer','event_rejection_threshold', float)
        if rej_thr is not None:
            self.event_rejection_threshold = rej_thr

        # Set map,reduce and extract functions
        self.map = map_func
        self.reduce = reduce_func
        self.extract_data = extract
        self.initialize_data_extraction = initialize

        if self.role == 'worker':

            self.psana_calib_dir = op.param('PsanaParallelizationLayer', 'psana_calib_dir', str, required=True)

        # The following is executed only on the master node
        if self.role == 'master':

            self.num_reduced_events = 0
            self.num_nomore = 0

            if self.offline is True:
                self.source_runs_dirname = cps.dirname_from_source_runs(source)

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

            psana.setOption('psana.calib-dir'.encode('ascii'), self.psana_calib_dir.encode('ascii'))
            self.psana_source = psana.DataSource(self.source.encode('ascii'))

            if self.offline is False:
                psana_events = self.psana_source.events()
            else:
                def psana_events_generator():
                    for r in self.psana_source.runs():
                        times = r.times()
                        mylength = int(numpy.ceil(len(times) / float(self.mpi_size - 1)))
                        mytimes = times[(self.mpi_rank - 1) * mylength: self.mpi_rank * mylength]
                        for mt in mytimes:
                            yield r.event(mt)

                psana_events = psana_events_generator()

            event = {'monitor_params': op.monitor_params}
            event['det'] = {}
            self.initialize_data_extraction(event['det'])

             # Loop over events and process
            for evt in psana_events:

                if evt is None:
                    continue

                # Reject events above the rejection threshold
                event_id = str(evt.get(psana.EventId))
                timestring = event_id.split('time=')[1].split(',')[0]
                timestamp = datetime.datetimestrptime(timestring[:-6], '%Y-%m-%d %H:%M:%S.%f')
                timestamp = datetime.fromtimestamp(time.mktime(timestamp))
                timenow = datetime.now()

                if (timenow - timestamp).total_seconds() > self.event_rejection_threshold:
                    continue

                event['det']['timestamp'] = timestamp

                # Check if a shutdown message is coming from the server
                if MPI.COMM_WORLD.Iprobe(source=0, tag=self.DIETAG):
                    self.shutdown('Shutting down RANK: {0}'.format(self.mpi_rank))

                event['evt'] = evt

                self.extract_data(event, self)

                if self.raw_data is None:
                    continue

                result = self.map()

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
                        self.num_nomore += 1
                        if self.num_nomore == self.mpi_size - 1:
                            print('All workers have run out of events.')
                            print('Shutting down.')
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
                    exit(0)

        return

    def end_processing(self):
        print('Processing finished. Processed', self.num_reduced_events, 'events in total.')
        sys.stdout.flush()
        pass
