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
Utilities to manipulate CBF files.

This module contains the implementation of several functions used to
manipulate CBF files.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import fabio


def open_event(event):
    """
    Open the event.

    Make the content of the event (file) available in the 'data' entry
    of the event dictionary.

    Args:

        event (Dict): a dictionary with the event data.
    """
    # Open the CBF file using the fabio library and saved the content
    # (stored as a cbf_obj object) in the 'data' entry of the event
    # dictionary.
    event['data'] = fabio.open(event['metadata']['full_path'])


def close_event(_):
    """
    Close event.

    Args:

        event (Dict): a dictionary with the event data.
    """
    # Do nothing: CBF files do not need to be closed.
    pass
