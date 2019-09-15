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

This module contains a set of python exceptions that are specific to OnDA, and a
custom exception handler that reports the OnDA exceptions in a simplified way.
"""
from __future__ import absolute_import, division, print_function

import sys
import traceback  # pylint: disable=unused-import


class OndaException(Exception):
    """
    Base OnDA exception.

    All other OnDA-specific exceptions must subclass from this exception.
    """


class OndaHidraAPIError(OndaException):
    """
    Raised if an error happens during a HiDRA API call.
    """


class OndaMissingEventHandlingFunctionError(OndaException):
    """
    Raised if an Event Handling Function is not defined.
    """


class OndaMissingDataExtractionFunctionError(OndaException):
    """
    Raised if a Data Extraction Function is not defined.
    """


class OndaMissingPsanaInitializationFunctionError(OndaException):
    """
    Raised if a psana Detector Interface Initialization Function is not defined.
    """


class OndaConfigurationFileSyntaxError(OndaException):
    """
    Raised if there is a syntax error in the configuration file.
    """


class OndaConfigurationFileReadingError(OndaException):
    """
    Raised if an error happens while reading the configuration file.
    """


class OndaMissingParameterGroupError(OndaException):
    """
    Raised if a parameter group is missing from the configuration file.
    """


class OndaMissingParameterError(OndaException):
    """
    Raised if a parameter is missing from the configuration file.
    """


class OndaWrongParameterTypeError(OndaException):
    """
    Raised if the type of the configuration parameter does not match the requested one.
    """


class OndaDataExtractionError(OndaException):
    """
    Raised if an error happens during data extraction.
    """


class OndaInvalidSourceError(OndaException):
    """
    Raised if the format of the source string is not valid.
    """


class OndaMissingDependencyError(OndaException):
    """
    Raised if one of the dependencies of a module is not found on the system.
    """


class OndaHdf5FileReadingError(OndaException):
    """
    Raised if an error happens while reading an HDF5 file.
    """


class OndaMissingHdf5PathError(OndaException):
    """
    Raised if an internal HDF5 path is not found.
    """


def onda_exception_handler(type_, value, traceback_):
    """
    Custom OnDA exception handler.

    This function should never be called directly. Instead it should be used as a
    replacement for the standard exception handler. For all OnDA excceptions, this
    handler adds a label to the Exception and hides the stacktrace. All non-OnDA
    exceptions are instead reported normally.

    Arguments:

        type_ (Exception): exception type.

        value (str): exception value (the message that comes with the exception).

        traceback_ (str): traceback to be printed.
    """
    # TODO: Fix types.
    if issubclass(type_, OndaException):
        print("")
        print("OnDA ERROR: {0}".format(value))
        print("")
        sys.stdout.flush()
        sys.stderr.flush()
        sys.exit(0)
    else:
        traceback.print_exception(type_, value, traceback_)
        sys.stdout.flush()
        sys.stderr.flush()
        sys.exit(0)
