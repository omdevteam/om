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

cdef extern from "binning.hh":
    
   void c_bin_detector_data(double *data, double *binned_data, char *mask, int bin_size,
                       int min_good_pixel_count, double bad_pixel_value,
                       double saturation_value, int asic_size_fs,
                       int asic_size_ss, int num_asics_fs, int num_asics_ss);

def bin_detector_data(double[:,::1] data, double[:,::1] binned_data, char[:,::1] mask,
                       int bin_size, int min_good_pixel_count, double bad_pixel_value,
                       double saturation_value, int asic_size_fs,
                       int asic_size_ss, int num_asics_fs, int num_asics_ss):
    """
    Docstring here
    """

    c_bin_detector_data(&data[0, 0], &binned_data[0,0], &mask[0, 0], bin_size,
                       min_good_pixel_count, bad_pixel_value,
                       saturation_value, asic_size_fs,
                       asic_size_ss, num_asics_fs, num_asics_ss)