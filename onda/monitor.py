#!/usr/bin/env python
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
Main OnDA monitor.

This module contains the implementation of the main function used to
start OnDA monitors.
"""
from __future__ import absolute_import, division, print_function

import argparse
import sys
from builtins import str  # pylint: disable=W0622

import toml
from onda.utils import dynamic_import, exceptions, parameters


def main():
    """
    Main OnDA monitor function.
    """
    # Set a custom exception handler to deal with OnDA-specific
    # exceptions.
    sys.excepthook = exceptions.onda_exception_handler

    parser = argparse.ArgumentParser(
        prog="mpirun [MPI OPTIONS] onda.py",
        description="OnDA - Online Data Analysis"
    )

    parser.add_argument(
        'source',
        type=str,
        help="data source (file list, psana source string, etc.)"
    )

    parser.add_argument(
        '-i', '--ini',
        type=str,
        default='monitor.ini',
        help="monitor.ini file (default: monitor.ini file in the "
             "current working directory"
    )

    args = parser.parse_args()
    try:
        config = toml.load(args.ini)
    except IOError:
        # Raise an exception if the file cannot be opened or read.
        raise exceptions.ConfigFileReadingError(
            "Cannot open or read the configuration file {0}".format(
                args.ini
            )
        )

    except toml.TomlDecodeError:
        # Raise an exception if the file cannot be interpreted.
        raise exceptions.ConfigFileSyntaxError(
            "Syntax error in the configuration file {0}. "
            "Make sure that the configuration file follows "
            "the TOML syntax: https://github.com/toml-lang/toml".format(
                args.ini
            )
        )

    monitor_parameters = parameters.MonitorParams(config)

    processing_layer = dynamic_import.import_processing_layer(
        monitor_parameters
    )

    monitor = processing_layer.OndaMonitor(
        source=args.source,
        monitor_parameters=monitor_parameters
    )

    monitor.start()
