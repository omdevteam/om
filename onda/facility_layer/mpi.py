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

import sys

import importlib as il
from future.utils import raise_from
from mpi4py import MPI

import onda.utils.parameters as op
from onda.utils.exceptions import (DataExtractionError,
                                   MissingDataExtractionFunction)

# Import the detector module
detector_layer = il.import_module(
    'onda.detector_layer.{0}'.format(
        op.param(
            section='Onda',
            parameter='detector_layer',
            type_=str,
            required=True
        )
    )
)

# Import functions from the detector module
open_event = getattr(object=detector_layer, name='open_event')
close_event = getattr(object=detector_layer, name='close_event')
get_num_frames_in_event = getattr(
    object=detector_layer,
    name='get_num_frames_in_event'
)

# Import facility module
facility_layer = il.import_module(
    'onda.facility_layer.{0}'.format(
        op.param(
            section='Onda',
            parameter='facility_layer',
            type_=str,
            required=True
        )
    )
)

# Import functions from the facility module
event_generator = getattr(object=detector_layer, name='event_generator')
reject_filter = getattr(object=detector_layer, name='reject_filter')


def _prepare_data_extraction_functions():
    '''Recovers the requires data extraction functions

    The function recovers the required data extraction functions from the
    detector and instrument layers, and stores them in a tuple. It reads the
    list of functions to recover from the configuration file. It then looks for
    the required functions in the detector layer first, then in the facility
    layer. It raises an exception if a required data extraction function is not
    found in any of the two layers.

    Returns:

        func_list(tuple): a tuple containing data recovery functions
    '''

    # Recover list of requried data function from the parameter file
    data_extraction_funcs = [
        x.strip() for x in op.param(
            section='Onda',
            parameter='required_data',
            type_=list,
            required=True
        )
    ]

    # Create list that will be returned (after conversion to a tuple)
    func_list = []

    # Iterate over the required functions and look for them in the detector
    # and facility layer.
    for func in data_extraction_funcs:
        try:
            func_list.append(getattr(object=detector_layer, name=func))
        except AttributeError:
            try:
                func_list.append(getattr(object=facility_layer, name=func))
            except AttributeError:
                raise_from(
                    exc=MissingDataExtractionFunction(
                        'Data extraction function not defined for the'
                        'following data type: {0}'.format(func)
                    ),
                    cause=None
                )

    # Return the list of recovered functions after conversion to a tuple
    return tuple(func_list)


class MasterWorker(object):
    '''An MPI master-worker parallelization engine for OnDA
    '''

    NOMORE = 998
    DIETAG = 999
    DEADTAG = 1000

    def __init__(self, map_func, reduce_func, source):
        '''MasterWorker class initialization

        Initializes the MasterWorker class.

        map_func(func)


        self.mpi_rank = MPI.COMM_WORLD.Get_rank()
        self.mpi_size = MPI.COMM_WORLD.Get_size()
        if self.mpi_rank == 0:
            self.role = 'master'
        else:
            self.role = 'worker'

        filelist_filename = source

        self._map = map_func
        self._reduce = reduce_func

        with open(filelist_filename, 'r') as fh:
            self._filelist = fh.readlines()

        if self.role == 'master':
            self._num_nomore = 0
            self._num_reduced_events = 0

        if self.role == 'worker':

            self._data_extr_funcs = None
            self._shots_to_proc = op.param(
                'FilelistParallelizationLayer',
                'images_per_file_to_process',
                int,
                required=True
            )
            self._buffer = None

        return

    def shutdown(self, msg='Reason not provided.'):
        """Shuts down of the data processor.
        """
        print('Shutting down:', msg)
        sys.stdout.flush()

        if self.role == 'worker':
            self._buffer = MPI.COMM_WORLD.send(
                dest=0,
                tag=self.DEADTAG
            )
            MPI.Finalize()
            exit(0)

        if self.role == 'master':

            try:
                for nod_num in range(1, self.mpi_size()):
                    MPI.COMM_WORLD.isend(
                        0,
                        dest=nod_num,
                        tag=self.DIETAG
                    )
                num_shutdown_confirm = 0
                while True:
                    if MPI.COMM_WORLD.Iprobe(
                        source=MPI.ANY_SOURCE,
                        tag=0
                    ):
                        self._buffer = MPI.COMM_WORLD.recv(
                            source=MPI.ANY_SOURCE,
                            tag=0
                        )
                    if MPI.COMM_WORLD.Iprobe(
                        source=MPI.ANY_SOURCE,
                        tag=self.DEADTAG
                    ):
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

            self._data_extr_funcs = self._prepare_data_extraction_functions()
            events = event_generator()

            for event in events:

                if MPI.COMM_WORLD.Iprobe(
                    source=0,
                    tag=self.DIETAG
                ):
                    self.shutdown(
                        'Shutting down RANK: {0}.'.format(self.mpi_rank)
                    )

                if reject_filter(event):
                    continue

                n_events = get_num_frames_in_event(event)

                if n_events < self._shots_to_proc:
                    self._shots_to_proc = n_events

                opened_event = open_event(event)

                for shot_offset in range(-self._shots_to_proc, 0, 1):

                    event_data = create_event_data(event, shot_offset)

                    try:
                        self._extract_data(event_data)
                    except DataExtractionError as e:
                        print(
                            'OnDA Warning: Cannot interpret some event data: '
                            '{}. Skipping event....'.format(e)
                        )
                        continue

                    result = self._map()

                    if req:
                        req.Wait()
                    req = MPI.COMM_WORLD.isend(
                        result,
                        dest=0,
                        tag=0
                    )

                if req:
                    req.Wait()

                close_event(event)

            end_dict = {'end': True}
            if req:
                req.Wait()
            MPI.COMM_WORLD.isend(
                (end_dict, self.mpi_rank),
                dest=0,
                tag=0
            )
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

                    buffer_data = MPI.COMM_WORLD.recv(
                        source=MPI.ANY_SOURCE,
                        tag=0
                    )
                    if 'end' in buffer_data[0].keys():
                        print(
                            'Finalizing {}'.format(buffer_data[1])
                        )
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
        print(
            'Processing finished. Processed {} events in total.'.format(
                self._num_reduced_events
            )
        )
        sys.stdout.flush()


    def _extract_data(self, event):
        '''Extracts data and adds it to a dictionary

        The functions calls all the required data extraction functions
        Each function extracts the data and adds it to the 'data' dictionary.
        An exception is raised if any of the functions fails.

        Returns:

           data (dict): dictionary containing the extracted data
        '''

        for func_name in data_extraction_funcs:
            decorated_func_name = '_{}'.format(func_name)
            try:
                self.data[func_name] = globals()[decorated_func_name](event)
            except Exception as e:
                raise DataExtractionError(
                    'Error extracting {0}: {1}'.format(func_name, e)
                )


