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
# Copyright 2020 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Retrieval and handling of data events from the filesystem.

This module contains classes that retrieve and process data events from files written
on disk.
"""
import pathlib
import re
from typing import Any, Callable, Dict, Generator, List, TextIO, Tuple

import fabio  # type: ignore
import h5py  # type: ignore
import numpy  # type: ignore

from om.algorithms import calibration_algorithms as calib_algs
from om.data_retrieval_layer import base as drl_base
from om.data_retrieval_layer import functions_jungfrau1M, functions_pilatus, functions_eiger16M
from om.utils import parameters


class FilesBaseDataEventHandler(drl_base.OmDataEventHandler):
    def __init__(
        self, monitor_parameters: parameters.MonitorParams, source: str
    ) -> None:
        """
        Data event handler for events recovered from files.

        See documentation of the constructor of the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.__init.py__` .

        This class handles detector events recovered from files.
        """
        super(FilesBaseDataEventHandler, self).__init__(
            monitor_parameters=monitor_parameters, source=source,
        )

    def initialize_event_handling_on_collecting_node(
        self, node_rank: int, node_pool_size: int
    ) -> Any:
        """
        Initializes file event handling on the collecting node.

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.\
initialize_event_source`.

        There is no need to initialize a file source, so this function does nothing.
        """
        pass


class PilatusFilesDataEventHandler(FilesBaseDataEventHandler):
    """
    See documentation of the __init__ function.
    """

    def __init__(
        self, monitor_parameters: parameters.MonitorParams, source: str
    ) -> None:
        """
        Data event handler for Pilatus files read from the filesystem.

        See documentation of the constructor of the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler` .
        """
        super(PilatusFilesDataEventHandler, self).__init__(
            monitor_parameters=monitor_parameters, source=source,
        )

    @property
    def data_extraction_funcs(
        self,
    ) -> Dict[str, Callable[[Dict[str, Dict[str, Any]]], Any]]:
        """
        Retrieves the Data Extraction Functions for Pilatus files.

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.\
data_extraction_funcs`.
        """
        return {
            "timestamp": functions_pilatus.timestamp,
            "beam_energy": functions_pilatus.beam_energy,
            "detector_distance": functions_pilatus.detector_distance,
            "detector_data": functions_pilatus.detector_data,
            "event_id": functions_pilatus.event_id,
            "frame_id": functions_pilatus.frame_id,
        }

    def initialize_event_handling_on_collecting_node(
        self, node_rank: int, node_pool_size: int
    ) -> Any:
        """
        Initializes event handling on the collecting node for Pilatus files.

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.\
initialize_event_source`.

        There is no need to initialize the filesystem source, so this function does
        nothing.
        """
        pass

    def initialize_event_handling_on_processing_node(
        self, node_rank: int, node_pool_size: int
    ) -> Any:
        """
        Initializes event handling on the processing nodes for Pilatus files.

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.\
initialize_event_source`.
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
        if calibration is True:
            calibration_info_filename: str = self._monitor_params.get_param(
                group="data_retrieval_layer",
                parameter="calibration_filename",
                parameter_type=str,
            )
            self._event_info_to_append[
                "calibration_info_filename"
            ] = calibration_info_filename

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
        self, node_rank: int, node_pool_size: int,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Retrieves Pilatus data events to process from the filesystem.

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.event_generator`.

        The files to process are split evenly amongst the processing nodes, with the
        exception of the last node, which might get a lower number depending on how
        the number of files can is split.
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
        Opens an event retrieved from Pilatus files.

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.open_event`.

        For Pilatus data files, an event corresponds to the full content of a single
        Pilatus CBF file. This function makes the content of the file available in the
        'data' field of the 'event' object.
        """
        event["data"] = fabio.open(event["additional_info"]["full_path"])

    def close_event(self, event: Dict[str, Any]) -> None:
        """
        Closes an event retrieved from Pilatus files.

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.close_event` .

        Since an event corresponds to a CBF data file, which does not need to be closed,
        this function actually does nothing.
        """
        pass

    def get_num_frames_in_event(self, event: Dict[str, Any]) -> int:
        """
        Gets the number of frames in an event retrieved from Pilatus files.

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.\
get_num_frames_in_event`.

        For the Pilatus detector, an event corresponds to the content of a single CBF
        data file. Since the Pilatus detector writes one frame per file, this function
        always returns 1.

        Returns:

            int: the number of frames in the event.
        """
        return 1


class Eiger16MFilesDataEventHandler(FilesBaseDataEventHandler):
    """
    See documentation of the __init__ function.
    """

    def __init__(
        self, monitor_parameters: parameters.MonitorParams, source: str
    ) -> None:
        """
        Data event handler for Eiger files read from the filesystem.
        See documentation of the constructor of the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler` .
        """
        super(Eiger16MFilesDataEventHandler, self).__init__(
            monitor_parameters=monitor_parameters, source=source,
        )

    @property
    def data_extraction_funcs(
        self,
    ) -> Dict[str, Callable[[Dict[str, Dict[str, Any]]], Any]]:
        """
        Retrieves the Data Extraction Functions for Eiger files.
        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.\
data_extraction_funcs`.
        """
        return {
            "timestamp": functions_eiger16M.timestamp,
            "beam_energy": functions_eiger16M.beam_energy,
            "detector_distance": functions_eiger16M.detector_distance,
            "detector_data": functions_eiger16M.detector_data,
            "event_id": functions_eiger16M.event_id,
            "frame_id": functions_eiger16M.frame_id,
        }

    def initialize_event_handling_on_processing_node(
        self, node_rank: int, node_pool_size: int
    ) -> Any:
        """
        Initializes event handling on the processing nodes for Eiger files.

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.\
initialize_event_source`.
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
        if calibration is True:
            calibration_info_filename: str = self._monitor_params.get_param(
                group="data_retrieval_layer",
                parameter="calibration_filename",
                parameter_type=str,
            )
            self._event_info_to_append[
                "calibration_info_filename"
            ] = calibration_info_filename

        binning: Union[bool, None] = self._monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="binning",
            parameter_type=bool,
            required=False,
        )
        if binning is None:
            binning = False
        self._event_info_to_append["binning"] = binning

        binning_bad_pixel_map_fname: Union[str, None] = self._monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="binning_bad_pixel_map_filename",
            parameter_type=str,
        )
        if binning_bad_pixel_map_fname is not None:
            binning_bad_pixel_map_hdf5_path: Union[
                str, None
            ] = self._monitor_params.get_param(
                group="data_retrieval_layer",
                parameter="binning_bad_pixel_map_hdf5_path",
                parameter_type=str,
                required=True,
            )
        else:
            binning_bad_pixel_map_hdf5_path = None

        if binning_bad_pixel_map_fname is not None:
            try:
                map_hdf5_file_handle: Any
                with h5py.File(binning_bad_pixel_map_fname, "r") as map_hdf5_file_handle:
                    bad_pixel_map: Union[numpy.ndarray, None] = map_hdf5_file_handle[
                        binning_bad_pixel_map_hdf5_path
                    ][:]
            except (IOError, OSError, KeyError) as exc:
                exc_type, exc_value = sys.exc_info()[:2]
                # TODO: Fix type check
                raise RuntimeError(
                    "The following error occurred while reading the {0} field from"
                    "the {1} bad pixel map HDF5 file:"
                    "{2}: {3}".format(
                        binning_bad_pixel_map_fname,
                        binning_bad_pixel_map_hdf5_path,
                        exc_type.__name__,  # type: ignore
                        exc_value,
                    )
                ) from exc
        else:
            bad_pixel_map = None
        self._event_info_to_append["binning_bad_pixel_map"] = bad_pixel_map

        binning_min_good_pixel_count: Union[int, None] = self._monitor_params.get_param(
            group="data_retrieval_layer",
            parameter="binning_min_good_pixel_count",
            parameter_type=int,
            required=False,
        )
        if binning_min_good_pixel_count is None:
            binning_min_good_pixel_count = 4
        self._event_info_to_append["binning_min_good_pixel_count"] = binning_min_good_pixel_count

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
        self, node_rank: int, node_pool_size: int,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Retrieves Eiger data events to process from the filesystem.

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.event_generator`.

        The frames to process are split evenly amongst the processing nodes, with the
        exception of the last node, which might get a lower number depending on how
        the number of events can be split.
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
            filename: str = entry.strip()
            h5file: Any = h5py.File(filename, "r")
            num_frames: int = h5file["/entry/data/data"].shape[0]
            data_event["additional_info"]["h5file"] = h5file
            data_event["additional_info"]["full_path"] = str(
                pathlib.Path(filename).resolve()
            )
            data_event["additional_info"]["file_creation_time"] = numpy.float64(
                pathlib.Path(filename).stat().st_mtime
            )
            index: int
            for index in range(num_frames):
                data_event["additional_info"]["index"] = index
                yield data_event

    def open_event(self, event: Dict[str, Any]) -> None:
        """
        Opens an event retrieved from Jungfrau files.
        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.open_event`.
        """
        pass

    def close_event(self, event: Dict[str, Any]) -> None:
        """
        Closes an event retrieved from Jungfrau files.
        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.close_event` .
        """
        pass

    def get_num_frames_in_event(self, event: Dict[str, Any]) -> int:
        """
        Gets the number of frames in an event retrieved from Jungfrau files.
        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.\
get_num_frames_in_event`.
        Returns:
            int: the number of frames in the event.
        """
        return 1


class Jungfrau1MFilesDataEventHandler(FilesBaseDataEventHandler):
    """
    See documentation of the __init__ function.
    """

    def __init__(
        self, monitor_parameters: parameters.MonitorParams, source: str
    ) -> None:
        """
        Data event handler for Jungfrau files read from the filesystem.
        See documentation of the constructor of the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler` .
        """
        super(Jungfrau1MFilesDataEventHandler, self).__init__(
            monitor_parameters=monitor_parameters, source=source,
        )

    @property
    def data_extraction_funcs(
        self,
    ) -> Dict[str, Callable[[Dict[str, Dict[str, Any]]], Any]]:
        """
        Retrieves the Data Extraction Functions for Jungfrau files.
        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.\
data_extraction_funcs`.
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
        Initializes event handling on the processing nodes for Jungfrau files.

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.\
initialize_event_source`.
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
        self, node_rank: int, node_pool_size: int,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Retrieves Jungfrau data events to process from the filesystem.

        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.event_generator`.

        The frames to process are split evenly amongst the processing nodes, with the
        exception of the last node, which might get a lower number depending on how
        the number of events can be split.
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
        Opens an event retrieved from Jungfrau files.
        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.open_event`.
        """
        pass

    def close_event(self, event: Dict[str, Any]) -> None:
        """
        Closes an event retrieved from Jungfrau files.
        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.close_event` .
        """
        pass

    def get_num_frames_in_event(self, event: Dict[str, Any]) -> int:
        """
        Gets the number of frames in an event retrieved from Jungfrau files.
        See documentation of the function in the base class:
        :func:`~om.data_retrieval_layer.base.DataEventHandler.\
get_num_frames_in_event`.
        Returns:
            int: the number of frames in the event.
        """
        return 1
