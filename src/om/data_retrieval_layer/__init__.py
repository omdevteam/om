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

try:
    import asapo_consumer  # type: ignore  # noqa: F401

    from .data_event_handlers_asapo import AsapoDataEventHandler  # noqa: F401
except ModuleNotFoundError:
    ...

try:
    import fabio  # type: ignore  # noqa: F401

    from .data_event_handlers_files import PilatusFilesEventHandler  # noqa: F401
except ModuleNotFoundError:
    pass

try:
    import PIL  # type: ignore  # noqa: F401

    from .data_event_handlers_http import EigerHttpDataEventHandler  # noqa: F401
except ModuleNotFoundError:
    pass

try:
    import psana  # type: ignore  # noqa: F401

    from .data_event_handlers_psana import PsanaDataEventHandler  # noqa: F401
except ModuleNotFoundError:
    pass


try:
    import psana  # type: ignore  # noqa: F401

    from .data_event_handlers_psana2 import Psana2DataEventHandler  # noqa: F401
except ModuleNotFoundError:
    pass

from .data_event_handlers_files import (
    EigerFilesDataEventHandler,  # noqa: F401
    Jungfrau1MFilesDataEventHandler,  # noqa: F401
    Lambda1M5FilesDataEventHandler,  # noqa: F401
    RayonixMccdFilesEventHandler,  # noqa: F401
)

from .data_event_handlers_zmq import Jungfrau1MZmqDataEventHandler  # noqa: F401
