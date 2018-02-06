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
'''
Functions and classes to process data stored in files.
'''


from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import importlib
import os.path

import numpy
from future.utils import raise_from


def event_generator(source, node_rank, mpi_pool_size, _):
    '''
    Generate event list.

    Called once to initialize. It can be then iterated upon as it yelds
    a python iterator.

    Args:

            source (function): a python generator function from which
                worker nodes can recover data (by iterating over it).

            node_rank (int): rank of the worker node for which the event
                list will be generated.

            mpi_pool_size (int): size of the MPI pool that includes the node
                for which the event list will be generated.
    '''

    try:
        with open(source, 'r') as fhandle:
            filelist = fhandle.readlines()
    except OSError:
        raise_from(
            exc=RuntimeError(
                'Error reading the {} source file.'.format(
                    source
                )
            ),
            source=None
        )

    mylength = int(
        numpy.ceil(
            len(filelist) / float(mpi_pool_size - 1)
        )
    )
    myfiles = filelist[
        ((node_rank - 1) * mylength):(node_rank * mylength)
    ]

    for entry in myfiles:
        yield entry


class EventFilter(object):
    '''
    Filter events.

    Decide on the rejection of events that do no match certain criteria.
    '''

    def __init__(self, monitor_params):
        '''
        Initialize the EventFilter class.

        Args:

            monitor_params (:obj:`onda.utils.parameters.MonitorParameters`): an
            object of type MonitorParameters with the monitor parameters.
        '''

        # Import the detector layer.
        detector_layer = importlib.import_module(
            'onda.detector_layer.{0}'.format(
                monitor_params.get_param(
                    section='Onda',
                    parameter='detector_layer',
                    type_=str,
                    required=True
                )
            )
        )

        # Import the allowed file extensions from the detector layer and
        # store then in an attribute.
        self._file_extensions = getattr(
            object=detector_layer,
            name='FILE_EXTENSIONS'
        )

    def should_reject(self, event):
        '''
        Decide if the event should be rejected.

        Args:

            event (dict): event data (the exact format depends on the
            facility).

        Returns:

            bool: True if the event should be rejected. False if the event
            should be processed.
        '''

        # Check if the filename ends with one of the allowed file extensions.
        # If it doesn't, reject the file.
        if os.path.basename(event).endswith(self._file_extensions):
            return False
        else:
            return True
