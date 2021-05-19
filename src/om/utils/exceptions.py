# This file is part of OM.
#
# OM is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# OM is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with OM.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2020 -2021 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
OM-specific exceptions and exception handling.

This module contains a set of python exceptions that are specific to OM, and a custom
exception handler that reports the OM exceptions in a simplified way.
"""
import sys
import traceback


class OmException(Exception):
    """
    Base class for OM exceptions.

    Base class: Exception

    All other OM-specific exceptions should subclass from this exception.
    """


class OmConfigurationFileReadingError(OmException):
    """
    Raised if an error happens while reading the configuration file.

    Base class: [`OmException`][om.utils.exceptions.OmException]
    """


class OmConfigurationFileSyntaxError(OmException):
    """
    Raised if there is a syntax error in the configuration file.

    Base class: [`OmException`][om.utils.exceptions.OmException]
    """


class OmDataExtractionError(OmException):
    """
    Raised if an error happens during data extraction.

    Base class: [`OmException`][om.utils.exceptions.OmException]
    """


class OmHdf5FileReadingError(OmException):
    """
    Raised if an error happens while reading an HDF5 file.

    Base class: [`OmException`][om.utils.exceptions.OmException]
    """


class OmHdf5PathError(OmException):
    """
    Raised if an internal HDF5 path is not found.

    Base class: [`OmException`][om.utils.exceptions.OmException]
    """


class OmHidraAPIError(OmException):
    """
    Raised if an error happens during a HiDRA API call.

    Base class: [`OmException`][om.utils.exceptions.OmException]
    """


class OmInvalidSourceError(OmException):
    """
    Raised if the format of the source string is not valid.

    Base class: [`OmException`][om.utils.exceptions.OmException]
    """


class OmInvalidDataBroadcastUrl(OmException):
    """
    Raised if the format of the data broadcasting URL is not valid.

    Base class: [`OmException`][om.utils.exceptions.OmException]
    """


class OmInvalidRespondingUrl(OmException):
    """
    Raised if the format of the responding socket's URL is not valid.

    Base class: [`OmException`][om.utils.exceptions.OmException]
    """


class OmMissingDataEventHandlerError(OmException):
    """
    Raised if the implementation of a data event handler cannot be found on the system.

    Base class: [`OmException`][om.utils.exceptions.OmException]
    """


class OmMissingDataExtractionFunctionError(OmException):
    """
    Raised if a Data Extraction Function is not defined.

    Base class: [`OmException`][om.utils.exceptions.OmException]
    """


class OmMissingDependencyError(OmException):
    """
    Raised if one of the python module dependencies is not found on the system.

    Base class: [`OmException`][om.utils.exceptions.OmException]
    """


class OmMissingLayerModuleFileError(OmException):
    """
    Raised if the python implementation of an OM layer cannot be found on the system.

    Base class: [`OmException`][om.utils.exceptions.OmException]
    """


class OmMissingParameterError(OmException):
    """
    Raised if a parameter is missing from the configuration file.

    Base class: [`OmException`][om.utils.exceptions.OmException]
    """


class OmMissingParameterGroupError(OmException):
    """
    Raised if a parameter group is missing from the configuration file.

    Base class: [`OmException`][om.utils.exceptions.OmException]
    """


class OmMissingPsanaInitializationFunctionError(OmException):
    """
    Raised if a psana Detector interface initialization Function is not defined.

    Base class: [`OmException`][om.utils.exceptions.OmException]
    """


class OmWrongParameterTypeError(OmException):
    """
    Raised if the type of a configuration parameter does not match the requested type.

    Base class: [`OmException`][om.utils.exceptions.OmException]
    """


def om_exception_handler(parameter_type, value, traceback_):  # type: ignore
    """
    Custom OM exception handler.

    This function should never be called directly. Instead it should be used as a
    replacement for the standard exception handler. For all OM exceptions, this
    handler adds a label to the exception and hides the stacktrace. All non-OM
    exceptions are instead reported normally.

    Arguments:

        parameter_type (Exception): exception type.

        value (str): exception value (the message that comes with the exception).

        traceback_ (str): traceback to be printed.
    """
    # TODO: Fix types.
    if issubclass(parameter_type, OmException):
        print("OM ERROR: {0}".format(value))
        sys.stdout.flush()
        sys.stderr.flush()
        sys.exit(0)
    else:
        traceback.print_exception(parameter_type, value, traceback_)
        sys.stdout.flush()
        sys.stderr.flush()
        sys.exit(0)
