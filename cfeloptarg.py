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


"""
Utilities for parsing command line options and configuration files.

This module contains utilities for parsing of command line options and
configuration files.
"""


import argparse
import os


def parse_cmdline_args():
    """Parses command line arguments for source and monitor.ini file.

    Uses the argparse module to parse command line arguments.
    It parses the following arguments:

        source (1st positional argument): data source (file list, psana source
        string, etc.).

        configuration file (-i/--ini): file containing user-provided
        parameters.
    """

    parser = argparse.ArgumentParser(prog='mpirun [MPI OPTIONS] onda.py', description='OnDA - Online Data Analysis')
    parser.add_argument('source', type=str,
                        help="data source (file list, psana source string, etc.")
    parser.add_argument('-i', '--ini', type=str, default='monitor.ini',
                        help="monitor.ini file (default: monitor.ini), see monitor.ini.template for an example")

    args = parser.parse_args()

    # check that args.ini exists
    if not os.path.exists(args.ini):
        raise NameError('ini file does not exist: ' + args.ini)
    return args


def parse_parameters(config):
    """Sets correct types for parameter dictionaries.

    Reads a parameter dictionary returned by the ConfigParser python modue,
    and assigns correct types to parameters, without changing the structure of
    the dictionary.

    The parser tries to interpret each entry in the dictionary according to the
    following rules:

    - If the entry starts and ends with a single quote, it is interpreted as a
      string.
    - If the entry is the word None, without quotes, then the entry is
      interpreted as NoneType.
    - If the entry is the word False, without quotes, then the entry is
      interpreted as a boolean False.
    - If the entry is the word True, without quotes, then the entry is
      interpreted as a boolean True.
    - If non of the previous options match the content of the entry,
      the parser tries to interpret the entry in order as:

        - An integer number.
        - A float number.
        - A string.

      The first choice that succeeds determines the entry type.

    Args:

        config (dict): parameter dictionary returned by ConfigParser.

    Returns:

        monitor_params (dict): dictionary with the same structure as the input
        dictionary, but with correct types assigned to each entry.
    """

    monitor_params = {}

    for sect in config.sections():
        monitor_params[sect] = {}
        for op in config.options(sect):
            monitor_params[sect][op] = config.get(sect, op)
            if monitor_params[sect][op].startswith("'") and monitor_params[sect][op].endswith("'"):
                monitor_params[sect][op] = monitor_params[sect][op][1:-1]
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
            except:
                try:
                    monitor_params[sect][op] = float(monitor_params[sect][op])
                    continue
                except:
                    pass

    return monitor_params
