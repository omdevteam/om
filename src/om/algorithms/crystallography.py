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
Algorithms for the processing of crystallography data.

This module contains algorithms that perform data processing operations related to
serial crystallography (peak finding, etc.). Additionally, it contains several typed
dictionaries that store the data needed or produced by these algorithms.

"""
import sys
from typing import Any, Dict, List, Tuple, Union

import h5py  # type: ignore
import numpy
from numpy.typing import NDArray
from typing_extensions import TypedDict

from om.lib.peakfinder8_extension import peakfinder_8  # type: ignore
from om.utils import parameters as param_utils


class TypePeakfinder8Info(TypedDict, total=True):
    """
    Detector layout information for the peakfinder8 algorithm.

    This typed dictionary stores information about the internal data layout of a
    detector data frame (number and size of ASICs, etc.). The information
    is needed by the
    [`Peakfinder8PeakDetection`][om.algorithms.crystallography.Peakfinder8PeakDetection]
    algorithm, and is usually retrieved via the
    [`get_peakfinder8_info`][om.algorithms.crystallography.get_peakfinder8_info]
    function.

    Attributes:

        asic_nx: The fs size in pixels of each detector panel in the data frame.

        asic_ny: The ss size in pixels of each detector panel in the data frame.

        nasics_x: The number of detector panels along the fs axis of the data frame.

        nasics_y: The number of detector panels along the ss axis of the data frame.
    """

    asic_nx: int
    asic_ny: int
    nasics_x: int
    nasics_y: int


class TypePeakList(TypedDict, total=True):
    """
    Detected peaks information.

    This typed dictionary stores information about a set of peaks found by the
    [`Peakfinder8PeakDetection`][om.algorithms.crystallography.Peakfinder8PeakDetection]
    algorithm in a detector data frame.

    Attributes:

        num_peaks: The number of peaks that were detected in the data frame.

        fs: A list of fractional fs indexes that locate the detected peaks in the data
            frame.

        ss: A list of fractional ss indexes that locate the detected peaks in the data
            frame.

        intensity: A list of integrated intensities for the detected peaks.

        num_pixels: A list storing the number of pixels that make up each detected
            peak.

        max_pixel_intensity: A list storing, for each peak, the value of the pixel with
            the maximum intensity.

        snr: A list storing  the signal-to-noise ratio of each detected peak.
    """

    num_peaks: int
    fs: List[float]
    ss: List[float]
    intensity: List[float]
    num_pixels: List[float]
    max_pixel_intensity: List[float]
    snr: List[float]


def get_peakfinder8_info(*, detector_type: str) -> TypePeakfinder8Info:
    """
    Gets the peakfinder8 information for a detector.

    This function retrieves, for supported detector types, the data layout information
    needed by the
    [`Peakfinder8PeakDetection`][om.algorithms.crystallography.Peakfinder8PeakDetection]
    algorithm.

    Arguments:

        detector_type: The type of detector for which the information needs to be
            retrieved. The following detector types are currently supported:

            * `cspad`: The CSPAD detector used at the CXI beamline of the LCLS facility
              before 2020.

            * `pilatus`: The Pilatus detector used at the P11 beamline of the PETRA III
              facility.

            * `jungfrau1M`: The 1M version of the Jungfrau detector used at the PETRA
              III facility.

            * `jungfrau4M`: The 4M version of the Jungfrau detector used at the CXI
              beamline of the LCLS facility.

            * `epix10k2M`: The 2M version of the Epix10KA detector used at the MFX
              beamline of the LCLS facility.

            * `rayonix`: The Rayonix detector used at the MFX beamline of the LCLS
              facility.

            * `eiger16M`: The 16M version of the Eiger2 detector used at the PETRA III
              facility.

    Returns:

        A dictionary storing the data layout information.
    """
    if detector_type == "cspad":
        peakfinder8_info: TypePeakfinder8Info = {
            "asic_nx": 194,
            "asic_ny": 185,
            "nasics_x": 8,
            "nasics_y": 8,
        }
    elif detector_type == "pilatus":
        peakfinder8_info = {
            "asic_nx": 2463,
            "asic_ny": 2527,
            "nasics_x": 1,
            "nasics_y": 1,
        }
    elif detector_type == "jungfrau1M":
        peakfinder8_info = {
            "asic_nx": 1024,
            "asic_ny": 512,
            "nasics_x": 1,
            "nasics_y": 2,
        }
    elif detector_type == "jungfrau4M":
        peakfinder8_info = {
            "asic_nx": 1024,
            "asic_ny": 512,
            "nasics_x": 1,
            "nasics_y": 8,
        }
    elif detector_type == "epix10k2M":
        peakfinder8_info = {
            "asic_nx": 384,
            "asic_ny": 352,
            "nasics_x": 1,
            "nasics_y": 16,
        }
    elif detector_type == "rayonix":
        peakfinder8_info = {
            "asic_nx": 1920,
            "asic_ny": 1920,
            "nasics_x": 1,
            "nasics_y": 1,
        }
    elif detector_type == "eiger16M":
        peakfinder8_info = {
            "asic_nx": 4148,
            "asic_ny": 4362,
            "nasics_x": 1,
            "nasics_y": 1,
        }
    else:
        raise RuntimeError(
            "The peakfinder8 information for the {0} detector "
            "cannot be retrieved: detector type unknown"
        )

    return peakfinder8_info


class Peakfinder8PeakDetection:
    """
    See documentation of the `__init__` function.
    """

    def __init__(
        self,
        *,
        radius_pixel_map: NDArray[numpy.float_],
        parameters: Dict[str, Any],
    ) -> None:
        """
        Peakfinder8 algorithm for peak detection.

        This algorithm stores the parameters required to perform peak-finding on a
        detector data frame using the `peakfinder8` strategy. It can then detect peaks
        in a provided frame. The `peakfinder8` peak detection approach is described in
        the following publication:

        A. Barty, R. A. Kirian, F. R. N. C. Maia, M. Hantke, C. H. Yoon, T. A. White,
        and H. N. Chapman, "Cheetah: software for high-throughput reduction and
        analysis of serial femtosecond x-ray diffraction data", J Appl  Crystallogr,
        vol. 47, pp. 1118-1131 (2014).

        Arguments:

            parameters: A set of OM configuration parameters collected together in a
                parameter group. The parameter group must contain the following
                entries:

                * `max_num_peaks`: The maximum number of peaks that will be retrieved
                  from each data frame. Additional peaks will be ignored.

                * `asic_nx`: The fs size, in pixels, of each detector panel in the data
                  frame (Can be retrieved from a
                  [TypePeakfinder8Info][om.algorithms.crystallography.TypePeakfinder8Info]
                  dictionary).

                * `asic_ny`: The ss size, in pixels, of each detector panel in the data
                  frame (Can be retrieved from a
                  [TypePeakfinder8Info][om.algorithms.crystallography.TypePeakfinder8Info]
                  dictionary).

                * `nasics_x`: The number of detector panels along the fs axis of the
                  data frame (Can be retrieved from a
                  [TypePeakfinder8Info][om.algorithms.crystallography.TypePeakfinder8Info]
                  dictionary).

                * `nasics_y`: The number of detector panels along the ss axis of the
                  data frame (Can be retrieved from a
                  [TypePeakfinder8Info][om.algorithms.crystallography.TypePeakfinder8Info]
                  dictionary).

                * `adc_threshold`: The minimum ADC threshold for peak detection.

                * `minimum_snr`: The minimum signal-to-noise ratio for peak detection.

                * `min_pixel_count`: The minimum size of a peak (in pixels).

                * `max_pixel_count`: The maximum size of a peak (in pixels).

                * `local_bg_radius`: The radius, in pixels, for the estimation of the
                  local background.

                * `min_res`: The minimum resolution (in pixels) for a peak.

                * `max_res`: The maximum resolution (in pixels) for a peak.

                * `bad_pixel_map_filename`: The relative or absolute path to an HDF5
                   file containing a bad pixel map. The map can be used to exclude
                   regions of the data frame from the peak search. If the value of this
                   entry is None, the search will extend to the full frame. Defaults to
                   None.

                    - The map must be a numpy array with the same shape as the data
                      frame on which the algorithm will be applied.

                    - Each pixel in the map must have a value of either 0, meaning that
                      the corresponding pixel in the data frame should be ignored, or
                      1, meaning that the corresponding pixel should be included in the
                      peak search.

                    - The map is only used to exclude areas from the peak search: the
                      data is not modified in any way.

                * `bad_pixel_map_hdf5_path`: The internal HDF5 path to the data block
                  where the bad pixel map data is located. Defaults to None.

                    * If the `bad_pixel_map_filename` entry is not None, this entry
                      must also be provided, and cannot be None. Otherwise it is
                      ignored.

            radius_pixel_map: A numpy array with radius information for the detector
                data frame.

                * The array must have the same shape as the data frame on which the
                  algorithm will be applied.

                * Each element of the array must store, for the corresponding pixel in
                  the data frame, its distance (in pixels) from the origin of the
                  detector reference system (usually the center of the detector).
        """
        peakfinder8_info: TypePeakfinder8Info = get_peakfinder8_info(
            detector_type=param_utils.get_parameter_from_parameter_group(
                group=parameters,
                parameter="detector_type",
                parameter_type=str,
                required=True,
            )
        )
        self._asic_nx: int = peakfinder8_info["asic_nx"]
        self._asic_ny: int = peakfinder8_info["asic_ny"]
        self._nasics_x: int = peakfinder8_info["nasics_x"]
        self._nasics_y: int = peakfinder8_info["nasics_y"]
        self._max_num_peaks: int = param_utils.get_parameter_from_parameter_group(
            group=parameters,
            parameter="max_num_peaks",
            parameter_type=int,
            required=True,
        )
        self._adc_threshold: float = param_utils.get_parameter_from_parameter_group(
            group=parameters,
            parameter="adc_threshold",
            parameter_type=float,
            required=True,
        )
        self._minimum_snr: float = param_utils.get_parameter_from_parameter_group(
            group=parameters,
            parameter="minimum_snr",
            parameter_type=float,
            required=True,
        )
        self._min_pixel_count: int = param_utils.get_parameter_from_parameter_group(
            group=parameters,
            parameter="min_pixel_count",
            parameter_type=int,
            required=True,
        )
        self._max_pixel_count: int = param_utils.get_parameter_from_parameter_group(
            group=parameters,
            parameter="max_pixel_count",
            parameter_type=int,
            required=True,
        )
        self._local_bg_radius: int = param_utils.get_parameter_from_parameter_group(
            group=parameters,
            parameter="local_bg_radius",
            parameter_type=int,
            required=True,
        )
        self._min_res: int = param_utils.get_parameter_from_parameter_group(
            group=parameters,
            parameter="min_res",
            parameter_type=int,
            required=True,
        )
        self._max_res: int = param_utils.get_parameter_from_parameter_group(
            group=parameters,
            parameter="max_res",
            parameter_type=int,
            required=True,
        )
        bad_pixel_map_filename: Union[
            str, None
        ] = param_utils.get_parameter_from_parameter_group(
            group=parameters,
            parameter="bad_pixel_map_filename",
            parameter_type=str,
        )
        if bad_pixel_map_filename is not None:
            bad_pixel_map_hdf5_path: Union[
                str, None
            ] = param_utils.get_parameter_from_parameter_group(
                group=parameters,
                parameter="bad_pixel_map_hdf5_path",
                parameter_type=str,
                required=True,
            )
        else:
            bad_pixel_map_hdf5_path = None

        if bad_pixel_map_filename is not None:
            try:
                map_hdf5_file_handle: Any
                with h5py.File(bad_pixel_map_filename, "r") as map_hdf5_file_handle:
                    self._bad_pixel_map: Union[
                        NDArray[numpy.int_], None
                    ] = map_hdf5_file_handle[bad_pixel_map_hdf5_path][:]
            except (IOError, OSError, KeyError) as exc:
                exc_type, exc_value = sys.exc_info()[:2]
                # TODO: Fix type check
                raise RuntimeError(
                    "The following error occurred while reading the "  # type: ignore
                    f"{bad_pixel_map_hdf5_path} field from the "
                    f"{bad_pixel_map_filename} bad pixel map HDF5 file:"
                    f"{exc_type.__name__}: {exc_value}"
                ) from exc
        else:
            self._bad_pixel_map = None

        self._mask: Union[NDArray[numpy.int_], None] = None
        self._radius_pixel_map: NDArray[numpy.float_] = radius_pixel_map

    def set_peakfinder8_info(self, peakfinder8_info: TypePeakfinder8Info) -> None:
        self._asic_nx = peakfinder8_info["asic_nx"]
        self._asic_ny = peakfinder8_info["asic_ny"]
        self._nasics_x = peakfinder8_info["nasics_x"]
        self._nasics_y = peakfinder8_info["nasics_y"]

    def get_bad_pixel_mask(self) -> Union[NDArray[numpy.int_], None]:
        return self._bad_pixel_mask

    def set_bad_pixel_mask(
        self, bad_pixel_mask: Union[NDArray[numpy.int_], None]
    ) -> None:
        self._bad_pixel_mask = bad_pixel_mask

    def set_radius_pixel_map(self, radius_pixel_map: NDArray[numpy.float_]) -> None:
        self._radius_pixel_map = radius_pixel_map.astype(numpy.float32)

    def get_adc_thresh(self) -> float:
        """
        Gets the minimum ADC threshold for peak detection.

        This function returns the minimum ADC threshold currently used by the algorithm
        for peak detection.

        Returns:

            The minimum ADC threshold currently used by the algorithm.
        """
        return self._minimum_snr

    def set_adc_thresh(self, *, adc_thresh: float) -> None:
        """
        Sets the current minimum ADC threshold for peak detection.

        This function sets the minimum ADC threshold that the algorithm should use for
        peak detection. Any future call to the
        [`find_peaks`][om.algorithms.crystallography.Peakfinder8PeakDetection.find_peaks]
        method will use, for the `adc_thresh` parameter, the value provided here.

        Arguments:

            adc_thresh: The new value of the minimum ADC threshold for peak detection.
        """
        self._adc_thresh = adc_thresh

    def get_minimum_snr(self) -> float:
        """
        Gets the current minimum signal-to-noise ratio for peak detection.

        This function returns the minimum signal-to-noise ratio currently used by
        the algorithm for peak detection.

        Returns:

            The minimum singal-to-noise ratio currently used by the algorithm.
        """
        return self._minimum_snr

    def set_minimum_snr(self, *, minimum_snr: float) -> None:
        """
        Sets the minimum signal-to-noise ratio for peak detection.

        This function sets the minimum signal-to-noise ratio that the algorithm should
        use for peak detection. Any future call to the
        [`find_peaks`][om.algorithms.crystallography.Peakfinder8PeakDetection.find_peaks]
        method will use, for the `minimum_snr` algorithm parameter, the value provided
        here.

        Arguments:

            minimum_snr: The new value of the minimum singal-to-noise ratio for peak
                detection.
        """
        self._minimum_snr = minimum_snr

    def get_min_pixel_count(self) -> int:
        """
        Gets the current minimum size for a peak (in pixels).

        This function returns the minimum size, in pixels, that the algorithm currently
        expects a peak to have.

        Returns:

            The current minimum size for a peak (in pixels).
        """
        return self._min_pixel_count

    def set_min_pixel_count(self, *, min_pixel_count: int) -> None:
        """
        Sets the minimum size for a peak (in pixels).

        This function sets the minimum size, in pixels, that the algorithm should
        expect a peak to have. Any future call to the
        [`find_peaks`][om.algorithms.crystallography.Peakfinder8PeakDetection.find_peaks]
        method will use, for the `min_pixel_count` parameter, the value provided here.

        Arguments:

            min_pixel_count: The new minimum size for a peak (in pixels).
        """
        self._min_pixel_count = min_pixel_count

    def get_max_pixel_count(self) -> int:
        """
        Gets the current maximum size for a peak (in pixels).

        This function returns the maximum size, in pixels, that the algorithm
        currently expects a peak to have.

        Returns:

            The current maximum size for a peak (in pixels).
        """
        return self._max_pixel_count

    def set_max_pixel_count(self, *, max_pixel_count: int) -> None:
        """
        Sets the maximum size for a peak (in pixels).

        This function sets the maximum size, in pixels, that the algorithm should
        expect a peak to have. Any future call to the
        [`find_peaks`][om.algorithms.crystallography.Peakfinder8PeakDetection.find_peaks]
        method will use, for the `max_pixel_count` parameter, the value provided here.

        Arguments:

            max_pixel_count: The new maximum size for a peak (in pixels).
        """
        self._max_pixel_count = max_pixel_count

    def get_local_bg_radius(self) -> int:
        """
        Gets the radius, in pixels, currently used to estimate of the local background.

        This function returns the radius (in pixels) currently used by the algorithm to
        estimate the local background.

        Returns:

            The radius, in pixels, currently used for the estimation of the local
            background.
        """
        return self._local_bg_radius

    def set_local_bg_radius(self, *, local_bg_radius: int) -> None:
        """
        Sets the radius, in pixels, for the estimation of the local background.

        This function sets the radius (in pixels) that the algorithm should use to
        estimate the local background. Any future call to the
        [`find_peaks`][om.algorithms.crystallography.Peakfinder8PeakDetection.find_peaks]
        method will use, for the `local_bg_radius` parameter, the value provided here.

        Arguments:

            local_bg_radius: The new radius, in pixels, that should be used for the
                estimation of the local background.
        """
        self._local_bg_radius = local_bg_radius

    def get_min_res(self) -> int:
        """
        Gets the minimum resolution for a peak in pixels.

        This function returns the current minimum resolution (in pixels) that allows a
        peak to be detected by the algorithm.

        Returns:

            The minimum resolution (in pixels) for a peak.
        """
        return self._min_res

    def set_min_res(self, *, min_res: int) -> None:
        """
        Sets the minimum resolution for a peak (in pixels).

        This function sets the minimum resolution, in pixels, that allows a peak to be
        detected by the algorithm. Any future call to the
        [`find_peaks`][om.algorithms.crystallography.Peakfinder8PeakDetection.find_peaks]
        method will use, for the `min_res` parameter, the value provided here.

        Arguments:

            min_res: The new minimum resolution (in pixels) for a peak.
        """
        self._min_res = min_res
        self._mask = None

    def get_max_res(self) -> int:
        """
        Gets the maximum resolution a peak (in pixels).

        This function returns the current maximum resolution (in pixels) that allows a
        peak to be detected by the algorithm.

        Returns:

            The maximum resolution (in pixels) for a peak.
        """
        return self._max_res

    def set_max_res(self, max_res: int) -> None:
        """
        Sets the maximum resolution for a peak (in pixels).

        This function sets the maximum resolution, in pixels, that allows a peak to be
        detected by the algorithm. Any future call to the
        [`find_peaks`][om.algorithms.crystallography.Peakfinder8PeakDetection.find_peaks]
        method will use, for the `max_res` parameter, the value provided here.

        Arguments:

            max_res: The new maximum resolution (in pixels) for a peak.
        """
        self._max_res = max_res
        self._mask = None

    def find_peaks(self, *, data: NDArray[numpy.float_]) -> TypePeakList:
        """
        Finds peaks in a detector data frame.

        This function detects peaks in a provided data frame, and returns information
        about their location, size and intensity.

        Arguments:

            data: The detector data frame on which the peak-finding operation must be
                performed.

        Returns:

            A [TypePeakList][om.algorithms.crystallography.TypePeakList] dictionary
            with information about the detected peaks.
        """
        if self._mask is None:
            if self._bad_pixel_mask is None:
                self._mask = numpy.ones_like(data, dtype=numpy.int8)
            else:
                self._mask = self._bad_pixel_mask.astype(numpy.int8)

            self._mask[numpy.where(self._radius_pixel_map < self._min_res)] = 0
            self._mask[numpy.where(self._radius_pixel_map > self._max_res)] = 0

        peak_list: Tuple[List[float], ...] = peakfinder_8(
            self._max_num_peaks,
            data.astype(numpy.float32),
            self._mask,
            self._radius_pixel_map,
            self._asic_nx,
            self._asic_ny,
            self._nasics_x,
            self._nasics_y,
            self._adc_thresh,
            self._minimum_snr,
            self._min_pixel_count,
            self._max_pixel_count,
            self._local_bg_radius,
        )

        return {
            "num_peaks": len(peak_list[0]),
            "fs": peak_list[0],
            "ss": peak_list[1],
            "intensity": peak_list[2],
            "num_pixels": peak_list[4],
            "max_pixel_intensity": peak_list[5],
            "snr": peak_list[6],
        }
