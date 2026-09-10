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
OM's Data Retrieval Layer.

This package contains OM's Data Retrieval Layer, which takes care of retrieving data
and data events to be processed. Modules in this package contain functions and classes
for specific detectors, facilities or software frameworks.
"""

from importlib.machinery import ModuleSpec
from importlib.util import find_spec

from .data_event_handlers_files import (
    EigerFilesDataEventHandler as EigerFilesDataEventHandler,
)
from .data_event_handlers_files import (
    Jungfrau1MFilesDataEventHandler as Jungfrau1MFilesDataEventHandler,
)
from .data_event_handlers_files import (
    Lambda1M5FilesDataEventHandler as Lambda1M5FilesDataEventHandler,
)
from .data_event_handlers_files import (
    RayonixMccdFilesEventHandler as RayonixMccdFilesEventHandler,
)
from .data_event_handlers_zmq import (
    Jungfrau1MZmqDataEventHandler as Jungfrau1MZmqDataEventHandler,
)

spec: ModuleSpec | None = find_spec("asapo_consumer")
if spec is not None:
    from .data_event_handlers_asapo import (
        AsapoDataEventHandler as AsapoDataEventHandler,
    )

spec = find_spec("fabio")
if spec is not None:
    from .data_event_handlers_files import (
        PilatusFilesEventHandler as PilatusFilesEventHandler,
    )

spec = find_spec("PIL")
if spec is not None:
    from .data_event_handlers_http import (
        EigerHttpDataEventHandler as EigerHttpDataEventHandler,
    )

spec = find_spec("psana")
if spec is not None:
    from .data_event_handlers_psana import (
        PsanaDataEventHandler as PsanaDataEventHandler,
    )

spec = find_spec("psana")
if spec is not None:
    from .data_event_handlers_psana2 import (
        Psana2DataEventHandler as Psana2DataEventHandler,
    )

spec = find_spec("_xtcpp")
if spec is not None:
    from .data_event_handlers_xtcpp import (
        XtcppDataEventHandler as XtcppDataEventHandler,
    )
