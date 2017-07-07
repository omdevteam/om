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


cdef extern from "adaptions/onda/radialBackgroundSubtraction_wrapper.h":

    ctypedef struct radialRankFilter_constantArguments_t:

        void*       precomputedConstants
        void*       detectorRawFormat
        void*       detectorPositions


cdef extern from "adaptions/onda/pythonWrapperTypes.h":

    ctypedef struct detectorGeometryMatrix_pythonWrapper_t:

        float*      detectorGeometryMatrix_x
        float*      detectorGeometryMatrix_y

cdef extern from "radialBackgroundSubtraction.h":

    ctypedef struct radialRankFilter_accuracyConstants_pythonWrapper_t:

        uint32_t    minValuesPerBin
        uint32_t    minBinWidth

        uint32_t    maxConsideredValuesPerBin

        uint8_t*    detectorsToConsiderSubscripts_x
        uint8_t*    detectorsToConsiderSubscripts_y
        uint16_t    detectorsToConsiderCount

        uint8_t*    detectorsToCorrectSubscripts_x
        uint8_t*    detectorsToCorrectSubscripts_y
        uint16_t    detectorsToCorrectCount

        float       rank

    radialRankFilter_constantArguments_t precomputeRadialRankFilterConstantArguments(const uint8_t* mask, const float* detectorGeometryRadiusMatrix,
        const detectorRawFormat_t& detectorRawFormat, const radialRankFilter_accuracyConstants_pythonWrapper_t& accuracyConstants_pythonWrapper,
        detectorGeometryMatrix_pythonWrapper_t detectorGeometryMatrix_python)

    void applyRadialRankFilter(float* data, radialRankFilter_constantArguments_t radialRankFilter_constantArguments)

    void freePrecomputeRadialRankFilterConstants(radialRankFilter_constantArguments_t radialRankFilter_constantArguments)


cdef extern from "detectorRawFormat.h":

    ctypedef struct detectorRawFormat_t:
        uint16_t    asic_nx
        uint16_t    asic_ny
        uint8_t     nasics_x
        uint8_t     nasics_y

        uint16_t    pix_nx
        uint16_t    pix_ny
        uint32_t    pix_nn


cdef class RadialBackgroundSubtractionClass:

    cdef radialRankFilter_constantArguments_t _radial_background_subtraction_constant_arguments

    def __cinit__(self, min_values_per_bin, min_bin_width,
                  int max_considered_values_per_bin,
                  cnumpy.ndarray[cnumpy.int8_t, ndim=2, mode="c"] mask,
                  cnumpy.ndarray[cnumpy.uint8_t, ndim=1, mode="c"] detectors_to_consider_subscripts_x,
                  cnumpy.ndarray[cnumpy.uint8_t, ndim=1, mode="c"] detectors_to_consider_subscripts_y,
                  cnumpy.ndarray[cnumpy.uint8_t, ndim=1, mode="c"] detectors_to_correct_subscripts_x,
                  cnumpy.ndarray[cnumpy.uint8_t, ndim=1, mode="c"] detectors_to_correct_subscripts_y,
                  int rank,
                  long asic_nx, long asic_ny, long nasics_x, long nasics_y,
                  cnumpy.ndarray[cnumpy.float32_t, ndim=2, mode="c"] pixel_map_x,
                  cnumpy.ndarray[cnumpy.float32_t, ndim=2, mode="c"] pixel_map_y,
                  cnumpy.ndarray[cnumpy.float32_t, ndim=2, mode="c"] pixel_map_r):

        cdef radialRankFilter_accuracyConstants_pythonWrapper_t radial_rank_filter_accuracy_constants
        cdef detectorRawFormat_t detector_raw_format
        cdef detectorGeometryMatrix_pythonWrapper_t detector_geometry_matrix

        radial_rank_filter_accuracy_constants.minValuesPerBin = min_values_per_bin
        radial_rank_filter_accuracy_constants.minBinWidth = min_bin_width
        radial_rank_filter_accuracy_constants.maxConsideredValuesPerBin = max_considered_values_per_bin
        radial_rank_filter_accuracy_constants.detectorsToConsiderSubscripts_x = detectors_to_consider_subscripts_x
        radial_rank_filter_accuracy_constants.detectorsToConsiderSubscripts_y = detectors_to_consider_subscripts_y
        radial_rank_filter_accuracy_constants.detectorsToConsiderCount = len(detectors_to_consider_subscripts_y)
        radial_rank_filter_accuracy_constants.detectorsToCorrectSubscripts_x = detectors_to_correct_subscripts_x
        radial_rank_filter_accuracy_constants.detectorsToCorrectSubscripts_y = detectors_to_correct_subscripts_y
        radial_rank_filter_accuracy_constants.detectorsToCorrectCount = (detectors_to_correct_subscripts_y)
        radial_rank_filter_accuracy_constants.rank = rank

        detector_raw_format.asic_nx = asic_nx
        detector_raw_format.asic_ny = asic_ny
        detector_raw_format.nasics_x = nasics_x
        detector_raw_format.nasics_y = nasics_y

        detector_raw_format.pix_nx = asic_nx * nasics_x
        detector_raw_format.pix_ny = asic_ny * nasics_y
        detector_raw_format.pix_nn = asic_nx * nasics_x * asic_ny * nasics_y

        detector_geometry_matrix.detectorGeometryMatrix_x = &pixel_map_x[0, 0]
        detector_geometry_matrix.detectorGeometryMatrix_y = &pixel_map_y[0, 0]

        self._radial_background_subtraction_constant_arguments = precomputeRadialRankFilterConstantArguments(mask,
             &pixel_map_r[0, 0], detector_raw_format, radial_rank_filter_accuracy_constants, detector_geometry_matrix)


    def apply_radial_filter(self, cnumpy.ndarray[cnumpy.float32_t, ndim=2, mode="c"] data):

        applyRadialRankFilter(&data[0, 0], self._radial_background_subtraction_constant_arguments)


    def __dealloc__(self):
        freePrecomputeRadialRankFilterConstants(self._radial_background_subtraction_constant_arguments)
