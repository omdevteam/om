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
Handling of file-based data events.

This module contains Data Event Handler classes that manipulate file-based events.
"""
import pathlib
import re
import sys
from typing import Any, Dict, Generator, List, TextIO, Tuple

import h5py  # type: ignore
import numpy  # type: ignore

from om.data_retrieval_layer import base as drl_base
from om.utils import exceptions, parameters

try:
    import fabio  # type: ignore
except ImportError:
    raise exceptions.OmMissingDependencyError(
        "The following required module cannot be imported: fabio"
    )


class PilatusFilesEventHandler(drl_base.OmDataEventHandler):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        source: str,
        data_sources: Dict[str, drl_base.OmDataSource],
        monitor_parameters: parameters.MonitorParams,
    ) -> None:
        """
        Data Event Handler for Pilatus single-frame files.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class handles data events originating from single-frame CBF files written
        by a Pilatus detector.

        * For this Event Handler, a data event corresponds to the content of an
          individual single-frame CBF file.

        * The source string required by this Data Event Handler is the path to a file
          containing a list of CBF files to process, one per line, with their
          absolute or relative path.

        Arguments:

            source: A string describing the data event source.

            data_sources: A dictionary containing a set of Data Sources.

                * Each dictionary key must define the name of a data source.

                * The corresponding dictionary value must store the instance of the
                  [Data Source class][om.data_retrieval_layer.base.OmDataSource] that
                  describes the source.

            monitor_parameters: An object storing OM's configuration parameters.
        """
        self._source: str = source
        self._monitor_params: parameters.MonitorParams = monitor_parameters
        self._data_sources: Dict[str, drl_base.OmDataSource] = data_sources

    def initialize_event_handling_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes Pilatus single-frame file event handling on the collecting node.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        There is usually no need to initialize a Pilatus file-based data source on the
        collecting node, so this function actually does nothing.

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
        Initializes Pilatus single-frame file event handling on the processing nodes.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        required_data: List[str] = self._monitor_params.get_parameter(
            group="data_retrieval_layer",
            parameter="required_data",
            parameter_type=list,
            required=True,
        )

        self._required_data_sources = drl_base.filter_data_sources(
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
        Retrieves PIlatus single-frame file events.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves events for processing (each event corresponds to the
        content of an individual single-frame CBF file). It tries to distribute the
        events as evenly as possible across all the processing nodes. Each node should
        ideally process the same number of events. Only the last node might process
        fewer, depending on how evenly the total number can be split.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        # Computes how many files the current processing node should process. Splits
        # the files as equally as possible amongst the processing nodes with the last
        # processing node getting a smaller number of files if the number of files to
        # be processed cannot be exactly divided by the number of processing nodes.
        try:
            fhandle: TextIO
            with open(self._source, "r") as fhandle:
                filelist: List[str] = fhandle.readlines()
        except (IOError, OSError) as exc:
            raise RuntimeError(
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

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function opens the CBF file associated with the data event and stores its
        content in the `event` dictionary, as the value corresponding to the `data`
        key.

        Arguments:

            event: A dictionary storing the event data.
        """
        event["data"] = fabio.open(event["additional_info"]["full_path"])

    def close_event(self, *, event: Dict[str, Any]) -> None:
        """
        Closes a Pilatus single-frame file event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        CBF files don't need to be closed, so this function does nothing.

        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    def get_num_frames_in_event(self, *, event: Dict[str, Any]) -> int:
        """
        Gets the number of frames in a Pilatus single-frame file event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Pilatus single-frame files contain by definition only one frame per file,
        so this function always returns 1.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The number of frames in the event.
        """
        return 1

    def extract_data(
        self,
        *,
        event: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extracts data from a Pilatus single-frame file event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A dictionary storing the extracted data.

            * Each dictionary key identifies a Data Source in the event for which data
              has been retrieved.

            * The corresponding dictionary value stores the data extracted from the
              Data Source for the frame being processed.
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
                    raise exceptions.OmDataExtractionError(
                        f"OM Warning: Cannot interpret {source_name} event data due "
                        f"to the following error: {exc_type.__name__}: {exc_value}"
                    )

        return data


class Jungfrau1MFilesDataEventHandler(drl_base.OmDataEventHandler):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        source: str,
        data_sources: Dict[str, drl_base.OmDataSource],
        monitor_parameters: parameters.MonitorParams,
    ) -> None:
        """
        Data Event Handler for Jungfrau 1M files.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This Data Event Handler deals with events originating from files written by a
        Jungfrau 1M detector in HDF5 format.

        * For this Event Handler, a data event corresponds to all the information
          associated with an individual frame stored in an HDF5 file.

        * The source string required by this Data Event Handler is the path to a file
          containing a list of HDF5 files to process, one per line, with their absolute
          or relative path. Each file can store more than one detector data frame, each
          corresponding to an event.

        Arguments:

            source: A string describing the data event source.

            data_sources: A dictionary containing a set of Data Sources.

                * Each dictionary key must define the name of a data source.

                * The corresponding dictionary value must store the instance of the
                  [Data Source class][om.data_retrieval_layer.base.OmDataSource] that
                  describes the source.

            monitor_parameters: An object storing OM's configuration parameters.
        """
        self._source: str = source
        self._monitor_params: parameters.MonitorParams = monitor_parameters
        self._data_sources: Dict[str, drl_base.OmDataSource] = data_sources

    def initialize_event_handling_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes Jungfrau 1M file event handling on the collecting node.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        There is usually no need to initialize a Jungfrau 1M file-based data source on
        the collecting node, so this function actually does nothing.

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
        Initializes Jungfrau 1M file event handling on the processing nodes.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        required_data: List[str] = self._monitor_params.get_parameter(
            group="data_retrieval_layer",
            parameter="required_data",
            parameter_type=list,
            required=True,
        )

        self._required_data_sources = drl_base.filter_data_sources(
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

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves events for processing (each event corresponds to a
        single detector frame with all the associated data). It tries to distribute the
        events as evenly as possible across all the processing nodes. Each node should
        ideally process the same number of events. Only the last node might process
        fewer, depending on how evenly the total number can be split.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        # Computes how many events the current processing node should process. Splits
        # the events as equally as possible amongst the processing nodes with the last
        # processing node getting a smaller number of events if the number of events to
        # be processed cannot be exactly divided by the number of processing nodes.
        try:
            fhandle: TextIO
            with open(self._source, "r") as fhandle:
                filelist: List[str] = fhandle.readlines()  # type
        except (IOError, OSError) as exc:
            raise RuntimeError(
                f"Error reading the {self._source0} source file."
            ) from exc
        frame_list: List[Dict[str, Any]] = []
        # TODO: Specify types better
        filename: str
        for filename in filelist:
            # input filename must be from panel 'd0'
            if re.match(r".+_d0_.+\.h5", filename):
                filename_d0: str = filename.strip()
            else:
                continue
            filename_d1: str = re.sub(r"(_d0_)(.+\.h5)", r"_d1_\2", str(filename_d0))

            h5files: Tuple[Any, Any] = (
                h5py.File(pathlib.Path(filename_d0).resolve(), "r"),
                h5py.File(pathlib.Path(filename_d1).resolve(), "r"),
            )

            h5_data_path: str = "/data_" + re.findall(r"_(f\d+)_", filename)[0]

            try:
                frame_numbers: List[numpy.ndarray] = [
                    h5file["/frameNumber"][:] for h5file in h5files
                ]
            except KeyError:
                frame_numbers = [h5file["/frame number"][:] for h5file in h5files]

            ind0: int
            frame_number: numpy.ndarray
            for ind0, frame_number in enumerate(frame_numbers[0]):
                try:
                    ind1: int = numpy.where(frame_numbers[1] == frame_number)[0][0]
                except IndexError:
                    continue

                # TODO: Type this dictionary
                frame_list.append(
                    {
                        "h5files": h5files,
                        "index": (ind0, ind1),
                        "h5_data_path": h5_data_path,
                        "frame_number": frame_number,
                        "jf_internal_clock": h5files[0]["/timestamp"][ind0]
                        - h5files[0]["/timestamp"][0],
                        "file_creation_time": numpy.float64(
                            pathlib.Path(filename_d0).stat().st_ctime
                        ),
                    }
                )

        num_frames_curr_node: int = int(
            numpy.ceil(len(frame_list) / float(node_pool_size - 1))
        )
        frames_curr_node: List[Dict[str, Any]] = frame_list[
            ((node_rank - 1) * num_frames_curr_node) : (
                node_rank * num_frames_curr_node
            )
        ]

        print("Num frames current node:", node_rank, num_frames_curr_node)

        self._data_sources["timestamp"].initialize_data_source()
        source_name: str
        for source_name in self._required_data_sources:
            self._data_sources[source_name].initialize_data_source()

        data_event: Dict[str, Dict[str, Any]] = {}
        data_event["additional_info"] = {}

        entry: Dict[str, Any]
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

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Since each detector frame in each HDF5 file is considered a separate event, the
        `event_generator` method, which splits the frames across the processing nodes,
        takes care of opening and closing the files. This function therefore does
        nothing.

        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    def close_event(self, *, event: Dict[str, Any]) -> None:
        """
        Closes a Jungfrau 1M file event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Since each detector frame in each HDF5 file is considered a separate event, the
        `event_generator` method, which splits the frames across the processing nodes,
        takes care of opening and closing the files. This function therefore does
        nothing.

        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    def get_num_frames_in_event(self, *, event: Dict[str, Any]) -> int:
        """
        Gets the number of frames in a Jungfrau 1M file event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Since each Jungfrau 1M frame is considered a separate event, this function
        always returns 1.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The number of frames in the event.
        """
        return 1

    def extract_data(
        self,
        *,
        event: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extracts data from a Jungfrau 1M file event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A dictionary storing the extracted data.

            * Each dictionary key identifies a Data Source in the event for which data
              has been retrieved.

            * The corresponding dictionary value stores the data extracted from the
              Data Source for the frame being processed.
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
                    raise exceptions.OmDataExtractionError(
                        f"OM Warning: Cannot interpret {source_name} event data due "
                        f"to the following error: {exc_type.__name__}: {exc_value}"
                    )

        return data


class Eiger16MFilesDataEventHandler(drl_base.OmDataEventHandler):
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        source: str,
        data_sources: Dict[str, drl_base.OmDataSource],
        monitor_parameters: parameters.MonitorParams,
    ) -> None:
        """
        Data Event Handler for Eiger 16M files.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This Data Event Handler deals with events originating from files written by a
        Eiger 16M detector in HDF5 format.

        * For this Event Handler, a data event corresponds to all the information
          associated with an individual frame stored in an HDF5 file.

        * The source string required by this Data Event Handler is the path to a file
          containing a list of HDF5 files to process, one per line, with their absolute
          or relative path. Each file can store more than one detector data frame, each
          corresponding to an event.

        Arguments:

            source: A string describing the data event source.

            data_sources: A dictionary containing a set of Data Sources.

                * Each dictionary key must define the name of a data source.

                * The corresponding dictionary value must store the instance of the
                  [Data Source class][om.data_retrieval_layer.base.OmDataSource] that
                  describes the source.

            monitor_parameters: An object storing OM's configuration parameters.
        """
        self._source: str = source
        self._monitor_params: parameters.MonitorParams = monitor_parameters
        self._data_sources: Dict[str, drl_base.OmDataSource] = data_sources

    def initialize_event_handling_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes Eiger 16M file event handling on the collecting node.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        There is usually no need to initialize a Eiger 16M file-based data source on
        the collecting node, so this function actually does nothing.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.S
        """
        pass

    def initialize_event_handling_on_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> None:
        """
        Initializes Eiger 16M file event handling on the processing nodes.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        required_data: List[str] = self._monitor_params.get_parameter(
            group="data_retrieval_layer",
            parameter="required_data",
            parameter_type=list,
            required=True,
        )

        self._required_data_sources = drl_base.filter_data_sources(
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
        Retrieves Eiger 16M file events.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function retrieves events for processing (each events corresponds to a
        single detector frame with all the associated data). It tries to distribute the
        events as evenly as possible across all the processing nodes. Each node should
        ideally process the same number of events. Only the last node might process
        fewer, depending on how evenly the total number can be split.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.
        """
        # Computes how many files the current processing node should process. Splits
        # the files as equally as possible amongst the processing nodes with the last
        # processing node getting a smaller number of files if the number of files to
        # be processed cannot be exactly divided by the number of processing nodes.
        try:
            fhandle: TextIO
            with open(self._source, "r") as fhandle:
                filelist: List[str] = fhandle.readlines()  # type
        except (IOError, OSError) as exc:
            raise RuntimeError(
                f"Error reading the {self._source} source file.")
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
        Opens a Eiger 16M file event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Since each detector frame in each HDF5 file is considered a separate event, the
        `event_generator` method, which splits the frames across the processing nodes,
        takes care of opening and closing the files. This function therefore does
        nothing.

        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    def close_event(self, *, event: Dict[str, Any]) -> None:
        """
        Closes a Eiger 16M file event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Since each detector frame in each HDF5 file is considered a separate event, the
        `event_generator` method, which splits the frames across the processing nodes,
        takes care of opening and closing the files. This function therefore does
        nothing.

        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    def get_num_frames_in_event(self, *, event: Dict[str, Any]) -> int:
        """
        Gets the number of frames in a Eiger 16M file event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Since each frame in each HDF5 file is considered as a separate event, this
        function always returns 1.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The number of frames in the event.
        """
        return 1

    def extract_data(
        self,
        *,
        event: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extracts data from an Eiger 16M file event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A dictionary storing the extracted data.

            * Each dictionary key identifies a Data Source in the event for which data
              has been retrieved.

            * The corresponding dictionary value stores the data extraced from the
              Data Source for the frame being processed.
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
                    raise exceptions.OmDataExtractionError(
                        f"OM Warning: Cannot interpret {source_name} event data due "
                        "to the following error: {exc_type.__name__}: {exc_value}"
                    )

        return data
