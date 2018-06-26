#    This file is part of cfelpyutils.
#
#    cfelpyutils is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    cfelpyutils is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with cfelpyutils.  If not, see <http://www.gnu.org/licenses/>.
"""
Parameter parsing utilities.

This module contains the implementation of several utilities used
to parse and manipulate dictionaries that store options and parameters.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import ast


def _parsing_error(section, option):
    # Raise an exception after a parsing error.
    raise RuntimeError(
        "Error parsing parameter {0} in section [{1}]. Make sure that the "
        "syntax is correct: list elements must be separated by commas and "
        "dict entries must contain the colon symbol. Strings must be quoted, "
        "even in lists and dicts.".format(option, section)
    )


def convert_parameters(config_dict):
    """
    Convert strings in parameter dictionaries to the correct data type.

    Convert a dictionary return by the configparse module to a
    dictionar contaning the same parameters converted from string to
    their correct type (int, float, string, etc.)

    Try to convert each entry in the dictionary according to the
    following rules. The first rule that applies to the entry
    determines the type.

    - If the entry starts and ends with a single quote or double quote,
      leave it as a string.
    - If the entry starts and ends with a square bracket, convert it to
      a list.
    - If the entry starts and ends with a curly braces, convert it to a
      dictionary or a set.
    - If the entry is the word None, without quotes, convert it to
      NoneType.
    - If the entry is the word False, without quotes, convert it to a
      boolean False.
    - If the entry is the word True, without quotes, convert it to a
      boolean True.
    - If none of the previous options match the content of the entry,
      try to interpret the entry in order as:

        - An integer number.
        - A float number.
        - A string.

    - If all else fails, raise an exception.

    Args:

        config (Dict): a dictionary containing strings (the dictionary
            returned by Config Parser).

    Returns:

        Dict: dictionary with the same structure as the input
        dictionary, but with correct types assigned to each entry.

    Raises:

        RuntimeError: if an entry cannot be converted to any supported
        type.
    """

    monitor_params = {}

    for section in config_dict.keys():
        monitor_params[section] = {}
        for option in config_dict[section].keys():
            recovered_option = config_dict[section][option]
            if (
                    recovered_option.startswith("'") and
                    recovered_option.endswith("'")
            ):
                monitor_params[section][option] = recovered_option[1:-1]
                continue

            if (
                    recovered_option.startswith('"') and
                    recovered_option.endswith('"')
            ):
                monitor_params[section][option] = recovered_option[1:-1]
                continue

            if (
                    recovered_option.startswith("[") and
                    recovered_option.endswith("]")
            ):
                try:
                    monitor_params[section][option] = ast.literal_eval(
                        recovered_option
                    )
                    continue
                except (SyntaxError, ValueError):
                    _parsing_error(section, option)

            if (
                    recovered_option.startswith("{") and
                    recovered_option.endswith("}")
            ):
                try:
                    monitor_params[section][option] = ast.literal_eval(
                        recovered_option
                    )
                    continue
                except (SyntaxError, ValueError):
                    _parsing_error(section, option)

            if recovered_option == 'None':
                monitor_params[section][option] = None
                continue

            if recovered_option == 'False':
                monitor_params[section][option] = False
                continue

            if recovered_option == 'True':
                monitor_params[section][option] = True
                continue

            try:
                monitor_params[section][option] = int(recovered_option)
                continue
            except ValueError:
                try:
                    monitor_params[section][option] = float(
                        recovered_option
                    )
                    continue
                except ValueError:
                    _parsing_error(section, option)

    return monitor_params
