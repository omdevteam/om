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

import time
from builtins import str
from collections import namedtuple
from sys import stdout

from future.utils import raise_from
from mpi4py import MPI
from numpy import ceil, float64

import psana
from cfelpyutils.cfel_psana import dirname_from_source_runs

import ondautils.onda_dynamic_import_utils as di
import ondautils.onda_param_utils as op
from ondautils.onda_exception_utils import (DataExtractionError,
                                            MissingDataExtractionFunction)


EventData = namedtuple('EventData', ['psana_event', 'detector', 'timestamp'])


def _raw_data_init():
    return psana.Detector(op.param('PsanaFacilityLayer', 'detector_name', str, required=True))


def _timestamp_init():
    return None


def _detector_distance_init():
    return psana.Detector(op.param('PsanaFacilityLayer', 'detector_dist_epics_name', str,
                                   required=True).encode('ascii'))


def _beam_energy_init():
    return psana.Detector('EBeam'.encode('ascii'))


def _timetool_data_init():
    return psana.Detector(op.param('PsanaFacilityLayer', 'timetool_epics_name', str, required=True).encode('ascii'))


def _digitizer_data_init():
    return psana.Detector(op.param('PsanaFacilityLayer', 'digitizer_name', str, required=True).encode('ascii'))


def _digitizer2_data_init():
    return psana.Detector(op.param('PsanaFacilityLayer', 'digitizer2_name', str, required=True).encode('ascii'))


def _digitizer3_data_init():
    return psana.Detector(op.param('PsanaFacilityLayer', 'digitizer3_name', str, required=True).encode('ascii'))


def _digitizer4_data_init():
    return psana.Detector(op.param('PsanaFacilityLayer', 'digitizer4_name', str, required=True).encode('ascii'))


def _opal_data_init():
    return psana.Detector(op.param('PsanaFacilityLayer', 'opal_name', str, required=True).encode('ascii'))


def _event_codes_init():
    return psana.Detector('evr0')


def _timestamp(event):
    return event.timestamp


def _detector_distance(event):
    return event.detector['detector_distance']()


def _beam_energy(event):
    return event.detector['beam_energy'].get(event.psana_event).ebeamPhotonEnergy()


def _timetool_data(event):
    return event.detector['timetool_data']()


def _digitizer_data(event):
    return event.detector['digitizer_data'].waveform(event.psana_event)


def _digitizer2_data(event):
    return event.detector['digitizer2_data'].waveform(event.psana_event)


def _digitizer3_data(event):
    return event.detector['digitizer3_data'].waveform(event.psana_event)


def _digitizer4_data(event):
    return event.detector['digitizer4_data'].waveform(event.psana_event)


def _opal_data(event):
    return event.detector['opal_data'].calib(event.psana_event)


def _event_codes_dataext(event):
    return event.detector['event_codes'].eventCodes(event.psana_event)


def _initialize():
    detector = {}
    for init_data_source in data_extraction_funcs:
        detector[init_data_source] = (globals()['_' + init_data_source + '_init'])()
    return detector


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
        rej_thr = op.param('PsanaFacilityLayer', 'event_rejection_threshold')
        if rej_thr is not None:
            self._event_rejection_threshold = rej_thr

        # Set map,reduce and extract functions
        self._map = map_func
        self._reduce = reduce_func
        self._extract_data = _extract
        self._initialize_data_extraction = _initialize

        if self.role == 'worker':
            self._psana_calib_dir = op.param('PsanaFacilityLayer', 'psana_calib_dir', str, required=True)

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

            detector = self._initialize_data_extraction()

            # Loop over events and process
            for evt in psana_events:

                if evt is None:
                    continue

                # Reject events above the rejection threshold
                time_epoch = evt.get(psana.EventId).time()
                timestamp = float64(str(time_epoch[0]) + '.' + str(time_epoch[1]))
                timenow = float64(time.time())

                if (timenow - timestamp) > self._event_rejection_threshold:
                    continue

                # Check if a shutdown message is coming from the server
                if MPI.COMM_WORLD.Iprobe(source=0, tag=self.DIETAG):
                    self.shutdown('Shutting down RANK: {0}'.format(self.mpi_rank))

                event = EventData(evt, detector, timestamp)

                try:
                    self._extract_data(event, self)
                except DataExtractionError as e:
                    print('OnDA Warning: Cannot interpret some event data: {}. Skipping event....'.format(e))
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


in_layer = di.import_correct_layer_module('detector_layer', op.monitor_params)

data_extraction_funcs = [x.strip() for x in op.param('Onda', 'required_data', list, required=True)]

for func in data_extraction_funcs:
    try:
        globals()[func + '_init'] = getattr(in_layer, func + '_init')
    except AttributeError:
        try:
            globals()[func + '_init'] = '_' + func + '_init'
        except AttributeError:
            raise_from(MissingDataExtractionFunction('Data extraction function not defined for the following '
                                                     'data type: {0}'.format(func)), None)

for func in data_extraction_funcs:
    try:
        if func == 'raw_data' and op.param('PsanaFacilityLayer', 'pedestals_only', bool):
            globals()['_' + func] = getattr(in_layer, func + '_pedestals_only')
        else:
            globals()['_' + func] = getattr(in_layer, func)
    except AttributeError:
        try:
            if func == 'raw_data' and op.param('PsanaFacilityLayer', 'pedestals_only', bool):
                globals()['_' + func] = globals()['_' + func + '_pedestals_only']
            else:
                globals()['_' + func] = globals()['_' + func]
        except AttributeError:
            if func == 'raw_data' and op.param('PsanaFacilityLayer', 'pedestals_only', bool):
                raise_from(MissingDataExtractionFunction(
                    'Data extraction function not defined for the following '
                    'data type: {0} (pedestals_only)'.format(func)), None)
            else:
                raise_from(MissingDataExtractionFunction(
                    'Data extraction function not defined for the following '
                    'data type: {0}'.format(func)), None)
