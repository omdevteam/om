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
Handling of file-based data events.

This module contains Data Event Handler classes that manipulate file-based events.
"""
import pathlib
import re
import sys
from datetime import datetime
from typing import Any, Dict, Generator, List, TextIO, Tuple, TypedDict

import h5py  # type: ignore
import numpy
from numpy.typing import NDArray

from om.lib.exceptions import (
    OmDataExtractionError,
    OmInvalidSourceError,
    OmMissingDependencyError,
)
from om.lib.layer_management import filter_data_sources
from om.lib.parameters import MonitorParameters
from om.protocols.data_retrieval_layer import (
    OmDataEventHandlerProtocol,
    OmDataSourceProtocol,
)

try:
    import fabio  # type: ignore
except ImportError:
    raise OmMissingDependencyError(
        "The following required module cannot be imported: fabio"
    )


class _TypeJungfrau1MFrameInfo(TypedDict):
    # This typed dictionary is used internally to store additional information
    # required to retrieve Jungfrau 1M frame data.
    h5file: Any
    index: int
    file_timestamp: float


class PilatusFilesEventHandler(OmDataEventHandlerProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        source: str,
        data_sources: Dict[str, OmDataSourceProtocol],
        monitor_parameters: MonitorParameters,
    ) -> None:
        """
        Data Event Handler for Pilatus single-frame files.

        This class handles data events originating from single-frame CBF files written
        by a Pilatus detector.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        * For this Event Handler, a data event corresponds to the content of an
          individual single-frame CBF file.

        * The source string required by this Data Event Handler is the path to a file
          containing a list of CBF files to process, one per line, with their
          absolute or relative path.

        Arguments:

            source: A string describing the data event source.

            data_sources: A dictionary containing a set of Data Source class instances.

                * Each dictionary key must define the name of a data source.

                * The corresponding dictionary value must store the instance of the
                  [Data Source class][om.protocols.data_retrieval_layer.OmDataSourceProtocol]  # noqa: E501
                  that describes the source.

            monitor_parameters: An object storing OM's configuration parameters.
        """
        self._source: str = source
        self._monitor_params: MonitorParameters = monitor_parameters
        self._data_sources: Dict[str, OmDataSourceProtocol] = data_sources

    def initialize_event_handling_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes Pilatus single-frame file event handling on the collecting node.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        There is usually no need to initialize Pilatus file-based event handling on the
        collecting node, so this function actually does nothing.

        Arguments:

            node_rank: The OM rank of the current node int the OM node pool. The rank
                is an integer that unambiguously identifies the node in the pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        pass

    def initialize_event_handling_on_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes Pilatus single-frame file event handling on the processing nodes.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node int the OM node pool. The rank
                is an integer that unambiguously identifies the node in the pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        required_data: List[str] = self._monitor_params.get_parameter(
            group="data_retrieval_layer",
            parameter="required_data",
            parameter_type=list,
            required=True,
        )

        self._required_data_sources = filter_data_sources(
            data_sources=self._data_sources,
            required_data=required_data,
        )

    def event_generator(
        self,
        *,
        node_rank: int,
        node_pool_size: int,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Retrieves Pilatus single-frame file events.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves data events on the processing nodes. Each retrieved
        event corresponds to the content of an individual single-frame CBF file. The
        function tries to distribute the events as evenly as possible across all the
        processing nodes, with each node ideally processing the same number of events.
        If the total number of events cannot be split evenly, the last last node will
        process fewer events than the others.

        Arguments:

            node_rank: The OM rank of the current node int the OM node pool. The rank
                is an integer that unambiguously identifies the node in the pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        # Computes how many files the current processing node should process. Splits
        # the files as equally as possible amongst the processing nodes with the last
        # processing node getting a smaller number of files if the number of files to
        # be processed cannot be exactly divided by the number of processing nodes.
        try:
            file_handle: TextIO
            with open(self._source, "r") as file_handle:
                filelist: List[str] = file_handle.readlines()
        except (IOError, OSError) as exc:
            raise OmInvalidSourceError(
                f"Error reading the {self._source} source file."
            ) from exc
        num_files_curr_node: int = int(
            numpy.ceil(len(filelist) / float(node_pool_size - 1))
        )
        files_curr_node: List[str] = filelist[
            ((node_rank - 1) * num_files_curr_node) : (node_rank * num_files_curr_node)
        ]

        self._data_sources["timestamp"].initialize_data_source()
        source_name: str
        for source_name in self._required_data_sources:
            self._data_sources[source_name].initialize_data_source()

        data_event: Dict[str, Any] = {}
        data_event["additional_info"] = {}

        entry: str
        for entry in files_curr_node:
            stripped_entry: str = entry.strip()
            data_event["additional_info"]["full_path"] = stripped_entry

            # File modification time is used as a first approximation of the timestamp
            # when the timestamp is not available.
            data_event["additional_info"]["file_modification_time"] = numpy.float64(
                pathlib.Path(stripped_entry).stat().st_mtime
            )

            data_event["additional_info"]["timestamp"] = self._data_sources[
                "timestamp"
            ].get_data(event=data_event)

            yield data_event

    def open_event(self, *, event: Dict[str, Any]) -> None:
        """
        Opens a Pilatus single-frame file event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function opens the CBF file associated with the data event and stores its
        content in the provided `event` dictionary, as the value corresponding to the
        `data` key.

        Arguments:

            event: A dictionary storing the event data.
        """
        event["data"] = fabio.open(event["additional_info"]["full_path"])

    def close_event(self, *, event: Dict[str, Any]) -> None:
        """
        Closes a Pilatus single-frame file event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        CBF files don't need to be closed, so this function does nothing.

        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    def extract_data(
        self,
        *,
        event: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extracts data from a Pilatus single-frame file event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A dictionary storing the extracted data.

                * Each dictionary key identifies a Data Source in the event for which
                data has been retrieved.

                * The corresponding dictionary value stores the data extracted from the
                Data Source for the event being processed.

        Raises:

            OmDataExtractionError: Raised when data cannot be extracted from the event.
        """
        data: Dict[str, Any] = {}
        source_name: str
        data["timestamp"] = event["additional_info"]["timestamp"]
        for source_name in self._required_data_sources:
            try:
                data[source_name] = self._data_sources[source_name].get_data(
                    event=event
                )
            # One should never do the following, but it is not possible to anticipate
            # every possible error raised by the facility frameworks.
            except Exception:
                exc_type, exc_value = sys.exc_info()[:2]
                if exc_type is not None:
                    raise OmDataExtractionError(
                        f"OM Warning: Cannot interpret {source_name} event data due "
                        f"to the following error: {exc_type.__name__}: {exc_value}"
                    )

        return data

    def initialize_event_data_retrieval(self) -> None:
        """
        Initializes data data retrieval from Pilatus single-frame files.

        This function initializes the retrieval of single standalone data events from
        Pilatus single-frame data files.

        Please see the documentation of the base Protocol class for additional
        information about this method.
        """
        required_data: List[str] = self._monitor_params.get_parameter(
            group="data_retrieval_layer",
            parameter="required_data",
            parameter_type=list,
            required=True,
        )

        self._required_data_sources = filter_data_sources(
            data_sources=self._data_sources,
            required_data=required_data,
        )

        self._data_sources["timestamp"].initialize_data_source()
        source_name: str
        for source_name in self._required_data_sources:
            self._data_sources[source_name].initialize_data_source()

    def retrieve_event_data(self, event_id: str) -> Dict[str, Any]:
        """
        Retrieves all data related to the requested event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves all data related to the event specified by the provided
        identifier. A Pilatus single-frame file event identifier corresponds to the
        relative or absolute path to a file containing the event data.

        Arguments:

            event_id: A string that uniquely identifies a data event.

        Returns:

            All data related to the requested event.
        """
        data_event: Dict[str, Any] = {}
        data_event["additional_info"] = {}

        data_event["additional_info"]["full_path"] = event_id
        # File modification time is used as a first approximation of the timestamp
        # when the timestamp is not available.
        data_event["additional_info"]["file_modification_time"] = numpy.float64(
            pathlib.Path(event_id).stat().st_mtime
        )
        data_event["data"] = fabio.open(pathlib.Path(event_id))
        data_event["additional_info"]["timestamp"] = self._data_sources[
            "timestamp"
        ].get_data(event=data_event)
        return self.extract_data(event=data_event)


class Jungfrau1MFilesDataEventHandler(OmDataEventHandlerProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        source: str,
        data_sources: Dict[str, OmDataSourceProtocol],
        monitor_parameters: MonitorParameters,
    ) -> None:
        """
        Data Event Handler for Jungfrau 1M files.

        This class handles data events retrieved from files written by a Jungfrau 1M
        detector in HDF5 format.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        * For this Event Handler, a data event corresponds to all the information
          associated with an individual frame stored in an HDF5 file.

        * The source string required by this Data Event Handler is the path to a file
          containing a list of master HDF5 files to process, one per line, with their
          absolute or relative path. Each file can store more than one detector data
          frame, and each frame in the file is processed as a separate event.

        Arguments:

            source: A string describing the data event source.

            data_sources: A dictionary containing a set of Data Source class instances.

                * Each dictionary key must define the name of a data source.

                * The corresponding dictionary value must store the instance of the
                  [Data Source class][om.protocols.data_retrieval_layer.OmDataSourceProtocol]  # noqa: E501
                  that describes the source.

            monitor_parameters: An object storing OM's configuration parameters.
        """
        self._source: str = source
        self._monitor_params: MonitorParameters = monitor_parameters
        self._data_sources: Dict[str, OmDataSourceProtocol] = data_sources

    def initialize_event_handling_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes Jungfrau 1M file event handling on the collecting node.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        There is usually no need to initialize Jungfrau 1M file-based event handling on
        the collecting node, so this function actually does nothing.

        Arguments:

            node_rank: The OM rank of the current node int the OM node pool. The rank
                is an integer that unambiguously identifies the node in the pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        pass

    def initialize_event_handling_on_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes Jungfrau 1M file event handling on the processing nodes.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node int the OM node pool. The rank
                is an integer that unambiguously identifies the node in the pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        required_data: List[str] = self._monitor_params.get_parameter(
            group="data_retrieval_layer",
            parameter="required_data",
            parameter_type=list,
            required=True,
        )

        self._required_data_sources = filter_data_sources(
            data_sources=self._data_sources,
            required_data=required_data,
        )

    def event_generator(  # noqa: C901
        self,
        *,
        node_rank: int,
        node_pool_size: int,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Retrieves Jungfrau 1M file events.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves data events on the processing nodes. Each retrieved
        event corresponds to a single single detector data frame with all its
        associated data. The function tries to distribute the events as evenly as
        possible across all the processing nodes, with each node ideally processing the
        same number of events. If the total number of events cannot be split evenly,
        the last last node processes fewer events than the others.

        Arguments:

            node_rank: The OM rank of the current node int the OM node pool. The rank
                is an integer that unambiguously identifies the node in the pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        # Computes how many events the current processing node should process. Splits
        # the events as equally as possible amongst the processing nodes with the last
        # processing node getting a smaller number of events if the number of events to
        # be processed cannot be exactly divided by the number of processing nodes.
        try:
            file_handle: TextIO
            with open(self._source, "r") as file_handle:
                filelist: List[str] = file_handle.readlines()  # type
        except (IOError, OSError) as exc:
            raise OmInvalidSourceError(
                f"Error reading the {self._source} source file."
            ) from exc
        frame_list: List[_TypeJungfrau1MFrameInfo] = []
        line: str
        for line in filelist:
            filename: str = line.strip()
            # input filename must be a 'master' h5 file
            if not re.match(r".+_master_.+\.h5", filename):
                continue

            h5file: Any = h5py.File(pathlib.Path(filename).resolve(), "r")
            try:
                file_timestamp: float = datetime.strptime(
                    h5file["/entry/instrument/detector/timestamp"][()]
                    .decode("utf-8")
                    .strip(),
                    "%a %b %d %H:%M:%S %Y",
                ).timestamp()
            except KeyError:
                file_timestamp = datetime.strptime(
                    h5file["/entry/instrument/detector/Timestamp"][()]
                    .decode("utf-8")
                    .strip(),
                    "%a %b %d %H:%M:%S %Y",
                ).timestamp()

            index: int
            for index in range(h5file["/entry/data/data"].shape[0]):
                frame_list.append(
                    {
                        "h5file": h5file,
                        "index": index,
                        "file_timestamp": file_timestamp,
                    }
                )

        num_frames_curr_node: int = int(
            numpy.ceil(len(frame_list) / float(node_pool_size - 1))
        )
        frames_curr_node: List[_TypeJungfrau1MFrameInfo] = frame_list[
            ((node_rank - 1) * num_frames_curr_node) : (
                node_rank * num_frames_curr_node
            )
        ]

        print("Num frames current node:", node_rank, num_frames_curr_node)

        self._data_sources["timestamp"].initialize_data_source()
        source_name: str
        for source_name in self._required_data_sources:
            self._data_sources[source_name].initialize_data_source()

        data_event: Dict[str, Any] = {}
        data_event["additional_info"] = {}

        entry: _TypeJungfrau1MFrameInfo
        for entry in frames_curr_node:
            data_event["additional_info"].update(entry)
            data_event["additional_info"]["num_frames_curr_node"] = len(
                frames_curr_node
            )

            data_event["additional_info"]["timestamp"] = self._data_sources[
                "timestamp"
            ].get_data(event=data_event)

            yield data_event

    def open_event(self, *, event: Dict[str, Any]) -> None:
        """
        Opens a Jungfrau 1M file event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Since each detector frame in each HDF5 file is considered a separate event, the
        `event_generator` method, which distributes the frames across the processing
        nodes, takes care of opening and closing the files. This function therefore
        does nothing.

        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    def close_event(self, *, event: Dict[str, Any]) -> None:
        """
        Closes a Jungfrau 1M file event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Since each detector frame in each HDF5 file is considered a separate event, the
        `event_generator` method, which distributes the frames across the processing
        nodes, takes care of opening and closing the files. This function therefore
        does nothing.

        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    def extract_data(
        self,
        *,
        event: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extracts data from a Jungfrau 1M file event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A dictionary storing the extracted data.

                * Each dictionary key identifies a Data Source in the event for which
                data has been retrieved.

                * The corresponding dictionary value stores the data extracted from the
                Data Source for the event being processed.

        Raises:

            OmDataExtractionError: Raised when data cannot be extracted from the event.
        """
        data: Dict[str, Any] = {}
        f_name: str
        data["timestamp"] = event["additional_info"]["timestamp"]
        for source_name in self._required_data_sources:
            try:
                data[source_name] = self._data_sources[source_name].get_data(
                    event=event
                )
            # One should never do the following, but it is not possible to anticipate
            # every possible error raised by the facility frameworks.
            except Exception:
                exc_type, exc_value = sys.exc_info()[:2]
                if exc_type is not None:
                    raise OmDataExtractionError(
                        f"OM Warning: Cannot interpret {source_name} event data due "
                        f"to the following error: {exc_type.__name__}: {exc_value}"
                    )

        return data

    def initialize_event_data_retrieval(self) -> None:
        """
        Initializes event data retrieval from Jungfrau 1M HDF5 files.

        This function initializes the retrieval of single standalone data events from
        Jungfrau 1M HDF5 files.

        Please see the documentation of the base Protocol class for additional
        information about this method.
        """
        required_data: List[str] = self._monitor_params.get_parameter(
            group="data_retrieval_layer",
            parameter="required_data",
            parameter_type=list,
            required=True,
        )

        self._required_data_sources = filter_data_sources(
            data_sources=self._data_sources,
            required_data=required_data,
        )

        self._data_sources["timestamp"].initialize_data_source()
        source_name: str
        for source_name in self._required_data_sources:
            self._data_sources[source_name].initialize_data_source()

    def retrieve_event_data(self, event_id: str) -> Dict[str, Any]:
        """
        Retrieves all data related to the requested event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves all data related to the event specified by the provided
        identifier. A Jungfrau 1M unique event identifier is a string consisting of the
        absolute or relative path to the master HDF5 file attached to the event, and
        the index of the event within the file, separated by the '//' symbol.

        Arguments:

            event_id: A string that uniquely identifies a data event.

        Returns:

            All data related to the requested event.
        """
        data_event: Dict[str, Any] = {}

        event_id_parts: List[str] = event_id.split("//")
        filename: str = event_id_parts[0].strip()
        index: int = int(event_id_parts[1].strip())
        h5file: Any = h5py.File(pathlib.Path(filename).resolve(), "r")
        try:
            file_timestamp: float = datetime.strptime(
                h5file["/entry/instrument/detector/timestamp"][()]
                .decode("utf-8")
                .strip(),
                "%a %b %d %H:%M:%S %Y",
            ).timestamp()
        except:  # noqa: E722
            # TODO: Bare except
            file_timestamp = datetime.strptime(
                h5file["/entry/instrument/detector/Timestamp"][()]
                .decode("utf-8")
                .strip(),
                "%a %b %d %H:%M:%S %Y",
            ).timestamp()

        data_event["additional_info"] = {
            "h5file": h5file,
            "index": index,
            "file_timestamp": file_timestamp,
        }

        data_event["additional_info"]["timestamp"] = self._data_sources[
            "timestamp"
        ].get_data(event=data_event)

        extracted_data: Dict[str, Any] = self.extract_data(event=data_event)
        h5file.close()

        return extracted_data


class EigerFilesDataEventHandler(OmDataEventHandlerProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        source: str,
        data_sources: Dict[str, OmDataSourceProtocol],
        monitor_parameters: MonitorParameters,
    ) -> None:
        """
        Data Event Handler for Eiger files.

        This Data Event Handler deals with events originating from files written by an
        Eiger detector in HDF5 format.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        * For this Event Handler, a data event corresponds to all the information
          associated with an individual frame stored in an HDF5 file.

        * The source string required by this Data Event Handler is the path to a file
          containing a list of HDF5 files to process, one per line, with their absolute
          or relative path. Each file can store more than one detector data frame, and
          each frame in the file is processed as a separate event.

        Arguments:

            source: A string describing the data event source.

            data_sources: A dictionary containing a set of Data Source class instances.

                * Each dictionary key must define the name of a data source.

                * The corresponding dictionary value must store the instance of the
                  [Data Source class][om.protocols.data_retrieval_layer.OmDataSourceProtocol]  # noqa: E501
                  that describes the source.

            monitor_parameters: An object storing OM's configuration parameters.
        """
        self._source: str = source
        self._monitor_params: MonitorParameters = monitor_parameters
        self._data_sources: Dict[str, OmDataSourceProtocol] = data_sources

    def initialize_event_handling_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes Eiger file event handling on the collecting node.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        There is usually no need to initialize Eiger's file-based data handling on the
        collecting node, so this function actually does nothing.

        Arguments:

            node_rank: The OM rank of the current node int the OM node pool. The rank
                is an integer that unambiguously identifies the node in the pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        pass

    def initialize_event_handling_on_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes Eiger file event handling on the processing nodes.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node int the OM node pool. The rank
                is an integer that unambiguously identifies the node in the pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        required_data: List[str] = self._monitor_params.get_parameter(
            group="data_retrieval_layer",
            parameter="required_data",
            parameter_type=list,
            required=True,
        )

        self._required_data_sources = filter_data_sources(
            data_sources=self._data_sources,
            required_data=required_data,
        )

    def event_generator(
        self,
        *,
        node_rank: int,
        node_pool_size: int,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Retrieves Eiger file events.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves data events on the processing nodes. Each retrieved
        event corresponds to a single detector data frame with all its associated
        data. The function tries to distribute the events as evenly as possible across
        all the processing nodes, with each node ideally processing the same number of
        events. If the total number of events cannot be split evenly, the last node
        processes fewer events than the others.

        Arguments:

            node_rank: The OM rank of the current node int the OM node pool. The rank
                is an integer that unambiguously identifies the node in the pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        # Computes how many files the current processing node should process. Splits
        # the files as equally as possible amongst the processing nodes with the last
        # processing node getting a smaller number of files if the number of files to
        # be processed cannot be exactly divided by the number of processing nodes.
        try:
            file_handle: TextIO
            with open(self._source, "r") as file_handle:
                filelist: List[str] = file_handle.readlines()  # type
        except (IOError, OSError) as exc:
            raise OmInvalidSourceError(
                f"Error reading the {self._source} source file."
            ) from exc
        num_files_curr_node: int = int(
            numpy.ceil(len(filelist) / float(node_pool_size - 1))
        )
        files_curr_node: List[str] = filelist[
            ((node_rank - 1) * num_files_curr_node) : (node_rank * num_files_curr_node)
        ]

        self._data_sources["timestamp"].initialize_data_source()
        source_name: str
        for source_name in self._required_data_sources:
            self._data_sources[source_name].initialize_data_source()

        data_event: Dict[str, Dict[str, Any]] = {}
        data_event["additional_info"] = {}

        entry: str
        for entry in files_curr_node:
            filename: str = entry.strip()
            h5file: Any = h5py.File(filename, "r")
            num_frames: int = h5file["/entry/data/data"].shape[0]
            data_event["additional_info"]["h5file"] = h5file
            data_event["additional_info"]["full_path"] = str(
                pathlib.Path(filename).resolve()
            )
            data_event["additional_info"]["file_modification_time"] = numpy.float64(
                pathlib.Path(filename).stat().st_mtime
            )
            data_event["additional_info"]["timestamp"] = self._data_sources[
                "timestamp"
            ].get_data(event=data_event)
            index: int
            for index in range(num_frames):
                data_event["additional_info"]["index"] = index
                yield data_event

    def open_event(self, *, event: Dict[str, Any]) -> None:
        """
        Opens a Eiger file event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Since each detector frame in each HDF5 file is considered a separate event, the
        `event_generator` method, which distributes the frames across the processing
        nodes, takes care of opening and closing the files. This function therefore
        does nothing.

        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    def close_event(self, *, event: Dict[str, Any]) -> None:
        """
        Closes a Eiger file event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Since each detector frame in each HDF5 file is considered a separate event, the
        `event_generator` method, which distributes the frames across the processing
        nodes, takes care of opening and closing the files. This function therefore
        does nothing.

        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    def extract_data(
        self,
        *,
        event: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extracts data from an Eiger file event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A dictionary storing the extracted data.

                * Each dictionary key identifies a Data Source in the event for which
                data has been retrieved.

                * The corresponding dictionary value stores the data extracted from the
                Data Source for the event being processed.

        Raises:

            OmDataExtractionError: Raised when data cannot be extracted from the event.
        """
        data: Dict[str, Any] = {}
        f_name: str
        data["timestamp"] = event["additional_info"]["timestamp"]
        for source_name in self._required_data_sources:
            try:
                data[source_name] = self._data_sources[source_name].get_data(
                    event=event
                )
            # One should never do the following, but it is not possible to anticipate
            # every possible error raised by the facility frameworks.
            except Exception:
                exc_type, exc_value = sys.exc_info()[:2]
                if exc_type is not None:
                    raise OmDataExtractionError(
                        f"OM Warning: Cannot interpret {source_name} event data due "
                        f"to the following error: {exc_type.__name__}: {exc_value}"
                    )

        return data

    def initialize_event_data_retrieval(self) -> None:
        """
        Initializes event data retrieval from Eiger files.

        This function initializes the retrieval of single standalone data events from
        Eiger files.

        Please see the documentation of the base Protocol class for additional
        information about this method.
        """
        required_data: List[str] = self._monitor_params.get_parameter(
            group="data_retrieval_layer",
            parameter="required_data",
            parameter_type=list,
            required=True,
        )

        self._required_data_sources = filter_data_sources(
            data_sources=self._data_sources,
            required_data=required_data,
        )

        self._data_sources["timestamp"].initialize_data_source()
        source_name: str
        for source_name in self._required_data_sources:
            self._data_sources[source_name].initialize_data_source()

    def retrieve_event_data(self, event_id: str) -> Dict[str, Any]:
        """
        Retrieves all data related to the requested event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves all data related to the event specified by the provided
        identifier. An Eiger event identifier is a string consisting of the absolute or
        relative path to the HDF5 data file attached to the event, and the index of the
        event within the file, separated by '//' symbol.

        Arguments:

            event_id: A string that uniquely identifies a data event.

        Returns:

            All data related to the requested event.
        """

        event_id_parts: List[str] = event_id.split("//")
        filename: str = event_id_parts[0].strip()
        index: int = int(event_id_parts[1].strip())

        data_event: Dict[str, Any] = {}
        data_event["additional_info"] = {}

        h5file: Any = h5py.File(filename, "r")
        data_event["additional_info"]["h5file"] = h5file
        data_event["additional_info"]["full_path"] = str(
            pathlib.Path(filename).resolve()
        )
        data_event["additional_info"]["file_modification_time"] = numpy.float64(
            pathlib.Path(filename).stat().st_mtime
        )
        data_event["additional_info"]["timestamp"] = self._data_sources[
            "timestamp"
        ].get_data(event=data_event)
        data_event["additional_info"]["index"] = index

        extracted_data: Dict[str, Any] = self.extract_data(event=data_event)
        h5file.close()

        return extracted_data


class RayonixMccdFilesEventHandler(OmDataEventHandlerProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        source: str,
        data_sources: Dict[str, OmDataSourceProtocol],
        monitor_parameters: MonitorParameters,
    ) -> None:
        """
        Data Event Handler for Rayonix MX340-HS single-frame files.

        This class handles data events originating from single-frame mccd files written
        by a Rayonix MX340-HS detector.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        * For this Event Handler, a data event corresponds to the content of an
          individual single-frame mccd file.

        * The source string required by this Data Event Handler is the path to a file
          containing a list of mccd files to process, one per line, with their
          absolute or relative path.

        Arguments:

            source: A string describing the data event source.

            data_sources: A dictionary containing a set of Data Source class instances.

                * Each dictionary key must define the name of a data source.

                * The corresponding dictionary value must store the instance of the
                  [Data Source class][om.protocols.data_retrieval_layer.OmDataSourceProtocol]  # noqa: E501
                  that describes the source.

            monitor_parameters: An object storing OM's configuration parameters.
        """
        self._source: str = source
        self._monitor_params: MonitorParameters = monitor_parameters
        self._data_sources: Dict[str, OmDataSourceProtocol] = data_sources

    def initialize_event_handling_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes Rayonix MX340-HS file-based event handling on the collecting node.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        There is usually no need to initialize Rayonix MX340-HS file-based data
        event handling on the collecting node, so this function actually does nothing.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        pass

    def initialize_event_handling_on_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes Rayonix MX340-HS file-based event handling on the processing nodes.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node int the OM node pool. The rank
                is an integer that unambiguously identifies the node in the pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        required_data: List[str] = self._monitor_params.get_parameter(
            group="data_retrieval_layer",
            parameter="required_data",
            parameter_type=list,
            required=True,
        )

        self._required_data_sources = filter_data_sources(
            data_sources=self._data_sources,
            required_data=required_data,
        )

    def event_generator(
        self,
        *,
        node_rank: int,
        node_pool_size: int,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Retrieves Rayonix MX340-HS single-frame file events.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves data events on the processing nodes. Each retrieved
        event corresponds to the content of an individual single-frame mccd file. The
        function tries to distribute the events as evenly as possible across all the
        processing nodes, with each node ideally processing the same number of events.
        If the total number of events cannot be split evenly, the last last node
        processes fewer events than the others.

        Arguments:

            node_rank: The OM rank of the current node int the OM node pool. The rank
                is an integer that unambiguously identifies the node in the pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        # Computes how many files the current processing node should process. Splits
        # the files as equally as possible amongst the processing nodes with the last
        # processing node getting a smaller number of files if the number of files to
        # be processed cannot be exactly divided by the number of processing nodes.
        try:
            file_handle: TextIO
            with open(self._source, "r") as file_handle:
                filelist: List[str] = file_handle.readlines()
        except (IOError, OSError) as exc:
            raise OmInvalidSourceError(
                f"Error reading the {self._source} source file."
            ) from exc
        num_files_curr_node: int = int(
            numpy.ceil(len(filelist) / float(node_pool_size - 1))
        )
        files_curr_node: List[str] = filelist[
            ((node_rank - 1) * num_files_curr_node) : (node_rank * num_files_curr_node)
        ]

        self._data_sources["timestamp"].initialize_data_source()
        source_name: str
        for source_name in self._required_data_sources:
            self._data_sources[source_name].initialize_data_source()

        data_event: Dict[str, Any] = {}
        data_event["additional_info"] = {}

        entry: str
        for entry in files_curr_node:
            stripped_entry: str = entry.strip()
            data_event["additional_info"]["full_path"] = stripped_entry

            # File modification time is used as a first approximation of the timestamp
            # when the timestamp is not available.
            data_event["additional_info"]["file_modification_time"] = numpy.float64(
                pathlib.Path(stripped_entry).stat().st_mtime
            )

            data_event["additional_info"]["timestamp"] = self._data_sources[
                "timestamp"
            ].get_data(event=data_event)

            yield data_event

    def open_event(self, *, event: Dict[str, Any]) -> None:
        """
        Opens a Rayonix MX340-HS single-frame file event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Since detector_data is the only event data which is retrieved from the mccd
        files, the Data Source that handles this type of data takes care of opening and
        closing the files. This function therefore does nothing.

        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    def close_event(self, *, event: Dict[str, Any]) -> None:
        """
        Closes a Rayonix MX340-HS single-frame file event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Since detector_data is the only event data which is retrieved from the mccd
        files, the Data Source that handles this type of data takes care of opening and
        closing the files. This function therefore does nothing.

        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    def extract_data(
        self,
        *,
        event: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extracts data from a Rayonix MX340-HS single-frame file event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A dictionary storing the extracted data.

                * Each dictionary key identifies a Data Source in the event for which
                data has been retrieved.

                * The corresponding dictionary value stores the data extracted from the
                Data Source for the event being processed.

        Raises:

            OmDataExtractionError: Raised when data cannot be extracted from the event.
        """
        data: Dict[str, Any] = {}
        source_name: str
        data["timestamp"] = event["additional_info"]["timestamp"]
        for source_name in self._required_data_sources:
            try:
                data[source_name] = self._data_sources[source_name].get_data(
                    event=event
                )
            # One should never do the following, but it is not possible to anticipate
            # every possible error raised by the facility frameworks.
            except Exception:
                exc_type, exc_value = sys.exc_info()[:2]
                if exc_type is not None:
                    raise OmDataExtractionError(
                        f"OM Warning: Cannot interpret {source_name} event data due "
                        f"to the following error: {exc_type.__name__}: {exc_value}"
                    )

        return data

    def initialize_event_data_retrieval(self) -> None:
        """
        Initializes event data retrievals from Rayonix MX340-HS single-frame files.

        This function initializes the retrieval of single standalone data events
        from Rayonix MX340-HS single-frame files.

        Please see the documentation of the base Protocol class for additional
        information about this method.
        """
        required_data: List[str] = self._monitor_params.get_parameter(
            group="data_retrieval_layer",
            parameter="required_data",
            parameter_type=list,
            required=True,
        )

        self._required_data_sources = filter_data_sources(
            data_sources=self._data_sources,
            required_data=required_data,
        )

        self._data_sources["timestamp"].initialize_data_source()
        source_name: str
        for source_name in self._required_data_sources:
            self._data_sources[source_name].initialize_data_source()

    def retrieve_event_data(self, event_id: str) -> Dict[str, Any]:
        """
        Retrieves all data related to the requested event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves all data related to the event specified by the provided
        identifier. A Rayonix MX340-HS event identifier is the full absolute or
        relative path to the mccd file associated with the event.

        Arguments:

            event_id: A string that uniquely identifies a data event.

        Returns:

            All data related to the requested detector event.
        """
        data_event: Dict[str, Any] = {}
        data_event["additional_info"] = {}

        data_event["additional_info"]["full_path"] = event_id
        # File modification time is used as a first approximation of the timestamp
        # when the timestamp is not available.
        data_event["additional_info"]["file_modification_time"] = numpy.float64(
            pathlib.Path(event_id).stat().st_mtime
        )
        data_event["additional_info"]["timestamp"] = self._data_sources[
            "timestamp"
        ].get_data(event=data_event)
        return self.extract_data(event=data_event)


class Lambda1M5FilesDataEventHandler(OmDataEventHandlerProtocol):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        source: str,
        data_sources: Dict[str, OmDataSourceProtocol],
        monitor_parameters: MonitorParameters,
    ) -> None:
        """
        Data Event Handler for Lambda 1.5M files.

        This Data Event Handler deals with events originating from files written by a
        Lambda 1.5M detector in HDF5 format.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        * For this Event Handler, a data event corresponds to all the information
          associated with an individual frame stored in two separate HDF5 files written
          by two detector modules.

        * The source string required by this Data Event Handler is the path to a file
          containing a list of HDF5 files written by the first detector module
          ("*_m01*.nxs"), one per line, with their absolute or relative path. Each file
          can store more than one detector data frame, and each frame in the file is
          processed as a separate event.

        Arguments:

            source: A string describing the data event source.

            data_sources: A dictionary containing a set of Data Source class instances.

                * Each dictionary key must define the name of a data source.

                * The corresponding dictionary value must store the instance of the
                  [Data Source class][om.protocols.data_retrieval_layer.OmDataSourceProtocol]  # noqa: E501
                  that describes the source.

            monitor_parameters: An object storing OM's configuration parameters.
        """
        self._source: str = source
        self._monitor_params: MonitorParameters = monitor_parameters
        self._data_sources: Dict[str, OmDataSourceProtocol] = data_sources

    def initialize_event_handling_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes Lambda 1.5M file event handling on the collecting node.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        There is usually no need to initialize Lambda 1.5M file-based event handling on
        the collecting node, so this function actually does nothing.

        Arguments:

            node_rank: The OM rank of the current node int the OM node pool. The rank
                is an integer that unambiguously identifies the node in the pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        pass

    def initialize_event_handling_on_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes Lambda 1.5M file event handling on the processing nodes.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            node_rank: The OM rank of the current node int the OM node pool. The rank
                is an integer that unambiguously identifies the node in the pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        required_data: List[str] = self._monitor_params.get_parameter(
            group="data_retrieval_layer",
            parameter="required_data",
            parameter_type=list,
            required=True,
        )

        self._required_data_sources = filter_data_sources(
            data_sources=self._data_sources,
            required_data=required_data,
        )

    def event_generator(  # noqa: C901
        self,
        *,
        node_rank: int,
        node_pool_size: int,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Retrieves Lambda 1.5M file events.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves data events on the processing nodes. Each retrieved
        event corresponds to a single detector frame with all its associated data. The
        function tries to distribute the events as evenly as possible across all the
        processing nodes, with each node ideally processing the same number of events.
        If the total number of events cannot be split evenly, the last last node
        processes fewer events than the others.

        Arguments:

            node_rank: The OM rank of the current node int the OM node pool. The rank
                is an integer that unambiguously identifies the node in the pool.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        # Computes how many events the current processing node should process. Splits
        # the events as equally as possible amongst the processing nodes with the last
        # processing node getting a smaller number of events if the number of events to
        # be processed cannot be exactly divided by the number of processing nodes.
        try:
            file_: TextIO
            with open(self._source, "r") as file_handle:
                filelist: List[str] = []
                line: str
                for line in file_handle:
                    filename: str = line.strip()
                    # input filename must be a 'm01' nexus file
                    if re.match(r".+_m01(_.+)?\.nxs", filename):
                        filelist.append(filename)
        except (IOError, OSError) as exc:
            raise OmInvalidSourceError(
                f"Error reading the {self._source} source file."
            ) from exc
        num_files_curr_node: int = int(
            numpy.ceil(len(filelist) / float(node_pool_size - 1))
        )
        files_curr_node: List[str] = filelist[
            ((node_rank - 1) * num_files_curr_node) : (node_rank * num_files_curr_node)
        ]

        self._data_sources["timestamp"].initialize_data_source()
        source_name: str
        for source_name in self._required_data_sources:
            self._data_sources[source_name].initialize_data_source()

        data_event: Dict[str, Dict[str, Any]] = {}

        for filename in files_curr_node:
            h5files: Tuple[Any, Any] = (
                h5py.File(filename, "r"),
                h5py.File(re.sub(r"_m01(_.+)?\.nxs", r"_m02\1.nxs", filename), "r"),
            )
            frame_numbers: List[NDArray[numpy.int_]] = [
                h5file["/entry/instrument/detector/sequence_number"][:]
                for h5file in h5files
            ]
            index_m1: int
            frame_number: int
            for index_m1, frame_number in enumerate(frame_numbers[0]):
                try:
                    index_m2: int = numpy.where(frame_numbers[1] == frame_number)[0][0]
                except IndexError:
                    continue
                data_event["additional_info"] = {
                    "full_path": str(pathlib.Path(filename).resolve()),
                    "h5files": h5files,
                    "index": (index_m1, index_m2),
                    "file_modification_time": numpy.float64(
                        pathlib.Path(filename).stat().st_mtime
                    ),
                }
                data_event["additional_info"]["timestamp"] = self._data_sources[
                    "timestamp"
                ].get_data(event=data_event)
                yield data_event

    def open_event(self, *, event: Dict[str, Any]) -> None:
        """
        Opens a Lambda 1.5M file event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Since each detector frame in each HDF5 file is considered a separate event, the
        `event_generator` method, which distributes the frames across the processing
        nodes, takes care of opening and closing the files. This function therefore
        does nothing.

        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    def close_event(self, *, event: Dict[str, Any]) -> None:
        """
        Closes a Lambda 1.5M file event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Since each detector frame in each HDF5 file is considered a separate event, the
        `event_generator` method, which distributes the frames across the processing
        nodes, takes care of opening and closing the files. This function therefore
        does nothing.

        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    def extract_data(
        self,
        *,
        event: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extracts data from a Lambda 1.5M file event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A dictionary storing the extracted data.

                * Each dictionary key identifies a Data Source in the event for which
                data has been retrieved.

                * The corresponding dictionary value stores the data extracted from the
                Data Source for the event being processed.

        Raises:

            OmDataExtractionError: Raised when data cannot be extracted from the event.
        """
        data: Dict[str, Any] = {}
        source_name: str
        data["timestamp"] = event["additional_info"]["timestamp"]
        for source_name in self._required_data_sources:
            try:
                data[source_name] = self._data_sources[source_name].get_data(
                    event=event
                )
            # One should never do the following, but it is not possible to anticipate
            # every possible error raised by the facility frameworks.
            except Exception:
                exc_type, exc_value = sys.exc_info()[:2]
                if exc_type is not None:
                    raise OmDataExtractionError(
                        f"OM Warning: Cannot interpret {source_name} event data due "
                        f"to the following error: {exc_type.__name__}: {exc_value}"
                    )

        return data

    def initialize_event_data_retrieval(self) -> None:
        """
        Initializes event data retrievals from Lambda 1.5M HDF5 files.

        This function initializes the retrieval of single standalone events from
        Lambda 1.5M HDF5 files.

        Please see the documentation of the base Protocol class for additional
        information about this method.
        """
        required_data: List[str] = self._monitor_params.get_parameter(
            group="data_retrieval_layer",
            parameter="required_data",
            parameter_type=list,
            required=True,
        )

        self._required_data_sources = filter_data_sources(
            data_sources=self._data_sources,
            required_data=required_data,
        )

        self._data_sources["timestamp"].initialize_data_source()
        source_name: str
        for source_name in self._required_data_sources:
            self._data_sources[source_name].initialize_data_source()

    def retrieve_event_data(self, event_id: str) -> Dict[str, Any]:
        """
        Retrieves all data related to the requested event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves all data related to the event specified by the provided
        identifier. A Lambda 1.5M unique event identifier is a string consisting of two
        parts. The first part is the absolute or relative path to the HDF5 file storing
        the first panel of the detector data frame attached to the event ("*_m01.nxs"),
        while the second part is the index of the event within the file. The two parts
        are separated by the '//' symbol.

        Arguments:

            event_id: A string that uniquely identifies a data event.

        Returns:

            All data related to the requested event.
        """
        event_id_parts: List[str] = event_id.split("//")
        filename: str = event_id_parts[0].strip()
        index_m1: int = int(event_id_parts[1].strip())
        h5files: Tuple[Any, Any] = (
            h5py.File(filename, "r"),
            h5py.File(re.sub(r"(_m01.nxs)", r"_m02.nxs", filename), "r"),
        )
        frame_number: int = h5files[0]["/entry/instrument/detector/sequence_number"][
            index_m1
        ]
        index_m2: int = numpy.where(
            h5files[1]["/entry/instrument/detector/sequence_number"][:] == frame_number
        )[0][0]

        data_event: Dict[str, Any] = {}
        data_event["additional_info"] = {
            "full_path": str(pathlib.Path(filename).resolve()),
            "h5files": h5files,
            "index": (index_m1, index_m2),
            "file_modification_time": numpy.float64(
                pathlib.Path(filename).stat().st_mtime
            ),
        }
        data_event["additional_info"]["timestamp"] = self._data_sources[
            "timestamp"
        ].get_data(event=data_event)

        extracted_data: Dict[str, Any] = self.extract_data(event=data_event)
        h5file: Any
        for h5file in h5files:
            h5file.close()

        return extracted_data
