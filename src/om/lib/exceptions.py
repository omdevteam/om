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
# Copyright 2020 -2023 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
OM-specific exceptions and exception handling.

This module contains a set of python exceptions that are specific to OM.
"""


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


class OmHttpInterfaceInitializationError(OmException):
    """
    Raised if an error happens while OM is accessing an HTTP/REST interface.
    """


class OmGeometryError(OmException):
    """
    Raised if there is syntax error in a geometry file read by OM.
    """


class OmHdf5FileReadingError(OmException):
    """
    Raised if there is an error while reading an HDF5 data file.
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
    Raised if the format of the source string or file is not valid.
    """


class OmInvalidZmqUrl(OmException):
    """
    Raised if the format of a ZMQ socket's URL is not valid.
    """


class OmMissingLayerClassError(OmException):
    """
    Raised if a class that defines one of OM's layers cannot be found.
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


class OmMissingLayerModuleError(OmException):
    """
    Raised if the python implementation of one of OM's layer cannot be found.
    """


class OmMissingParameterError(OmException):
    """
    Raised if a parameter is missing from OM's configuration file.
    """


class OmMissingParameterGroupError(OmException):
    """
    Raised if a parameter group is missing from OM's configuration file.
    """


class OmWrongArrayShape(OmException):
    """
    Raised if the shape of an array does not fit the data it should contain.
    """


class OmWrongParameterTypeError(OmException):
    """
    Raised if the type of an OM's configuration parameter is not correct.
    """
