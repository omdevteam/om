// This file is part of OM.
//
// OM is free software: you can redistribute it and/or modify it under the terms
// of the GNU General Public License as published by the Free Software
// Foundation, either version 3 of the License, or (at your option) any later
// version.
//
// OM is distributed in the hope that it will be useful, but WITHOUT ANY
// WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
// A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License along with
// OnDA. If not, see <http://www.gnu.org/licenses/>.
//
// Copyright 2020 -2021 SLAC National Accelerator Laboratory
//
// Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
// a research centre of the Helmholtz Association.
#ifndef PEAKFINDER8_H
#define PEAKFINDER8_H

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdlib>
#include <cstring>
#include <float.h>
#include <iostream>
#include <memory>
#include <new>
#include <stdio.h>
#include <vector>

/**
 * Public facing peak list. Holds center-of-mass of each peak found, in both
 * the fast-scan and slow-scan dimensions on a per panel basis. Indices are
 * in a panel convention, and the corresponding panel of each peak is also
 * stored. Signal-to-noise statistics are also maintained for the peak as well
 * as the local background.
 */
struct tPeakList {
  long   nPeaks;              ///< Number of peaks found
  int		 memoryAllocated;     ///< Whether memory has been allocated
  long	 nPeaks_max;          ///< Maxmimum number of peaks to find

  float* peak_maxintensity;		///< Maximum intensity in corresponding peak
  float* peak_totalintensity;	///< Integrated intensity in corresponding peak
  float* peak_sigma;			    ///< Signal-to-noise ratio of peak's background
  float* peak_snr;				    ///< Signal-to-noise ratio of peak
  float* peak_npix;				    ///< Number of pixels in peak
  float* peak_com_x;			    ///< Peak center of mass x (fs) (panel indices)
  float* peak_com_y;			    ///< Peak center of mass y (ss) (panel indices)
  long*  peak_com_index;		  ///< Closest pixel to peak COM as 1D panel index
  int*   peak_panel_number;   ///< Panel that the peak resides in
};

void allocatePeakList(tPeakList* peak, long NpeaksMax);
void freePeakList(tPeakList peak);

int peakfinder8(tPeakList* peaklist, float* data, char* mask, float* pix_radius,
                const std::vector<int>& data_shape, float ADCthresh,
                float hitfinderMinSNR, long hitfinderMinPixCount,
                long hitfinderMaxPixCount, long hitfinderLocalBGRadius);

#endif // PEAKFINDER8_H
