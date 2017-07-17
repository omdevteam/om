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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from mpi4py import MPI
from traceback import print_exception
import sys


class OndaException(Exception):
    pass


class DynamicImportError(OndaException):
    pass


class HidraAPIError(OndaException):
    pass


class ParameterInputError(OndaException):
    pass


class MLLLogFleParsingError(OndaException):
    pass


class MissingDataExtractionFunction(OndaException):
    pass


class MissingFile(OndaException):
    pass


class MissingParameterFileSection(OndaException):
    pass


class MissingParameter(OndaException):
    pass


class WrongParameterType(OndaException):
    pass


class DataExtractionError(OndaException):
    pass


def onda_exception_handler(type_, value, traceback):
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
