#    This file is part of OnDA.
#
#    OnDA is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    OnDA is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with OnDA.  If not, see <http://www.gnu.org/licenses/>.


import numpy
import sys

from libc.stdlib cimport malloc, free
from libc.stdint cimport *

cimport numpy as cnumpy



cdef extern from "adaptions/onda/streakFinder_wrapper.h":


    ctypedef struct streakFinder_constantArguments_t:
        void*       accuracyConstants
        void*       detectorRawFormat
        void*       detectorPositions
        void*       streakFinder_precomputedConstant

    ctypedef struct streakFinder_accuracyConstants_pythonWrapper_t:

        uint8_t     filterLength
        uint8_t     minFilterLength
        float       filterStep

        float       sigmaFactor
        uint8_t     streakElongationMinStepsCount
        float       streakElongationRadiusFactor
        uint8_t     streakPixelMaskRadius

        uint16_t*   pixelsToCheck_x
        uint16_t*   pixelsToCheck_y
        uint16_t    pixelsToCheckCount

        uint16_t*   backgroundEstimationRegions_upperLeftCorner_x
        uint16_t*   backgroundEstimationRegions_upperLeftCorner_y
        uint16_t*   backgroundEstimationRegions_lowerRightCorner_x
        uint16_t*   backgroundEstimationRegions_lowerRightCorner_y
        uint16_t    backgroundEstimationRegionsCount

cdef extern from "adaptions/onda/pythonWrapperTypes.h":

    ctypedef struct detectorGeometryMatrix_pythonWrapper_t:

        float*      detectorGeometryMatrix_x
        float*      detectorGeometryMatrix_y

cdef extern from "detectorRawFormat.h":

    ctypedef struct detectorRawFormat_t:
        uint16_t    asic_nx
        uint16_t    asic_ny
        uint8_t     nasics_x
        uint8_t     nasics_y

        uint16_t    pix_nx
        uint16_t    pix_ny
        uint32_t    pix_nn

cdef extern from "adaptions/onda/streakFinder_wrapper.h":

    streakFinder_constantArguments_t precomputeStreakFinderConstantArguments(
            streakFinder_accuracyConstants_pythonWrapper_t streakFinder_accuracyConstants,
            detectorRawFormat_t detectorRawFormat,
            detectorGeometryMatrix_pythonWrapper_t detectorGeometryMatrix_python,
            uint8_t *mask)

    void freePrecomputedStreakFinderConstantArguments(streakFinder_constantArguments_t streakfinder_constant_arguments)

    void streakFinder_allInOne(const float* data_linear, uint8_t* streakMask,
                               streakFinder_constantArguments_t streakFinderConstantArguments)


cdef class StreakDetectionClass:

    cdef streakFinder_constantArguments_t _streakfinder_constant_arguments

    def __cinit__(self, uint8_t filter_length,
                  uint8_t min_filter_length, float filter_step,
                  float sigma_factor, uint8_t streak_elongation_min_steps_count,
                  float streak_elongation_radius_factor,
                  uint8_t streak_pixel_mask_radius,
                  cnumpy.ndarray[cnumpy.uint16_t, ndim=1, mode="c"] pixels_to_check_x,
                  cnumpy.ndarray[cnumpy.uint16_t, ndim=1, mode="c"] pixels_to_check_y,
                  cnumpy.ndarray[cnumpy.uint16_t, ndim=1, mode="c"] background_estimation_regions_upper_left_corner_x,
                  cnumpy.ndarray[cnumpy.uint16_t, ndim=1, mode="c"] background_estimation_regions_upper_left_corner_y,
                  cnumpy.ndarray[cnumpy.uint16_t, ndim=1, mode="c"] background_estimation_regions_lower_right_corner_x,
                  cnumpy.ndarray[cnumpy.uint16_t, ndim=1, mode="c"] background_estimation_regions_lower_right_corner_y,
                  long asic_nx, long asic_ny, long nasics_x, long nasics_y,
                  cnumpy.ndarray[cnumpy.float32_t, ndim=2, mode="c"] pixel_map_x,
                  cnumpy.ndarray[cnumpy.float32_t, ndim=2, mode="c"] pixel_map_y,
                  cnumpy.ndarray[cnumpy.uint8_t, ndim=2, mode="c"] mask):

        cdef streakFinder_accuracyConstants_pythonWrapper_t streakfinder_accuracy_constants
        cdef detectorRawFormat_t detector_raw_format
        cdef detectorGeometryMatrix_pythonWrapper_t detector_geometry_matrix

        streakfinder_accuracy_constants.filterLength = filter_length
        streakfinder_accuracy_constants.minFilterLength = min_filter_length
        streakfinder_accuracy_constants.filterStep = filter_step

        streakfinder_accuracy_constants.sigmaFactor = sigma_factor
        streakfinder_accuracy_constants.streakElongationMinStepsCount = streak_elongation_min_steps_count
        streakfinder_accuracy_constants.streakElongationRadiusFactor = streak_elongation_radius_factor
        streakfinder_accuracy_constants.streakPixelMaskRadius = streak_pixel_mask_radius

        streakfinder_accuracy_constants.pixelsToCheck_x = &pixels_to_check_x[0]
        streakfinder_accuracy_constants.pixelsToCheck_y = &pixels_to_check_y[0]
        streakfinder_accuracy_constants.pixelsToCheckCount = pixels_to_check_y.shape[0]

        streakfinder_accuracy_constants.backgroundEstimationRegions_upperLeftCorner_x = &background_estimation_regions_upper_left_corner_x[0]
        streakfinder_accuracy_constants.backgroundEstimationRegions_upperLeftCorner_y = &background_estimation_regions_upper_left_corner_y[0]
        streakfinder_accuracy_constants.backgroundEstimationRegions_lowerRightCorner_x = &background_estimation_regions_lower_right_corner_x[0]
        streakfinder_accuracy_constants.backgroundEstimationRegions_lowerRightCorner_y = &background_estimation_regions_lower_right_corner_y[0]
        streakfinder_accuracy_constants.backgroundEstimationRegionsCount = background_estimation_regions_lower_right_corner_y.shape[0]

        detector_raw_format.asic_nx = asic_nx
        detector_raw_format.asic_ny = asic_ny
        detector_raw_format.nasics_x = nasics_x
        detector_raw_format.nasics_y = nasics_y

        detector_raw_format.pix_nx = asic_nx * nasics_x
        detector_raw_format.pix_ny = asic_ny * nasics_y
        detector_raw_format.pix_nn = asic_nx * nasics_x * asic_ny * nasics_y

        detector_geometry_matrix.detectorGeometryMatrix_x = &pixel_map_x[0, 0]
        detector_geometry_matrix.detectorGeometryMatrix_y = &pixel_map_y[0, 0]

        self._streakfinder_constant_arguments = precomputeStreakFinderConstantArguments(
            streakfinder_accuracy_constants,
            detector_raw_format,
            detector_geometry_matrix,
            &mask[0, 0])


    def find_streaks(self, cnumpy.ndarray[cnumpy.float32_t, ndim=2, mode="c"] data,
                     cnumpy.ndarray[cnumpy.uint8_t, ndim=2, mode="c"] streak_mask):
        streakFinder_allInOne(&data[0, 0], &streak_mask[0, 0], self._streakfinder_constant_arguments)

    def __dealloc__(self):
        freePrecomputedStreakFinderConstantArguments(self._streakfinder_constant_arguments)