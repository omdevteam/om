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
Rich console utilities.

This module contains classes and functions that OM uses to improve and augment its
terminal console output, using the Rich python library.
"""

from datetime import datetime
from typing import Dict

from rich.console import Console
from rich.theme import Theme
from rich.traceback import install

console = Console(force_terminal=True, force_interactive=False)
om_base_theme = Theme({"warning": "bold yellow", "error": "red"})
console.push_theme(om_base_theme)
install(show_locals=True, console=console)


def get_current_timestamp() -> str:
    """
    Gets the current timestamp formatted for console output.

    This function returns the current timestamp, with seconds precision, formatted in a
    style that is fit to be printed in the rich console.

    Returns:

        A string with the formatted timestamp.
    """
    return datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")


def set_null_theme() -> None:
    """
    Configures OM's rich console not to use colors.

    This function configures OM's rich console to use an null theme, effectively
    preventing it from using colors when displaying its output.
    """
    null_theme: Theme = Theme({"warning": "none", "error": "none"}, inherit=False)
    console.push_theme(null_theme, inherit=False)


def set_custom_theme(*, theme_dict: Dict[str, str]) -> None:
    """
    Sets a custom theme for OM's rich console.

    This function configures OM's rich console to use a custom theme. A dictionary
    passed to this function as an input parameter must stores the theme definition,
    using the syntax adopted by the python
    [Rich library][https://rich.readthedocs.io/en/stable/style.html].
    The custom theme is applied on top of OM's base rich console's theme: the console
    will fall back to the base theme for any entry not defined in the dictionary passed
    to this function.

    Arguments:

        theme_dict: A dictionary storing the custom theme definition, following the
            syntax defined by python Rich library.
    """
    custom_theme: Theme = Theme(theme_dict)
    console.push_theme(custom_theme)
