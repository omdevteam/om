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
import random
import sys
from typing import Any, Dict, List, Tuple, TypedDict, Union

import numpy
import scipy  # type: ignore
from numpy.typing import NDArray

from om.lib.parameters import get_parameter_from_parameter_group

from ._crystallography import peakfinder_8  # type: ignore


def _read_profile(*, profile_filename: str) -> Union[NDArray[numpy.float_], None]:
    if profile_filename is not None:
        try:
            return numpy.loadtxt(profile_filename)
        except (IOError, OSError, KeyError) as exc:
            # TODO: type this
            exc_type, exc_value = sys.exc_info()[:2]
            raise RuntimeError(
                "The following error occurred while reading the {0} profile file."
                "file: {1}: {2}".format(
                    profile_filename,
                    exc_type.__name__,  # type: ignore
                    exc_value,
                )
            ) from exc
    else:
        return None


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

            * `eiger16M`: The 16M version of the Eiger2 detector used at the PETRA III
            facility.

            * `epix10k2M`: The 2M version of the Epix10KA detector used at the MFX
            beamline of the LCLS facility.

            * `jungfrau1M`: The 1M version of the Jungfrau detector used at the PETRA
            III facility.

            * `jungfrau4M`: The 4M version of the Jungfrau detector used at the CXI
            beamline of the LCLS facility.

            * `lambda1M5`: The Lambda detector used at the P09 beamline of the PETRA
            III facility.

            * `pilatus`: The Pilatus detector used at the P11 beamline of the PETRA III
            facility.

            * `rayonix`: The Rayonix detector used at the MFX beamline of the LCLS
            facility.

            * `rayonix16M`: The 16M version of the Rayonix detector used at the BioCars
            beamline of the APS facility.

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
    elif detector_type == "rayonix16M":
        peakfinder8_info = {
            "asic_nx": 3840,
            "asic_ny": 3840,
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
    elif detector_type == "lambda1M5":
        peakfinder8_info = {
            "asic_nx": 1556,
            "asic_ny": 516,
            "nasics_x": 1,
            "nasics_y": 2,
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
        bad_pixel_map: Union[NDArray[numpy.int_], None],
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
            detector_type=get_parameter_from_parameter_group(
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
        self._max_num_peaks: int = get_parameter_from_parameter_group(
            group=parameters,
            parameter="max_num_peaks",
            parameter_type=int,
            required=True,
        )
        self._adc_thresh: float = get_parameter_from_parameter_group(
            group=parameters,
            parameter="adc_threshold",
            parameter_type=float,
            required=True,
        )
        self._minimum_snr: float = get_parameter_from_parameter_group(
            group=parameters,
            parameter="minimum_snr",
            parameter_type=float,
            required=True,
        )
        self._min_pixel_count: int = get_parameter_from_parameter_group(
            group=parameters,
            parameter="min_pixel_count",
            parameter_type=int,
            required=True,
        )
        self._max_pixel_count: int = get_parameter_from_parameter_group(
            group=parameters,
            parameter="max_pixel_count",
            parameter_type=int,
            required=True,
        )
        self._local_bg_radius: int = get_parameter_from_parameter_group(
            group=parameters,
            parameter="local_bg_radius",
            parameter_type=int,
            required=True,
        )
        self._min_res: int = get_parameter_from_parameter_group(
            group=parameters,
            parameter="min_res",
            parameter_type=int,
            required=True,
        )
        self._max_res: int = get_parameter_from_parameter_group(
            group=parameters,
            parameter="max_res",
            parameter_type=int,
            required=True,
        )

        self._bad_pixel_map = bad_pixel_map
        self._mask: Union[NDArray[numpy.int_], None] = None
        self._radius_pixel_map: NDArray[numpy.float_] = radius_pixel_map

        self._radial_stats_pixel_index: Union[None, NDArray[numpy.int_]] = None
        self._radial_stats_radius: Union[None, NDArray[numpy.int_]] = None
        self._radial_stats_num_pixels: int = 0
        fast_mode: Union[bool, None] = get_parameter_from_parameter_group(
            group=parameters,
            parameter="fast_mode",
            parameter_type=bool,
            required=False,
        )
        if fast_mode is None:
            self._fast_mode: bool = False
        else:
            self._fast_mode = fast_mode

        if self._fast_mode is True:
            self._num_pixels_per_bin: int = get_parameter_from_parameter_group(
                group=parameters,
                parameter="rstats_numpix_per_bin",
                parameter_type=int,
                required=False,
                default=100,
            )
            self._compute_radial_stats_pixels(
                num_pixels_per_bin=self._num_pixels_per_bin
            )

    def _compute_radial_stats_pixels(self, *, num_pixels_per_bin: int) -> None:
        radius_pixel_map_as_int: NDArray[numpy.int_] = (
            numpy.rint(self._radius_pixel_map).astype(int).ravel()
        )
        peak_index: List[int] = []
        radius: List[int] = []
        idx: NDArray[numpy.int_]
        for idx in numpy.split(
            numpy.argsort(radius_pixel_map_as_int, kind="mergesort"),
            numpy.cumsum(numpy.bincount(radius_pixel_map_as_int)[:-1]),
        ):
            if len(idx) < num_pixels_per_bin:
                peak_index.extend(idx)
                radius.extend(radius_pixel_map_as_int[(idx,)])
            else:
                idx_sample = random.sample(list(idx), num_pixels_per_bin)
                peak_index.extend(idx_sample)
                radius.extend(radius_pixel_map_as_int[(idx_sample,)])
        self._radial_stats_pixel_index = numpy.array(peak_index).astype(numpy.int32)
        self._radial_stats_radius = numpy.array(radius).astype(numpy.int32)
        self._radial_stats_num_pixels = self._radial_stats_pixel_index.shape[0]

    def set_peakfinder8_info(self, peakfinder8_info: TypePeakfinder8Info) -> None:
        self._asic_nx = peakfinder8_info["asic_nx"]
        self._asic_ny = peakfinder8_info["asic_ny"]
        self._nasics_x = peakfinder8_info["nasics_x"]
        self._nasics_y = peakfinder8_info["nasics_y"]

    def get_bad_pixel_map(self) -> Union[NDArray[numpy.int_], None]:
        return self._bad_pixel_map

    def set_bad_pixel_map(
        self, bad_pixel_map: Union[NDArray[numpy.int_], None]
    ) -> None:
        self._bad_pixel_map = bad_pixel_map

    def set_radius_pixel_map(self, radius_pixel_map: NDArray[numpy.float_]) -> None:
        self._radius_pixel_map = radius_pixel_map.astype(numpy.float32)
        self._compute_radial_stats_pixels(num_pixels_per_bin=self._num_pixels_per_bin)

    def get_adc_thresh(self) -> float:
        """
        Gets the minimum ADC threshold for peak detection.

        This function returns the minimum ADC threshold currently used by the algorithm
        for peak detection.

        Returns:

            The minimum ADC threshold currently used by the algorithm.
        """
        return self._adc_thresh

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

            The minimum signal-to-noise ratio currently used by the algorithm.
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

            minimum_snr: The new value of the minimum signal-to-noise ratio for peak
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

    def find_peaks(
        self, *, data: Union[NDArray[numpy.int_], NDArray[numpy.float_]]
    ) -> TypePeakList:
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
            if self._bad_pixel_map is None:
                self._mask = numpy.ones_like(data, dtype=numpy.int8)
            else:
                self._mask = self._bad_pixel_map.astype(numpy.int8)

            self._mask[numpy.where(self._radius_pixel_map < self._min_res)] = 0
            self._mask[numpy.where(self._radius_pixel_map > self._max_res)] = 0

        peak_list: Tuple[List[float], ...] = peakfinder_8(
            self._max_num_peaks,
            data.astype(numpy.float32),
            self._mask,
            self._radius_pixel_map,
            self._radial_stats_num_pixels,
            self._radial_stats_pixel_index,
            self._radial_stats_radius,
            int(self._fast_mode),
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


class RadialProfileAnalysisWithSampleDetection:
    """
    See documentation of the '__init__' function.
    """

    def __init__(
        self,
        *,
        radius_pixel_map: NDArray[numpy.float_],
        swaxs_parameters: Dict[str, Any],
        bad_pixel_map: Union[NDArray[numpy.int_], None],
    ) -> None:
        """
        Algorithm for aqueous droplet detection.

        This class stores the parameters needed by a droplet detection algorithm, and
        detects droplets in a detector data frame upon request. The algorithm has two
        modes of operation. The simple mode measures the ratio of the water peak height
        to the sample peak height. The more complex mode uses least squares to fit the
        radial profile with a pure sample and water profile and decide if its sample or
        water.

        Arguments:

            sample_detection_enabled: Whether to apply or not droplet detection.

            save_radials: Whether or not to save radials and droplet detection results
                in an hdf5 file. This should be False if running on shared memory, but
                can be True when accessing data on disk, and can be useful for creating
                pure sample and water profiles.

            sample_peak_min_i: The minimum radial distance from the center of the
                detector reference system defining the sample peak (in pixels).

            sample_peak_max_i: The maximum radial distance from the center of the
                detector reference system defining the sample peak (in pixels).

            water_peak_min_i: The minimum radial distance from the center of the
                detector reference system defining the water peak (in pixels).

            water_peak_max_i: The maximum radial distance from the center of the
                detector reference system defining the water peak (in pixels).

            sample_profile: The radial profile for pure sample.

            water_profile: The radial profile for pure water or buffer.

            threshold:

            radius_pixel_map: A numpy array with radius information.

                * The array must have the same shape as the data frame on which the
                  algorithm will be applied.

                * Each element of the array must store, for the corresponding pixel in
                  the data frame, the distance in pixels from the origin
                  of the detector reference system (usually the center of the
                  detector).

            bad_pixel_map: An array storing a bad pixel map. The map can be used to
                mark areas of the data frame that must be excluded from the peak
                search. If the value of this argument is None, no area will be excluded
                from the search. Defaults to None.

                * The map must be a numpy array of the same shape as the data frame on
                  which the algorithm will be applied.

                * Each pixel in the map must have a value of either 0, meaning that
                  the corresponding pixel in the data frame should be ignored, or 1,
                  meaning that the corresponding pixel should be included in the
                  search.

                * The map is only used to exclude areas from the peak search: the data
                  is not modified in any way.

        #TODO: Fix documentation
        """

        self._sample_peak_min_bin: int = get_parameter_from_parameter_group(
            group=swaxs_parameters,
            parameter="sample_peak_min_bin",
            parameter_type=int,
            required=True,
        )
        self._sample_peak_max_bin: int = get_parameter_from_parameter_group(
            group=swaxs_parameters,
            parameter="sample_peak_max_bin",
            parameter_type=int,
            required=True,
        )
        self._water_peak_min_bin: int = get_parameter_from_parameter_group(
            group=swaxs_parameters,
            parameter="water_peak_min_bin",
            parameter_type=int,
            required=True,
        )
        self._water_peak_max_bin: int = get_parameter_from_parameter_group(
            group=swaxs_parameters,
            parameter="water_peak_max_bin",
            parameter_type=int,
            required=True,
        )
        self._threshold_min: float = get_parameter_from_parameter_group(
            group=swaxs_parameters,
            parameter="minimum_sample_to_water_ratio_for_sample",
            parameter_type=float,
            required=True,
        )
        self._threshold_max: float = get_parameter_from_parameter_group(
            group=swaxs_parameters,
            parameter="maximum_sample_to_water_ratio_for_sample",
            parameter_type=float,
            required=True,
        )
        sample_profile_filename: str = get_parameter_from_parameter_group(
            group=swaxs_parameters,
            parameter="sample_profile_filename",
            parameter_type=str,
        )

        if sample_profile_filename is not None:
            self._sample_profile = _read_profile(
                profile_filename=sample_profile_filename
            )

        water_profile_filename: str = get_parameter_from_parameter_group(
            group=swaxs_parameters,
            parameter="water_profile_filename",
            parameter_type=str,
        )

        if water_profile_filename is not None:
            self._water_profile = _read_profile(profile_filename=water_profile_filename)

        self._bad_pixel_map = bad_pixel_map

        # Calculate radial bins just on initialization
        radial_step: float = 1.0
        num_bins: int = int(radius_pixel_map.max() / radial_step)
        radial_bins = numpy.linspace(0, num_bins * radial_step, num_bins + 1)

        # Create an array labeling each pixel according to the radial bin it belongs to
        self._radial_bin_labels: NDArray[numpy.int_] = numpy.searchsorted(
            radial_bins, radius_pixel_map, "right"
        )
        self._radial_bin_labels -= 1
        self._mask: Union[NDArray[numpy.float_], None] = None

    def compute_radial_profile(
        self,
        *,
        data: Union[NDArray[numpy.float_], NDArray[numpy.int_]],
    ) -> Tuple[NDArray[numpy.float_], NDArray[numpy.float_]]:
        """
        Calculate radial profile from a detector data frame.

        This function calculates a radial profile based on the detector data frame
        provided to the function as input.

        Arguments:

            data: the detector data frame from which the radial profile will be
                calculated.

        Returns:

            A radial profile whose value is the average radial intensity calculated
            from the data frame.

        #TODO: Fix documentation
        """
        if self._mask is None:
            if self._bad_pixel_map is None:
                self._mask = numpy.ones_like(data, dtype=bool)
            else:
                self._mask = self._bad_pixel_map.astype(bool)
        bin_sum: NDArray[numpy.int_] = numpy.bincount(
            self._radial_bin_labels[self._mask].ravel(), data[self._mask].ravel()
        )
        bin_count: NDArray[numpy.int_] = numpy.bincount(
            self._radial_bin_labels[self._mask].ravel()
        )
        with numpy.errstate(divide="ignore", invalid="ignore"):
            # numpy.errstate just allows us to ignore the divide by zero warning
            radial: NDArray[numpy.float_] = numpy.nan_to_num(bin_sum / bin_count)
        errors: NDArray[numpy.float_] = scipy.stats.binned_statistic(
            self._radial_bin_labels[self._mask].ravel(),
            data[self._mask].ravel(),
            "std",
        )[0]
        # TODO: What are the next lines for?
        if len(errors) != len(radial):
            errors = radial * 0.03
        return radial, errors

    def detect_sample(self, radial_profile: NDArray[numpy.float_]) -> bool:
        """
        Decides whether a radial profile is from an aqueous droplet.

        This function takes a input a radial profile. It analyzes the profile and
        estimates the likelihood that the scattering profile originates from a
        water droplet. From the estimation, the function then returns a binary
        assessment (the profile matches or does match a water droplet)

        Arguments:

            radial: The radial profile to assess.

        Returns:

            True if the radial profile matches an aqueous droplet, False otherwise.
        """
        if self._sample_profile is not None and self._water_profile is not None:
            # More complex algorithm where the radial is fit with a linear combination
            # of user defined sample and water profiles using least squares
            vectors: NDArray[numpy.float_] = numpy.vstack(
                (self._sample_profile, self._water_profile)
            )
            coefficients = fit_by_least_squares(
                radial_profile=radial_profile, vectors=vectors
            )
            water_profile_to_sample_profile_ratio: float = float(
                coefficients[1] / coefficients[0]
            )
            if coefficients[0] < 0:
                # If sample coefficient is negative, it's all water
                water_profile_to_sample_profile_ratio = 1.0
            if coefficients[1] < 0:
                # If water coefficient is negative, it's all sample
                water_profile_to_sample_profile_ratio = 0.0
        else:
            # TODO: Why a try/except?
            # Simple ratio of water peak intensity to sample peak intensity
            sample_profile_mean: numpy.float_ = numpy.mean(
                radial_profile[self._sample_peak_min_bin : self._sample_peak_max_bin]
            )
            water_profile_mean: numpy.float_ = numpy.mean(
                radial_profile[self._water_peak_min_bin : self._water_peak_max_bin]
            )
            water_profile_to_sample_profile_ratio = float(
                water_profile_mean / sample_profile_mean
            )
        sample_detected: bool = (
            # Having a threshold maximum helps filtering out nozzle hits too
            (water_profile_to_sample_profile_ratio > self._threshold_min)
            and (water_profile_to_sample_profile_ratio < self._threshold_max)
        )

        return sample_detected


def fit_by_least_squares(
    *,
    radial_profile: NDArray[numpy.float_],
    vectors: NDArray[numpy.float_],
    start_bin: Union[int, None] = None,
    stop_bin: Union[int, None] = None,
) -> NDArray[numpy.float_]:
    # This function fits a set of linearly combined vectors to a radial profile,
    # using a least-squares-based approach. The fit only takes into account the
    # range of radial bins defined by the xmin and xmax arguments.
    if start_bin is None:
        start_bin = 0
    if stop_bin is None:
        stop_bin = len(radial_profile)
    a: NDArray[numpy.float_] = numpy.nan_to_num(numpy.atleast_2d(vectors).T)
    b: NDArray[numpy.float_] = numpy.nan_to_num(radial_profile)
    a = a[start_bin:stop_bin]
    b = b[start_bin:stop_bin]
    coefficients: NDArray[numpy.float_]
    coefficients, _, _, _ = numpy.linalg.lstsq(a, b, rcond=None)
    return coefficients
