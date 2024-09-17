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
"""

from typing import Any, Dict, List, Type

from om.lib.exceptions import OmMissingDataSourceClassError
from om.lib.protocols import OmDataSourceProtocol


def filter_data_sources(
    *,
    data_sources: Dict[str, Type[OmDataSourceProtocol]],
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


def instantiate_data_sources(
    data_sources: Dict[str, Type[OmDataSourceProtocol]],
    data_retrieval_parameters: Dict[str, Any],
    required_data_sources: List[str],
) -> Dict[str, OmDataSourceProtocol]:
    """ """

    instantiated_data_sources: Dict[str, OmDataSourceProtocol] = {
        "timestamp": data_sources["timestamp"](
            data_source_name="timestamp", parameters=data_retrieval_parameters
        )
    }
    instantiated_data_sources["timestamp"].initialize_data_source()

    source_name: str
    for source_name in required_data_sources:
        instantiated_data_sources[source_name] = data_sources[source_name](
            data_source_name=source_name, parameters=data_retrieval_parameters
        )
        instantiated_data_sources[source_name].initialize_data_source()

    return instantiated_data_sources
