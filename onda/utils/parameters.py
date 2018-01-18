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


def get_param(section, parameter, type_=None, required=False):

    # Check if the requested section exists in the parameter file
    if section not in monitor_params:
        raise MissingParameterFileSection(
            'Section {0} is not in the configuration file'.format(section)
        )
    else:

        # If the section exists, try to recover the parameter
        # If the parameter does not exist, None is recovered.
        ret = monitor_params[section].get(parameter)

        # If the parameter is not found, (or it is None), but it is required,
        # raise and exception
        if ret is None and required is True:
            raise MissingParameter(
                'Parameter {0} in section [{1}] was not found, but is '
                'required.'.format(parameter, section)
            )

        # If the parameter is found (and it is not None) and a type check is
        # required, perform the type check. The return the parameter value
        if ret is not None and type_ is not None:
            if not isinstance(ret, type_):
                raise WrongParameterType(
                    'Wrong type for parameter {0}: should be {1}, '
                    'is {2}.'.format(
                        parameter,
                        str(type_).split()[1][1:-2],
                        str(type(ret)).split()[1][1:-2]
                    )
                )
            else:
                return ret
        else:
            return ret
