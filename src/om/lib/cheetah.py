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
from typing import Any, TextIO, cast

import h5py  # type: ignore[import-untyped]  # ty: ignore[unused-ignore-comment]
import hdf5plugin  ## type: ignore[import-untyped]  # ty: ignore[unused-ignore-comment]
import numpy
from numpy.typing import NDArray

from om.algorithms.common import PeakList
from om.lib.exceptions import OmHdf5UnsupportedDataFormat
from om.lib.logging import log
from om.lib.parameters import CheetahParameters, Hdf5Compression


@dataclass
class ClassSumData:
    """
    Cheetah data class sum data.

    A dictionary storing the number of detector frames belonging to a specific data
    class, their sum, and the virtual powder pattern generated from the Bragg peaks
    detected in them.
    """

    num_frames: int
    """The number of detector frames belonging to the data class."""

    sum_frames: NDArray[numpy.floating[Any]]
    """The sum of the detector frames belonging to the class."""

    peak_powder: NDArray[numpy.floating[Any]]
    """The virtual powder pattern for the data class."""


@dataclass(order=True)
class FramelistData:
    """
    Cheetah frame list data.

    This named tuple is used to store the detector frame data which is later written
    into the `frames.txt` file.
    """

    timestamp: numpy.floating[Any]
    """The timestamp of the frame."""

    event_id: str | None
    """A unique identifier for the event attached to the frame."""

    frame_is_hit: int
    """A flag indicating whether the event attached to the frame is
    labelled as a hit."""

    filename: str
    """The name of the file containing the frame."""

    index_in_file: int
    """The index of the frame in the file."""

    num_peaks: int
    """The number of peaks in the frame."""

    average_intensity: numpy.floating[Any]
    """The average intensity of the Bragg peaks detected in the frame."""

    def __post_init__(self) -> None:
        self.sort_index = self.timestamp


class CheetahStatusFileWriter:
    """
    See documentation for the `__init__` function.
    """

    def __init__(self, *, parameters: CheetahParameters) -> None:
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
                    parameter group.
        """
        self._status_filename: pathlib.Path = (
            pathlib.Path(parameters.processed_directory).resolve() / "status.txt"
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


class CheetahlistFilesWriter:
    """
    See documentation for the `__init__` function.
    """

    def __init__(
        self,
        *,
        parameters: CheetahParameters,
    ) -> None:
        """
        Cheetah list files writer.

        This class manages the information that gets written to the 'frames.txt',
        'cleaned.txt', 'events.lst', 'hits.lst' and 'peaks.txt' files, required by the
        Cheetah GUI.

        * 'frames.txt' contains a list of all the detector frames processed by Cheetah,
          with information about the frame timestamp, event ID, whether the frame is a
          hit, the name of the file containing the frame, the index of the frame in the
          file, the number of peaks detected in the frame, and the average intensity of
          the peaks in the frame.

        * 'cleaned.txt' contains a list of all the detector frames that have been
          identified as hits by Cheetah, with the same information as 'frames.txt'.

        * 'events.lst' contains a list of all the event identifiers for the detector
          frames processed by Cheetah.

        * 'hits.lst' contains a list of all the event identifiers for the detector
          frames that have been identified as hits by Cheetah.

        * 'peaks.txt' contains a list of all the Bragg peaks detected by Cheetah, with
          information about the event ID of the frame to which the peak belongs, the
          number of peaks in the frame, the fast-scan and slow-scan coordinates of the
          peak, the peak intensity, the number of pixels in the peak, the maximum
          pixel intensity in the peak, and the signal-to-noise ratio of the peak.

        Arguments:

            parameters: An object storing Cheetah's configuration parameters.
        """
        self._status_filename: pathlib.Path = (
            pathlib.Path(parameters.processed_directory).resolve() / "status.txt"
        )

        processed_directory: pathlib.Path = pathlib.Path(
            parameters.processed_directory
        ).resolve()

        self._processed_filename_extension: str = (
            f".{parameters.processed_filename_extension}"
        )

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

        self._frame_list: list[FramelistData] = []

    def add_frame(
        self,
        *,
        frame_data: FramelistData,
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
        frame_list: list[FramelistData] = sorted(self._frame_list)
        self._frames_file.close()
        self._events_file.close()
        self._hits_file.close()
        self._peaks_file.close()

        fh: TextIO
        with open(self._events_filename, "w") as fh:
            frame: FramelistData
            for frame in frame_list:
                fh.write(f"{frame.event_id}\n")
        with open(self._hits_filename, "w") as fh:
            for frame in frame_list:
                if frame.frame_is_hit:
                    fh.write(f"{frame.event_id}\n")
        with open(self._frames_filename, "w") as fh:
            fh.write(
                "# timestamp, event_id, hit, filename, index, num_peaks, "
                "ave_intensity\n"
            )
            for frame in frame_list:
                if frame.filename != "---":
                    frame.filename = str(
                        pathlib.Path(frame.filename).with_suffix(
                            self._processed_filename_extension
                        )
                    )
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
        parameters: CheetahParameters,
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

            parameters: A set of OM configuration parameters collected together in a
                parameter group.

            num_classes: The total number of data classes currently managed by Cheetah.
        """
        self._cheetah_parameters: CheetahParameters = parameters
        self._sum_sending_counter: int = 0
        self._num_classes: int = num_classes

    def add_frame(
        self,
        *,
        class_number: int,
        frame_data: NDArray[numpy.floating[Any] | numpy.signedinteger[Any]],
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
        if self._cheetah_parameters.class_sums_sending_interval == -1:
            return
        if self._sum_sending_counter == 0:
            self._sums: list[ClassSumData] = [
                ClassSumData(
                    num_frames=0,
                    sum_frames=numpy.zeros(frame_data.shape),
                    peak_powder=numpy.zeros(frame_data.shape),
                )
                for _ in range(self._num_classes)
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
    ) -> list[ClassSumData] | None:
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
            >= self._cheetah_parameters.class_sums_sending_interval
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
        parameters: CheetahParameters,
        num_classes: int,
    ) -> None:
        """
        Cheetah data class sum collector.

        This class collects accumulated data class information retrieved from the
        processing nodes, and stores the cumulative total information associated with
        the data class. The information collected by this class can optionally be
        written to an HDF5 file.

        Arguments:

            parameters: A set of OM configuration parameters collected together
                in a parameter group.

            num_classes: The total number of data classes currently managed by Cheetah.

        """
        self._num_classes: int = num_classes

        self._write_class_sums: bool = parameters.write_class_sums
        self._class_sums_update_interval: int = parameters.class_sums_update_interval

        if self._write_class_sums:
            self._sum_writers: dict[int, SumHDF5Writer] = {
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
        class_sums: list[ClassSumData],
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
            self._sums: list[ClassSumData] = class_sums
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
        if self._class_sum_update_counter % self._class_sums_update_interval == 0:
            self.save_sums()

    def save_sums(self) -> None:
        """
        Saves the collector's data  to an HDF5 file.

        This function saves the collector's accumulated data to an HDF5 file. It is
        called automatically by the collector when required, but can also be called
        manually.
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
        parameters: CheetahParameters,
    ) -> None:
        """
        Event data writer.

        This class creates HDF5 data files that store the event information processed
        by Cheetah. For each data event, this class saves into an HDF5 file a processed
        detector data frame, the list of Bragg peaks detected in the frame, and some
        additional information (timestamp, beam energy, detector distance, pump laser
        state).

        Arguments:

            parameters: A set of OM configuration parameters collected together
                in a parameter group.

            node_rank: The rank of the OM node that writes the data in the output
                files.
        """
        self._cheetah_parameters: CheetahParameters = parameters

        self._processed_filename: pathlib.Path = (
            pathlib.Path(parameters.processed_directory).resolve()
            / f"{parameters.processed_filename_prefix}_"
            f"{node_rank}.inprogress"
        )

        self._processed_filename_extension: str = (
            f".{parameters.processed_filename_extension}"
        )

        # Compression
        if parameters.hdf5_file_compression == Hdf5Compression.gzip:
            self._compression_kwargs: dict[str, Any] = {
                "compression": "gzip",
                "compression_opts": (parameters.hdf5_file_gzip_compression_level,),
            }
        elif parameters.hdf5_file_compression == Hdf5Compression.bitshuffle_with_zstd:
            self._compression_kwargs = dict(
                hdf5plugin.Bitshuffle(  # pyright: ignore[reportPrivaeImportUsage]
                    cname="zstd",
                    clevel=(parameters.hdf5_file_zstd_compression_level),
                )
            )
        else:
            self._compression_kwargs = {}

        self._compression_kwargs["shuffle"] = parameters.hdf5_file_compression_shuffle
        # TODO: Check

        self._h5file: Any = None
        self._resizable_datasets: dict[str, Any] = {}
        self._extra_groups: dict[str, Any] = {}
        self._requested_datasets: set[str] = set(parameters.hdf5_fields.keys())
        self._num_frames: int = 0

    def _create_file_and_datasets(self, *, processed_data: dict[str, Any]) -> None:
        # This function is called when the first data comes. It opens the output hdf5
        # file and creates all the requested datasets.
        self._h5file = h5py.File(str(self._processed_filename), "w")
        if (
            "detector_data" in processed_data
            and "detector_data" in self._requested_datasets
        ):
            if self._cheetah_parameters.hdf5_file_data_type is None:
                self._data_type = processed_data["detector_data"].dtype
            self._resizable_datasets["detector_data"] = self._h5file.create_dataset(
                name=self._cheetah_parameters.hdf5_fields["detector_data"],
                shape=(0,) + processed_data["detector_data"].shape,
                maxshape=(None,) + processed_data["detector_data"].shape,
                dtype=self._cheetah_parameters.hdf5_file_data_type,
                chunks=(1,) + processed_data["detector_data"].shape,
                **self._compression_kwargs,
            )

        if "event_id" in self._cheetah_parameters.hdf5_fields.keys():
            self._resizable_datasets["event_id"] = self._h5file.create_dataset(
                name=self._cheetah_parameters.hdf5_fields["event_id"],
                shape=(0,),
                maxshape=(None,),
                dtype=h5py.string_dtype(),
            )
        if "optical_laser_active" in self._cheetah_parameters.hdf5_fields.keys():
            self._resizable_datasets["optical_laser_active"] = (
                self._h5file.create_dataset(
                    name=self._cheetah_parameters.hdf5_fields["optical_laser_active"],
                    shape=(0,),
                    maxshape=(None,),
                    dtype=numpy.int8,
                )
            )

        # Creating all requested 1D float64 datasets:
        key: str
        for key in (
            "timestamp",
            "beam_energy",
            "pixel_size",
            "detector_distance",
            "image_sum",
        ):
            if key in self._cheetah_parameters.hdf5_fields.keys():
                self._resizable_datasets[key] = self._h5file.create_dataset(
                    name=self._cheetah_parameters.hdf5_fields[key],
                    shape=(0,),
                    maxshape=(None,),
                    dtype=numpy.float64,
                )
        if "peak_list" in self._cheetah_parameters.hdf5_fields.keys():
            self._resizable_datasets.update(
                {
                    "npeaks": self._h5file.create_dataset(
                        name=self._cheetah_parameters.hdf5_fields["peak_list"]
                        + "/nPeaks",
                        shape=(0,),
                        maxshape=(None,),
                        dtype=numpy.int64,
                    ),
                    "fs": self._h5file.create_dataset(
                        name=self._cheetah_parameters.hdf5_fields["peak_list"]
                        + "/peakXPosRaw",
                        shape=(0, self._cheetah_parameters.hdf5_file_max_num_peaks),
                        maxshape=(
                            None,
                            self._cheetah_parameters.hdf5_file_max_num_peaks,
                        ),
                        dtype=numpy.float32,
                    ),
                    "ss": self._h5file.create_dataset(
                        name=self._cheetah_parameters.hdf5_fields["peak_list"]
                        + "/peakYPosRaw",
                        shape=(0, self._cheetah_parameters.hdf5_file_max_num_peaks),
                        maxshape=(
                            None,
                            self._cheetah_parameters.hdf5_file_max_num_peaks,
                        ),
                        dtype=numpy.float32,
                    ),
                    "intensity": self._h5file.create_dataset(
                        name=self._cheetah_parameters.hdf5_fields["peak_list"]
                        + "/peakTotalIntensity",
                        shape=(0, self._cheetah_parameters.hdf5_file_max_num_peaks),
                        maxshape=(
                            None,
                            self._cheetah_parameters.hdf5_file_max_num_peaks,
                        ),
                        dtype=numpy.float32,
                    ),
                    "num_pixels": self._h5file.create_dataset(
                        name=self._cheetah_parameters.hdf5_fields["peak_list"]
                        + "/peakNPixels",
                        shape=(0, self._cheetah_parameters.hdf5_file_max_num_peaks),
                        maxshape=(
                            None,
                            self._cheetah_parameters.hdf5_file_max_num_peaks,
                        ),
                        dtype=numpy.float32,
                    ),
                    "max_pixel_intensity": self._h5file.create_dataset(
                        name=self._cheetah_parameters.hdf5_fields["peak_list"]
                        + "/peakMaximumValue",
                        shape=(0, self._cheetah_parameters.hdf5_file_max_num_peaks),
                        maxshape=(
                            None,
                            self._cheetah_parameters.hdf5_file_max_num_peaks,
                        ),
                        dtype=numpy.float32,
                    ),
                    "snr": self._h5file.create_dataset(
                        name=self._cheetah_parameters.hdf5_fields["peak_list"]
                        + "/peakSNR",
                        shape=(0, self._cheetah_parameters.hdf5_file_max_num_peaks),
                        maxshape=(
                            None,
                            self._cheetah_parameters.hdf5_file_max_num_peaks,
                        ),
                        dtype=numpy.float32,
                    ),
                }
            )

        # SWAXS Cheetah writing
        for key in ("q", "radial"):
            if key in self._cheetah_parameters.hdf5_fields.keys():
                self._resizable_datasets[key] = self._h5file.create_dataset(
                    name=self._cheetah_parameters.hdf5_fields[key],
                    shape=(0,) + processed_data[key].shape,
                    maxshape=(None,) + processed_data[key].shape,
                    dtype=numpy.float64,
                    chunks=(1,) + processed_data[key].shape,
                    **self._compression_kwargs,
                )

        for key in self._requested_datasets:
            if key.endswith("_extra"):
                self._extra_groups[key] = self._h5file.create_group(
                    self._cheetah_parameters.hdf5_fields[key]
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
        self, *, group_name: str, extra_data: dict[str, Any]
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
                    shape=(0, *value.shape),  # pyright: ignore[reportUnknownMemberType]
                    maxshape=(
                        None,
                        *value.shape,
                    ),  # pyright: ignore[reportUnknownMemberType]
                    dtype=value.dtype,  # pyright: ignore[reportUnknownMemberType]
                )
            elif isinstance(value, str):
                self._resizable_datasets[group_name + "/" + key] = self._extra_groups[
                    group_name
                ].create_dataset(
                    name=key,
                    shape=(0,),
                    maxshape=(None,),
                    dtype=h5py.string_dtype(),
                )
            elif (
                isinstance(value, int)
                or isinstance(value, float)
                or isinstance(value, bool)
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

    def _write_extra_data(self, *, group_name: str, extra_data: dict[str, Any]) -> None:
        # Writes the extra_data items.
        key: str
        for key, _ in extra_data.items():
            self._extra_groups[group_name][key][self._num_frames - 1] = extra_data[key]

    def write_frame(self, *, processed_data: dict[str, Any]) -> None:  # noqa: C901
        """
        Writes data into an HDF5 data file.

        This function writes the provided data into an HDF5 data file, assuming that
        all the data belongs to the same processed data event.

        Arguments:

            processed_data: A dictionary containing the data to write into the HDF5
                file.
        """
        # Datasets to write:
        fields: set[str] = set(processed_data.keys()) & self._requested_datasets
        if len(fields) == 0:
            return

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
            "q",
            "radial",
            "image_sum",
        ):
            if dataset_dict_key in fields:
                self._resizable_datasets[dataset_dict_key][frame_num] = processed_data[
                    dataset_dict_key
                ]

        if "peak_list" in fields:
            peak_list: PeakList = processed_data["peak_list"]
            n_peaks: int = min(
                peak_list.num_peaks, self._cheetah_parameters.hdf5_file_max_num_peaks
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
        log.info(f"{self._num_frames} frames saved in {final_filename} file.")

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
        parameters: CheetahParameters,
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
        self._filename: pathlib.Path = (
            pathlib.Path(parameters.processed_directory).resolve()
            / f"{parameters.processed_filename_prefix}"
            f"-detector0-class{powder_class}-sum.h5"
        )

    def _create_hdf5_file_and_datasets(self, *, data_shape: tuple[int, ...]) -> None:
        # Creates the HDF5 file and all datasets.
        self._h5file: Any = h5py.File(str(self._filename), "w")
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
        for _ in range(5):
            # If file is opened by someone else try 5 times during 10 seconds and exit
            try:
                self._h5file = h5py.File(str(self._filename), "r+")
                self._h5file["/data/nframes"][0] = data.num_frames
                self._h5file["/data/data"][:] = data.sum_frames
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


def write_VDS_master_file(
    *,
    parameters: CheetahParameters,
):
    """
    Writes the master HDF5 file.

    This function creates an HDF5 file containing a virtual dataset that aggregates the
    data stored in the HDF5 files created by the `HDF5Writer` class. The master file is
    created in the same directory as the other files, and contains links to all the
    data sorted by timestamp.

    Arguments:
        parameters: A set of OM configuration parameters collected together in a
            parameter group.
    """
    processed_directory: pathlib.Path = pathlib.Path(
        parameters.processed_directory
    ).resolve()
    master_filename: pathlib.Path = (
        processed_directory / f"{parameters.processed_filename_prefix}-master."
        f"{parameters.processed_filename_extension}"
    )

    cleaned_filename: pathlib.Path = processed_directory / "cleaned.txt"
    if not cleaned_filename.exists():
        log.warning(
            f'Cannot create the master file: "{cleaned_filename}" file does not exist.'
        )
        return

    fh: TextIO
    frames: list[FramelistData] = []
    with open(cleaned_filename, "r") as fh:
        for line in fh:
            if line.startswith("#") or line.strip() == "":
                continue
            items: list[str] = line.split(",")
            filename: str = items[3].strip()
            if filename == "---" or not pathlib.Path(filename).exists():
                continue
            frames.append(
                FramelistData(
                    timestamp=float(items[0].strip()),
                    event_id=items[1].strip(),
                    frame_is_hit=int(items[2].strip()),
                    filename=filename,
                    index_in_file=int(items[4].strip()),
                    num_peaks=int(items[5].strip()),
                    average_intensity=float(items[6].strip()),
                )
            )

    # Sort by timestamp:
    frames.sort(key=lambda frame: frame.timestamp)

    # Copy all datasets from the individual files into the master file
    source_file: Any = h5py.File(str(frames[0].filename), "r")
    master_file: Any = h5py.File(str(master_filename), "w")

    datasets: list[str] = []
    source_file.visit(
        lambda key: (
            datasets.append(key) if isinstance(source_file[key], h5py.Dataset) else None
        )
    )

    n_frames: int = len(frames)
    virtual_layouts: dict[str, h5py.VirtualLayout] = {}
    for dataset_name in datasets:
        dataset_shape: tuple[int, ...] = source_file[dataset_name].shape[1:]
        dataset_dtype: Any = source_file[dataset_name].dtype
        virtual_layouts[dataset_name] = h5py.VirtualLayout(
            shape=(n_frames,) + dataset_shape, dtype=dataset_dtype
        )
    source_file.close()

    source_files: dict[str, Any] = {}
    for dataset_name in datasets:
        virtual_sources: dict[str, Any] = {}
        for i, frame in enumerate(frames):
            if frame.filename not in source_files:
                source_files[frame.filename] = h5py.File(str(frame.filename), "r")
            if frame.filename not in virtual_sources:
                virtual_sources[frame.filename] = h5py.VirtualSource(
                    source_files[frame.filename][dataset_name]
                )
            virtual_layouts[dataset_name][i] = virtual_sources[frame.filename][
                frame.index_in_file
            ]
        master_file.create_virtual_dataset(dataset_name, virtual_layouts[dataset_name])
    for source_file in source_files.values():
        source_file.close()

    log.info(f"Master file created: {master_filename}, containing {n_frames} frames.")
    master_file.close()
