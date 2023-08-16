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
from typing import Dict

from om.data_retrieval_layer.data_event_handlers_files import (
    EigerFilesDataEventHandler,
    Jungfrau1MFilesDataEventHandler,
    Lambda1M5FilesDataEventHandler,
    PilatusFilesEventHandler,
    RayonixMccdFilesEventHandler,
)
from om.data_retrieval_layer.data_sources_files import (
    Eiger16MFiles,
    EventIdEiger16MFiles,
    EventIdFromFilePath,
    EventIdJungfrau1MFiles,
    EventIdLambda1M5Files,
    Jungfrau1MFiles,
    Lambda1M5Files,
    PilatusSingleFrameFiles,
    RayonixMccdSingleFrameFiles,
    TimestampFromFileModificationTime,
    TimestampJungfrau1MFiles,
)
from om.data_retrieval_layer.data_sources_generic import FloatEntryFromConfiguration
from om.lib.parameters import MonitorParameters
from om.protocols.data_retrieval_layer import (
    OmDataEventHandlerProtocol,
    OmDataRetrievalProtocol,
    OmDataSourceProtocol,
)


class PilatusFilesDataRetrieval(OmDataRetrievalProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(self, *, monitor_parameters: MonitorParameters, source: str):
        """
        Data retrieval for Pilatus' single-frame CBF files.

        This class implements OM's Data Retrieval Layer for a set of single-frame files
        written by a Pilatus detector in CBF format.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        * This class considers an individual data event as corresponding to the content
          of a single Pilatus CBF file.

        * The full path to the CBF file is used as event identifier.

        * Since Pilatus files do not contain any timestamp information, the
          modification time of the each file is taken as a first approximation of the
          timestamp of the data it contains.

        * Since Pilatus files do not contain any detector distance or beam energy
          information, their values are retrieved from OM's configuration parameters
          (specifically, the `fallback_detector_distance_in_mm` and
          `fallback_beam_energy_in_eV` entries in the `data_retrieval_layer`
          parameter group).

        * The source string required by this Data Retrieval class is the path to a file
          containing a list of CBF files to process, one per line, with their absolute
          or relative path.

        Arguments:

            monitor_parameters: An object storing OM's configuration parameters.

            source: A string describing the data event source.
        """
        data_sources: Dict[str, OmDataSourceProtocol] = {
            "timestamp": TimestampFromFileModificationTime(
                data_source_name="timestamp", monitor_parameters=monitor_parameters
            ),
            "event_id": EventIdFromFilePath(
                data_source_name="eventid", monitor_parameters=monitor_parameters
            ),
            "detector_data": PilatusSingleFrameFiles(
                data_source_name="detector", monitor_parameters=monitor_parameters
            ),
            "beam_energy": FloatEntryFromConfiguration(
                data_source_name="fallback_beam_energy_in_eV",
                monitor_parameters=monitor_parameters,
            ),
            "detector_distance": FloatEntryFromConfiguration(
                data_source_name="fallback_detector_distance_in_mm",
                monitor_parameters=monitor_parameters,
            ),
        }

        self._data_event_handler: OmDataEventHandlerProtocol = PilatusFilesEventHandler(
            source=source,
            monitor_parameters=monitor_parameters,
            data_sources=data_sources,
        )

    def get_data_event_handler(self) -> OmDataEventHandlerProtocol:
        """
        Retrieves the Data Event Handler used by the Data Retrieval class.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Returns:

            The Data Event Handler used by the Data Retrieval class.
        """
        return self._data_event_handler


class Jungfrau1MFilesDataRetrieval(OmDataRetrievalProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(self, *, monitor_parameters: MonitorParameters, source: str):
        """
        Data Retrieval for Jungfrau 1M's HDF5 files.

        This class implements OM's Data Retrieval Layer for a set of files written by
        a Jungfrau 1M detector in HDF5 format.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        * This class considers an individual data event as equivalent to a single
          detector frame stored in an HDF5 file, with all its attached information.

        * The full path to the file containing the frame and the index of the frame in
          the file, combined into a single string and separated by the '//' symbol, are
          used as event identifier.

        * Jungfrau 1M files do not contain any absolute timestamp information, but they
          store the readout of the internal detector clock for every frame. As a first
          approximation, the modification time of each file is taken as the timestamp
          of the first frame it contains, and the timestamp of all other frames is
          computed according to the internal clock difference.

        * Since Jungfrau 1M files do not contain any detector distance or beam energy
          information, their values are retrieved from OM's configuration parameters
          (specifically, the `fallback_detector_distance_in_mm` and
          `fallback_beam_energy_in_eV` entries in the `data_retrieval_layer`
          parameter group).

        * The source string required by this Data Retrieval class is the path to a file
          containing a list of master HDF5 files to process, one per line, with their
          absolute or relative path.

        Arguments:

            monitor_parameters: An object storing OM's configuration parameters.

            source: A string describing the data event source.
        """

        data_sources: Dict[str, OmDataSourceProtocol] = {
            "timestamp": TimestampJungfrau1MFiles(
                data_source_name="timestamp", monitor_parameters=monitor_parameters
            ),
            "event_id": EventIdJungfrau1MFiles(
                data_source_name="eventid", monitor_parameters=monitor_parameters
            ),
            "detector_data": Jungfrau1MFiles(
                data_source_name="detector", monitor_parameters=monitor_parameters
            ),
            "beam_energy": FloatEntryFromConfiguration(
                data_source_name="fallback_beam_energy_in_eV",
                monitor_parameters=monitor_parameters,
            ),
            "detector_distance": FloatEntryFromConfiguration(
                data_source_name="fallback_detector_distance_in_mm",
                monitor_parameters=monitor_parameters,
            ),
        }

        self._data_event_handler: OmDataEventHandlerProtocol = (
            Jungfrau1MFilesDataEventHandler(
                source=source,
                monitor_parameters=monitor_parameters,
                data_sources=data_sources,
            )
        )

    def get_data_event_handler(self) -> OmDataEventHandlerProtocol:
        """
        Retrieves the Data Event Handler used by the Data Retrieval class.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Returns:

            The Data Event Handler used by the Data Retrieval class.
        """
        return self._data_event_handler


class EigerFilesDataRetrieval(OmDataRetrievalProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(self, *, monitor_parameters: MonitorParameters, source: str):
        """
        Data Retrieval for Eiger's HDF5 files.

        This class implements OM's Data Retrieval Layer for a set of files written by
        an Eiger detector in HDF5 format.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        * This class considers an individual data event as corresponding to a single
          detector frame stored in an HDF5 file.

        * The full path to the file containing the frame and the index of the frame in
          the file, combined into a single string and separated by the '//' symbol, are
          used as event identifier.

        * Since Eiger's files do not contain any absolute timestamp information, the
          modification time of a file is taken as a first approximation of the
          timestamp of the data it contains.

        * Since Eiger's files do not contain any detector distance or beam energy
          information, their values are retrieved from OM's configuration parameters
          (specifically, the `fallback_detector_distance_in_mm` and
          `fallback_beam_energy_in_eV` entries in the `data_retrieval_layer`
          parameter group).

        * The source string required by this Data Retrieval class is the path to a file
          containing a list of HDF5 files to process, one per line, with their absolute
          or relative path.

        Arguments:

            monitor_parameters: An object storing OM's configuration parameters.

            source: A string describing the data event source.
        """
        data_sources: Dict[str, OmDataSourceProtocol] = {
            "timestamp": TimestampFromFileModificationTime(
                data_source_name="timestamp", monitor_parameters=monitor_parameters
            ),
            "event_id": EventIdEiger16MFiles(
                data_source_name="eventid", monitor_parameters=monitor_parameters
            ),
            "detector_data": Eiger16MFiles(
                data_source_name="detector", monitor_parameters=monitor_parameters
            ),
            "beam_energy": FloatEntryFromConfiguration(
                data_source_name="fallback_beam_energy_in_eV",
                monitor_parameters=monitor_parameters,
            ),
            "detector_distance": FloatEntryFromConfiguration(
                data_source_name="fallback_detector_distance_in_mm",
                monitor_parameters=monitor_parameters,
            ),
        }

        self._data_event_handler: OmDataEventHandlerProtocol = (
            EigerFilesDataEventHandler(
                source=source,
                monitor_parameters=monitor_parameters,
                data_sources=data_sources,
            )
        )

    def get_data_event_handler(self) -> OmDataEventHandlerProtocol:
        """
        Retrieves the Data Event Handler used by the Data Retrieval class.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Returns:

            The Data Event Handler used by the Data Retrieval class.
        """
        return self._data_event_handler


class RayonixMccdFilesDataRetrieval(OmDataRetrievalProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(self, *, monitor_parameters: MonitorParameters, source: str):
        """
        Data Retrieval for Rayonix MX340-HS's single-frame mccd files.

        This class implements OM's Data Retrieval Layer for a set of single-frame files
        written by a Rayonix detector in mccd format.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        * This class considers an individual data event as corresponding to the content
          of a single Rayonix mccd file.

        * The full path to the mccd file is used as event identifier.

        * Since Rayonix mccd files do not contain any timestamp information, the
          modification time of each file is taken as a first approximation of the
          timestamp of the data it contains.

        * Since Rayonix mccd files do not contain any detector distance or beam energy
          information, their values are retrieved from OM's configuration parameters
          (specifically, the `fallback_detector_distance_in_mm` and
          `fallback_beam_energy_in_eV` entries in the `data_retrieval_layer`
          parameter group).

        * The source string required by this Data Retrieval class is the path to a file
          containing a list of mccd files to process, one per line, with their absolute
          or relative path.

        Arguments:

            monitor_parameters: An object storing OM's configuration parameters.

            source: A string describing the data event source.
        """
        data_sources: Dict[str, OmDataSourceProtocol] = {
            "timestamp": TimestampFromFileModificationTime(
                data_source_name="timestamp", monitor_parameters=monitor_parameters
            ),
            "event_id": EventIdFromFilePath(
                data_source_name="eventid", monitor_parameters=monitor_parameters
            ),
            "detector_data": RayonixMccdSingleFrameFiles(
                data_source_name="detector", monitor_parameters=monitor_parameters
            ),
            "beam_energy": FloatEntryFromConfiguration(
                data_source_name="fallback_beam_energy_in_eV",
                monitor_parameters=monitor_parameters,
            ),
            "detector_distance": FloatEntryFromConfiguration(
                data_source_name="fallback_detector_distance_in_mm",
                monitor_parameters=monitor_parameters,
            ),
        }

        self._data_event_handler: OmDataEventHandlerProtocol = (
            RayonixMccdFilesEventHandler(
                source=source,
                monitor_parameters=monitor_parameters,
                data_sources=data_sources,
            )
        )

    def get_data_event_handler(self) -> OmDataEventHandlerProtocol:
        """
        Retrieves the Data Event Handler used by the Data Retrieval class.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Returns:

            The Data Event Handler used by the Data Retrieval class.
        """
        return self._data_event_handler


class Lambda1M5FilesDataRetrieval(OmDataRetrievalProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(self, *, monitor_parameters: MonitorParameters, source: str):
        """
        Data Retrieval for Lambda 1.5M's HDF5 files.

        This class implements OM's Data Retrieval Layer for a set of files written by
        a Lambda 1.5M detector in HDF5 format.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        * This class considers an individual data event as equivalent to an single
          detector frame, stored in two separate HDF5 files written by two detector
          modules, together with its attached information.

        * The full path to the file written by the first detector module ("*_m01.nxs"),
          and the index of the frame in the file, combined into a single string and
          separated by '//' symbol, are used as event identifier.

        * Since Lambda 1.5M files do not contain any timestamp information, the
          modification time of each file is taken as a first approximation of the
          timestamp of the data it contains.

        * Since Lambda 1.5M files do not contain any detector distance or beam energy
          information, their values are retrieved from OM's configuration parameters
          (specifically, the `fallback_detector_distance_in_mm` and
          `fallback_beam_energy_in_eV` entries in the `data_retrieval_layer`
          parameter group).

        * The source string required by this Data Retrieval class is the path to a file
          containing a list of HDF5 files written by the first detector module
          ("*_m01*.nxs"), one per line, with their absolute or relative path. Each file
          can store more than one detector data frame, and each frame in the file is
          processed as a separate event.

        Arguments:

            monitor_parameters: An object storing OM's configuration parameters.

            source: A string describing the data event source.
        """

        data_sources: Dict[str, OmDataSourceProtocol] = {
            "timestamp": TimestampFromFileModificationTime(
                data_source_name="timestamp", monitor_parameters=monitor_parameters
            ),
            "event_id": EventIdLambda1M5Files(
                data_source_name="eventid", monitor_parameters=monitor_parameters
            ),
            "detector_data": Lambda1M5Files(
                data_source_name="detector", monitor_parameters=monitor_parameters
            ),
            "beam_energy": FloatEntryFromConfiguration(
                data_source_name="fallback_beam_energy_in_eV",
                monitor_parameters=monitor_parameters,
            ),
            "detector_distance": FloatEntryFromConfiguration(
                data_source_name="fallback_detector_distance_in_mm",
                monitor_parameters=monitor_parameters,
            ),
        }

        self._data_event_handler: OmDataEventHandlerProtocol = (
            Lambda1M5FilesDataEventHandler(
                source=source,
                monitor_parameters=monitor_parameters,
                data_sources=data_sources,
            )
        )

    def get_data_event_handler(self) -> OmDataEventHandlerProtocol:
        """
        Retrieves the Data Event Handler used by the Data Retrieval class.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Returns:

            The Data Event Handler used by the Data Retrieval class.
        """
        return self._data_event_handler
