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

cdef extern from "cheetah_extensions_yaroslav/pythonWrapperConversions.h":

    ctypedef struct streakFinderConstantArguments_t:
        void        *accuracyConstants
        void        *detectorRawSize_cheetah
        void        *detectorPositions
        void        *streakFinder_precomputedConstant

    enum detectorCategory_t:
        detectorCategory_CSPAD

cdef extern from "cheetah_extensions_yaroslav/streakfinder_wrapper.h":

    streakFinderConstantArguments_t *precompute_streakfinder_constant_arguments(
        uint_fast8_t filter_length,
        uint_fast8_t min_filter_length, float filter_step,
        float sigma_factor, uint_fast8_t streak_elongation_min_steps_count,
        float streak_elongation_radius_factor,
        uint_fast8_t streak_pixel_mask_radius, uint_fast8_t num_lines_to_check,
        detectorCategory_t detector_type, int background_region_preset,
        int background_region_dist_from_edge,
        long asic_nx, long asic_ny, long nasics_x, long nasics_y,
        float *pixel_map_x, float *pixel_map_y, uint8_t *mask,
        char* background_region_mask)

    void free_precomputed_streak_finder_constant_arguments(streakFinderConstantArguments_t *streakfinder_constant_arguments)

    void streakfinder(float* data, uint8_t* streak_mask, uint8_t* input_mask, streakFinderConstantArguments_t* streakfinder_constant_arguments)


cdef class StreakDetectionClass:

    cdef:
        streakFinderConstantArguments_t *_streakfinder_constant_arguments
        long _mask_x_size, mask_y_size

    def __cinit__(self, uint_fast8_t filter_length,
                  uint_fast8_t min_filter_length, float filter_step,
                  float sigma_factor, uint_fast8_t streak_elongation_min_steps_count,
                  float streak_elongation_radius_factor,
                  uint_fast8_t streak_pixel_mask_radius, uint_fast8_t num_lines_to_check,
                  detectorCategory_t detector_type, int background_region_preset,
                  int background_region_dist_from_edge,
                  long asic_nx, long asic_ny, long nasics_x, long nasics_y,
                  cnumpy.ndarray[cnumpy.float32_t, ndim=2, mode="c"] pixel_map_x,
                  cnumpy.ndarray[cnumpy.float32_t, ndim=2, mode="c"] pixel_map_y,
                  cnumpy.ndarray[cnumpy.uint8_t, ndim=2, mode="c"] mask,
                  cnumpy.ndarray[cnumpy.uint8_t, ndim=2, mode="c"] background_region_mask):

        cdef cnumpy.uint8_t * _brmask_pointer = &background_region_mask[0, 0]
        cdef char * _brmask_char_pointer = <char*> _brmask_pointer

        self._streakfinder_constant_arguments = precompute_streakfinder_constant_arguments(
            filter_length,
            min_filter_length, filter_step,
            sigma_factor, streak_elongation_min_steps_count,
            streak_elongation_radius_factor,
            streak_pixel_mask_radius, num_lines_to_check,
            detector_type, background_region_preset,
            background_region_dist_from_edge,
            asic_nx, asic_ny, nasics_x, nasics_y,
            &pixel_map_x[0, 0], &pixel_map_y[0, 0], &mask[0, 0], _brmask_char_pointer)


    def find_streaks(self, cnumpy.ndarray[cnumpy.float32_t, ndim=2, mode="c"] data, cnumpy.ndarray[cnumpy.uint8_t, ndim=2, mode="c"] streak_mask,
                     cnumpy.ndarray[cnumpy.uint8_t, ndim=2, mode="c"] input_mask):
        streakfinder(&data[0, 0], &streak_mask[0, 0], &input_mask[0, 0], self._streakfinder_constant_arguments)

    def __dealloc__(self):
        free_precomputed_streak_finder_constant_arguments(self._streakfinder_constant_arguments)
