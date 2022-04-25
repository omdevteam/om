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
Console utilities.

This module contains classes and functions that OM uses to improve and augment its
terminal console output.
"""

from datetime import datetime
from typing import Any, Callable, Dict, Union

from rich import console, theme

from om.utils import parameters


def get_om_print(
    monitor_parameters: parameters.MonitorParams,
) -> Union[Callable[..., None], None]:
    """
    Get OM's output console.

    This function normally prepares and activates OM's rich terminal console (based
    on based on Python's [`rich`](https://github.com/Textualize/rich) library). It
    returns a function that behaves like Python's built-in print function, but output
    nicely formatted print to the rich console. If the `om_rich_console` parameter in
    OM's `om` configuration parameter group is set to false, OM's rich console is
    disabled and this function returns None.

    OM's rich console theme can be modified via OM's `om_rich_console_theme`
    configuration parameter in the `om` group.

    Arguments:

        monitor_parameters: An object storing OM's configuration parameters.

    Returns:

        A function printing to OM's .
    """

    om_rich_console: Union[bool, None] = monitor_parameters.get_parameter(
        group="om",
        parameter="om_rich_console",
        parameter_type=bool,
    )

    if om_rich_console is False:
        return None

    theme_from_configuration: Union[
        Dict[str, str], None
    ] = monitor_parameters.get_parameter(
        group="om",
        parameter="om_rich_console_theme",
        parameter_type=dict,
    )

    if theme_from_configuration is None:
        console_theme: theme.Theme = theme.Theme(
            {
                "info": "dim cyan",
                "warning": "magenta",
            }
        )
    else:
        console_theme = theme.Theme(theme_from_configuration)

    rich_console: console.Console = console.Console(theme=console_theme)

    def om_print(*args: Any, **kwargs: Any) -> None:

        rich_console.print(
            datetime.now().strftime("[%d-%m-%Y %H:%M:%S]"), *args, **kwargs
        )

    return om_print
