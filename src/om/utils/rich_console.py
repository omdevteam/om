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
Rich console utilities.

This module contains classes and functions that OM uses to improve and augment its
terminal console output, using the python Rich library.
"""

from datetime import datetime

from rich.console import Console

console = Console()


def get_current_timestamp() -> str:
    """
    Get the current timestamp formatted for console output.

    This function returns the current timestamp, with second precision, formatted in a
    style that is fit to be printed in the rich console.

    Returns:

        A string with the formatted timestamp.
    """
    return datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
