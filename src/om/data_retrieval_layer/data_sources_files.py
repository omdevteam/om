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
File-based data sources.

This module contains Data Source classes that deal with data stored in files.
"""
from typing import Any, Dict, Tuple, Type, TypeVar, Union, cast

import numpy
from numpy.typing import NDArray

from om.data_retrieval_layer.data_sources_common import OmJungfrau1MDataSourceMixin
from om.lib.exceptions import OmMissingDependencyError
from om.typing import OmDataSourceProtocol

try:
    from PIL import Image  # type: ignore
except ImportError:
    raise OmMissingDependencyError(
        "The following required module cannot be imported: PIL.Image"
    )

T = TypeVar("T")


class OmBaseFileDataSourceMixin:
    """
    See documentation of the `__init__` function.
    """

    def __new__(cls: Type[T], *args: Any, **kwargs: Any) -> T:
        if cls is OmBaseFileDataSourceMixin:
            raise TypeError(
                f"{cls.__name__} is a Mixin class and should not be instantiated"
            )
        return object.__new__(cls, *args, **kwargs)

    def __init__(
        self,
        *,
        data_source_name: str,
        parameters: Dict[str, Any],
    ):
        """
        Detector data frames from Pilatus single-frame CBF files.

        This class deals with the retrieval of Pilatus detector data frames from
        single-frame files written by the detector in CBF format.

        This class implements the interface described by its base Protocol class.
        Please see the documentation of that class for additional information about
        the interface.

        Arguments:

            data_source_name: A name that identifies the current data source. It is
                used, for example, in communications with the user or for the retrieval
                of a sensor's initialization parameters.

            parameters: An object storing OM's configuration parameters.
        """
        del data_source_name
        del parameters

    def initialize_data_source(self) -> None:
        """
        Initializes CBF file-based Pilatus detector data source.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        No initialization is needed to retrieve detector data frames from single-frame
        CBF files, so this function actually does nothing.
        """
        pass


class PilatusSingleFrameFiles(OmBaseFileDataSourceMixin, OmDataSourceProtocol):
    """
    See documentation of the `__init__` function.
    """

    def get_data(self, *, event: Dict[str, Any]) -> NDArray[numpy.float_]:
        """
        Retrieves an Eiger 16M detector data frame from files.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves the detector data frame associated with the provided
        file-based event, and returns the detector frame as a 2D array storing pixel
        information.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A detector data frame.
        """
        return cast(NDArray[numpy.float_], event["data"].data)


class Eiger16MFiles(OmBaseFileDataSourceMixin, OmDataSourceProtocol):
    """
    See documentation of the `__init__` function.
    """

    def get_data(self, *, event: Dict[str, Any]) -> NDArray[numpy.int_]:
        """
        Retrieves an Eiger 16M detector data frame from files.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves the detector data frame associated with the provided
        file-based event, and returns the detector frame as a 2D array storing pixel
        information.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A detector data frame.
        """
        return cast(
            NDArray[numpy.int_],
            event["additional_info"]["h5file"]["entry/data/data"][
                event["additional_info"]["index"]
            ],
        )


class RayonixMccdSingleFrameFiles(OmBaseFileDataSourceMixin, OmDataSourceProtocol):
    """
    See documentation of the `__init__` function.
    """

    def get_data(self, *, event: Dict[str, Any]) -> NDArray[numpy.int_]:
        """
        Retrieves a Rayonix MX340-HS detector data frame from files.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves the detector data frame associated with the provided
        file-based event, and returns the detector frame as a 2D array storing pixel
        information.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A detector data frame.
        """
        img: Any
        with Image.open(event["additional_info"]["full_path"]) as img:
            data: NDArray[numpy.int_] = numpy.array(img)
        return data


class Lambda1M5Files(OmBaseFileDataSourceMixin, OmDataSourceProtocol):
    """
    See documentation of the `__init__` function.
    """

    def get_data(
        self, *, event: Dict[str, Any]
    ) -> Union[NDArray[numpy.float_], NDArray[numpy.int_]]:
        """
        Retrieves a Lambda 1.5M detector data frame from files.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves the detector data frame associated with the provided
        file-based event, and returns the detector frame as a 2D array storing pixel
        information.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            Detector data frame.
        """
        h5files: Tuple[Any, Any] = event["additional_info"]["h5files"]
        index: Tuple[int, int] = event["additional_info"]["index"]
        return cast(
            NDArray[numpy.int_],
            numpy.concatenate(
                [
                    h5files[i]["/entry/instrument/detector/data"][index[i]]
                    for i in range(len(h5files))
                ]
            ),
        )


class TimestampFromFileModificationTime(
    OmBaseFileDataSourceMixin, OmDataSourceProtocol
):
    """ """

    def get_data(self, *, event: Dict[str, Any]) -> numpy.float64:
        """
        Retrieves timestamp information from the modification date of a file.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves the timestamp information associated with the provided
        file-based event. It uses as timestamp the last modification time of the file
        attached to the event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The timestamp of the data event.
        """
        return cast(numpy.float64, event["additional_info"]["file_modification_time"])


class TimestampJungfrau1MFiles(OmBaseFileDataSourceMixin, OmDataSourceProtocol):
    """
    See documentation of the `__init__` function.
    """

    def get_data(self, *, event: Dict[str, Any]) -> numpy.float64:
        """
        Retrieves the timestamp information for a Jungfrau 1M data event from files.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves the timestamp information associated with the provided
        file-based event. It computes the timestamp using the last modification time of
        the file attached to the event, modified by the internal clock reading of the
        frame associated to the event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            The timestamp for the Jungfrau 1M data event.
        """

        file_timestamp: numpy.float64 = numpy.float64(
            event["additional_info"]["file_timestamp"]
        )
        jf_clock_value: int = (
            event["additional_info"]["h5file"]["/entry/data/timestamp"][
                event["additional_info"]["index"]
            ][0]
            - event["additional_info"]["h5file"]["/entry/data/timestamp"][0][0]
        )
        # Jungfrau internal clock frequency in Hz
        jf_clock_frequency: int = 10000000
        return file_timestamp + jf_clock_value / jf_clock_frequency


class EventIdFromFilePath(OmBaseFileDataSourceMixin, OmDataSourceProtocol):
    """
    See documentation of the `__init__` function.
    """

    def get_data(self, *, event: Dict[str, Any]) -> str:
        """
        Retrieves the event identifier from the full path of a file.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves a unique event identifier for the provided file-based\
        event, using as identifier the full path of the file attached to the event.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A unique event identifier.
        """
        return cast(str, event["additional_info"]["full_path"])


class EventIdJungfrau1MFiles(OmBaseFileDataSourceMixin, OmDataSourceProtocol):
    """
    See documentation of the `__init__` function.
    """

    def get_data(self, *, event: Dict[str, Any]) -> str:
        """
        Retrieves the event identifier for a Jungfrau 1M data event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function constructs the event identifier for the provided file-based event
        by joining the following elements in a single string, with the "//" symbol
        placed between them.

        * The full path to the HDF5 file attached to the event.

        * The index, within the file, of the frame being processed.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A unique event identifier.
        """
        filename: str = event["additional_info"]["h5file"].filename
        index: str = event["additional_info"]["index"]
        return f"{filename} // {index:05d}"


class EventIdEiger16MFiles(OmBaseFileDataSourceMixin, OmDataSourceProtocol):
    """
    See documentation of the `__init__` function.
    """

    def get_data(self, *, event: Dict[str, Any]) -> str:
        """
        Retrieves the event identifier for an Eiger 16M data event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function constructs the event identifier for the provided file-based event
        by joining the following elements in a single string, with the "//" symbol
        placed between them.

        * The full path to the HDF5 file attached to the provided event.

        * The index, within the file, of the frame being processed.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A unique event identifier.
        """
        filename: str = event["additional_info"]["full_path"]
        index: str = event["additional_info"]["index"]
        return f"{filename} // {index:04d}"


class EventIdLambda1M5Files(OmBaseFileDataSourceMixin, OmDataSourceProtocol):
    """
    See documentation of the `__init__` function.
    """

    def get_data(self, *, event: Dict[str, Any]) -> str:
        """
        Retrieves the event identifier for an Lambda 1.5M data event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function constructs the event identifier for the provided file-based event
        by joining the following elements in a single string, with the "//" symbol
        placed between them.

        * The full path to the HDF5 file attached to the event and written by the first
          detector module,

        * The index, within the file, of the frame being processed.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            A unique event identifier.
        """
        filename: str = event["additional_info"]["full_path"]
        index: str = event["additional_info"]["index"][0]
        return f"{filename} // {index:05d}"


class Jungfrau1MFiles(OmJungfrau1MDataSourceMixin, OmDataSourceProtocol):
    """
    See documentation of the `__init__` function.
    """

    def get_data(
        self, *, event: Dict[str, Any]
    ) -> Union[NDArray[numpy.float_], NDArray[numpy.int_]]:
        """
        Retrieves a Jungfrau 1M detector data frame from a file-based event.

        Please see the documentation of the base Protocol class for additional
        information about this method.

        This function retrieves the detector data frame associated with the provided
        file-based event, and returns the detector frame as a 2D array storing pixel
        information. The data is retrieved in calibrated or non-calibrated form
        depending on the value of the `{source_protocols_name}_calibration` entry in
        OM's `data_retrieval_layer` configuration parameter group.

        Arguments:

            event: A dictionary storing the event data.

        Returns:

            One detector data frame.
        """
        data: NDArray[numpy.int_] = event["additional_info"]["h5file"][
            "/entry/data/data"
        ][event["additional_info"]["index"]]

        if self._calibrated_data_required:
            return self._calibration.apply_calibration(data=data)
        else:
            return data
