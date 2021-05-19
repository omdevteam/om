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
Retrieval and handling of data events from a filesystem.

This module contains Data Event Handlers for files saved in a filesystem (on a physical
or virtual disk).
"""
import pathlib
import re
from typing import Any, Callable, Dict, Generator, List, TextIO, Tuple

import h5py  # type: ignore
import numpy  # type: ignore

from om.algorithms import calibration as calib_algs
from om.data_retrieval_layer import base as drl_base
from om.data_retrieval_layer import functions_jungfrau1M, functions_pilatus
from om.utils import exceptions, parameters

try:
    import fabio  # type: ignore
except ImportError:
    raise exceptions.OmMissingDependencyError(
        "The following required module cannot be imported: fabio"
    )


class FilesBaseDataEventHandler(drl_base.OmDataEventHandler):
    """
    See documentation of the `__init__` function.

    Base class: [`OmDataEventHandler`][om.data_retrieval_layer.base.OmDataEventHandler]
    """

    def __init__(
        self, monitor_parameters: parameters.MonitorParams, source: str
    ) -> None:
        """
        Base Data Event Handler class for events retrieved from files.

        This is the base class for Data Event Handlers that deal with files. It is a
        subclass of the more generic [OmDataEventHandler]
        [om.data_retrieval_layer.base.OmDataEventHandler] base class, and should in
        turn be subclassed to implement Data Event Handlers for specific file types.

        Arguments:

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.

            source: A string describing the data source.
        """
        super(FilesBaseDataEventHandler, self).__init__(
            monitor_parameters=monitor_parameters,
            source=source,
        )

    def initialize_event_handling_on_collecting_node(
        self, node_rank: int, node_pool_size: int
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


class PilatusFilesDataEventHandler(FilesBaseDataEventHandler):
    """
    See documentation of the `__init__` function.

    Base class: [`FilesBaseDataEventHandler`]
    [om.data_retrieval_layer.data_handlers_filesystem.FilesBaseDataEventHandler]
    """

    def __init__(
        self, monitor_parameters: parameters.MonitorParams, source: str
    ) -> None:
        """
        Data Event Handler for Pilatus files.

        This Data Event Handler deals with files written by a 1M Pilatus detector in
        CBF format. It is a subclass of the [FilesBaseDataEventHandler]
        [om.data_retrieval_layer.data_handlers_filesystem.FilesBaseDataEventHandler]
        class.

        The source string for this Data Event Handler is a path to a file containing a
        list of CBF files to process, one per line, with their absolute or relative
        path. Each retrieved event corresponds to the content of one CBF file, which
        usually stores a single detector data frame.

        Arguments:

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.

            source: A string describing the data source.
        """
        super(PilatusFilesDataEventHandler, self).__init__(
            monitor_parameters=monitor_parameters,
            source=source,
        )

    @property
    def data_extraction_funcs(
        self,
    ) -> Dict[str, Callable[[Dict[str, Dict[str, Any]]], Any]]:
        """
        Retrieves the Data Extraction Functions for Pilatus file events.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Returns:

            A dictionary storing the Data Extraction functions available to the current
            Data Event Handler.

            * Each dictionary key defines the name of a function.

            * The corresponding dictionary value stores the function implementation.
        """
        return {
            "timestamp": functions_pilatus.timestamp,
            "beam_energy": functions_pilatus.beam_energy,
            "detector_distance": functions_pilatus.detector_distance,
            "detector_data": functions_pilatus.detector_data,
            "event_id": functions_pilatus.event_id,
            "frame_id": functions_pilatus.frame_id,
        }

    def initialize_event_handling_on_processing_node(
        self, node_rank: int, node_pool_size: int
    ) -> Any:
        """
        Initializes Pilatus file event handling on the processing nodes.

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
        required_data: List[str] = self._monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="required_data",
            parameter_type=list,
            required=True,
        )

        self._required_data_extraction_funcs: Dict[
            str, Callable[[Dict[str, Dict[str, Any]]], Any]
        ] = drl_base.filter_data_extraction_funcs(
            self.data_extraction_funcs, required_data
        )

        # Fills the event info dictionary with static data that will be retrieved
        # later.
        self._event_info_to_append: Dict[str, Any] = {}

        calibration: bool = self._monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="calibration",
            parameter_type=bool,
            required=True,
        )
        self._event_info_to_append["calibration"] = calibration

        if "beam_energy" in required_data:
            self._event_info_to_append["beam_energy"] = self._monitor_params.get_param(
                group="data_retrieval_layer",
                parameter="fallback_beam_energy_in_eV",
                parameter_type=float,
                required=True,
            )
        if "detector_distance" in required_data:
            self._event_info_to_append[
                "detector_distance"
            ] = self._monitor_params.get_param(
                group="data_retrieval_layer",
                parameter="fallback_detector_distance_in_mm",
                parameter_type=float,
                required=True,
            )

    def event_generator(
        self,
        node_rank: int,
        node_pool_size: int,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Retrieves Pilatus file events.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This Data Event Handler distributes the files from the data source as evenly as
        possible across all the processing nodes. Each node ideally retrieves the same
        number of files from the source. Only the last node might retrieve fewer files,
        depending on how evenly the total number can be split.

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

        data_event: Dict[str, Dict[str, Any]] = {}
        data_event["data_extraction_funcs"] = self._required_data_extraction_funcs
        data_event["additional_info"] = {}
        data_event["additional_info"].update(self._event_info_to_append)

        entry: str
        for entry in files_curr_node:
            stripped_entry: str = entry.strip()
            data_event["additional_info"]["full_path"] = stripped_entry

            # File modification time is used as a first approximation of the timestamp
            # when the timestamp is not available.
            data_event["additional_info"]["file_creation_time"] = numpy.float64(
                pathlib.Path(stripped_entry).stat().st_mtime
            )

            yield data_event

    def open_event(self, event: Dict[str, Any]) -> None:
        """
        Opens a Pilatus file event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This function opens each CBF file and associates its content with the 'data'
        key of the 'event' dictionary.

        Arguments:

            event: A dictionary storing the event data.
        """
        event["data"] = fabio.open(event["additional_info"]["full_path"])

    def close_event(self, event: Dict[str, Any]) -> None:
        """
        Closes a Pilatus file event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        CBF files don't need to be closed, therefore this function does nothing.

        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    def get_num_frames_in_event(self, event: Dict[str, Any]) -> int:
        """
        Gets the number of frames in a Pilatus file  event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Since a Pilatus detector usually writes only one frame per file, this function
        always returns 1.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The number of frames in the event.
        """
        return 1


class Jungfrau1MFilesDataEventHandler(FilesBaseDataEventHandler):
    """
    See documentation of the `__init__` function.

    Base class: [`FilesBaseDataEventHandler`]
    [om.data_retrieval_layer.data_handlers_filesystem.FilesBaseDataEventHandler]
    """

    def __init__(
        self, monitor_parameters: parameters.MonitorParams, source: str
    ) -> None:
        """
        Data Event Handler for Jungfrau 1M files.

        This Data Event Handler deals with files written by a Jungfrau 1M detector in
        HDF5 format. It is a subclass of the [`FilesBaseDataEventHandler`]
        [om.data_retrieval_layer.data_handlers_filesystem.FilesBaseDataEventHandler]
        class.

        The source string for this Data Event Handler is a path to a file containing a
        list of HDF5 files to process, one per line, with their absolute or relative
        path. Each file stores multiple detector data frames. Each retrieved event
        corresponds to a single frame from a file.

        Arguments:

            monitor_parameters: A [MonitorParams]
                [om.utils.parameters.MonitorParams] object storing the OM monitor
                parameters from the configuration file.

            source: A string describing the data source.
        """
        super(Jungfrau1MFilesDataEventHandler, self).__init__(
            monitor_parameters=monitor_parameters,
            source=source,
        )

    @property
    def data_extraction_funcs(
        self,
    ) -> Dict[str, Callable[[Dict[str, Dict[str, Any]]], Any]]:
        """
        Retrieves the Data Extraction Functions for Jungfrau 1M file events.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Returns:

            A dictionary storing the Data Extraction functions available to the current
            Data Event Handler.

            * Each dictionary key defines the name of a function.

            * The corresponding dictionary value stores the function implementation.
        """
        return {
            "timestamp": functions_jungfrau1M.timestamp,
            "beam_energy": functions_jungfrau1M.beam_energy,
            "detector_distance": functions_jungfrau1M.detector_distance,
            "detector_data": functions_jungfrau1M.detector_data,
            "event_id": functions_jungfrau1M.event_id,
            "frame_id": functions_jungfrau1M.frame_id,
        }

    def initialize_event_handling_on_processing_node(
        self, node_rank: int, node_pool_size: int
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
        required_data: List[str] = self._monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="required_data",
            parameter_type=list,
            required=True,
        )

        self._required_data_extraction_funcs: Dict[
            str, Callable[[Dict[str, Dict[str, Any]]], Any]
        ] = drl_base.filter_data_extraction_funcs(
            self.data_extraction_funcs, required_data
        )

        self._event_info_to_append: Dict[str, Any] = {}

        calibration: bool = self._monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="calibration",
            parameter_type=bool,
            required=True,
        )
        self._event_info_to_append["calibration"] = calibration
        if calibration is True:
            calibration_dark_filenames: List[str] = self._monitor_params.get_param(
                group="data_retrieval_layer",
                parameter="calibration_dark_filenames",
                parameter_type=list,
                required=True,
            )
            calibration_gain_filenames: List[str] = self._monitor_params.get_param(
                group="data_retrieval_layer",
                parameter="calibration_gain_filenames",
                parameter_type=list,
                required=True,
            )
            calibration_photon_energy_kev: float = self._monitor_params.get_param(
                group="data_retrieval_layer",
                parameter="calibration_photon_energy_kev",
                parameter_type=float,
                required=True,
            )
            self._event_info_to_append[
                "calibration_algorithm"
            ] = calib_algs.Jungfrau1MCalibration(
                calibration_dark_filenames,
                calibration_gain_filenames,
                calibration_photon_energy_kev,
            )

        if "beam_energy" in required_data:
            self._event_info_to_append["beam_energy"] = self._monitor_params.get_param(
                group="data_retrieval_layer",
                parameter="fallback_beam_energy_in_eV",
                parameter_type=float,
                required=True,
            )
        if "detector_distance" in required_data:
            self._event_info_to_append[
                "detector_distance"
            ] = self._monitor_params.get_param(
                group="data_retrieval_layer",
                parameter="fallback_detector_distance_in_mm",
                parameter_type=float,
                required=True,
            )

    def event_generator(
        self,
        node_rank: int,
        node_pool_size: int,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Retrieves Jungfrau 1M file events.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        This Event Data Handler considers each detector frame, not each file, a
        separate event. The frames retrieved from the data source are split as evenly
        as possible across all the processing nodes. Each node ideally retrieves the
        same number of frames from the source. Only the last node might retrieve fewer
        frames, depending on how evenly the total number can be split.

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

            frame_numbers: List[numpy.ndarray] = [
                h5file["/frameNumber"][:] for h5file in h5files
            ]
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

        data_event: Dict[str, Dict[str, Any]] = {}
        data_event["data_extraction_funcs"] = self._required_data_extraction_funcs
        data_event["additional_info"] = {}
        data_event["additional_info"].update(self._event_info_to_append)

        entry: Dict[str, Any]
        for entry in frames_curr_node:
            data_event["additional_info"].update(entry)
            data_event["additional_info"]["num_frames_curr_node"] = len(
                frames_curr_node
            )

            yield data_event

    def open_event(self, event: Dict[str, Any]) -> None:
        """
        Opens a Jungfrau 1M file event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Since each detector frame in a file is considered a separate event, the event
        generator, which splits the frames across the processing nodes, takes care of
        opening and closing the files. This function therefore does nothing.

        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    def close_event(self, event: Dict[str, Any]) -> None:
        """
        Closes a Jungfrau 1M file event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.

        Since each detector frame in a file is considered a separate event, the event
        generator, which splits the frames across the processing nodes, takes care of
        opening and closing the files. This function therefore does nothing.


        Arguments:

            event: A dictionary storing the event data.
        """
        pass

    def get_num_frames_in_event(self, event: Dict[str, Any]) -> int:
        """
        Gets the number of frames in a Jungfrau 1M file event.

        This method overrides the corresponding method of the base class: please also
        refer to the documentation of that class for more information.


        Since each frame in a file is considered a separate event, this function always
        returns 1.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The number of frames in the event.
        """
        return 1
