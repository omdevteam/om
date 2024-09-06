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
Data retrieval from files.

This module contains Data Retrieval classes that deal with files.
"""

import sys
from importlib import import_module
from types import ModuleType
from typing import Any, Dict, Optional, Type

from pydantic import BaseModel, Field

from om.lib.exceptions import OmMissingLayerClassError, OmMissingLayerModuleError
from om.lib.protocols import OmDataSourceProtocol


class _DataRetrievalParameters(BaseModel):
    data_source_type_override: Optional[str] = Field(default=None)


def _import_data_source_from_data_retrieval_layer(
    *,
    class_name: str,
) -> Type[OmDataSourceProtocol]:
    try:
        imported_layer: ModuleType = import_module("data_retrieval_layer")
    except ImportError:
        try:
            imported_layer = import_module("om.data_retrieval_layer")
        except ImportError as exc:
            exc_type, exc_value = sys.exc_info()[:2]
            # TODO: Fix types
            if exc_type is not None:
                raise OmMissingLayerModuleError(
                    f"The python module file data_retrieval_layer/__init__py cannot be "
                    "found or loaded due to the following error: "
                    f"{exc_type.__name__}: {exc_value}"
                ) from exc
    try:
        imported_class: Type[OmDataSourceProtocol] = getattr(imported_layer, class_name)
        return imported_class
    except AttributeError:
        raise OmMissingLayerClassError(
            "The Data Source class for the following type override cannot be found in "
            f"the Data Retrieval Layer: {class_name}"
        )


def data_source_overrides(
    *, parameters: Dict[str, Any], data_sources: Dict[str, Type[OmDataSourceProtocol]]
) -> Dict[str, Type[OmDataSourceProtocol]]:
    """ """

    data_source: str
    for data_source in data_sources:
        if data_source in parameters:
            data_source_parameters: _DataRetrievalParameters = (
                _DataRetrievalParameters.model_validate(parameters[data_source])
            )
            if data_source_parameters.data_source_type_override is not None:

                data_source_type: Type[OmDataSourceProtocol] = (
                    _import_data_source_from_data_retrieval_layer(
                        class_name=data_source_parameters.data_source_type_override,
                    )
                )
                data_sources[data_source] = data_source_type

    return data_sources
