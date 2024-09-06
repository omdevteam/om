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
Cheetah classes and functions.

This module contains classes and functions used by Cheetah, a data-processing program
for Serial X-ray Crystallography, based on OM but not designed to be run in real time.
"""


import pathlib
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set, TextIO, Tuple, Union, cast

import h5py  # type: ignore
import hdf5plugin  # type: ignore
import numpy
from numpy.typing import NDArray
from pydantic import BaseModel, Field, ValidationError, model_validator
from typing_extensions import Self

from om.algorithms.common import PeakList
from om.lib.exceptions import (
    OmConfigurationFileSyntaxError,
    OmHdf5UnsupportedDataFormat,
)
from om.lib.logging import log


class _Hdf5Compression(str, Enum):
    gzip = "gzip"
    bitshuffle_with_zstd = "bitshuffle_with_zstd"
    none = "none"


class _CheetahFileWriterParameters(BaseModel):
    processed_directory: str


class _MonitorFileWriterParameters(BaseModel):
    cheetah: _CheetahFileWriterParameters


class _CheetahSumsAccumulatorParameters(BaseModel):
    class_sums_sending_interval: int = Field(default=-1)


class _MonitorSumsAccumulatorParameters(BaseModel):
    cheetah: _CheetahSumsAccumulatorParameters


class _CheetahClassSumsCollectorParameters(BaseModel):
    write_class_sums: bool
    class_sums_update_interval: int

    @model_validator(mode="after")
    def check_sums_update_interval(self) -> Self:
        if self.write_class_sums and self.class_sums_update_interval is None:
            raise ValueError(
                "If writing of the class sums is requested from Cheetah, the following"
                "entry must be present in the cheetah section of the configuration"
                "file:  class_sums_update_interval "
            )
        return self


class _MonitorClassSumsCollectorParameters(BaseModel):
    cheetah: _CheetahClassSumsCollectorParameters


class _CheetahHdf5WriterParameters(BaseModel):
    processed_directory: str
    processed_filename_prefix: str = Field(default="processed")
    processed_filename_extension: str = Field(default="h5")
    hdf5_fields: dict[str, str]
    hdf5_file_data_type: str
    hdf5_file_compression: _Hdf5Compression = Field(default="none")
    hdf5_file_gzip_compression_level: int = Field(default=4)
    hdf5_file_zstd_compression_level: int = Field(default=3)
    hdf5_file_compression_shuffle: bool = Field(default=False)
    hdf5_file_max_num_peaks: int = Field(default=1024)


class _MonitorHdf5WriterParameters(BaseModel):
    cheetah: _CheetahHdf5WriterParameters


class _CheetahSumHDF5WriterParameters(BaseModel):
    processed_directory: str
    processed_filename_prefix: str = Field(default="processed")


class _MonitorSumHDF5WriterParameters(BaseModel):
    cheetah: _CheetahSumHDF5WriterParameters


@dataclass
class ClassSumData:
    """
    Cheetah data class sum data.

    A dictionary storing the number of detector frames belonging to a specific data
    class, their sum, and the virtual powder pattern generated from the Bragg peaks
    detected in them.

    Attributes:

        num_frames: The number of detector frames belonging to the data class.

        sum_frames: The sum of the detector frames belonging to the class.

        peak_powder: The virtual powder pattern for the data class.
    """

    num_frames: int
    sum_frames: NDArray[numpy.float_]
    peak_powder: NDArray[numpy.float_]


@dataclass(order=True)
class FrameListData:
    """
    Cheetah frame list data.

    This named tuple is used to store the detector frame data which is later written
    into the `frames.txt` file.

    Attributes:

        timestamp: The timestamp of the frame.

        event_id: A unique identifier for the event attached to the frame.

        frame_is_hit: A flag indicating whether the event attached to the frame is
            labelled as a hit.

        filename: The name of the file containing the frame.

        index_in_file: The index of the frame in the file.

        num_peaks: The number of peaks in the frame.

        average_intensity: The average intensity of the Bragg peaks detected in the
            frame.
    """

    timestamp: numpy.float64
    event_id: Optional[str]
    frame_is_hit: int
    filename: str
    index_in_file: int
    num_peaks: int
    average_intensity: numpy.float64

    def __post_init__(self) -> None:
        self.sort_index = self.timestamp


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

        This class stores information about the current status of data processing in
        Cheetah (number of processed frames, number of hits, etc.).

        After the class has been initialized, the information it stores can be updated
        with new data processing statistics. Upon receiving them, this class writes
        the updated data processing information to a "status" file, which can then
        be inspected by external programs.

        Arguments:

            parameters: A set of OM configuration parameters collected together in a
                parameter group. The parameter group must contain the following
                entries:

                * `processed_directory`: A relative or absolute path to the
                  directory where the output files are to be written.

        """
        try:
            self._parameters = _MonitorFileWriterParameters.model_validate(parameters)
        except ValidationError as exception:
            raise OmConfigurationFileSyntaxError(
                "Error parsing OM's configuration parameters: " f"{exception}"
            )

        self._status_filename: pathlib.Path = (
            pathlib.Path(self._parameters.cheetah.processed_directory).resolve()
            / "status.txt"
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
        Updates the data processing information and writes the status to a file.

        This function updates the data stored by this class with the provided data
        processing information. Additionally, it writes the updated data processing
        statistics to a `status file`. External program, like the Cheetah GUI, can
        inspect this file to get information about Cheetah's current state.

        Arguments:

            status: A string describing the current status of the data processing in
                Cheetah.

            num_frames: The number of detector frames processed so far by Cheetah.

            num_hits: The number of hits found so far by Cheetah.
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
        parameters: Dict[str, Any],
    ) -> None:
        """
        Cheetah list files writer.

        This class manages the information that gets written to the `frames.txt`,
        `cleaned.txt`, `events.lst`, `hits.lst` and `peaks.txt` files, required by the
        Cheetah GUI.

        * `frames.txt` contains a list of all the detector frames processed by Cheetah,
          with information about the frame timestamp, event ID, whether the frame is a
          hit, the name of the file containing the frame, the index of the frame in the
          file, the number of peaks detected in the frame, and the average intensity of
          the peaks in the frame.

        * `cleaned.txt` contains a list of all the detector frames that have been
          identified as hits by Cheetah, with the same information as `frames.txt`.

        * `events.lst` contains a list of all the event identifiers for the detector
          frames processed by Cheetah.

        * `hits.lst` contains a list of all the event identifiers for the detector
          frames that have been identified as hits by Cheetah.

        * `peaks.txt` contains a list of all the Bragg peaks detected by Cheetah, with
           information about the event ID of the frame to which the peak belongs, the
           number of peaks in the frame, the fast-scan and slow-scan coordinates of the
           peak, the peak intensity, the number of pixels in the peak, the maximum
           pixel intensity in the peak, and the signal-to-noise ratio of the peak.

        Arguments:

            cheetah_parameters: An object storing Cheetah's configuration parameters.
        """
        try:
            self._parameters = _MonitorFileWriterParameters.model_validate(parameters)
        except ValidationError as exception:
            raise OmConfigurationFileSyntaxError(
                "Error parsing OM's configuration parameters: " f"{exception}"
            )

        self._status_filename: pathlib.Path = (
            pathlib.Path(self._parameters.cheetah.processed_directory).resolve()
            / "status.txt"
        )

        processed_directory: pathlib.Path = pathlib.Path(
            self._parameters.cheetah.processed_directory
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

        self._frame_list: List[FrameListData] = []

    def add_frame(
        self,
        *,
        frame_data: FrameListData,
        peak_list: PeakList,
    ) -> None:
        """
        Adds a frame to the list files.

        This function adds information related to a single detector data frame to the
        list files.

        Arguments:

            frame_data: Information about the frame that must be added to the list
                files.

            peak_list: The list of peaks detected in the frame being added to the
                files.
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
                    f"{peak_list.num_peaks}, "
                    f"{peak_list.fs[i]}, "
                    f"{peak_list.ss[i]}, "
                    f"{peak_list.intensity[i]}, "
                    f"{peak_list.num_pixels[i]}, "
                    f"{peak_list.max_pixel_intensity[i]}, "
                    f"{peak_list.snr[i]}\n"
                    for i in range(peak_list.num_peaks)
                )
            )

    def flush_files(self) -> None:
        """
        Flushes the list files.

        This function flushes the list files to disk, writing on storage media the
        information still stored only in memory.
        """
        self._frames_file.flush()
        self._peaks_file.flush()
        self._events_file.flush()
        self._hits_file.flush()

    def sort_frames_and_close_files(self) -> None:
        """
        Performs final operations on the list files.

        This functions performs some operations on the list files just before closing
        them: it sorts the frames according to their event identifier and it writes the
        sorted data to the `frames.txt`, `cleaned.txt` and `events.lst` files. The
        function then closes all the list files.
        """
        frame_list: List[FrameListData] = sorted(self._frame_list)
        self._frames_file.close()
        self._events_file.close()
        self._hits_file.close()
        self._peaks_file.close()

        fh: TextIO
        with open(self._events_filename, "w") as fh:
            frame: FrameListData
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
        parameters: Dict[str, Any],
        num_classes: int,
    ) -> None:
        """
        Cheetah data class sum accumulator.

        This class accumulates information about the sum and virtual powder pattern of
        all detector frames belonging to a specific data class.

        After the accumulator has been initialized, data frame information can be added
        to it. The cumulative sum and virtual powder pattern for the data in the class
        can be retrieved from the accumulator either after a predefined number of
        frames have been added, or on-demand.

        Arguments:

            cheetah_parameters: A set of OM configuration parameters collected
                together in a parameter group. The parameter group must contain the
                following entries:

                class_sums_sending_interval: The maximum number of detector frames that
                    the accumulator can receive before returning the sum and virtual
                    powder plot information. After the data is returned, the frame
                    counter is reset.

            num_classes: The total number of data classes currently managed by Cheetah.
        """

        try:
            self._parameters = _MonitorSumsAccumulatorParameters.model_validate(
                parameters
            )
        except ValidationError as exception:
            raise OmConfigurationFileSyntaxError(
                "Error parsing OM's configuration parameters: " f"{exception}"
            )

        self._sum_sending_counter: int = 0
        self._num_classes: int = num_classes

    def add_frame(
        self,
        *,
        class_number: int,
        frame_data: Union[NDArray[numpy.float_], NDArray[numpy.int_]],
        peak_list: PeakList,
    ) -> None:
        """
        Adds a detector frame to the accumulator.

        This function adds information about a detector data frame to the accumulator.

        Arguments:

            class_number: The data class number to which the frame being added belongs.

            frame_data: Information about the detector data frame that must be added to
                the accumulator.

            peak_list: The list of peaks detected in the frame being added to the
                accumulator.
        """
        if self._parameters.cheetah.class_sums_sending_interval == -1:
            return
        if self._sum_sending_counter == 0:
            self._sums: List[ClassSumData] = [
                ClassSumData(
                    num_frames=0,
                    sum_frames=numpy.zeros(frame_data.shape),
                    peak_powder=numpy.zeros(frame_data.shape),
                )
                for class_number in range(self._num_classes)
            ]
        self._sums[class_number].num_frames += 1
        self._sums[class_number].sum_frames += frame_data

        peak_fs: float
        peak_ss: float
        peak_value: float
        for peak_fs, peak_ss, peak_value in zip(
            peak_list.fs, peak_list.ss, peak_list.intensity
        ):
            cast(h5py.Dataset, self._sums[class_number].peak_powder)[
                int(round(peak_ss)), int(round(peak_fs))
            ] += peak_value

        self._sum_sending_counter += 1

    def get_sums_for_sending(
        self, disregard_counter: bool = False
    ) -> Union[None, List[ClassSumData]]:
        """
        Retrieves the frame sum and virtual powder pattern from the accumulator.

        This function returns the data stored in the accumulator if the predefined
        number of frames has been added to the accumulator, or if the
        `disregard_counter` argument is `True`. Otherwise, it returns `None`.

        Arguments:

            disregard_counter: If the value of this argument is True, the accumulator's
                internal frame counter is ignored, and the class sum and virtual powder
                pattern are returned. The frame counter is then reset.

        Returns:

            The sum and virtual powder plot stored by the accumulator, or None.
        """
        if (
            self._sum_sending_counter
            >= self._parameters.cheetah.class_sums_sending_interval
        ) or (self._sum_sending_counter > 0 and disregard_counter):
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
        parameters: Dict[str, Any],
        num_classes: int,
    ) -> None:
        """
        Cheetah data class sum collector.

        This class collects accumulated data class information retrieved from the
        processing nodes, and stores the cumulative total information associated with
        the data class. The information collected by this class can optionally be
        written to an HDF5 file.

        Arguments:

            cheetah_parameters: A set of OM configuration parameters collected together
                in a parameter group. The parameter group must contain the following
                entries:

                * `write_class_sums`: Whether the information stored by the collector
                  should be written to disk regularly.

                * `class_sums_update_interval`: If the information stored by the
                  collector must be written to disk (see the `write_class_sums`
                  parameter), this parameter determines how many times the collector
                  can be updated before the accumulated data is written to a file.
                  After the file has been written, the update count is reset.

            num_classes: The total number of data classes currently managed by Cheetah.

        """
        self._num_classes: int = num_classes

        try:
            self._parameters = _MonitorClassSumsCollectorParameters.model_validate(
                parameters
            )
        except ValidationError as exception:
            raise OmConfigurationFileSyntaxError(
                "Error parsing OM's configuration parameters: " f"{exception}"
            )

        if self._parameters.cheetah.write_class_sums:
            self._sum_writers: Dict[int, SumHDF5Writer] = {
                class_number: SumHDF5Writer(
                    powder_class=class_number,
                    parameters=parameters,
                )
                for class_number in range(self._num_classes)
            }
            self._class_sum_update_counter: int = 0

    def add_sums(
        self,
        *,
        class_sums: List[ClassSumData],
    ) -> None:
        """
        Adds information to the collectors

        Adds class sums information, retrieved from the processing nodes, to the
        collector. If the predefined number of updates has been reached, the function
        triggers the writing of the collector's data to an HDF5 file.

        Arguments:

            class_sums: The information to be added to the collector.
        """

        if self._class_sum_update_counter == 0:
            self._sums: List[ClassSumData] = class_sums
        else:
            class_number: int
            for class_number in range(len(class_sums)):
                self._sums[class_number].num_frames += class_sums[
                    class_number
                ].num_frames
                self._sums[class_number].sum_frames += class_sums[
                    class_number
                ].sum_frames
                self._sums[class_number].peak_powder += class_sums[
                    class_number
                ].peak_powder

        self._class_sum_update_counter += 1
        if (
            self._class_sum_update_counter
            % self._parameters.cheetah.class_sums_update_interval
            == 0
        ):
            self.save_sums()

    def save_sums(self) -> None:
        """
        Saves the collector's data  to an HDF5 file.

        This function saves the collector's accumulated data to an HDF5 file. It is
        called automatically by the collector when required, but can also be called
        manually.
        """
        if (
            self._parameters.cheetah.write_class_sums
            and self._class_sum_update_counter > 0
        ):
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
        parameters: Dict[str, Any],
    ) -> None:
        """
        Event data writer.

        This class creates HDF5 data files that store the event information processed
        by Cheetah. For each data event, this class saves into an HDF5 file a processed
        detector data frame, the list of Bragg peaks detected in the frame, and some
        additional information (timestamp, beam energy, detector distance, pump laser
        state).

        Arguments:

            cheetah_parameters: A set of OM configuration parameters collected together
                in a parameter group. The parameter group must contain the following
                entries:

                processed_directory: A relative or absolute path to the directory where
                    the output files are written.

                compression: The compression filter to be applied to the data in the
                    output file.

                hdf5_fields: A dictionary storing information about the internal HDF5
                    path where each data entry must be written.

                    * The keys in the dictionary must store the names of data entries
                      to write.

                    * The corresponding dictionary values must contain the internal
                      HDF5 paths where the entries must be written.

                processed_filename_prefix: A string that is prepended to the name of
                    the output files. Optional. If the value of this entry is None, the
                    string 'processed_' will be used as prefix. Defaults to None.

                processed_filename_extension: An extension string that is appended to
                    the name of the output files. Optional. If the value of this entry
                    is None, the string 'h5' is be used as extension. Defaults to
                    None.

                compression_opts: The compression level to be used, if data compression
                    is applied to the output files. The information in this entry only
                    applies if the corresponding `compression` entry is not None,
                    otherwise, it is ignored. Optional. If the value of this entry is
                    None, the compression level is set to 4. Defaults to None.

                compression_shuffle: Whether the `shuffle` filter is applied. If the
                    value of this entry is True, the filter is applied to the data
                    being written, otherwise it is not. Defaults to False.

                max_num_peaks: The maximum number of detected Bragg peaks that must be
                    written to the HDF5 file for each event. Optional. If the value
                    of this entry is None, only the first 1024 peaks detected in each
                    frame are written to the output file. Defaults to None.

            node_rank: The rank of the OM node that writes the data in the output
                files.
        """

        try:
            self._parameters = _MonitorHdf5WriterParameters.model_validate(parameters)
        except ValidationError as exception:
            raise OmConfigurationFileSyntaxError(
                "Error parsing OM's configuration parameters: " f"{exception}"
            )

        self._processed_filename: pathlib.Path = (
            pathlib.Path(self._parameters.cheetah.processed_directory).resolve()
            / f"{self._parameters.cheetah.processed_filename_prefix}_"
            "{node_rank}.inprogress"
        )

        self._processed_filename_extension: str = (
            f".{self._parameters.cheetah.processed_filename_extension}"
        )

        # Compression
        if self._parameters.cheetah.hdf5_file_compression == "gzip":
            self._compression_kwargs: Dict[str, Any] = {
                "compression": "gzip",
                "compression_opts": (
                    self._parameters.cheetah.hdf5_file_gzip_compression_level,
                ),
            }
        elif self._parameters.cheetah.hdf5_file_compression == "bitshuffle_with_zstd":
            self._compression_kwargs = dict(
                hdf5plugin.Bitshuffle(
                    cname="zstd",
                    clevel=(self._parameters.cheetah.hdf5_file_zstd_compression_level),
                )
            )
        else:
            self._compression_kwargs = {}

        self._compression_kwargs["shuffle"] = (
            self._parameters.cheetah.hdf5_file_compression_shuffle
        )
        # TODO: Check

        self._h5file: Any = None
        self._resizable_datasets: Dict[str, Any] = {}
        self._extra_groups: Dict[str, Any] = {}
        self._requested_datasets: Set[str] = set(
            self._parameters.cheetah.hdf5_fields.keys()
        )
        self._num_frames: int = 0

    def _create_file_and_datasets(self, *, processed_data: Dict[str, Any]) -> None:
        # This function is called when the first data comes. It opens the output hdf5
        # file and creates all the requested datasets.
        self._h5file = h5py.File(self._processed_filename, "w")
        if (
            "detector_data" in processed_data
            and "detector_data" in self._requested_datasets
        ):
            if self._parameters.cheetah.hdf5_file_data_type is None:
                self._data_type = processed_data["detector_data"].dtype
            self._resizable_datasets["detector_data"] = self._h5file.create_dataset(
                name=self._parameters.cheetah.hdf5_fields["detector_data"],
                shape=(0,) + processed_data["detector_data"].shape,
                maxshape=(None,) + processed_data["detector_data"].shape,
                dtype=self._parameters.cheetah.hdf5_file_data_type,
                chunks=(1,) + processed_data["detector_data"].shape,
                **self._compression_kwargs,
            )

        if "event_id" in self._parameters.cheetah.hdf5_fields.keys():
            self._resizable_datasets["event_id"] = self._h5file.create_dataset(
                name=self._parameters.cheetah.hdf5_fields["event_id"],
                shape=(0,),
                maxshape=(None,),
                dtype=h5py.special_dtype(vlen=str),
            )
        if "optical_laser_active" in self._parameters.cheetah.hdf5_fields.keys():
            self._resizable_datasets["optical_laser_active"] = (
                self._h5file.create_dataset(
                    name=self._parameters.cheetah.hdf5_fields["optical_laser_active"],
                    shape=(0,),
                    maxshape=(None,),
                    dtype=numpy.bool_,
                )
            )

        # Creating all requested 1D float64 datasets:
        key: str
        for key in ("timestamp", "beam_energy", "pixel_size", "detector_distance"):
            if key in self._parameters.cheetah.hdf5_fields.keys():
                self._resizable_datasets[key] = self._h5file.create_dataset(
                    name=self._parameters.cheetah.hdf5_fields[key],
                    shape=(0,),
                    maxshape=(None,),
                    dtype=numpy.float64,
                )
        if "peak_list" in self._parameters.cheetah.hdf5_fields.keys():
            self._resizable_datasets.update(
                {
                    "npeaks": self._h5file.create_dataset(
                        name=self._parameters.cheetah.hdf5_fields["peak_list"]
                        + "/nPeaks",
                        shape=(0,),
                        maxshape=(None,),
                        dtype=numpy.int64,
                    ),
                    "fs": self._h5file.create_dataset(
                        name=self._parameters.cheetah.hdf5_fields["peak_list"]
                        + "/peakXPosRaw",
                        shape=(0, self._parameters.cheetah.hdf5_file_max_num_peaks),
                        maxshape=(
                            None,
                            self._parameters.cheetah.hdf5_file_max_num_peaks,
                        ),
                        dtype=numpy.float32,
                    ),
                    "ss": self._h5file.create_dataset(
                        name=self._parameters.cheetah.hdf5_fields["peak_list"]
                        + "/peakYPosRaw",
                        shape=(0, self._parameters.cheetah.hdf5_file_max_num_peaks),
                        maxshape=(
                            None,
                            self._parameters.cheetah.hdf5_file_max_num_peaks,
                        ),
                        dtype=numpy.float32,
                    ),
                    "intensity": self._h5file.create_dataset(
                        name=self._parameters.cheetah.hdf5_fields["peak_list"]
                        + "/peakTotalIntensity",
                        shape=(0, self._parameters.cheetah.hdf5_file_max_num_peaks),
                        maxshape=(
                            None,
                            self._parameters.cheetah.hdf5_file_max_num_peaks,
                        ),
                        dtype=numpy.float32,
                    ),
                    "num_pixels": self._h5file.create_dataset(
                        name=self._parameters.cheetah.hdf5_fields["peak_list"]
                        + "/peakNPixels",
                        shape=(0, self._parameters.cheetah.hdf5_file_max_num_peaks),
                        maxshape=(
                            None,
                            self._parameters.cheetah.hdf5_file_max_num_peaks,
                        ),
                        dtype=numpy.float32,
                    ),
                    "max_pixel_intensity": self._h5file.create_dataset(
                        name=self._parameters.cheetah.hdf5_fields["peak_list"]
                        + "/peakMaximumValue",
                        shape=(0, self._parameters.cheetah.hdf5_file_max_num_peaks),
                        maxshape=(
                            None,
                            self._parameters.cheetah.hdf5_file_max_num_peaks,
                        ),
                        dtype=numpy.float32,
                    ),
                    "snr": self._h5file.create_dataset(
                        name=self._parameters.cheetah.hdf5_fields["peak_list"]
                        + "/peakSNR",
                        shape=(0, self._parameters.cheetah.hdf5_file_max_num_peaks),
                        maxshape=(
                            None,
                            self._parameters.cheetah.hdf5_file_max_num_peaks,
                        ),
                        dtype=numpy.float32,
                    ),
                }
            )

        for key in self._requested_datasets:
            if key.endswith("_extra"):
                self._extra_groups[key] = self._h5file.create_group(
                    self._parameters.cheetah.hdf5_fields[key]
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
        # Creates an empty dataset in the extra data group for each item in extra_data
        # dict using dict keys as dataset names. Supported data types: numpy arrays,
        # str, float, int and bool.
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
        # Writes the extra_data items.
        key: str
        value: Any
        for key, value in extra_data.items():
            self._extra_groups[group_name][key][self._num_frames - 1] = extra_data[key]

    def write_frame(self, *, processed_data: Dict[str, Any]) -> None:  # noqa: C901
        """
        Writes data into an HDF5 data file.

        This function writes the provided data into an HDF5 data file, assuming that
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
            peak_list: PeakList = processed_data["peak_list"]
            n_peaks: int = min(
                peak_list.num_peaks, self._parameters.cheetah.hdf5_file_max_num_peaks
            )
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
                self._resizable_datasets[peak_dict_key][frame_num, :n_peaks] = getattr(
                    peak_list, peak_dict_key
                )[:n_peaks]

        for extra_group_name in self._extra_groups:
            if extra_group_name in fields:
                self._write_extra_data(
                    group_name=extra_group_name,
                    extra_data=processed_data[extra_group_name],
                )

    def close(self) -> None:
        """
        Closes the file currently being written.

        This function closes the HDF5 file that the class is currently writing.
        """
        if self._h5file is None:
            return
        self._h5file.close()
        final_filename: pathlib.Path = self._processed_filename.with_suffix(
            self._processed_filename_extension
        )
        self._processed_filename.rename(final_filename)
        log.info(f"{self._num_frames} frames saved in " f"{final_filename} file.")

    def get_current_filename(self) -> pathlib.Path:
        """
        Retrieves the path to the file currently being written.

        This function retrieves the full path to the file that the class is currently
        writing.

        Returns:

            The path to the file currently being written.
        """
        return self._processed_filename

    def get_num_written_frames(self) -> int:
        """
        Retrieves the number of data events already written to the current file.

        This function retrieves the number of data events that the class has already
        saved into the file that is currently writing.

        Returns:

            The number of data events already written in the current file.
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
        parameters: Dict[str, Any],
    ) -> None:
        """
        Frame sum writer.

        This class creates HDF5 data files to store the aggregate information collected
        by Cheetah. The function saves into an HDF5 file a sum of detector data frames,
        together with a virtual powder pattern created using the Bragg peaks detected
        in the frames. Different sum writers are usually created for different data
        classes.

        Arguments:

            powder_class: A unique identifier for the data class to which the data
                being written belongs.

            cheetah_parameters: A dictionary containing Cheetah's configuration
                parameters.
        """

        cheetah_sum_hdf5_writer_parameters = (
            _MonitorHdf5WriterParameters.model_validate(parameters)
        )

        self._filename: pathlib.Path = (
            pathlib.Path(
                cheetah_sum_hdf5_writer_parameters.cheetah.processed_directory
            ).resolve()
            / f"{cheetah_sum_hdf5_writer_parameters.cheetah.processed_filename_prefix}"
            "-detector0-class{powder_class}-sum.h5"
        )

    def _create_hdf5_file_and_datasets(self, *, data_shape: Tuple[int, ...]) -> None:
        # Creates the HDF5 file and all datasets.
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
        data: ClassSumData,
    ) -> None:
        """
        Writes aggregated frame data into an HDF5 file.

        This function writes the provided aggregated frame data into an HDF5 file.

        Arguments:

            data: A dictionary containing the aggregated data to write into the file.
        """
        if not self._filename.exists():
            self._create_hdf5_file_and_datasets(data_shape=data.sum_frames.shape)
        attempt: int
        for attempt in range(5):
            # If file is opened by someone else try 5 times during 10 seconds and exit
            try:
                self._h5file = h5py.File(self._filename, "r+")
                self._h5file["/data/nframes"][0] = data.num_frames
                self._h5file["/data/data"][:] = data.sum_frames
                if data.peak_powder is not None:
                    self._h5file["/data/peakpowder"][:] = data.peak_powder
                self._h5file.close()
                return
            except OSError:
                time.sleep(2)
                ...
        log.warning(
            f'Another application is reading the file "{self._filename} exclusively. '
            "Five attempts to open the files failed. Cannot update the file."
        )
