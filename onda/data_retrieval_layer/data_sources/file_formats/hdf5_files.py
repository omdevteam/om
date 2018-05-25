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

"""
Utilities to manipulate HDF5 files.

Exports:

    Functions:

        open_event: open an event.

        close_event: close an event.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import h5py


def open_event(event):
    """
    Open event.

    Open the event by opening the file using the h5py library. Save
    the open file filehandle in the 'data' entry of the event
    dictionary).

    Args:

        event (Dict): a dictionary with the event data.
    """
    event['data'] = h5py.File(
        name=event['metadata']['full_path'],
        mode='r'
    )


def close_event(event):
    """
    Close event.

    Close event by closing the h5py file.

    Args:

        event (Dict): a dictionary with the event data.
    """
    event['data'].close()
