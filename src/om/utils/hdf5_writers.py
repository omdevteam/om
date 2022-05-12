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
HDF5 writing.

This module contains classes and functions that allow OM monitors to write data to
files in HDF5 format.
"""
import pathlib
import sys
import time
from typing import Any, Dict, List, Set, Tuple, Union

import h5py  # type: ignore
import numpy
from numpy.typing import DTypeLike, NDArray

from om.algorithms import crystallography as cryst_algs
from om.utils import crystfel_geometry, exceptions
from om.utils import parameters as param_utils
from om.utils.rich_console import console, get_current_timestamp

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal


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
        HDF5 file writer for Cheetah.

        This class creates HDF5 data files to store the detector information processed
        by the Cheetah software package. For each detector frame, this class saves into
        an HDF5 file the processed data frame, the list of Bragg peaks detected in the
        frame, and some additional information (timestamp, beam energy, detector
        distance, pump laser state).

        Arguments:

            parameters: A set of OM configuration parameters collected together in a
                parameter group. The parameter group must contain the following
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
                    is applied to the output files. This is entry is considered only
                    if the `compression` entry is not None, otherwise, it is ignored.
                    Optional. If the value of this entry is None, the compression level
                    will be set to 4. Defaults to None.

                compression_shuffle: Whether the `shuffle` filter is applied. If the
                    value of this entry is True, the `shuffle` filter will be applied,
                    otherwise it will not. Defaults to None.

                max_num_peaks: The maximum number of detected Bragg peaks that will be
                    written in the HDF5 for each detector frame. Optional. If the value
                    of this entry is None, only the first 1024 peaks detected in each
                    frame will be written to the output file. Defaults to None.

            node_rank: The rank of the OM node that will write the data in the output
                files.
        """
        directory_for_processed_data: str = (
            param_utils.get_parameter_from_parameter_group(
                group=parameters,
                parameter="processed_directory",
                parameter_type=str,
                required=True,
            )
        )
        processed_filename_prefix: Union[
            str, None
        ] = param_utils.get_parameter_from_parameter_group(
            group=parameters,
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
        ] = param_utils.get_parameter_from_parameter_group(
            group=parameters,
            parameter="processed_filename_extension",
            parameter_type=str,
        )
        if processed_filename_extension is None:
            processed_filename_extension = "h5"
        self._processed_filename_extension: str = f".{processed_filename_extension}"

        self._data_type: Union[
            str, DTypeLike, None
        ] = param_utils.get_parameter_from_parameter_group(
            group=parameters,
            parameter="hdf5_file_data_type",
            parameter_type=str,
        )
        self._compression: Union[
            str, None
        ] = param_utils.get_parameter_from_parameter_group(
            group=parameters,
            parameter="hdf5_file_compression",
            parameter_type=str,
        )
        self._compression_opts: Union[
            int, None
        ] = param_utils.get_parameter_from_parameter_group(
            group=parameters,
            parameter="hdf5_file_compression_opts",
            parameter_type=int,
        )
        self._compression_shuffle: Union[
            bool, None
        ] = param_utils.get_parameter_from_parameter_group(
            group=parameters,
            parameter="hdf5_file_compression_shuffle",
            parameter_type=bool,
        )
        if self._compression is None:
            self._compression_opts = None
        elif self._compression_opts is None:
            self._compression_opts = 4
        if self._compression_shuffle is None:
            self._compression_shuffle = False

        max_num_peaks: Union[
            int, None
        ] = param_utils.get_parameter_from_parameter_group(
            group=parameters,
            parameter="hdf5_file_max_num_peaks",
            parameter_type=int,
        )
        if max_num_peaks is None:
            self._max_num_peaks: int = 1024
        else:
            self._max_num_peaks = max_num_peaks

        self._hdf5_fields = param_utils.get_parameter_from_parameter_group(
            group=parameters,
            parameter="hdf5_fields",
            parameter_type=dict,
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
                compression=self._compression,
                compression_opts=self._compression_opts,
                shuffle=self._compression_shuffle,
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
        # dictusing dict keys as dataset names. Supported data types: numpy arrays,
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
                raise exceptions.OmHdf5UnsupportedDataFormat(
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
        Writes data related to one detector frame into an HDF5 data file.

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
        dataset_dict_keys_to_write: List[
            Literal[
                "detector_data",
                "event_id",
                "timestamp",
                "beam_energy",
                "detector_distance",
                "optical_laser_active",
            ]
        ] = [
            "detector_data",
            "event_id",
            "timestamp",
            "beam_energy",
            "detector_distance",
            "optical_laser_active",
        ]
        dataset_dict_key: str
        for dataset_dict_key in dataset_dict_keys_to_write:
            if dataset_dict_key in fields:
                self._resizable_datasets[dataset_dict_key][frame_num] = processed_data[
                    dataset_dict_key
                ]

        if "peak_list" in fields:
            peak_list: cryst_algs.TypePeakList = processed_data["peak_list"]
            n_peaks: int = min(peak_list["num_peaks"], self._max_num_peaks)
            self._resizable_datasets["npeaks"][frame_num] = n_peaks
            peak_dict_keys_to_write: List[
                Literal[
                    "fs", "ss", "intensity", "num_pixels", "max_pixel_intensity", "snr"
                ]
            ] = ["fs", "ss", "intensity", "num_pixels", "max_pixel_intensity", "snr"]
            peak_dict_key: str
            for peak_dict_key in peak_dict_keys_to_write:
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
        Retrieves the number frames that have been written into the current file.

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
        directory_for_processed_data: str,
        powder_class: int,
        detector_data_shape: Tuple[int, ...],
        sum_filename_prefix: Union[str, None] = None,
    ) -> None:
        """
        HDF5 writer for sum of frames.

        This class creates HDF5 data files to store the aggregated detector information
        processed by the Cheetah software package. It saves sums of detector data
        frames into HDF5 files,together with virtual powder patterns created using the
        Bragg peaks detected in the frames.

        Arguments:

            directory_for_processed_data: A relative or absolute path to the directory
                where the output files will be written.

            powder_class: A unique identifier for the sum of frames and virtual powder
                pattern being saved.

            detector_data_shape: The numpy shape of the detector data array that will
                be written to the output files.

            sum_filename_prefix: a string that will be prepended to the name of the
                output files. Optional. If the value of this argument is None, the
                string 'processed' will be used as prefix. Defaults to None.
        """
        if sum_filename_prefix is None:
            sum_filename_prefix = "processed"

        self._class_filename: pathlib.Path = (
            pathlib.Path(directory_for_processed_data).resolve()
            / f"{sum_filename_prefix}-detector0-class{powder_class}-sum.h5"
        )
        self._h5file: Any = h5py.File(self._class_filename, "w")

        self._h5file.create_dataset(
            name="/data/nframes",
            shape=(1,),
            dtype=numpy.int64,
        )
        self._h5file.create_dataset(
            name="/data/data",
            shape=detector_data_shape,
            dtype=numpy.float64,
        )
        self._h5file.create_dataset(
            name="/data/peakpowder",
            shape=detector_data_shape,
            dtype=numpy.float64,
        )
        self._h5file.close()

    def write_sums(
        self,
        *,
        num_frames: int,
        sum_frames: NDArray[numpy.float_],
        virtual_powder_pattern: NDArray[numpy.float_],
    ) -> None:
        """
        Writes aggregated detector frame data into an HDF5 file.

        Arguments:

            num_frames: The number of frames in the sum.

            sum_frames: The sum of detector frames that will be written in the output
                file.

            virtual_powder_pattern: The virtual powder patter that will be written in
                the output file.
        """
        attempt: int
        for attempt in range(5):
            # If file is opened by someone else try 5 times during 10 seconds and exit
            try:
                self._h5file = h5py.File(self._class_filename, "r+")
                self._h5file["/data/nframes"][0] = num_frames
                self._h5file["/data/data"][:] = sum_frames
                self._h5file["/data/peakpowder"][:] = virtual_powder_pattern
                self._h5file.close()
                return
            except OSError:
                time.sleep(2)
                pass
        console.print(
            f"{get_current_timestamp()} Another application is reading the file "
            f"{self._class_filename} exclusively. Five attempts to open the files "
            "failed. Cannot update the file.",
            style="warning",
        )
