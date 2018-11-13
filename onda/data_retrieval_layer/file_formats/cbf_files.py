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
#
#    Copyright 2014-2018 Deutsches Elektronen-Synchrotron DESY,
#    a research centre of the Helmholtz Association.
"""
Manipulation of CBF files.

Classes and functions used to manipulate files in CBF format.
"""
from __future__ import absolute_import, division, print_function

from future.utils import raise_from

from onda.utils import exceptions

try:
    import fabio
except ImportError:
    raise_from(
        exc=exceptions.MissingDependency(
            "The cbf_files module could not be loaded. The following"
            "dependency does not appear to be available on the "
            "system: fabio."
        ),
        cause=None
    )


def open_event(event):
    """
    Opens a CBF file event.

    Makes the content of the event (file) available in the 'data' entry
    of the event dictionary.

    Args:

        event (Dict): a dictionary with the event data.
    """
    # Opens the CBF file using the fabio library and saves the content
    # (stored as a cbf_obj object) in the 'data' entry of the event
    # dictionary.
    event['data'] = fabio.open(event['full_path'])


def close_event(event):
    """
    Closes an CBF file event.

    Args:

        event (Dict): a dictionary with the event data.
    """
    del event
    # The function does nothing: CBF files do not need to be closed.
