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

This module contains algorithms that perform crystallography-related data processing
(peak finding, etc.). In addition, it also contains several typed dictionaries that
store data needed or produced by these algorithms.
"""
import sys
from typing import Any, Dict, List, Tuple, Union

import h5py  # type: ignore
import numpy  # type: ignore
from typing_extensions import TypedDict

from om.lib.peakfinder8_extension import peakfinder_8  # type: ignore
from om.utils import parameters as param_utils


class TypePeakfinder8Info(TypedDict, total=True):
    """
    Detector layout information for the peakfinder8 algorithm.

    Base class: `TypedDict`

    This typed dictionary is used to store information about the data layout in a
    detector data frame, in the format needed by the [Peakfinder8PeakDetection]
    [om.algorithms.crystallography.Peakfinder8PeakDetection] algorithm. This
    information is usually retrieved via the [get_peakfinder8_info]
    [om.algorithms.crystallography.get_peakfinder8_info] function.

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

    This typed dictionary is used to store information about a set of peaks that
    were detected in a data frame.

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

    This function retrieves, for a supported detector type, the data layout information
    required by the [Peakfinder8PeakDetection]
    [om.algorithms.crystallography.Peakfinder8PeakDetection] algorithm.

    Arguments:

        detector_type: The type of detector for which the information needs to be
            retrieved. The following detector types are currently supported:

            * 'cspad': The CSPAD detector used at the CXI beamline of the LCLS facility
              before 2020.

            * 'pilatus': The Pilatus detector used at the P11 beamline of the PETRA III
              facility.

            * 'jungfrau1M': The 1M version of the Jungfrau detector used at the PETRA
              III facility.

            * 'jungfrau4M': The 4M version of the Jungfrau detector used at the CXI
              beamline of the LCLS facility.

            * 'epix10k2M': The 2M version of the Epix10KA detector used at the MFX
              beamline of the LCLS facility.

            * 'rayonix': The Rayonix detector used at the MFX beamline of the LCLS
              facility.

    Returns:

        A [TypePeakfinder8Info][om.algorithms.crystallography.TypePeakfinder8Info]
        dictionary storing the data layout information.
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
        radius_pixel_map: numpy.ndarray,
        max_num_peaks: Union[int, None] = None,
        asic_nx: Union[int, None] = None,
        asic_ny: Union[int, None] = None,
        nasics_x: Union[int, None] = None,
        nasics_y: Union[int, None] = None,
        adc_threshold: Union[float, None] = None,
        minimum_snr: Union[float, None] = None,
        min_pixel_count: Union[int, None] = None,
        max_pixel_count: Union[int, None] = None,
        local_bg_radius: Union[int, None] = None,
        min_res: Union[int, None] = None,
        max_res: Union[int, None] = None,
        bad_pixel_map: Union[numpy.ndarray, None] = None,
        parameters: Union[Dict[str, Any], None] = None,
    ) -> None:
        """
        Peakfinder8 algorithm for peak detection.

        This algorithm stores the parameters required to find peaks in a detector data
        frame using the 'peakfinder8' strategy, and performs peak finding on a data
        frame upon request. The 'peakfinder8' peak detection strategy is described in
        the following publication:

        A. Barty, R. A. Kirian, F. R. N. C. Maia, M. Hantke, C. H. Yoon, T. A. White,
        and H. N. Chapman, "Cheetah: software for high-throughput reduction and
        analysis of serial femtosecond x-ray diffraction data", J Appl  Crystallogr,
        vol. 47, pp. 1118-1131 (2014).

        Arguments:

            max_num_peaks: The maximum number of peaks that will be retrieved from each
                data frame. Additional peaks will be ignored.

            asic_nx: The fs size in pixels of each detector panel in the data frame
                (Can be retrieved from a [TypePeakfinder8Info]
                [om.algorithms.crystallography.TypePeakfinder8Info] dictionary).

            asic_ny: The ss size in pixels of each detector panel in the data frame
                (Can be retrieved from a [TypePeakfinder8Info]
                [om.algorithms.crystallography.TypePeakfinder8Info] dictionary).

            nasics_x: The number of panels along the fs axis of the data frame
                (Can be retrieved from a [TypePeakfinder8Info]
                [om.algorithms.crystallography.TypePeakfinder8Info] dictionary).

            nasics_y: The number of panels along the ss axis of the data frame
                (Can be retrieved from a [TypePeakfinder8Info]
                [om.algorithms.crystallography.TypePeakfinder8Info] dictionary).

            adc_threshold: The minimum ADC threshold for peak detection.

            minimum_snr: The minimum signal-to-noise ratio for peak detection.

            min_pixel_count: The minimum size of a peak in pixels.

            max_pixel_count: The maximum size of a peak in pixels.

            local_bg_radius: The radius for the estimation of the local background in
                pixels.

            min_res: The minimum resolution for a peak in pixels.

            max_res: The maximum resolution for a peak in pixels.

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

            radius_pixel_map: A numpy array with radius information.

                * The array must have the same shape as the data frame on which the
                  algorithm will be applied.

                * Each element of the array must store, for the corresponding pixel in
                  the data frame, the distance in pixels from the origin
                  of the detector reference system (usually the center of the
                  detector).
        """
        if parameters is not None:
            peakfinder8_info: TypePeakfinder8Info = get_peakfinder8_info(
                detector_type=param_utils.get_parameter_from_parameter_group(
                    group=parameters,
                    parameter="detector_type",
                    parameter_type=str,
                    required=True,
                )
            )
            asic_nx = peakfinder8_info["asic_nx"]
            asic_ny = peakfinder8_info["asic_ny"]
            nasics_x = peakfinder8_info["nasics_x"]
            nasics_y = peakfinder8_info["nasics_y"]
            max_num_peaks = param_utils.get_parameter_from_parameter_group(
                group=parameters,
                parameter="max_num_peaks",
                parameter_type=int,
                required=True,
            )
            adc_threshold = param_utils.get_parameter_from_parameter_group(
                group=parameters,
                parameter="adc_threshold",
                parameter_type=float,
                required=True,
            )
            minimum_snr = param_utils.get_parameter_from_parameter_group(
                group=parameters,
                parameter="minimum_snr",
                parameter_type=float,
                required=True,
            )
            min_pixel_count = param_utils.get_parameter_from_parameter_group(
                group=parameters,
                parameter="min_pixel_count",
                parameter_type=int,
                required=True,
            )
            max_pixel_count = param_utils.get_parameter_from_parameter_group(
                group=parameters,
                parameter="max_pixel_count",
                parameter_type=int,
                required=True,
            )
            local_bg_radius = param_utils.get_parameter_from_parameter_group(
                group=parameters,
                parameter="local_bg_radius",
                parameter_type=int,
                required=True,
            )
            min_res = param_utils.get_parameter_from_parameter_group(
                group=parameters,
                parameter="min_res",
                parameter_type=int,
                required=True,
            )
            max_res = param_utils.get_parameter_from_parameter_group(
                group=parameters,
                parameter="max_res",
                parameter_type=int,
                required=True,
            )
            bad_pixel_map_fname: str = param_utils.get_parameter_from_parameter_group(
                group=parameters,
                parameter="bad_pixel_map_filename",
                parameter_type=str,
            )
            if bad_pixel_map_fname is not None:
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

            if bad_pixel_map_fname is not None:
                try:
                    map_hdf5_file_handle: Any
                    with h5py.File(bad_pixel_map_fname, "r") as map_hdf5_file_handle:
                        bad_pixel_map = map_hdf5_file_handle[bad_pixel_map_hdf5_path][:]
                except (IOError, OSError, KeyError) as exc:
                    exc_type, exc_value = sys.exc_info()[:2]
                    # TODO: Fix type check
                    raise RuntimeError(
                        "The following error occurred while reading the {0} field from"
                        "the {1} bad pixel map HDF5 file:"
                        "{2}: {3}".format(
                            bad_pixel_map_fname,
                            bad_pixel_map_hdf5_path,
                            exc_type.__name__,  # type: ignore
                            exc_value,
                        )
                    ) from exc
            else:
                bad_pixel_map = None

        else:
            print(
                "OM Warning: Initializing the Peakfinder8PeakDetection algorithm with "
                "individual parameters (max_num_peaks, asic_nx, asic_ny, nasics_x, "
                "nasics_y, adc_threshold, minimum_snr, min_pixel_count, "
                "max_pixel_count, local_bg_radius, min_res, max_res, bad_pixel_map "
                "and radius_pixel_map) is deprecated and will be removed in a future "
                "version of OM. Please use the new parameter group-based "
                "initialization interface (which requires only the parameters and "
                "photon_energy_kev arguments)."
            )

        if (
            max_num_peaks is None
            or asic_nx is None
            or asic_ny is None
            or nasics_x is None
            or nasics_y is None
            or adc_threshold is None
            or minimum_snr is None
            or min_pixel_count is None
            or max_pixel_count is None
            or min_res is None
            or max_res is None
        ):
            raise RuntimeError(
                "OM ERROR: Some parameters required for the initialization of the "
                "Peakfinder8PeakDetection algorithm have not been defined. Please "
                "check the command used to initialize the algorithm."
            )

        self._max_num_peaks: Union[int, None] = max_num_peaks
        self._asic_nx: Union[int, None] = asic_nx
        self._asic_ny: Union[int, None] = asic_ny
        self._nasics_x: Union[int, None] = nasics_x
        self._nasics_y: Union[int, None] = nasics_y
        self._adc_thresh: Union[float, None] = adc_threshold
        self._minimum_snr: Union[float, None] = minimum_snr
        self._min_pixel_count: Union[int, None] = min_pixel_count
        self._max_pixel_count: Union[int, None] = max_pixel_count
        self._local_bg_radius: Union[int, None] = local_bg_radius
        self._min_res: Union[int, None] = min_res
        self._max_res: Union[int, None] = max_res
        self._bad_pixel_mask: Union[numpy.ndarray, None] = bad_pixel_map
        self._mask: Union[numpy.ndarray, None] = None
        self._radius_pixel_map: numpy.ndarray = radius_pixel_map

    def get_adc_thresh(self) -> Union[float, None]:
        """
        Gets the minimum ADC threshold for peak detection.

        This function returns the minimum ADC threshold currently used by the algorithm
        for peak detection.

        Returns:

            The minimum singal-to-noise ratio currently used by the algorithm.
        """
        return self._minimum_snr

    def set_adc_thresh(self, adc_thresh: float) -> None:
        """
        Sets the minimum ADC threshold for peak detection.

        This function sets the minimum ADC threshold used by the algorithm for peak
        detection. Any future call to the
        [find_peaks1][om.algorithm.crystallography.Peakfinder8PeakDetection.find_peaks]
        method will use the value provided here for this specific parameter.

        Arguments:

            adc_threshold: The new value of the minimum singal-to-noise ratio for peak
            detection.
        """
        self._adc_thresh = adc_thresh

    def get_minimum_snr(self) -> Union[float, None]:
        """
        Gets the minimum signal-to-noise ratio for peak detection.

        This function returns the minimum signal-to-noise ratio currently used by
        the algorithm for peak detection.

        Returns:

            The minimum singal-to-noise ratio currently used by the algorithm.
        """
        return self._minimum_snr

    def set_minimum_snr(self, minimum_snr: float) -> None:
        """
        Sets the minimum signal-to-noise ratio for peak detection.

        This function sets the minimum signal-to-noise ratio used by the algorithm for
        peak detection. Any future call to the
        [find_peaks1][om.algorithm.crystallography.Peakfinder8PeakDetection.find_peaks]
        method will use the value provided here for this specific parameter.

        Arguments:

            minimum_snr: The new value of the minimum singal-to-noise ratio for peak
            detection.
        """
        self._minimum_snr = minimum_snr

    def get_min_pixel_count(self) -> Union[int, None]:
        """
        Gets the minimum size for a peak in pixels.

        This function returns the current minimum size in pixels that allows a peak
        to be detected by the algorithm.

        Returns:

            The minimum size in pixels for a peak.
        """
        return self._min_pixel_count

    def set_min_pixel_count(self, min_pixel_count: int) -> None:
        """
        Sets the minimum size for a peak in pixels.

        This function sets the minimum size in pixels that allows a peak to be
        detected by the algorithm. Any future call to the
        [find_peaks1][om.algorithm.crystallography.Peakfinder8PeakDetection.find_peaks]
        method will use the value provided here for this specific parameter.

        Arguments:

            min_pixel_count: The new minimum size in pixels for a peak.
        """
        self._min_pixel_count = min_pixel_count

    def get_max_pixel_count(self) -> Union[int, None]:
        """
        Gets the maximum size for a peak in pixels.

        This function returns the current maximum size in pixels that allows a peak
        to be detected by the algorithm.

        Returns:

            The maximum size in pixels for a peak.
        """
        return self._max_pixel_count

    def set_max_pixel_count(self, max_pixel_count: int) -> None:
        """
        Sets the maximum size for a peak in pixels.

        This function sets the maximum size in pixels that allows a peak to be
        detected by the algorithm. Any future call to the
        [find_peaks1][om.algorithm.crystallography.Peakfinder8PeakDetection.find_peaks]
        method will use the value provided here for this specific parameter.

        Arguments:

            max_pixel_count: The new minimum size in pixels for a peak.
        """
        self._max_pixel_count = max_pixel_count

    def get_local_bg_radius(self) -> Union[int, None]:
        """
        Gets the radius in pixels for the estimation of the local background.

        This function returns the radius in pixels currently used by the algorithm to
        estimate the background.

        Returns:

            The radius in pixels for the estimation of the local background.
        """
        return self._local_bg_radius

    def set_local_bg_radius(self, local_bg_radius: int) -> None:
        """
        Sets the radius in pixels for the estimation of the local background.

        This function sets the radius in pixels used by the algorithm to estimate the
        local background. Any future call to the
        [find_peaks1][om.algorithm.crystallography.Peakfinder8PeakDetection.find_peaks]
        method will use the value provided here for this specific parameter.

        Arguments:

            max_pixel_count: The new minimum size in pixels for a peak.
        """
        self._local_bg_radius = local_bg_radius

    def get_min_res(self) -> Union[int, None]:
        """
        Gets the minimum resolution for a peak in pixels.

        This function returns the current minimum resolution in pixels that allows a
        peak to be detected by the algorithm.

        Returns:

            The minimum resolution in pixels for a peak.
        """
        return self._min_res

    def set_min_res(self, min_res: int) -> None:
        """
        Sets the minimum resolution for a peak in pixels.

        This function sets the minimum resolution in pixels that allows a peak to be
        detected by the algorithm. Any future call to the
        [find_peaks1][om.algorithm.crystallography.Peakfinder8PeakDetection.find_peaks]
        method will use the value provided here for this specific parameter.

        Arguments:

            max_res: The new maximum resolution in pixels for a peak.
        """
        self._min_res = min_res
        self._mask = None

    def get_max_res(self) -> Union[int, None]:
        """
        Gets the maximum resolution a peak in pixels.

        This function returns the current maximum resolution in pixels that allows a
        peak to be detected by the algorithm.

        Returns:

            The maximum resolution in pixels for a peak.
        """
        return self._max_res

    def set_max_res(self, max_res: int) -> None:
        """
        Sets the maximum resolution for a peak in pixels.

        This function sets the maximum resolution in pixels that allows a peak to be
        detected by the algorithm. Any future call to the
        [find_peaks1][om.algorithm.crystallography.Peakfinder8PeakDetection.find_peaks]
        method will use the value provided here for this specific parameter.

        Arguments:

            max_res: The new maximum resolution in pixels for a peak.
        """
        self._max_res = max_res
        self._mask = None

    def find_peaks(self, *, data: numpy.ndarray) -> TypePeakList:
        """
        Finds peaks in a detector data frame.

        This function detects peaks in a data frame, and returns information about
        their location, size and intensity.

        Arguments:

            data: The detector data frame on which the peak finding must be performed.

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
