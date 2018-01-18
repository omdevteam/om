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
Utilities for parsing command line options and configuration files.

This module contains utilities for parsing of command line options and
configuration files.
"""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import ast


def _parsing_error(section, option):
    # Raise an exception after a parsing error.

    raise RuntimeError(
        'Error parsing parameter {0} in section [{1}]. Make sure that the '
        'syntax is correct: list elements must be separated by commas and '
        'dict entries must contain the colon symbol. Strings must be quoted, '
        'even in lists and dicts.'.format(
            option,
            section
        )
    )


def convert_parameters(config_dict):
    """Convert strings in parameter dictionaries to the corrent data type.

    Read a parameter dictionary returned by the ConfigParser python module,
    and assign correct types to the parameters, without changing the structure
    of the dictionary.

    Try to interpret each entry in the dictionary according to the following
    rules. The first rule that returns an valid result determines the type in
    which the entry will be converted.

    - If the entry starts and ends with a single quote or double quote, it is
      interpreted as a string.
    - If the entry starts and ends with a square bracket, it is interpreted as
      a list.
    - If the entry starts and ends with a brace, it is interpreted as a
      dictionary.
    - If the entry is the word None, without quotes, then the entry is
      interpreted as NoneType.
    - If the entry is the word False, without quotes, then the entry is
      interpreted as a boolean False.
    - If the entry is the word True, without quotes, then the entry is
      interpreted as a boolean True.
    - If none of the previous options match the content of the entry,
      the parser tries to interpret the entry in order as:

        - An integer number.
        - A float number.
        - A string.

    Args:

        config (dict): a dictionary containing the parameters as strings
            (the dictionary as returned by COnfig Parser).

    Returns:

        dict: dictionary with the same structure as the input
            dictionary, but with correct types assigned to each entry.
    """

    # Create the dictionary that will be returned.
    monitor_params = {}

    # Iterate over the first level of the configuration dictionary.
    for section in config_dict.keys():

        # Add the section to the dictionary that will be returned.
        monitor_params[section] = {}

        # Iterate over the content of each section (the second level in the
        # configuration dictonary).
        for option in config_dict['section'].keys():

            # Get the option from the dictionary (None is returned if the
            # dictionary does not contain the option).
            recovered_option = config_dict['section'].get(option)

            # Check if the option is a string delimited by single quotes.
            if (
                    recovered_option.startswith("'") and
                    recovered_option.endswith("'")
            ):
                monitor_params[section][option] = recovered_option[1:-1]
                continue

            # Check if the option is a string delimited by double quotes.
            if (
                    recovered_option.startswith('"') and
                    recovered_option.endswith('"')
            ):
                monitor_params[section][option] = recovered_option[1:-1]
                continue

            # Check if the option is a list. If it is, interpret it using the
            # literal_eval function.
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

            # Check if the option is a dictionary or a set. If it is,
            # interpret it using the literal_eval function.
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

            # Check if the option is the special string 'None' (without
            # quotes).
            if recovered_option == 'None':
                monitor_params[section][option] = None
                continue

            # Check if the option is the special string 'False' (without
            # quotes).
            if recovered_option == 'False':
                monitor_params[section][option] = False
                continue

            # Check if the option is the special string 'True' (without
            # quotes).
            if recovered_option == 'True':
                monitor_params[section][option] = True
                continue

            # Check if the option is an int by trying to convert it to an int.
            try:
                monitor_params[section][option] = int(recovered_option)
                continue
            except ValueError:
                # If the conversion to int falied, try to conver it to a float.
                try:
                    monitor_params[section][option] = float(
                        recovered_option
                    )
                    continue
                except ValueError:
                    # If the conversion to float also failed, return a parsing
                    # error.
                    _parsing_error(section, option)

    # Returned the converted dictionary.
    return monitor_params
