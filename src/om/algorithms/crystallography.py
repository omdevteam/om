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
Algorithms for the processing of crystallography data.

This module contains algorithms that perform data processing operations for Serial
Crystallography. Additionally, it contains the definitions of several typed
dictionaries that store data produced or required by these algorithms.
"""

from ._crystallography import Peakfinder8PeakDetection, TypePeakList  # noqa: F401

try:
    import peaknet  # noqa: F401
    import torch  # noqa: F401

    from ._crystallography_ml import PeakNetPeakDetection  # noqa: F401
except ModuleNotFoundError:
    pass
