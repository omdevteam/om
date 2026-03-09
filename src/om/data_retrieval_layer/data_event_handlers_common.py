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
""" """

from typing import Any

from om.lib.layer_management import import_data_source_class
from om.lib.logging import log_error_and_exit
from om.lib.parameters import DataSourceParameters
from om.lib.protocols import OmDataSourceProtocol


def instantiate_data_sources(
    data_sources: dict[str, DataSourceParameters],
    modules: list[str],
    additional_info: dict[str, Any],
) -> dict[str, OmDataSourceProtocol]:
    """ """
    if "timestamp" not in data_sources:
        log_error_and_exit(
            "Data source 'timestamp' (mandatory) is not defined in"
            "the configuration file"
        )
    instantiated_data_sources: dict[str, OmDataSourceProtocol] = {}
    data_source_name: str
    for data_source_name in data_sources:
        data_source_class: type[OmDataSourceProtocol] = import_data_source_class(
            module_names=modules,
            class_name=data_sources[data_source_name].type,
        )
        instantiated_data_sources[data_source_name] = data_source_class(
            data_source_name=data_source_name,
            parameters=data_sources[data_source_name],
            additional_info=additional_info,
        )
        instantiated_data_sources[data_source_name].initialize_data_source()

    return instantiated_data_sources
