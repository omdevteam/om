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
# You should have received a copy of the GNU General Public License along with OnDA.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2020 -2023 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Peakfinder8 extension.

This extension contains an implementation of Cheetah's 'peakfinder8' peak detection
algorithm.
"""
from libcpp.vector cimport vector
from libc.stdlib cimport malloc, free
from libc.stdint cimport int8_t

import numpy

cdef extern from "peakfinder8.hh":

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

cdef extern from "peakfinder8.hh":

    int peakfinder8(tPeakList *peaklist, float *data, char *mask, float *pix_r,
                    int rstats_num_pix, int *rstats_pidx, int *rstats_radius, int fast,
                    long asic_nx, long asic_ny, long nasics_x, long nasics_y,
                    float ADCthresh, float hitfinderMinSNR,
                    long hitfinderMinPixCount, long hitfinderMaxPixCount,
                    long hitfinderLocalBGRadius, char* outliersMask);


def peakfinder_8(int max_num_peaks, float[:,::1] data, char[:,::1] mask,
                 float[:,::1] pix_r, int rstats_num_pix, int[:] rstats_pidx, 
                 int[:] rstats_radius, int fast, long asic_nx, long asic_ny, 
                 long nasics_x, long nasics_y, float adc_thresh, 
                 float hitfinder_min_snr, long hitfinder_min_pix_count, 
                 long hitfinder_max_pix_count, long hitfinder_local_bg_radius):
    """
    peakfinder_8(max_num_peaks, data, mask, pix_r, asic_nx, asic_ny, nasics_x, \
        nasics_y, adc_thresh, hitfinder_min_snr, hitfinder_min_pix_count, \
        hitfinder_max_pix_count, hitfinder_local_bg_radius)
    
    Peakfinder8 peak detection.

    This function finds peaks in a detector data frame using the 'peakfinder8'
    strategy from the Cheetah software package. The 'peakfinder8' peak detection
    strategy is described in the following publication:

    A. Barty, R. A. Kirian, F. R. N. C. Maia, M. Hantke, C. H. Yoon, T. A. White,
    and H. N. Chapman, "Cheetah: software for high-throughput reduction and
    analysis of serial femtosecond x-ray diffraction data", J Appl  Crystallogr,
    vol. 47, pp. 1118-1131 (2014).

    Arguments:

        max_num_peaks (:obj:`int`): The maximum number of peaks that will be retrieved
            from each data frame. Additional peaks will be ignored.

        data (:obj:`numpy.ndarray`): The detector data frame on which the peak finding
            must be performed (as an numpy array of float32).

        mask (:obj:`numpy.ndarray`): A numpy array of int8 storing a mask.  The map can
            be used to mark areas of the data frame that must be excluded from the peak
            search. 

            * The map must be a numpy array of the same shape as the data frame on
              which the algorithm will be applied.

            * Each pixel in the map must have a value of either 0, meaning that
              the corresponding pixel in the data frame should be ignored, or 1,
              meaning that the corresponding pixel should be included in the
              search.

            * The map is only used to exclude areas from the peak search: the data
              is not modified in any way.

        pix_r (:obj:`numpy.ndarray`): A numpy array of float32 with radius information.

            * The array must have the same shape as the data frame on which the
              algorithm will be applied.

            * Each element of the array must store, for the corresponding pixel in the
              data frame, the distance in pixels from the origin of the detector
              reference system (usually the center of the detector).

        asic_nx (:obj:`int`):: The fs size in pixels of each detector panel in the data
            frame.

        asic_ny (:obj:`int`):: The ss size in pixels of each detector panel in the data
            frame.

        nasics_x (:obj:`int`): The number of panels along the fs axis of the data
            frame.

        nasics_y (:obj:`int`): The number of panels along the ss axis of the data
            frame.

        adc_thresh (:obj:`float`):: The minimum ADC threshold for peak detection.

        hitfinder_min_snr (:obj:`float`): The minimum signal-to-noise ratio for peak
            detection.

        hitfinder_min_pix_count (:obj:`int`): The minimum size of a peak in pixels.

        hitfinder_max_pixel_count (:obj:`int`): The maximum size of a peak in pixels.

        local_bg_radius: The radius for the estimation of the local background in
            pixels.

    Returns:

        :obj:`Tuple[int, List[float], List[float], List[float], List[float], \
List[float], List[float]`: A tuple storing  information about the detected peaks. The
        tuple has the following elements:

            * The first entry stores the number of peaks that were detected in the data
            frame.

            * The second entry is a list storing the fractional fs indexes that locate
            thedetected peaks in the data frame.
    
            * The third entry is a list storing the fractional ss indexes that locate the
            the detected peaks in the data frame.
    
            * The fourth entry is a list storing the integrated intensities for the
            detected peaks.
    
            * The fifth entry is a list storing the number of pixels that make up each
            detected peak.

            * The sixth entry is a list storing, for each peak, the value of the pixel
            with the maximum intensity.
    
            * The seventh entry is a list storing the signal-to-noise ratio of each
            detected peak.
    """
    cdef tPeakList peak_list
    allocatePeakList(&peak_list, max_num_peaks)

    peakfinder8(&peak_list, &data[0, 0], &mask[0,0], &pix_r[0, 0], rstats_num_pix, 
                &rstats_pidx[0] if rstats_pidx is not None else NULL, 
                &rstats_radius[0] if rstats_radius is not None else NULL, 
                fast, asic_nx, asic_ny, nasics_x, nasics_y, adc_thresh, 
                hitfinder_min_snr, hitfinder_min_pix_count, hitfinder_max_pix_count,
                hitfinder_local_bg_radius, NULL)

    cdef int i
    cdef float peak_x, peak_y, peak_value
    cdef vector[double] peak_list_x
    cdef vector[double] peak_list_y
    cdef vector[long] peak_list_index
    cdef vector[double] peak_list_value
    cdef vector[double] peak_list_npix
    cdef vector[double] peak_list_maxi
    cdef vector[double] peak_list_sigma
    cdef vector[double] peak_list_snr

    num_peaks = peak_list.nPeaks

    if num_peaks > max_num_peaks:
        num_peaks = max_num_peaks

    for i in range(0, num_peaks):

        peak_x = peak_list.peak_com_x[i]
        peak_y = peak_list.peak_com_y[i]
        peak_index = peak_list.peak_com_index[i]
        peak_value = peak_list.peak_totalintensity[i]
        peak_npix = peak_list.peak_npix[i]
        peak_maxi = peak_list.peak_maxintensity[i]
        peak_sigma = peak_list.peak_sigma[i]
        peak_snr = peak_list.peak_snr[i]

        peak_list_x.push_back(peak_x)
        peak_list_y.push_back(peak_y)
        peak_list_index.push_back(peak_index)
        peak_list_value.push_back(peak_value)
        peak_list_npix.push_back(peak_npix)
        peak_list_maxi.push_back(peak_maxi)
        peak_list_sigma.push_back(peak_sigma)
        peak_list_snr.push_back(peak_snr)

    freePeakList(peak_list)

    return (peak_list_x, peak_list_y, peak_list_value, peak_list_index,
            peak_list_npix, peak_list_maxi, peak_list_sigma, peak_list_snr)