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


from libcpp.vector cimport vector
from libc.stdint cimport *

cimport numpy

cdef extern from "peakfinders.h":

    ctypedef struct tPeakList:
        long	    nPeaks
        long	    nHot
        float		peakResolution
        float		peakResolutionA
        float		peakDensity
        float		peakNpix
        float		peakTotal
        int			memoryAllocated
        long		nPeaks_max

        float       *peak_maxintensity
        float       *peak_totalintensity
        float       *peak_sigma
        float       *peak_snr
        float       *peak_npix
        float       *peak_com_x
        float       *peak_com_y
        long        *peak_com_index
        float       *peak_com_x_assembled
        float       *peak_com_y_assembled
        float       *peak_com_r_assembled
        float       *peak_com_q
        float       *peak_com_res

    void allocatePeakList(tPeakList* peak_list, long max_num_peaks)
    void freePeakList(tPeakList peak_list)

cdef extern from "cheetah_extensions_yaroslav/peakfinder9.h":

    int peakfinder9(tPeakList *peaklist,
                    float *data, char *mask, long asic_nx, long asic_ny,
                    long nasics_x, long nasics_y, float sigmaFactorBiggestPixel, float sigmaFactorPeakPixel,
                    float sigmaFactorWholePeak, float minimumSigma, float minimumPeakOversizeOverNeighbors,
                    uint_fast8_t windowRadius)


def peakfinder_9(int max_num_peaks,
                 numpy.ndarray[numpy.float32_t, ndim=2, mode="c"] data,
                 numpy.ndarray[numpy.int8_t, ndim=2, mode="c"] mask,
                 long asic_nx, long asic_ny,
                 long nasics_x, long nasics_y, float sigmaFactorBiggestPixel, float sigmaFactorPeakPixel,
                 float sigmaFactorWholePeak, float minimumSigma, float minimumPeakOversizeOverNeighbors,
                 uint_fast8_t windowRadius):

    cdef numpy.int8_t *mask_pointer = &mask[0, 0]
    cdef char *mask_char_pointer = <char*> mask_pointer

    cdef tPeakList peak_list
    allocatePeakList(&peak_list, max_num_peaks)

    peakfinder9(&peak_list, &data[0, 0], mask_char_pointer, 
                asic_nx, asic_ny, nasics_x, nasics_y,
                sigmaFactorBiggestPixel, sigmaFactorPeakPixel,
                sigmaFactorWholePeak, minimumSigma,
                minimumPeakOversizeOverNeighbors,
                windowRadius)

    cdef int i
    cdef float peak_x, peak_y, peak_value
    cdef vector[double] peak_list_x
    cdef vector[double] peak_list_y
    cdef vector[double] peak_list_value

    num_peaks = peak_list.nPeaks

    if num_peaks > max_num_peaks:
        num_peaks = max_num_peaks

    for i in range(0, num_peaks):

        peak_x = peak_list.peak_com_x[i]
        peak_y = peak_list.peak_com_y[i]
        peak_value = peak_list.peak_totalintensity[i]

        peak_list_x.push_back(peak_x)
        peak_list_y.push_back(peak_y)
        peak_list_value.push_back(peak_value)

    freePeakList(peak_list)

    return (peak_list_x, peak_list_y, peak_list_value)