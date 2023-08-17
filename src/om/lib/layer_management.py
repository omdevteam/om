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
OM's layer management.

This module contains classes and functions that mange OM's various data processing and
extraction layers.
"""
import importlib
import sys
from types import ModuleType
from typing import Dict, List, Type, Union

from om.lib.exceptions import (
    OmMissingDataSourceClassError,
    OmMissingLayerClassError,
    OmMissingLayerModuleError,
)
from om.protocols.data_retrieval_layer import (
    OmDataRetrievalProtocol,
    OmDataSourceProtocol,
)
from om.protocols.parallelization_layer import OmParallelizationProtocol
from om.protocols.processing_layer import OmProcessingProtocol


def import_class_from_layer(
    *, layer_name: str, class_name: str
) -> Union[
    Type[OmParallelizationProtocol],
    Type[OmProcessingProtocol],
    Type[OmDataRetrievalProtocol],
    None,
]:
    """
    Imports a class from an OM's layer.

    This function imports a class, identified by the `class_name` argument, from a
    layer identified by the `layer_name` argument. The function looks for the python
    module containing the layer code in the current directory first. Specifically, it
    looks for a python file with the same name as the layer. If the function cannot
    fine the file in the current directory, it imports the layer from the OM's normal
    installation directories. It then proceeds to import the requested class from the
    layer module.

    Arguments:

        layer_name: The name of the layer from which the class should be imported.

        class_name: The name of the class to import.

    Returns:

        The imported class.

    Raises:

        OmMissingLayerClass: Raised when the requested class cannot be found in the
            specified Python module.

        OmMissingLayerModuleFile: Raised when the requested python module cannot be
            found.
    """

    try:
        imported_layer: ModuleType = importlib.import_module(name=layer_name)
    except ImportError:
        try:
            imported_layer = importlib.import_module(f"om.{layer_name}")
            try:
                imported_class: Union[
                    Type[OmParallelizationProtocol],
                    Type[OmProcessingProtocol],
                    Type[OmDataRetrievalProtocol],
                ] = getattr(imported_layer, class_name)
                return imported_class
            except AttributeError:
                raise OmMissingLayerClassError(
                    f"The {class_name} class cannot be found in the {layer_name} file."
                )
        except ImportError as exc:
            exc_type, exc_value = sys.exc_info()[:2]
            # TODO: Fix types
            if exc_type is not None:
                raise OmMissingLayerModuleError(
                    f"The python module file {layer_name}.py cannot be found or loaded"
                    f"due to the following error: "
                    f"{exc_type.__name__}: {exc_value}"
                ) from exc
    return None


def filter_data_sources(
    *,
    data_sources: Dict[str, OmDataSourceProtocol],
    required_data: List[str],
) -> List[str]:
    """
    Filters a list Data Sources.

    This function filters the list of all Data Sources associated with a
    Data Retrieval class, returning only the subset of Data Sources needed to retrieve
    the data requested by the user.

    Arguments:

        data_sources: A list containing the names of all Data Sources available for a
            Data Retrieval class.

        required_data: A list containing the names of the data items requested by the
            user.

    Returns:

        A list of Data Source names containing only the needed Data Sources.

    Raises:

        OmMissingDataSourceClassError: Raised when one of the required Data Source
            class cannot be found in the list of Data Source available for the Data
            Retrieval.
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
