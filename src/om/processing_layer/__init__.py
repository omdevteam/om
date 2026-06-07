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
OM's Processing Layer.

This package contains OM's Processing Layer, which defines the scientific data analysis
logic for all OnDA Monitors. Each module in the package stores the implementation of a
different OnDA Monitor.
"""

from .cheetah import (
    CheetahProcessing,
    StreamingCheetahProcessing,
    CheetahNoProcessing,
)  # noqa: F401
from .crystallography import CrystallographyProcessing  # noqa: F401

try:
    from .cbc import CbCrystallographyProcessing, CbCheetahProcessing  # noqa: F401
except Exception:
    # cbclib_v2 is only available in the psana2mfx101210926 environment.
    # In all other environments this import is silently skipped and the class
    # will not be available.
    pass
from .swaxs import SwaxsCheetahProcessing, SwaxsProcessing  # noqa: F401
from .testing import TestProcessing  # noqa: F401
from .xes import XesProcessing  # noqa: F401
