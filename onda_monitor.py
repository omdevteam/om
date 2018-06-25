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
Main OnDA module.

This module contains the implementation of the main function used to
start an OnDA monitor.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import argparse
import configparser
import sys
from builtins import str  # pylint: disable=W0622

from onda.utils import dynamic_import, exceptions, parameters


def main():
    """
    Main OnDA monitor function.

    The function called to start an OnDA monitor.
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
    config = configparser.ConfigParser()
    try:
        config.read(args.ini)
    except OSError:
        # Raise a RuntimeError exception if the file cannot be
        # read.
        raise RuntimeError(
            "Error reading configuration file: {0}".format(args.ini)
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


if __name__ == '__main__':
    main()
