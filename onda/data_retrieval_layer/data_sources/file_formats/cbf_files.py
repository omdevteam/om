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

Exports:

    Functions:

        open_event: open an event.

        close_event: close an event.
"""
import fabio


def open_event(event):
    """
    Open event.

    Open the event by opening the file using the fabio library. Store
    the content of the cbf file as a fabio module cbf_obj object in the
    'data' entry of the event dictionary.

    Args:

        event (Dict): a dictionary with the event data.
    """
    event['data'] = fabio.open(event['metadata']['full_path'])


def close_event(_):
    """
    Close event.

    CBF files don't need to be closed, so do nothing.

    Args:

        event (Dict): a dictionary with the event data.
    """
    pass
