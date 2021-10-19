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
Retrieval and handling of data from files.

This module contains Data Event Handlers and Data Retrieval classes that deal with data
retrieved from files.
"""
import pathlib
import re
import sys
from typing import Any, Dict, Generator, List, TextIO, Tuple

import h5py  # type: ignore
import numpy  # type: ignore

from om.data_retrieval_layer import base as drl_base
from om.data_retrieval_layer import data_sources_files as ds_files
from om.data_retrieval_layer import data_sources_generic as ds_generic
from om.utils import exceptions, parameters

try:
    import fabio  # type: ignore
except ImportError:
    raise exceptions.OmMissingDependencyError(
        "The following required module cannot be imported: fabio"
    )


class _PilatusFilesEventHandler(drl_base.OmDataEventHandler):
    """
    See documentation of the `__init__` function.

    Base class: [`OmDataEventHandler`][om.data_retrieval_layer.base.OmDataEventHandler]
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
        by a Pilatus detector. It is a subclass of the
        [`OmDataEventHandler`][om.data_retrieval_layer.base.OmDataEventHandler] base
        class.

        For this Event Handler, a data event corresponds to the content of an
        individual single-frame CBF file. The source string is the path to a file
        containing a list of CBF files to process, one per line, with their absolute or
        relative path.

        Arguments:

            source: A string describing the data source.

            data_sources: A dictionary containing a set of Data Sources.

                * Each dictionary key must define the name of a data source.

                * The corresponding dictionary value must store an instance of the
                  corresponding
                  [Data Source][om.data_retrieval_layer.base.OmDataSource] class.

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.
        """
        self._source: str = source
        self._monitor_params: parameters.MonitorParams = monitor_parameters
        self._data_sources: Dict[str, drl_base.OmDataSource] = data_sources

    def initialize_event_handling_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> Any:
        """
        Initializes Pilatus single-frame file event handling on the collecting node.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        There is usually no need to initialize a file-based data source on the
        collecting node, so this function actually does nothing.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        Returns:

            An optional initialization token.
        """
        pass

    def initialize_event_handling_on_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> Any:
        """
        Initializes Pilatus single-frame file event handling on the processing nodes.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        Returns:

            An optional initialization token.
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

        This Data Event Handler distributes the files written by the Pilatus detector
        as evenly as possible across all the processing nodes. Each node ideally
        retrieves the same number of files. Only the last node might retrieve fewer
        files, depending on how evenly the total number can be split.

        Each retrieved event corresponds to the content of an individual single-frame
        CBF file.

        This generator function yields a dictionary storing the data for the current
        event.

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
                "Error reading the {0} source file.".format(self._source)
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

        This function opens the CBF file associated with the data event and store its
        content with the 'data' key of the 'event' dictionary.

        Arguments:

            event: A dictionary storing the event data.
        """
        event["data"] = fabio.open(event["additional_info"]["full_path"])

    def close_event(self, *, event: Dict[str, Any]) -> None:
        """
        Closes a Pilatus single-frame file event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        CBF files don't need to be closed, therefore this function does nothing.

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
        therefore this function always returns 1.

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

            * Each dictionary key identifies the Data Source from which the data has
              been retrieved.

            * The corresponding dictionary value stores the data that was extracted
              from the Data Source for the provided event.
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
                        "to the following error: {exc_type.__name__}: {exc_value}"
                    )

        return data


class _Jungfrau1MFilesDataEventHandler(drl_base.OmDataEventHandler):
    """
    See documentation of the `__init__` function.

    Base class: [`OmDataEventHandler`][om.data_retrieval_layer.base.OmDataEventHandler]
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
        Jungfrau 1M detector in HDF5 format. It is a subclass of the
        [`OmDataEventHandler`][om.data_retrieval_layer.base.OmDataEventHandler] base
        class.

        For this Event Handler, a data event corresponds to an individual frame
        stored in an HDF5 file. The source string is the path to a file containing a
        list of HDF5 files to process, one per line, with their absolute or relative
        path. Each file stores multiple detector data frames.

        Arguments:

            source: A string describing the data source.

            data_sources: A dictionary containing a set of Data Sources.

                * Each dictionary key must define the name of a data source.

                * The corresponding dictionary value must store an instance of the
                  corresponding
                  [Data Source][om.data_retrieval_layer.base.OmDataSource] class.

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.
        """
        self._source: str = source
        self._monitor_params: parameters.MonitorParams = monitor_parameters
        self._data_sources: Dict[str, drl_base.OmDataSource] = data_sources

    def initialize_event_handling_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> Any:
        """
        Initializes file event handling on the collecting node.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        There is usually no need to initialize a file-based data source on the
        collecting node, so this function actually does nothing.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        Returns:

            An optional initialization token.
        """
        pass

    def initialize_event_handling_on_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> Any:
        """
        Initializes Jungfrau 1M file event handling on the processing nodes.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        Returns:

        An optional initialization token.
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
        Retrieves Jungfrau 1M file events.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Each retrieved event corresponds to a single detector frame stored in an HDF5
        file. The detector frames are split as evenly as possible across all the
        processing nodes. Each node ideally retrieves the same number of
        frames. Only the last node might retrieve fewer frames, depending on how
        evenly the total number can be split.

        This generator function yields a dictionary storing the data for the current
        event.

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
                "Error reading the {0} source file.".format(self._source)
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

        Since each detector frame in each HDF5 file is considered as a separate event,
        the event generator, which splits the frames across the processing nodes, takes
        care of opening and closing the files. This function therefore does nothing.

        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    def close_event(self, *, event: Dict[str, Any]) -> None:
        """
        Closes a Jungfrau 1M file event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Since each detector frame in each HDF5 file is considered as a separate event,
        the event generator, which splits the frames across the processing nodes, takes
        care of opening and closing the files. This function therefore does nothing.

        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    def get_num_frames_in_event(self, *, event: Dict[str, Any]) -> int:
        """
        Gets the number of frames in a Jungfrau 1M file event.

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
        Extracts data from a Jungfrau 1M file event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A dictionary storing the data returned by the Data Extraction Functions.

            * Each dictionary key identifies the Data Extraction Function used to
              extract the data.

            * The corresponding dictionary value stores the data returned by the
              function.
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


class _Eiger16MFilesDataEventHandler(drl_base.OmDataEventHandler):
    """
    See documentation of the `__init__` function.

    Base class: [`OmDataEventHandler`][om.data_retrieval_layer.base.OmDataEventHandler]
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
        Eiger 16M detector in HDF5 format. It is a subclass of the
        [`OmDataEventHandler`][om.data_retrieval_layer.base.OmDataEventHandler] base
        class.

        For this Event Handler, a data event corresponds to an individual frame
        stored in an HDF5 file. The source string is the path to a file containing a
        list of HDF5 files to process, one per line, with their absolute or relative
        path. Each file stores multiple detector data frames.

        Arguments:

            source: A string describing the data source.

            data_sources: A dictionary containing a set of Data Sources.

                * Each dictionary key must define the name of a data source.

                * The corresponding dictionary value must store an instance of the
                  corresponding
                  [Data Source][om.data_retrieval_layer.base.OmDataSource] class.

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.
        """
        self._source: str = source
        self._monitor_params: parameters.MonitorParams = monitor_parameters
        self._data_sources: Dict[str, drl_base.OmDataSource] = data_sources

    def initialize_event_handling_on_collecting_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> Any:
        """
        Initializes file event handling on the collecting node.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        There is usually no need to initialize a file-based data source on the
        collecting node, so this function actually does nothing.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        Returns:

            An optional initialization token.
        """
        pass

    def initialize_event_handling_on_processing_node(
        self, *, node_rank: int, node_pool_size: int
    ) -> Any:
        """
        Initializes Eiger 16M file event handling on the processing nodes.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Arguments:

            node_rank: The rank, in the OM pool, of the processing node calling the
                function.

            node_pool_size: The total number of nodes in the OM pool, including all the
                processing nodes and the collecting node.

        Returns:

        An optional initialization token.
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

        Each retrieved event corresponds to a single detector frame stored in an HDF5
        file. The HDF5 files are split as evenly as possible across all the processing
        nodes. Each node ideally processes the same number of files. Only the last node
        might retrieve fewer frames, depending on how evenly the total number can be
        split.

        This generator function yields a dictionary storing the data for the current
        event.

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
                "Error reading the {0} source file.".format(self._source)
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

        Since each detector frame in each HDF5 file is considered as a separate event,
        the event generator, which splits the frames across the processing nodes, takes
        care of opening and closing the files. This function therefore does nothing.

        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    def close_event(self, *, event: Dict[str, Any]) -> None:
        """
        Closes a Eiger 16M file event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Since each detector frame in each HDF5 file is considered as a separate event,
        the event generator, which splits the frames across the processing nodes, takes
        care of opening and closing the files. This function therefore does nothing.

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

            A dictionary storing the data returned by the Data Extraction Functions.

            * Each dictionary key identifies the Data Extraction Function used to
              extract the data.

            * The corresponding dictionary value stores the data returned by the
              function.
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


class PilatusFilesDataRetrieval(drl_base.OmDataRetrieval):
    """
    See documentation of the `__init__` function.

    Base class: [`OmDataRetrieval`][om.data_retrieval_layer.base.OmDataRetrieval]
    """

    def __init__(self, *, monitor_parameters: parameters.MonitorParams, source: str):
        """
        Data Retrieval for Pilatus single-frame files.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class implements the operations needed to retrieve data from a set of
        single-frame files written by a Pilatus detector in CBF format.

        This class considers an individual data event as equivalent to the content of a
        single Pilatus CBF file. The full path to the CBF file is used as the event
        identifier. Since Pilatus files do not contain any timestamp information, the
        modification time of the file is taken as a first approximation of the
        timestamp of the data it contains. Futhermore, since Pilatus files do not
        contain any detector distance or beam energy information, their values need to
        be provided to OM through its configuration parameters (specifically, the
        `fallback_detector_distance_in_mm` and `fallback_beam_energy_in_eV` entries
        in the `data_retrieval_layer` parameter group). The source string for this
        Data Retrieval class is a path to a file containing a list of CBF files to
        process, one per line, with their absolute or relative path.

        Arguments:

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.

            source: A string describing the data source.
        """

        data_sources: Dict[str, drl_base.OmDataSource] = {
            "timestamp": ds_files.TimestampFromFileModificationTime(
                data_source_name="timestamp", monitor_parameters=monitor_parameters
            ),
            "event_id": ds_files.EventIdFromFilePath(
                data_source_name="eventid", monitor_parameters=monitor_parameters
            ),
            "frame_id": ds_generic.FrameIdZero(
                data_source_name="frameid", monitor_parameters=monitor_parameters
            ),
            "detector_data": ds_files.PilatusSingleFrameFiles(
                data_source_name="detector", monitor_parameters=monitor_parameters
            ),
            "beam_energy": ds_generic.FloatEntryFromConfiguration(
                data_source_name="fallback_beam_energy_in_eV",
                monitor_parameters=monitor_parameters,
            ),
            "detector_distance": ds_generic.FloatEntryFromConfiguration(
                data_source_name="fallback_detector_distance_in_mm",
                monitor_parameters=monitor_parameters,
            ),
        }

        self._data_event_handler: drl_base.OmDataEventHandler = (
            _PilatusFilesEventHandler(
                source=source,
                monitor_parameters=monitor_parameters,
                data_sources=data_sources,
            )
        )

    @property
    def data_event_handler(self) -> drl_base.OmDataEventHandler:
        return self._data_event_handler


class Jungfrau1MFilesDataRetrieval(drl_base.OmDataRetrieval):
    """
    See documentation of the `__init__` function.

    Base class: [`OmDataRetrieval`][om.data_retrieval_layer.base.OmDataRetrieval]
    """

    def __init__(self, *, monitor_parameters: parameters.MonitorParams, source: str):
        """
        Data Retrieval for Jungfrau 1M HDF5 files.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class implements the operations needed to retrieve data from a set of
        files written by a Jungfrau 1M detector in HDF5 format.

        This class considers an individual data event as equivalent to an single
        detector frame stored in an HDF5 file. The full path to the file containing
        the frame, together with the index of the frame in the file, is taken as
        the event identifier. Jungfrau 1M files do not contain any absolute timestamp
        information, but they store the readout of the internal detector clock for
        every frame. As a first approximation, the modification time of the file
        is taken as the timestamp of the first frame it contains, and the timestamp
        of all other frames is computed according to the internal clock difference.
        Futhermore, Jungfrau 1M files do not contain any detector distance or beam
        energy information: their values need to be provided to OM through its
        configuration parameters (specifically, the `fallback_detector_distance_in_mm`
        and `fallback_beam_energy_in_eV` entries in the `data_retrieval_layer`
        parameter group). The source string for this Data Retrieval class is the path
        to a file containing a list of HDF5 files to process, one per line, with their
        absolute or relative path.

        Arguments:

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.

            source: A string describing the data source.
        """

        data_sources: Dict[str, drl_base.OmDataSource] = {
            "timestamp": ds_files.TimestampJungfrau1MFiles(
                data_source_name="timestamp", monitor_parameters=monitor_parameters
            ),
            "event_id": ds_files.EventIdJungfrau1MFiles(
                data_source_name="eventid", monitor_parameters=monitor_parameters
            ),
            "frame_id": ds_generic.FrameIdZero(
                data_source_name="frameid", monitor_parameters=monitor_parameters
            ),
            "detector_data": ds_files.Jungfrau1MFiles(
                data_source_name="detector", monitor_parameters=monitor_parameters
            ),
            "beam_energy": ds_generic.FloatEntryFromConfiguration(
                data_source_name="fallback_beam_energy",
                monitor_parameters=monitor_parameters,
            ),
            "detector_distance": ds_generic.FloatEntryFromConfiguration(
                data_source_name="fallback_detector_distance",
                monitor_parameters=monitor_parameters,
            ),
        }

        self._data_event_handler: drl_base.OmDataEventHandler = (
            _Jungfrau1MFilesDataEventHandler(
                source=source,
                monitor_parameters=monitor_parameters,
                data_sources=data_sources,
            )
        )

    @property
    def data_event_handler(self) -> drl_base.OmDataEventHandler:
        return self._data_event_handler


class Eiger16MFilesDataRetrieval(drl_base.OmDataRetrieval):
    """
    See documentation of the `__init__` function.

    Base class: [`OmDataRetrieval`][om.data_retrieval_layer.base.OmDataRetrieval]
    """

    def __init__(self, *, monitor_parameters: parameters.MonitorParams, source: str):
        """
        Data Retrieval for Eiger 16M HDF5 files.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This class implements the operations needed to retrieve data from a set of
        files written by a Eiger 16M detector in HDF5 format.

        This class considers an individual data event as equivalent to a single
        detector frame stored in an HDF5 file. The full path to the file containing
        the frame, together with the index of the frame in the file, is taken as
        the event identifier. Eiger 16M files do not contain any absolute timestamp
        information, the modification time of the file is taken as a first approximation
        of the timestamp of the data it contains. Futhermore, Eiger 16M files do not
        contain any detector distance or beam energy information: their values need to
        be provided to OM through its configuration parameters (specifically, the
        `fallback_detector_distance_in_mm` and `fallback_beam_energy_in_eV` entries in
        the `data_retrieval_layer` parameter group). The source string for this Data
        Retrieval class is the path to a file containing a list of HDF5 files to
        process, one per line, with their absolute or relative path.

        Arguments:

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.

            source: A string describing the data source.
        """

        data_sources: Dict[str, drl_base.OmDataSource] = {
            "timestamp": ds_files.TimestampFromFileModificationTime(
                data_source_name="timestamp", monitor_parameters=monitor_parameters
            ),
            "event_id": ds_files.EventIdEiger16MFiles(
                data_source_name="eventid", monitor_parameters=monitor_parameters
            ),
            "frame_id": ds_generic.FrameIdZero(
                data_source_name="frameid", monitor_parameters=monitor_parameters
            ),
            "detector_data": ds_files.Eiger16MFiles(
                data_source_name="detector", monitor_parameters=monitor_parameters
            ),
            "beam_energy": ds_generic.FloatEntryFromConfiguration(
                data_source_name="fallback_beam_energy",
                monitor_parameters=monitor_parameters,
            ),
            "detector_distance": ds_generic.FloatEntryFromConfiguration(
                data_source_name="fallback_detector_distance",
                monitor_parameters=monitor_parameters,
            ),
        }

        self._data_event_handler: drl_base.OmDataEventHandler = (
            _Eiger16MFilesDataEventHandler(
                source=source,
                monitor_parameters=monitor_parameters,
                data_sources=data_sources,
            )
        )

    @property
    def data_event_handler(self) -> drl_base.OmDataEventHandler:
        return self._data_event_handler
