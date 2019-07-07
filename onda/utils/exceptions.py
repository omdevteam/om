# This file is part of OnDA.
#
# OnDA is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# OnDA is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with OnDA.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
OnDA-specific exceptions and exception handling.
"""
from __future__ import absolute_import, division, print_function

import sys
import traceback  # pylint: disable=unused-import
from traceback import print_exception
from typing import NoReturn  # pylint: disable=unused-import

from mpi4py import MPI


class OndaException(Exception):
    """
    Base OnDA exception.

    All other OnDA-specific exceptions must subclass from this exception.
    """


class OndaHidraAPIError(OndaException):
    """
    Error within a HiDRA API call.
    """


class OndaMissingEventHandlingFunctionError(OndaException):
    """
    An event handling function is not defined.
    """


class OndaMissingDataExtractionFunctionError(OndaException):
    """
    A data extraction function is not defined.
    """


class OndaMissingPsanaInitializationFunctionError(OndaException):
    """
    A psana Detector interface initialization function is not defined.
    """


class OndaConfigurationFileSyntaxError(OndaException):
    """
    There is a syntax error in the configuration file.
    """


class OndaConfigurationFileReadingError(OndaException):
    """
    Error while reading the configuration file.
    """


class OndaMissingParameterGroupError(OndaException):
    """
    A group of parameters is missing in the configuration file.
    """


class OndaMissingParameterError(OndaException):
    """
    A parameter is missing in the configuration file.
    """


class OndaWrongParameterTypeError(OndaException):
    """
    The type of the parameter in the config file does not match the requested type.
    """


class OndaDataExtractionError(OndaException):
    """
    Error during data extraction.
    """


class OndaInvalidSourceError(OndaException):
    """
    The format of the source string is not valid.
    """


class OndaMissingDependencyError(OndaException):
    """
    One of the dependecies of a module is not installed.
    """


class OndaHdf5FileReadingError(OndaException):
    """
    Error while reading an HDF5 file.
    """


def onda_exception_handler(type_, value, traceback_):
    # type: (Exception, str, traceback.traceback) -> NoReturn
    """
    Custom OnDA exception handler.

    This function should never be called directly. Instead it should be used as a
    replacement for the standard exception handler. For all OnDA excceptions, it adds a
    label to the Exception and hide the stacktrace. All non-OnDA exceptions are instead
    reported normally.

    Arguments:

        type_ (Exception): exception type.

        value (str): exception value (the message that comes with the exception).

        traceback_ (traceback.traceback): traceback to be printed.
    """
    if issubclass(type_, OndaException):
        print("")
        print(">>>>> OnDA ERROR: {0} <<<<<".format(value))
        print("")
        sys.stdout.flush()
        sys.stderr.flush()
        MPI.COMM_WORLD.Abort(0)
    else:
        print_exception(type_, value, traceback_)
        sys.stdout.flush()
        sys.stderr.flush()
        MPI.COMM_WORLD.Abort(0)
        exit(0)
