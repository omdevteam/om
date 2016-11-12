#    This file is part of cfelpyutils.
#
#    cfelpyutils is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    cfelpyutils is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with cfelpyutils.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from sys import version_info

"""
Utilities for parsing command line options and configuration files.

This module contains utilities for parsing of command line options and
configuration files.
"""


def parse_parameters(config):
    """Sets correct types for parameter dictionaries.

    Reads a parameter dictionary returned by the ConfigParser python module, and assigns correct types to parameters,
    without changing the structure of the dictionary.

    The parser tries to interpret each entry in the dictionary according to the following rules:

    - If the entry starts and ends with a single quote, it is interpreted as a string.
    - If the entry is the word None, without quotes, then the entry is interpreted as NoneType.
    - If the entry is the word False, without quotes, then the entry is interpreted as a boolean False.
    - If the entry is the word True, without quotes, then the entry is interpreted as a boolean True.
    - If non of the previous options match the content of the entry, the parser tries to interpret the entry in order
      as:

        - An integer number.
        - A float number.
        - A string.

      The first choice that succeeds determines the entry type.

    Args:

        config (class RawConfigParser): ConfigParser instance.

    Returns:

        monitor_params (dict): dictionary with the same structure as the input dictionary, but with correct types
        assigned to each entry.
    """

    monitor_params = {}

    for sect in config.sections():
        monitor_params[sect] = {}
        for op in config.options(sect):
            monitor_params[sect][op] = config.get(sect, op)
            if monitor_params[sect][op].startswith("'") and monitor_params[sect][op].endswith("'"):
                monitor_params[sect][op] = monitor_params[sect][op][1:-1]
                if version_info[0] == 2:
                    try:
                        monitor_params[sect][op] = unicode(monitor_params[sect][op])
                    except UnicodeDecodeError:
                        raise RuntimeError('Error parsing parameters. Only ASCII characters are allowed in parameter '
                                           'names and values.')
                continue
            if monitor_params[sect][op] == 'None':
                monitor_params[sect][op] = None
                continue
            if monitor_params[sect][op] == 'False':
                monitor_params[sect][op] = False
                continue
            if monitor_params[sect][op] == 'True':
                monitor_params[sect][op] = True
                continue
            try:
                monitor_params[sect][op] = int(monitor_params[sect][op])
                continue
            except ValueError:
                try:
                    monitor_params[sect][op] = float(monitor_params[sect][op])
                    continue
                except ValueError:
                    raise RuntimeError('Error parsing parameters. The parameter {0}/{1} parameter has an invalid type. '
                                       'Allowed types are None, int, float, bool and str. Strings must be '
                                       'single-quoted.'.format(sect, op))

    return monitor_params
