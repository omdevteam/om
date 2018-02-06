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

'''
Main OnDA module.
'''


from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import argparse
import configparser
import importlib
import sys


from onda.utils import exceptions, parameters


def main():
    '''
    Main OnDA monitor function.
    '''

    # Set a custom exception handler.
    sys.excepthook = exceptions.onda_exception_handler

    # Instantiate an argument parser.
    parser = argparse.ArgumentParser(
        prog='mpirun [MPI OPTIONS] onda.py',
        description='OnDA - Online Data Analysis'
    )

    # Add some arguments to the parser.
    parser.add_argument(
        name='source',
        type=str,
        help='data source (file list, psana source string, etc.'
    )

    parser.add_argument(
        flags=['-i', '--ini'],
        type=str,
        default='monitor.ini',
        help='monitor.ini file (default: monitor.ini), see '
             'monitor.ini.template for an example'
    )

    # Run the argument parser.
    args = parser.parse_args()

    # Instantiate the configuration file parser.
    config = configparser.ConfigParser()

    # Read the configuration file and parse it with the configuration
    # parser. Raise an exception if the file cannot be read.
    try:
        config.read(args.ini)
    except OSError:
        raise RuntimeError(
            'Error reading configuration file: {0}'.format(args.ini)
        )

    # Create a MonitorParams object from the parsed configuration file.
    monitor_parameters = parameters.MonitorParams(config)

    # Import the processing layer specified in the configuration file.
    processing_layer = importlib.import_module(
        'onda.processing_layer.{0}'.format(
            monitor_parameters.get_param(
                section='Onda',
                parameter='detector_layer',
                type_=str,
                required=True
            )
        )
    )

    # Import the OndaMonitor class from the processing layer.
    onda_monitor = getattr(
        object=processing_layer,
        name='OndaMonitor'
    )

    # Instantiate the OndaMonitor class and start the monitor.
    monitor = onda_monitor(source=args.source, parameters=monitor_parameters)
    monitor.start(verbose=False)


if __name__ == "__main__":
    main()
