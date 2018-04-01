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
OnDA-specific exceptions and exception handler.

Exports:

    Functions:

        onda_exception_handler: custom OnDA excpetion handler.

    Classes:

        OndaException: base OnDA exception.

        HidraAPIError: error in the HiDRA API.

        MissingEventHandlingFunction: non-defined eventhandling
            function.

        MissingDataExtractionFunction: non-defined data extraction
            function.

        MissingPsanaInitializationFunction: non-defined psana Detector
            interface initialization function.

        MissingFile: required file missing.

        MissingParameterFileSection: section missing in the
            configuration file.

        MissingParameter(OndaException): parameter missing in the
            configuration file.

        WrongParameterType: type of a parameter does not match the
            requested type.

        DataExtractionError: error during data extraction.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import sys
from traceback import print_exception

from mpi4py import MPI


class OndaException(Exception):
    """
    Base OnDA exception.

    Base OnDA exception, from which all other OnDA-specific exceptions
    inherit.
    """
    pass


class HidraAPIError(OndaException):
    """
    Error in the HiDRA API.

    Error within a HiDRA API call.
    """
    pass


class MissingEventHandlingFunction(OndaException):
    """
    Event handling function not defined.

    One of the required event handling functions is not defined.
    """
    pass


class MissingDataExtractionFunction(OndaException):
    """
    Data extraction function not defined.

    One of the requested data extraction functions is not defined.
    """
    pass

class  MissingPsanaInitializationFunction(OndaException):
    """
    Psana Detector interface initialization function not defined.

    One of the requested psana Detector interface initialization
    functions is not defined.
    """
    pass


class MissingParameterFileSection(OndaException):
    """
    Missing configuration file section.

    Missing section in the configuration file.
    """
    pass


class MissingParameter(OndaException):
    """
    Missing parameter.

    Parameter missing from the configuration file.
    """
    pass


class WrongParameterType(OndaException):
    """
    Wrong parameter type.

    Parameter type does not match requested type.
    """
    pass


class DataExtractionError(OndaException):
    """
    Data extraction error.

    Error during data extraction.
    """
    pass


def onda_exception_handler(type_, value, traceback):
    """
    Custom OnDA exception handler.

    Custom handler for OnDA. Add a label and hide the stracktrace for
    OnDA exceptions. Report all other exceptions normally.

    Args:
    """
    if issubclass(type, OndaException):
        print('')
        print('>>>>> OnDA ERROR: {0} <<<<<'.format(value))
        print('')
        MPI.COMM_WORLD.Abort(0)
    else:
        print_exception(type_, value, traceback)
        sys.stdout.flush()
        sys.stderr.flush()
        MPI.COMM_WORLD.Abort(0)
