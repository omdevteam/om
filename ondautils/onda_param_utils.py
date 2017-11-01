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


from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from builtins import str

from ondautils.onda_exception_utils import (MissingParameter,
                                            MissingParameterFileSection,
                                            WrongParameterType)


monitor_params = {}


def param(section, par, type_to_check=None, required=False):
    if section not in monitor_params:
        raise MissingParameterFileSection('Section {0} is not in the configuration file'.format(section))
    else:
        ret = monitor_params[section].get(par)
        if ret is None and required is True:
            raise MissingParameter('Parameter {0} in section [{1}] was not found, but is required.'.format(
                par, section))
        if ret is not None and type_to_check is not None:
            if not isinstance(ret, type_to_check):
                raise WrongParameterType('Wrong type for parameter {0}: should be {1}, is {2}.'.format(
                    par, str(type_to_check).split()[1][1:-2], str(type(ret)).split()[1][1:-2]))
            else:
                return ret
        else:
            return ret
