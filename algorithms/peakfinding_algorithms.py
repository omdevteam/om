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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import numpy

try:
    from python_extensions.peakfinder8_extension import peakfinder_8
except ImportError:
    raise RuntimeError('Error importing one or more cheetah wrappers, or one of their dependecies')
import cfelpyutils.cfel_hdf5 as ch5


##############################
# PEAKFINDER8 PEAK DETECTION #
##############################

class Peakfinder8PeakDetection:
    """Peak finding using cheetah's peakfinder8 algorithm.

    Implements peak finding using the peakfinder8 algorithm from Cheetah.
    """

    def __init__(self, max_num_peaks, asic_nx, asic_ny, nasics_x,
                 nasics_y, adc_threshold, minimum_snr, min_pixel_count,
                 max_pixel_count, local_bg_radius, min_res,
                 max_res, mask_filename, mask_hdf5_path, pixelmap_radius):
        """Initializes the peakfinder.

        Args:

            max_num_peaks (int): maximum number of peaks that will be returned by the algorithm.

            asic_nx (int): fs size of a detector's ASIC.

            asic_ny (int): ss size of a detector's ASIC.

            nasics_x (int): number of ASICs in the slab in the fs direction.

            nasics_y (int): number of ASICs in the slab in the ss direction.

            adc_threshold (float): minimum adc threshold for peak detection.

            minimum_snr (float): minimum signal to noise for peak detection.

            min_pixel_count (int): minimum size of the peak in pixels.

            max_pixel_count (int): maximum size of the peak in pixels.

            local_bg_radius (int): radius for the estimation of the local background.

            min_res (int): minimum resolution for a peak to be considered (in pixels).

            max_res (int): minimum resolution for a peak to be considered (in pixels).

            mask_filename (str): filename of the file containing the mask.

            mask_hdf5_path (str): internal hdf5 path of the data block containing the mask.

            pixelmap_radius (numpy.ndarray): pixelmap in 'slab' format listing for each pixel the distance from the
            center of the detector, in pixels.
        """

        self.max_num_peaks = max_num_peaks
        self.asic_nx = asic_nx
        self.asic_ny = asic_ny
        self.nasics_x = nasics_x
        self.nasics_y = nasics_y
        self.adc_thresh = adc_threshold
        self.minimum_snr = minimum_snr
        self.min_pixel_count = min_pixel_count
        self.max_pixel_count = max_pixel_count
        self.local_bg_radius = local_bg_radius
        self.pixelmap_radius = pixelmap_radius
        self.mask = ch5.load_nparray_from_hdf5_file(mask_filename, mask_hdf5_path)

        res_mask = numpy.ones(self.mask.shape, dtype=numpy.int8)
        res_mask[numpy.where(pixelmap_radius < min_res)] = 0
        res_mask[numpy.where(pixelmap_radius > max_res)] = 0

        self.mask *= res_mask

    def find_peaks(self, raw_data):
        """Finds peaks.

        Performs the peak finding.

        Args:

            raw_data (numpy.ndarray): the data on which peak finding is performed, in 'slab' format.

        Returns:

            peak_list (tuple list float, list float, list float): the peak list, as a tuple of three lists:
            ([peak_x], [peak_y], [peak_value]). The first two contain the coordinates of the peaks in the input data
            array, the third the intensity of the peaks. All are lists of float numbers.
        """

        peak_list = peakfinder_8(self.max_num_peaks,
                                 raw_data.astype(numpy.float32),
                                 self.mask.astype(numpy.int8),
                                 self.pixelmap_radius,
                                 self.asic_nx, self.asic_ny,
                                 self.nasics_x, self.nasics_y,
                                 self.adc_thresh, self.minimum_snr,
                                 self.min_pixel_count, self.max_pixel_count,
                                 self.local_bg_radius)

        return peak_list