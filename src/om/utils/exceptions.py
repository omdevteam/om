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
    Base class for OM's exceptions.

    All other OM-specific exceptions should inherit from this exception.
    """


class OmConfigurationFileReadingError(OmException):
    """
    Raised if an error happens while OM is reading its configuration file.

    """


class OmConfigurationFileSyntaxError(OmException):
    """
    Raised if there is a syntax error in OM's configuration file.

    """


class OmDataExtractionError(OmException):
    """
    Raised if an error happens during data extraction.

    """


class OmEigerHttpInterfaceInitializationError(OmException):
    """
    Raised if an error happens while OM is accessing Eiger http interface.

    """


class OmGeometryError(OmException):
    """
    Raised if an error in a geometry file read by OM.

    """


class OmHdf5FileReadingError(OmException):
    """
    Raised if an error happens while reading an HDF5 data file.

    """


class OmHdf5UnsupportedDataFormat(OmException):
    """
    Raised when trying to write an unsupported data format into an HDF5 data file.

    """


class OmHdf5PathError(OmException):
    """
    Raised if an internal HDF5 path cannot be found.

    """


class OmInvalidSourceError(OmException):
    """
    Raised if the format of the source string is not valid.

    """


class OmInvalidDataBroadcastUrl(OmException):
    """
    Raised if the format of the data broadcasting socket's URL is not valid.

    """


class OmInvalidRespondingUrl(OmException):
    """
    Raised if the format of the responding socket's URL is not valid.

    """


class OmMissingDataRetrievalClassError(OmException):
    """
    Raised if a Data Retrieval class cannot be found in the Data Retrieval Layer.

    """


class OmMissingDataEventError(OmException):
    """
    Raised if a data event cannot be retrieved from a data source.
    """


class OmMissingDataSourceClassError(OmException):
    """
    Raised if a Data Source class cannot be found in the Data Retrieval Layer.

    """


class OmMissingDependencyError(OmException):
    """
    Raised if one of the python module dependencies is not found on the system.

    """


class OmMissingFrameDataError(OmException):
    """
    Raised if detector frame data cannot be retrieved from a data event.

    """


class OmMissingLayerModuleFileError(OmException):
    """
    Raised if the python implementation of an OM layer cannot be found on the system.

    """


class OmMissingParameterError(OmException):
    """
    Raised if a parameter is missing from OM'sconfiguration file.

    """


class OmMissingParameterGroupError(OmException):
    """
    Raised if a parameter group is missing from OM's configuration file.

    """


class OmWrongParameterTypeError(OmException):
    """
    Raised if the type of an OM's configuration parameter is not correct.
    """
