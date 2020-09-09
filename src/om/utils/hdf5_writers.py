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
HDF5 writing.

This module contains classes and functions that allow OM monitors to write data to
HDF5 format files.
"""
import pathlib
import sys
import time
from typing import Any, Dict, List, Set, Tuple, Union
from typing_extensions import Literal

import h5py  # type: ignore
import numpy  # type: ignore

from om.algorithms import crystallography_algorithms as cryst_algs
from om.utils.crystfel_geometry import TypeDetector


class HDF5Writer(object):
    """
    See documentation of the '__init__' function.
    """

    def __init__(  # noqa: C901
        self,
        directory_for_processed_data: str,
        node_rank: int,
        geometry: TypeDetector,
        compression: Union[str, None],
        detector_data_type: Union[str, None],
        detector_data_shape: Tuple[int, int],
        hdf5_fields: Dict[str, str],
        processed_filename_prefix: Union[str, None] = None,
        processed_filename_extension: Union[str, None] = None,
        compression_opts: Union[int, None] = None,
        max_num_peaks: Union[int, None] = None,
    ) -> None:
        """
        TODO: Write documentation.

        Arguments:

            directory_for_processed_data (str): a relative or absolute path to the
                directory where the output files with the processed data will be
                written.

            node_rank (int): the rank of the OM node that will write the data in the
                output files.

            geometry (TypeDetector): a dictionary returned by the
                :func:`~om.utils.crystfel_geometry.load_crystfel_geometry` function),
                storing the geometry information.

            compression (Union[bool, None]): whether compression should be applied to
                the data in the output file.

            detector_data_type (str): the numpy type of the detector data that will
                be written to the output files.

            detector_data_shape (Tuple[int, int]): the numpy shape of the detector data
                that will be written to the output files.

            hdf5_fields (Dict[str, str]): a dictionary storing information about the
                internal HDF5 path where each data entry will be written.

                * The keys in the dictionary must store the names of data entries to
                  write.

                * The corresponding dictionary values must contain the internal HDF5
                  paths where the entries will be written.

            processed_filename_prefix (Union[str, None): a string that will be
                prepended to the name of the output files. Optional. If the value
                of this argument is None, the string 'processed_' will be used as
                prefix. Defaults to None.

            processed_filename_extension (Union[str, None]): a string that will
                appended to the name of the output files. Optional. If the value of
                this argument is None, the string 'h5' will be used as extension.
                Defaults to None.

            compression_opts (Union[int, None]): the compression level to be used if
                data compression is applied. This is argument is considered only if the
                'compression' argument is True, otherwise, the argument is ignored.
                Optional. If the value of this argument is None, the compression
                level will be set to 4. Defaults to None

            max_num_peaks (Union[int, None]): the maximum number of detected
                Bragg peaks that should be written in the HDF5 for each frame.
                Optional. If the value of this argument is None, only the first
                1024 detected peaks will be written in the output file for each frame.
                Defaults to None.
        """

        if processed_filename_prefix is None:
            processed_filename_prefix = "processed"
        if processed_filename_extension is None:
            processed_filename_extension = "h5"

        if detector_data_type is None:
            self._data_type: numpy.ndarray = numpy.float32
        else:
            self._data_type = numpy.dtype(detector_data_type)

        if max_num_peaks is None:
            self._max_num_peaks: int = 1024
        else:
            self._max_num_peaks = max_num_peaks

        self._processed_filename: pathlib.Path = pathlib.Path(
            directory_for_processed_data
        ).resolve() / "{0}_{1}.{2}".format(
            processed_filename_prefix, node_rank, processed_filename_extension
        )

        # TODO: fix cxiview (or even better, rewrite it)
        # Too get pixel size required for cxiview:
        self._pixel_size: float = (
            1 / geometry["panels"][tuple(geometry["panels"].keys())[0]]["res"]
        )

        compression_opts = None
        if compression is not None and compression_opts is None:
            compression_opts = 4

        # TODO: decide what to do if file exists
        self._h5file: Any = h5py.File(self._processed_filename, "w")

        self._resizable_datasets: Dict[str, Any] = {}

        if "detector_data" in hdf5_fields.keys():
            self._resizable_datasets["detector_data"] = self._h5file.create_dataset(
                name=hdf5_fields["detector_data"],
                shape=(0,) + detector_data_shape,
                maxshape=(None,) + detector_data_shape,
                dtype=detector_data_type,
                chunks=(1,) + detector_data_shape,
                compression=compression,
                compression_opts=compression_opts,
            )
        if "event_id" in hdf5_fields.keys():
            self._resizable_datasets["event_id"] = self._h5file.create_dataset(
                name=hdf5_fields["event_id"],
                shape=(0,),
                maxshape=(None,),
                dtype=h5py.special_dtype(vlen=str),
            )
        # Creating all requested 1D float64 datasets:
        key: str
        for key in ("timestamp", "beam_energy", "pixel_size", "detector_distance"):
            if key in hdf5_fields.keys():
                self._resizable_datasets[key] = self._h5file.create_dataset(
                    name=hdf5_fields[key],
                    shape=(0,),
                    maxshape=(None,),
                    dtype=numpy.float64,
                )
        if "peak_list" in hdf5_fields.keys():
            self._resizable_datasets.update(
                {
                    "npeaks": self._h5file.create_dataset(
                        name=hdf5_fields["peak_list"] + "/nPeaks",
                        shape=(0,),
                        maxshape=(None,),
                        dtype=numpy.int64,
                    ),
                    "fs": self._h5file.create_dataset(
                        name=hdf5_fields["peak_list"] + "/peakXPosRaw",
                        shape=(0, self._max_num_peaks),
                        maxshape=(None, self._max_num_peaks),
                        dtype=numpy.float32,
                    ),
                    "ss": self._h5file.create_dataset(
                        name=hdf5_fields["peak_list"] + "/peakYPosRaw",
                        shape=(0, self._max_num_peaks),
                        maxshape=(None, self._max_num_peaks),
                        dtype=numpy.float32,
                    ),
                    "intensity": self._h5file.create_dataset(
                        name=hdf5_fields["peak_list"] + "/peakTotalIntensity",
                        shape=(0, self._max_num_peaks),
                        maxshape=(None, self._max_num_peaks),
                        dtype=numpy.float32,
                    ),
                    "num_pixels": self._h5file.create_dataset(
                        name=hdf5_fields["peak_list"] + "/peakNPixels",
                        shape=(0, self._max_num_peaks),
                        maxshape=(None, self._max_num_peaks),
                        dtype=numpy.float32,
                    ),
                    "max_pixel_intensity": self._h5file.create_dataset(
                        name=hdf5_fields["peak_list"] + "/peakMaximumValue",
                        shape=(0, self._max_num_peaks),
                        maxshape=(None, self._max_num_peaks),
                        dtype=numpy.float32,
                    ),
                    "snr": self._h5file.create_dataset(
                        name=hdf5_fields["peak_list"] + "/peakSNR",
                        shape=(0, self._max_num_peaks),
                        maxshape=(None, self._max_num_peaks),
                        dtype=numpy.float32,
                    ),
                }
            )
        self._requested_datasets: Set[str] = set(hdf5_fields.keys())

        self._num_frames: int = 0

    def write_frame(self, processed_data: Dict[str, Any]) -> None:
        self._resize_datasets()
        # Datasets to write:
        fields: Set[str] = set(processed_data.keys()) & self._requested_datasets

        frame_num: int = self._num_frames - 1
        dataset_dict_keys_to_write: List[
            Literal[
                "detector_data",
                "event_id",
                "timestamp",
                "beam_energy",
                "detector_distance",
            ]
        ] = [
            "detector_data",
            "event_id",
            "timestamp",
            "beam_energy",
            "detector_distance",
        ]
        dataset_dict_key: str
        for dataset_dict_key in dataset_dict_keys_to_write:
            if dataset_dict_key in fields:
                self._resizable_datasets[dataset_dict_key][frame_num] = processed_data[
                    dataset_dict_key
                ]

        if "pixel_size" in self._requested_datasets:
            self._resizable_datasets["pixel_size"][frame_num] = self._pixel_size

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

    def close(self) -> None:
        self._h5file.close()
        print(
            "{0} frames saved in {1} file.".format(
                self._num_frames, self._processed_filename
            )
        )
        sys.stdout.flush()

    def get_current_filename(self) -> pathlib.Path:
        """
        Retrieves the path to the file being written.

        Returns:

            pathlib.Path: the path to the file currently being written.
        """
        return self._processed_filename

    def get_num_written_frames(self) -> int:
        """
        Retrieves the number of frames already written.

        Returns:

            int: the number of frames already written in the current file.
        """
        return self._num_frames - 1

    def _resize_datasets(self, extension_size: int = 1) -> None:
        # Extends all resizable datasets by the specified extension size
        dataset: Any
        for dataset in self._resizable_datasets.values():
            dataset.resize(self._num_frames + extension_size, axis=0)
        self._num_frames += extension_size


class SumHDF5Writer(object):
    """
    See documentation of the '__init__' function.
    """

    def __init__(
        self,
        directory_for_processed_data: str,
        powder_class: int,
        detector_data_shape: Tuple[int, int],
        sum_filename_prefix: Union[str, None] = None,
    ) -> None:
        """
        HDF5 writer for sum of frames.

        TODO: Add documentation

        Arguments:

            directory_for_processed_data (str): a relative or absolute path to the
                directory where the output files with the processed data will be
                written.

            powder_class (int): a unique identifier for the sum of frames being saved.

            detector_data_shape (Tuple[int, int]): the numpy shape of the detector data
                that will be written to the output files.

            sum_filename_prefix (Union[str, None): a string that will be prepended to
                the name of the output files. Optional. If the value of this argument
                is None, the string 'processed' will be used as
                prefix. Defaults to None.
        """

        if sum_filename_prefix is None:
            sum_filename_prefix = "processed"

        self._class_filename: pathlib.Path = pathlib.Path(
            directory_for_processed_data
        ).resolve() / "{0}-detector0-class{1}-sum.h5".format(
            sum_filename_prefix, powder_class
        )
        self._h5file: Any = h5py.File(self._class_filename, "w")

        self._h5file.create_dataset(
            name="/data/nframes", shape=(1,), dtype=numpy.int64,
        )
        self._h5file.create_dataset(
            name="/data/data", shape=detector_data_shape, dtype=numpy.float64,
        )
        self._h5file.create_dataset(
            name="/data/peakpowder", shape=detector_data_shape, dtype=numpy.float64,
        )
        self._h5file.close()

    def write_sums(
        self,
        num_frames: int,
        sum_frames: numpy.ndarray,
        virtual_powder_pattern: numpy.ndarray,
    ) -> None:
        """
        Writes accumulated frames and detected peaks into the output file.

        TODO: Add description

        Arguments:

            num_frames (int): the number of frames in the sum.

            sum_frames (numpy.ndarray): the sum of detector frames that will be written
                in the output file.

            virtual_powder_pattern (numpy.ndarray): the virtual powder patter that will
                be written in the output file.
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
        print(
            "Another application is reading the file {0} exclusively. Five attempts "
            "to open the files failed. Cannot update the file.".format(
                self._class_filename
            )
        )
