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

import pathlib
import sys
import time
from typing import Any, Dict, List, NamedTuple, Set, TextIO, Tuple, TypedDict, Union

import h5py  # type: ignore
import hdf5plugin
import numpy
from numpy.typing import DTypeLike, NDArray

from om.algorithms.crystallography import TypePeakList
from om.lib.exceptions import OmHdf5UnsupportedDataFormat
from om.lib.parameters import get_parameter_from_parameter_group
from om.lib.rich_console import console, get_current_timestamp


class TypeFrameListData(NamedTuple):
    """
    This named tuple is used to store frame data which is then written to frames.txt
    file.

    Arguments:

        timestamp: The timestamp of the frame.

        event_id: The event ID of the frame.

        frame_is_hit: A flag indicating whether the frame is a hit frame.

        filename: The name of the file containing the frame.

        index_in_file: The index of the frame in the file.

        num_peaks: The number of peaks in the frame.

        average_intensity: The average intensity of the peaks in the frame.
    """

    timestamp: numpy.float64
    event_id: Union[str, None]
    frame_is_hit: int
    filename: str
    index_in_file: int
    num_peaks: int
    average_intensity: numpy.float64


class TypeClassSumData(TypedDict):
    """
    A dictionary storing the number of detector frames belonging to a certain data
    class, their sum and the virtual peak powder.

    Arguments:

        num_frames: The number of detector frames belonging to a certain data class.

        sum_frames: The sum of the detector frames belonging to a certain data class.

        peak_powder: The virtual peak powder of a certain data class.
    """

    num_frames: int
    sum_frames: NDArray[numpy.float_]
    peak_powder: NDArray[numpy.float_]


class CheetahStatusFileWriter:
    """
    See documentation for the `__init__` function.
    """

    def __init__(
        self,
        *,
        parameters: Dict[str, Any],
    ) -> None:
        """
        Cheetah status file writer.

        This class writes a status file that the Cheetah GUI can inspect.

        Arguments:

            parameters: A set of OM configuration parameters collected together in a
                parameter group. The parameter group must contain the following
                entries:

                * `processed_directory`

        """
        directory_for_processed_data: str = get_parameter_from_parameter_group(
            group=parameters,
            parameter="processed_directory",
            parameter_type=str,
            required=True,
        )
        self._status_filename: pathlib.Path = (
            pathlib.Path(directory_for_processed_data).resolve() / "status.txt"
        )
        self._start_time: float = time.time()

    def update_status(
        self,
        *,
        status: str = "",
        num_frames: int = 0,
        num_hits: int = 0,
    ) -> None:
        """
        Writes a status file that the Cheetah GUI can inspect.

        Arguments:

            status: A string describing the current status of the Cheetah processing.

            num_frames: The number of detector frames processed so far.

            num_hits: The number of hits found so far.
        """
        fh: TextIO
        time_string: str = time.strftime("%a %b %d %H:%M:%S %Y")
        with open(self._status_filename, "w") as fh:
            fh.write("# Cheetah status\n")
            fh.write(f"Update time: {time_string}\n")
            dt: int = int(time.time() - self._start_time)
            hours: int
            minutes: int
            hours, minutes = divmod(dt, 3600)
            seconds: int
            minutes, seconds = divmod(minutes, 60)
            fh.write(f"Elapsed time: {hours}hr {minutes}min {seconds}sec\n")
            fh.write(f"Status: {status}\n")
            fh.write(f"Frames processed: {num_frames}\n")
            fh.write(f"Number of hits: {num_hits}\n")


class CheetahListFilesWriter:
    """
    See documentation for the `__init__` function.
    """

    def __init__(
        self,
        *,
        cheetah_parameters: Dict[str, Any],
    ) -> None:
        """
        Cheetah list files writer.

        This class writes "frames.txt", "cleaned.txt", "events.lst", "hits.lst" and
        "peaks.txt" files required by the Cheetah GUI.

        #TODO: describe the files

        Arguments:
            cheetah_parameters: The Cheetah parameters.
        """
        processed_directory: pathlib.Path = pathlib.Path(
            get_parameter_from_parameter_group(
                group=cheetah_parameters,
                parameter="processed_directory",
                parameter_type=str,
                required=True,
            )
        ).resolve()

        self._frames_filename: pathlib.Path = processed_directory / "frames.txt"
        self._frames_file: TextIO = open(self._frames_filename, "w")
        self._frames_file.write(
            "# timestamp, event_id, hit, filename, index, num_peaks, ave_intensity\n"
        )

        self._cleaned_filename: pathlib.Path = processed_directory / "cleaned.txt"

        self._peaks_filename: pathlib.Path = processed_directory / "peaks.txt"
        self._peaks_file: TextIO = open(self._peaks_filename, "w")
        self._peaks_file.write(
            "event_id, num_peaks, fs, ss, intensity, num_pixels, max_pixel_intensity, "
            "snr\n"
        )

        self._events_filename: pathlib.Path = processed_directory / "events.lst"
        self._events_file: TextIO = open(self._events_filename, "w")

        self._hits_filename: pathlib.Path = processed_directory / "hits.lst"
        self._hits_file: TextIO = open(self._hits_filename, "w")

        self._frame_list: List[TypeFrameListData] = []

    def add_frame(
        self,
        *,
        frame_data: TypeFrameListData,
        peak_list: TypePeakList,
    ) -> None:
        """
        Adds a frame to the list files.

        Arguments:
            frame_data: The frame data.

            peak_list: The peak list.
        """
        self._frame_list.append(frame_data)

        # Write frame to frames.txt
        self._frames_file.write(
            f"{frame_data.timestamp}, {frame_data.event_id}, "
            f"{frame_data.frame_is_hit}, {frame_data.filename}, "
            f"{frame_data.index_in_file}, {frame_data.num_peaks}, "
            f"{frame_data.average_intensity}\n"
        )

        # Write event ID to events.lst
        self._events_file.write(f"{frame_data.event_id}\n")

        if frame_data.frame_is_hit:
            # Write event ID to hits.lst
            self._hits_file.write(f"{frame_data.event_id}\n")

            # Write peaks to peaks.txt
            self._peaks_file.writelines(
                (
                    f"{frame_data.event_id}, "
                    f"{peak_list['num_peaks']}, "
                    f"{peak_list['fs'][i]}, "
                    f"{peak_list['ss'][i]}, "
                    f"{peak_list['intensity'][i]}, "
                    f"{peak_list['num_pixels'][i]}, "
                    f"{peak_list['max_pixel_intensity'][i]}, "
                    f"{peak_list['snr'][i]}\n"
                    for i in range(peak_list["num_peaks"])
                )
            )

    def flush_files(self) -> None:
        """
        Flushes the list files.
        """
        self._frames_file.flush()
        self._peaks_file.flush()
        self._events_file.flush()
        self._hits_file.flush()

    def sort_frames_and_close_files(self) -> None:
        """
        Sorts the frames by event ID, writes sorted data to frames.txt, cleaned.txt and
        events.lst and closes all list files.
        """
        frame_list: List[TypeFrameListData] = sorted(self._frame_list)
        self._frames_file.close()
        self._events_file.close()
        self._hits_file.close()
        self._peaks_file.close()

        fh: TextIO
        with open(self._events_filename, "w") as fh:
            frame: TypeFrameListData
            for frame in frame_list:
                fh.write(f"{frame.event_id}\n")
        with open(self._frames_filename, "w") as fh:
            fh.write(
                "# timestamp, event_id, hit, filename, index, num_peaks, "
                "ave_intensity\n"
            )
            for frame in frame_list:
                fh.write(
                    f"{frame.timestamp}, {frame.event_id}, {frame.frame_is_hit}, "
                    f"{frame.filename}, {frame.index_in_file}, {frame.num_peaks}, "
                    f"{frame.average_intensity}\n"
                )
        with open(self._cleaned_filename, "w") as fh:
            fh.write(
                "# timestamp, event_id, hit, filename, index, num_peaks, "
                "ave_intensity\n"
            )
            for frame in frame_list:
                if frame.frame_is_hit:
                    fh.write(
                        f"{frame.timestamp}, {frame.event_id}, {frame.frame_is_hit}, "
                        f"{frame.filename}, {frame.index_in_file}, {frame.num_peaks}, "
                        f"{frame.average_intensity}\n"
                    )


class CheetahClassSumsAccumulator:
    """
    See documentation for the `__init__` function.
    """

    def __init__(
        self,
        *,
        cheetah_parameters: Dict[str, Any],
        num_classes: int = 2,
    ) -> None:
        """
        Cheetah class sums accumulator.

        This class computes the sums of detector frames belonging to a certain data
        class and its virtual peak powder.

        Arguments:
            cheetah_parameters: The Cheetah parameters.

            num_classes: The number of data classes.
        """
        self._sum_sending_interval: int = get_parameter_from_parameter_group(
            group=cheetah_parameters,
            parameter="class_sums_sending_interval",
            parameter_type=int,
            default=-1,
        )
        self._sum_sending_counter: int = 0
        self._num_classes: int = num_classes

    def add_frame(
        self,
        *,
        class_number: int,
        frame_data: Union[NDArray[numpy.float_], NDArray[numpy.int_]],
        peak_list: TypePeakList,
    ) -> None:
        """
        Adds a detector frame to the class sums.

        Arguments:
            class_number: The class number of the frame.

            frame_data: The detector frame data.

            peak_list: The list of peaks found in the detector frame.
        """
        if self._sum_sending_interval == -1:
            return
        if self._sum_sending_counter == 0:
            self._sums: List[TypeClassSumData] = [
                {
                    "num_frames": 0,
                    "sum_frames": numpy.zeros(frame_data.shape),
                    "peak_powder": numpy.zeros(frame_data.shape),
                }
                for class_number in range(self._num_classes)
            ]
        self._sums[class_number]["num_frames"] += 1
        self._sums[class_number]["sum_frames"] += frame_data

        peak_fs: float
        peak_ss: float
        peak_value: float
        for peak_fs, peak_ss, peak_value in zip(
            peak_list["fs"], peak_list["ss"], peak_list["intensity"]
        ):
            self._sums[class_number]["peak_powder"][
                int(round(peak_ss)), int(round(peak_fs))
            ] += peak_value

        self._sum_sending_counter += 1

    def get_sums_for_sending(
        self, disregard_counter: bool = False
    ) -> Union[None, List[TypeClassSumData]]:
        """
        Returns the class sums if the sending interval has been reached or if the
        `disregard_counter` argument is `True`. Otherwise, returns `None`.

        Arguments:
            disregard_counter: If `True`, the sending counter is disregarded and the
                class sums are returned.

        Returns:
            The class sums if the sending interval has been reached or if the
            `disregard_counter` argument is `True`. Otherwise, `None`.
        """
        if self._sum_sending_counter >= self._sum_sending_interval or (
            self._sum_sending_counter > 0 and disregard_counter
        ):
            self._sum_sending_counter = 0
            return self._sums
        else:
            return None


class CheetahClassSumsCollector:
    """
    See documentation for the `__init__` function.
    """

    def __init__(
        self,
        *,
        cheetah_parameters: Dict[str, Any],
        num_classes: int = 2,
    ) -> None:
        """
        Cheetah class sums collector.

        This class collects the class sums from the different processes and calculates
        the total class sums. The class sums are then saved to HDF5 files periodically.

        Arguments:
            cheetah_parameters: The Cheetah parameters.

            num_classes: The number of data classes.
        """
        self._num_classes: int = num_classes

        # Sum HDF5 writers
        self._write_class_sums: bool = get_parameter_from_parameter_group(
            group=cheetah_parameters,
            parameter="write_class_sums",
            parameter_type=bool,
            required=True,
        )
        if self._write_class_sums:
            class_number: int
            self._sum_writers: Dict[int, SumHDF5Writer] = {
                class_number: SumHDF5Writer(
                    powder_class=class_number,
                    cheetah_parameters=cheetah_parameters,
                )
                for class_number in range(self._num_classes)
            }
            self._class_sum_update_interval: int = get_parameter_from_parameter_group(
                group=cheetah_parameters,
                parameter="class_sums_update_interval",
                parameter_type=int,
                required=True,
            )
            self._class_sum_update_counter: int = 0

    def add_sums(
        self,
        *,
        class_sums: List[TypeClassSumData],
    ) -> None:
        """
        Adds class sums to the collector. If the update interval has been reached, the
        class sums are saved to HDF5 files.

        Arguments:
            class_sums: The class sums to be added.
        """

        if self._class_sum_update_counter == 0:
            self._sums: List[TypeClassSumData] = class_sums
        else:
            class_number: int
            for class_number in range(len(class_sums)):
                key: str
                for key in class_sums[0]:
                    # TODO: fix mypy error:
                    self._sums[class_number][key] += class_sums[class_number][key]  # type: ignore  # noqa: E501

        self._class_sum_update_counter += 1
        if self._class_sum_update_counter % self._class_sum_update_interval == 0:
            self.save_sums()

    def save_sums(self) -> None:
        """
        Saves the class sums to HDF5 files.

        This function is called automatically when the update interval has been
        reached. It can also be called manually.
        """
        if self._write_class_sums and self._class_sum_update_counter > 0:
            class_number: int
            for class_number in range(self._num_classes):
                self._sum_writers[class_number].write_sums(
                    data=self._sums[class_number]
                )


class HDF5Writer:
    """
    See documentation of the `__init__` function.
    """

    def __init__(  # noqa: C901
        self,
        *,
        node_rank: int,
        cheetah_parameters: Dict[str, Any],
    ) -> None:
        """
        HDF5 file writer for Cheetah.

        This class creates HDF5 data files to store the information processed by the
        Cheetah software package. For each event, this class saves into an HDF5 file
        a processed detector data frame, the list of Bragg peaks detected in the
        frame, and some additional information (timestamp, beam energy, detector
        distance, pump laser state).

        Arguments:

            cheetah_parameters: A set of OM configuration parameters collected together
                in a parameter group. The parameter group must contain the following
                entries:

                directory_for_processed_data: A relative or absolute path to the
                    directory where the output files will be written.

                compression: The compression filter to be applied to the data in the
                    output file.

                hdf5_fields: A dictionary storing information about the internal HDF5
                    path where each data entry will be written.

                    * The keys in the dictionary must store the names of data entries
                      to write.

                    * The corresponding dictionary values must contain the internal
                      HDF5 paths where the entries will be written.

                processed_filename_prefix: A string that will be prepended to the name
                    of the output files. Optional. If the value of this entry is None,
                    the string 'processed_' will be used as prefix. Defaults to None.

                processed_filename_extension: An extension string that will appended to
                    the name of the output files. Optional. If the value of this entry
                    is None, the string 'h5' will be used as extension. Defaults to
                    None.

                compression_opts: The compression level to be used, if data compression
                    is applied to the output files. The information in this entry only
                    applies if the corresponding `compression` entry is not None,
                    otherwise, it is ignored. Optional. If the value of this entry is
                    None, the compression level is set to 4. Defaults to None.

                compression_shuffle: Whether the `shuffle` filter is applied. If the
                    value of this entry is True, the filter is applied to the data
                    being written, otherwise it is not. Defaults to None.

                max_num_peaks: The maximum number of detected Bragg peaks that are
                    written in the HDF5 file for each event. Optional. If the value
                    of this entry is None, only the first 1024 peaks detected in each
                    frame are be written to the output file. Defaults to None.

            node_rank: The rank of the OM node that writes the data in the output
                files.
        """
        # Output file
        directory_for_processed_data: str = get_parameter_from_parameter_group(
            group=cheetah_parameters,
            parameter="processed_directory",
            parameter_type=str,
            required=True,
        )
        processed_filename_prefix: Union[
            str, None
        ] = get_parameter_from_parameter_group(
            group=cheetah_parameters,
            parameter="processed_filename_prefix",
            parameter_type=str,
        )
        if processed_filename_prefix is None:
            processed_filename_prefix = "processed"
        self._processed_filename: pathlib.Path = (
            pathlib.Path(directory_for_processed_data).resolve()
            / f"{processed_filename_prefix}_{node_rank}.inprogress"
        )
        processed_filename_extension: Union[
            str, None
        ] = get_parameter_from_parameter_group(
            group=cheetah_parameters,
            parameter="processed_filename_extension",
            parameter_type=str,
        )
        if processed_filename_extension is None:
            processed_filename_extension = "h5"
        self._processed_filename_extension: str = f".{processed_filename_extension}"

        # HDF5 fields
        self._hdf5_fields = get_parameter_from_parameter_group(
            group=cheetah_parameters,
            parameter="hdf5_fields",
            parameter_type=dict,
        )

        # Data format
        self._data_type: Union[
            str, DTypeLike, None
        ] = get_parameter_from_parameter_group(
            group=cheetah_parameters,
            parameter="hdf5_file_data_type",
            parameter_type=str,
        )

        # Compression
        compression: Union[str, None] = get_parameter_from_parameter_group(
            group=cheetah_parameters,
            parameter="hdf5_file_compression",
            parameter_type=str,
        )
        if compression not in ("gzip", "bitshuffle_with_zstd"):
            # TODO: print a warning or an error for unsupported compression type
            # If a warning say no compression will be applied
            compression = None
        if compression == "gzip":
            compression_level: int = get_parameter_from_parameter_group(
                group=cheetah_parameters,
                parameter="hdf5_file_gzip_compression_level",
                parameter_type=int,
                default=4,
            )
            self._compression_kwargs: Dict[str, Any] = {
                "compression": "gzip",
                "compression_opts": compression_level,
            }
        elif compression == "bitshuffle_with_zstd":
            compression_level: int = get_parameter_from_parameter_group(
                group=cheetah_parameters,
                parameter="hdf5_file_zstd_compression_level",
                parameter_type=int,
                default=3,
            )
            self._compression_kwargs = dict(
                hdf5plugin.Bitshuffle(cname="zstd", clevel=compression_level)
            )
        else:
            self._compression_kwargs = {}
        self._compression_kwargs["shuffle"] = get_parameter_from_parameter_group(
            group=cheetah_parameters,
            parameter="hdf5_file_compression_shuffle",
            parameter_type=bool,
            default=False,
        )

        # Max number of peaks
        self._max_num_peaks: int = get_parameter_from_parameter_group(
            group=cheetah_parameters,
            parameter="hdf5_file_max_num_peaks",
            parameter_type=int,
            default=1024,
        )

        self._h5file: Any = None
        self._resizable_datasets: Dict[str, Any] = {}
        self._extra_groups: Dict[str, Any] = {}
        self._requested_datasets: Set[str] = set(self._hdf5_fields.keys())
        self._num_frames: int = 0

    def _create_file_and_datasets(self, *, processed_data: Dict[str, Any]) -> None:
        # This function is called when the first data comes. It opens output hdf5 file
        # and creates all requested datasets.
        self._h5file = h5py.File(self._processed_filename, "w")
        if (
            "detector_data" in processed_data
            and "detector_data" in self._requested_datasets
        ):
            if self._data_type is None:
                self._data_type = processed_data["detector_data"].dtype
            self._resizable_datasets["detector_data"] = self._h5file.create_dataset(
                name=self._hdf5_fields["detector_data"],
                shape=(0,) + processed_data["detector_data"].shape,
                maxshape=(None,) + processed_data["detector_data"].shape,
                dtype=self._data_type,
                chunks=(1,) + processed_data["detector_data"].shape,
                **self._compression_kwargs,
            )

        if "event_id" in self._hdf5_fields.keys():
            self._resizable_datasets["event_id"] = self._h5file.create_dataset(
                name=self._hdf5_fields["event_id"],
                shape=(0,),
                maxshape=(None,),
                dtype=h5py.special_dtype(vlen=str),
            )
        if "optical_laser_active" in self._hdf5_fields.keys():
            self._resizable_datasets[
                "optical_laser_active"
            ] = self._h5file.create_dataset(
                name=self._hdf5_fields["optical_laser_active"],
                shape=(0,),
                maxshape=(None,),
                dtype=numpy.bool_,
            )

        # Creating all requested 1D float64 datasets:
        key: str
        for key in ("timestamp", "beam_energy", "pixel_size", "detector_distance"):
            if key in self._hdf5_fields.keys():
                self._resizable_datasets[key] = self._h5file.create_dataset(
                    name=self._hdf5_fields[key],
                    shape=(0,),
                    maxshape=(None,),
                    dtype=numpy.float64,
                )
        if "peak_list" in self._hdf5_fields.keys():
            self._resizable_datasets.update(
                {
                    "npeaks": self._h5file.create_dataset(
                        name=self._hdf5_fields["peak_list"] + "/nPeaks",
                        shape=(0,),
                        maxshape=(None,),
                        dtype=numpy.int64,
                    ),
                    "fs": self._h5file.create_dataset(
                        name=self._hdf5_fields["peak_list"] + "/peakXPosRaw",
                        shape=(0, self._max_num_peaks),
                        maxshape=(None, self._max_num_peaks),
                        dtype=numpy.float32,
                    ),
                    "ss": self._h5file.create_dataset(
                        name=self._hdf5_fields["peak_list"] + "/peakYPosRaw",
                        shape=(0, self._max_num_peaks),
                        maxshape=(None, self._max_num_peaks),
                        dtype=numpy.float32,
                    ),
                    "intensity": self._h5file.create_dataset(
                        name=self._hdf5_fields["peak_list"] + "/peakTotalIntensity",
                        shape=(0, self._max_num_peaks),
                        maxshape=(None, self._max_num_peaks),
                        dtype=numpy.float32,
                    ),
                    "num_pixels": self._h5file.create_dataset(
                        name=self._hdf5_fields["peak_list"] + "/peakNPixels",
                        shape=(0, self._max_num_peaks),
                        maxshape=(None, self._max_num_peaks),
                        dtype=numpy.float32,
                    ),
                    "max_pixel_intensity": self._h5file.create_dataset(
                        name=self._hdf5_fields["peak_list"] + "/peakMaximumValue",
                        shape=(0, self._max_num_peaks),
                        maxshape=(None, self._max_num_peaks),
                        dtype=numpy.float32,
                    ),
                    "snr": self._h5file.create_dataset(
                        name=self._hdf5_fields["peak_list"] + "/peakSNR",
                        shape=(0, self._max_num_peaks),
                        maxshape=(None, self._max_num_peaks),
                        dtype=numpy.float32,
                    ),
                }
            )

        if "lcls_extra" in self._hdf5_fields.keys():
            self._extra_groups["lcls_extra"] = self._h5file.create_group(
                self._hdf5_fields["lcls_extra"]
            )

        extra_group_name: str
        for extra_group_name in self._extra_groups:
            if (
                extra_group_name in processed_data
                and extra_group_name in self._requested_datasets
            ):
                self._create_extra_datasets(
                    group_name=extra_group_name,
                    extra_data=processed_data[extra_group_name],
                )

    def _create_extra_datasets(
        self, *, group_name: str, extra_data: Dict[str, Any]
    ) -> None:
        # Creates empty dataset in the extra data group for each item in extra_data
        # dict using dict keys as dataset names. Supported data types: numpy arrays,
        # str, float, int and bool
        key: str
        value: Any
        for key, value in extra_data.items():
            if isinstance(value, numpy.ndarray):
                self._resizable_datasets[group_name + "/" + key] = self._extra_groups[
                    group_name
                ].create_dataset(
                    name=key,
                    shape=(0, *value.shape),
                    maxshape=(None, *value.shape),
                    dtype=value.dtype,
                )
            elif isinstance(value, str):
                self._resizable_datasets[group_name + "/" + key] = self._extra_groups[
                    group_name
                ].create_dataset(
                    name=key,
                    shape=(0,),
                    maxshape=(None,),
                    dtype=h5py.special_dtype(vlen=str),
                )
            elif (
                numpy.issubdtype(type(value), numpy.integer)
                or numpy.issubdtype(type(value), numpy.floating)
                or numpy.issubdtype(type(value), numpy.bool_)
            ):
                self._resizable_datasets[group_name + "/" + key] = self._extra_groups[
                    group_name
                ].create_dataset(
                    name=key,
                    shape=(0,),
                    maxshape=(None,),
                    dtype=type(value),
                )
            else:
                raise OmHdf5UnsupportedDataFormat(
                    f"Cannot write the '{key}' data entry into the output HDF5: "
                    "its format is not supported."
                )

    def _write_extra_data(self, *, group_name: str, extra_data: Dict[str, Any]) -> None:
        key: str
        value: Any
        for key, value in extra_data.items():
            self._extra_groups[group_name][key][self._num_frames - 1] = extra_data[key]

    def write_frame(self, *, processed_data: Dict[str, Any]) -> None:  # noqa: C901
        """
        Writes data into an HDF5 data file.

        This function writes the provided data into the HDF5 data file, assuming that
        all the data belongs to the same processed data event.

        Arguments:

            processed_data: A dictionary containing the data to write into the HDF5
                file.
        """
        # Datasets to write:
        fields: Set[str] = set(processed_data.keys()) & self._requested_datasets

        # When the first data comes create output file and all requested datasets:
        if self._num_frames == 0:
            self._create_file_and_datasets(processed_data=processed_data)

        self._resize_datasets()
        frame_num: int = self._num_frames - 1
        dataset_dict_key: str
        for dataset_dict_key in (
            "detector_data",
            "event_id",
            "timestamp",
            "beam_energy",
            "detector_distance",
            "optical_laser_active",
        ):
            if dataset_dict_key in fields:
                self._resizable_datasets[dataset_dict_key][frame_num] = processed_data[
                    dataset_dict_key
                ]

        if "peak_list" in fields:
            peak_list: TypePeakList = processed_data["peak_list"]
            n_peaks: int = min(peak_list["num_peaks"], self._max_num_peaks)
            self._resizable_datasets["npeaks"][frame_num] = n_peaks
            peak_dict_key: str
            for peak_dict_key in (
                "fs",
                "ss",
                "intensity",
                "num_pixels",
                "max_pixel_intensity",
                "snr",
            ):
                self._resizable_datasets[peak_dict_key][
                    frame_num, :n_peaks
                ] = peak_list[peak_dict_key][:n_peaks]

        for extra_group_name in self._extra_groups:
            if extra_group_name in fields:
                self._write_extra_data(
                    group_name=extra_group_name,
                    extra_data=processed_data[extra_group_name],
                )

    def close(self) -> None:
        """
        Closes the file currently being written.
        """
        if self._h5file is None:
            return
        self._h5file.close()
        final_filename: pathlib.Path = self._processed_filename.with_suffix(
            self._processed_filename_extension
        )
        self._processed_filename.rename(final_filename)
        console.print(
            f"{get_current_timestamp()} {self._num_frames} frames saved in "
            f"{final_filename} file."
        )
        sys.stdout.flush()

    def get_current_filename(self) -> pathlib.Path:
        """
        Retrieves the path to the file currently being written.

        Returns:

            The path to the file currently being written.
        """
        return self._processed_filename

    def get_num_written_frames(self) -> int:
        """
        Retrieves the number frames that have already been saved into the current file.

        Returns:

            The number of frames already written in the current file.
        """
        return self._num_frames - 1

    def _resize_datasets(self, *, extension_size: int = 1) -> None:
        # Extends all resizable datasets by the specified extension size
        dataset: Any
        for dataset in self._resizable_datasets.values():
            dataset.resize(self._num_frames + extension_size, axis=0)
        self._num_frames += extension_size


class SumHDF5Writer:
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        powder_class: int,
        cheetah_parameters: Dict[str, Any],
    ) -> None:
        """
        HDF5 writer for sum of frames.

        This class creates HDF5 data files to store the aggregated detector information
        processed by the Cheetah software package. It saves sums of detector data
        frames into HDF5 files,together with virtual powder patterns created using the
        Bragg peaks detected in the frames.

        Arguments:

            powder_class: A unique identifier for the sum of frames and virtual powder
                pattern being saved.

            cheetah_parameters: A dictionary containing the Cheetah parameters.
        """
        sum_filename_prefix: str = get_parameter_from_parameter_group(
            group=cheetah_parameters,
            parameter="class_sum_filename_prefix",
            parameter_type=str,
            default="processed",
        )
        directory_for_processed_data: str = get_parameter_from_parameter_group(
            group=cheetah_parameters,
            parameter="processed_directory",
            parameter_type=str,
            required=True,
        )

        self._filename: pathlib.Path = (
            pathlib.Path(directory_for_processed_data).resolve()
            / f"{sum_filename_prefix}-detector0-class{powder_class}-sum.h5"
        )

    def _create_hdf5_file_and_datasets(self, *, data_shape: Tuple[int, ...]) -> None:
        # Creates the HDF5 file and all datasets
        self._h5file: Any = h5py.File(self._filename, "w")
        self._h5file.create_dataset(
            name="/data/nframes",
            shape=(1,),
            dtype=numpy.int64,
        )
        self._h5file.create_dataset(
            name="/data/data",
            shape=data_shape,
            dtype=numpy.float64,
        )
        self._h5file.create_dataset(
            name="/data/peakpowder",
            shape=data_shape,
            dtype=numpy.float64,
        )
        self._h5file.close()

    def write_sums(
        self,
        *,
        data: TypeClassSumData,
    ) -> None:
        """
        Writes aggregated detector frame data into an HDF5 file.

        Arguments:

            data: A dictionary containing the aggregated detector frame data.
        """
        if not self._filename.exists():
            self._create_hdf5_file_and_datasets(data_shape=data["sum_frames"].shape)
        attempt: int
        for attempt in range(5):
            # If file is opened by someone else try 5 times during 10 seconds and exit
            try:
                self._h5file = h5py.File(self._filename, "r+")
                self._h5file["/data/nframes"][0] = data["num_frames"]
                self._h5file["/data/data"][:] = data["sum_frames"]
                if data["peak_powder"] is not None:
                    self._h5file["/data/peakpowder"][:] = data["peak_powder"]
                self._h5file.close()
                return
            except OSError:
                time.sleep(2)
                ...
        console.print(
            f"{get_current_timestamp()} Another application is reading the file "
            f"{self._filename} exclusively. Five attempts to open the files "
            "failed. Cannot update the file.",
            style="warning",
        )
