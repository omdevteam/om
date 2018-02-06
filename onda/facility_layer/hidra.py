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
import socket

from onda.facility_layer.hidra_api import Transfer

import numpy
from future.utils import raise_from


def initialize_event_generator(source, mpi_pool_size,
                               monitor_params):
    '''
    Generate event list.

    Called once to initialize. It can be then iterated upon as it yelds
    a python iterator.

    Args:

            source (function): a python generator function from which
                worker nodes can recover data (by iterating over it).
    '''

    # Read the requested transfer type from the configuration file.
    transfer_type = monitor_params.get_param(
        section='HidraFacilityLayer',
        parameter='transfer_type',
        type_='str',
        required=True
    )

    # Set some variables depending on the requested transfer type.
    # If the transfer type is data-based...
    if transfer_type == 'data':

        # Request the latest event with full data.
        query_text = 'QUERY_NEXT'

        # No base path, since data is tranferred over the network.
        data_base_path = ''

    # If the transfer type is metadata-based...
    elif transfer_type == 'metadata':

        # Request the latest event with metadata only.
        query_text = 'QUERY_METADATA'

        # Read the data base path from the configuration file.
        data_base_path = os.path.join(
            monitor_params.getparam(
                section='PetraIIIParallelizationLayer',
                parameter='data_base_path',
                type_=str,
                required=True
            )
        )

    # If the transfer type is unknown, raise an exception.
    else:
        raise RuntimeError(
            'Unrecognized transfer type for HiDRA Facility layer.'
        )

    base_port = monitor_params.get_param(
        section='PetraIIIParallelizationLayer',
        parameter='base_port',
        type_=int,
        required=True
    )

    targets = [['', '', 1]]

    for node_rank in range(1, mpi_pool_size):
        target_entry = [
            socket.gethostname(),
            str(base_port + node_rank),
            str(priority),
        ]
        targets.append(target_entry)





    query = Transfer(
        connection_type=query_text,
        signal_host=source,
        use_log=None
    )







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
