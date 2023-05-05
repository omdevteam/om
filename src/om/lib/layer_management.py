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
#TODO: Write docstring.
"""
import importlib
import sys
from types import ModuleType
from typing import Dict, List, Type, Union

from om.lib.exceptions import (
    OmMissingDataSourceClassError,
    OmMissingLayerClassError,
    OmMissingLayerModuleFileError,
)
from om.protocols.data_retrieval_layer import (
    OmDataRetrievalProtocol,
    OmDataSourceProtocol,
)
from om.protocols.parallelization_layer import OmParallelizationProtocol
from om.protocols.processing_layer import OmProcessingProtocol


def import_class_from_layer(
    *, layer: str, class_name: str
) -> Union[
    Type[OmParallelizationProtocol],
    Type[OmProcessingProtocol],
    Type[OmDataRetrievalProtocol],
]:
    try:
        imported_layer: ModuleType = importlib.import_module(name=layer)
    except ImportError:
        try:
            imported_layer = importlib.import_module(f"om.{layer}")
        except ImportError as exc:
            exc_type, exc_value = sys.exc_info()[:2]
            # TODO: Fix types
            if exc_type is not None:
                raise OmMissingLayerModuleFileError(
                    f"The python module file {layer}.py cannot be found or loaded due "
                    f"to the following error: {exc_type.__name__}: {exc_value}"
                ) from exc
    try:
        imported_class: Union[
            Type[OmParallelizationProtocol],
            Type[OmProcessingProtocol],
            Type[OmDataRetrievalProtocol],
        ] = getattr(imported_layer, class_name)
    except AttributeError:
        raise OmMissingLayerClassError(
            f"The {class_name} class cannot be found in the {layer} file."
        )

    return imported_class


def filter_data_sources(
    *,
    data_sources: Dict[str, OmDataSourceProtocol],
    required_data: List[str],
) -> List[str]:
    """
    Selects only the required Data Sources.

    This function filters the list of all Data Sources associated with a
    Data Retrieval class, returning only the subset of Data Sources needed to retrieve
    the data requested by the user.

    Arguments:

        data_sources: A list containing the names of all
            Data Sources available for a Data Retrieval class.

        required_data: A list containing the names of the data items requested by the
            user.

    Returns:

        A list of Data Source names containing only the required Data Sources.
    """
    required_data_sources: List[str] = []
    entry: str
    for entry in required_data:
        if entry == "timestamp":
            continue
        if entry in data_sources:
            required_data_sources.append(entry)
        else:
            raise OmMissingDataSourceClassError(f"Data source {entry} is not defined")
    return required_data_sources
