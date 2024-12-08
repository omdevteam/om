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

import logging
from typing import Any, Optional

from rich.logging import RichHandler


class RichHandlerWithAggregation(RichHandler):
    def __init__(
        self, *, recurring_msg_emit_interval: int = 100, **kwargs: Any
    ) -> None:
        super().__init__(**kwargs)
        self._recurring_msg_emit_interval = recurring_msg_emit_interval
        self._recurring_msg: str = ""
        self._last_recurring_record: Optional[logging.LogRecord] = None
        self._recurring_msg_counter: int = 0

    def format(self, record: logging.LogRecord) -> str:
        if self._recurring_msg_counter != 0:
            record.msg = f"{record.msg} (Repeated {self._recurring_msg_counter} times)"
        return super().format(record)

    def emit(self, record: logging.LogRecord) -> None:
        if record.msg != self._recurring_msg:
            if self._recurring_msg_counter != 0 and self._last_recurring_record is not None:
                super().emit(self._last_recurring_record)
            self._last_recurring_record = record
            self._recurring_msg = record.msg
            self._recurring_msg_counter = 0
            super().emit(record)
        else:
            self._recurring_msg_counter += 1
            self._last_recurring_record = record
            if self._recurring_msg_counter % self._recurring_msg_emit_interval == 0:
                super().emit(self._last_recurring_record)


logging.basicConfig(
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandlerWithAggregation(rich_tracebacks=True, show_path=False)],
)


logging.getLogger("rich").setLevel(logging.INFO)
log = logging.getLogger("rich")
