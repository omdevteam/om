// This file is part of OM.
//
// OM is free software: you can redistribute it and/or modify it under the terms of
// the GNU General Public License as published by the Free Software Foundation, either
// version 3 of the License, or (at your option) any later version.
//
// OM is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
// without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
// PURPOSE.  See the GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License along with OnDA.
// If not, see <http://www.gnu.org/licenses/>.
//
// Copyright 2020 -2021 SLAC National Accelerator Laboratory
//
// Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
// a research centre of the Helmholtz Association.

#include "binning.hh"

double process_bin(double *data, char *mask, int bin_origin_ss, int bin_origin_fs,
                   int bin_size, int asic_index_ss, int asic_index_fs, int asic_size_ss,
                   int asic_size_fs, int num_pix_slab_fs, int min_good_pixel_count,
                   double saturation_value, double bad_pixel_value)
{

     double bin_sum = 0.0;
     int pixels_in_bin_sum = 0;
     int total_pixels_in_bin = bin_size * bin_size;

     for (int ss_in_bin = 0; ss_in_bin < bin_size; ss_in_bin++)
     {
          for (int fs_in_bin = 0; fs_in_bin < bin_size; fs_in_bin++)
          {
               int slab_pixel_index =
                   ((bin_origin_ss + ss_in_bin) + asic_index_ss * asic_size_ss) * num_pix_slab_fs +
                   (bin_origin_fs + fs_in_bin) + asic_index_fs * asic_size_fs;
               double original_pixel_value;
               int pixel_is_good;
               if (bin_origin_ss + ss_in_bin < asic_size_ss && bin_origin_fs + fs_in_bin < asic_size_fs)
               {
                    original_pixel_value = data[slab_pixel_index];
                    pixel_is_good = mask[slab_pixel_index];
               }
               else
               {
                    pixel_is_good = 0;
               }

               if (pixel_is_good != 0 && saturation_value > 0 && original_pixel_value >= saturation_value)
               {
                    return bad_pixel_value;
               }

               if (pixel_is_good != 0)
               {
                    bin_sum += original_pixel_value;
                    pixels_in_bin_sum += 1;
               }
          }
     }

     if (pixels_in_bin_sum < min_good_pixel_count)
     {
          return bad_pixel_value;
     }

     return (bin_sum * (total_pixels_in_bin / pixels_in_bin_sum));
}

void process_panel(int asic_size_fs, int asic_size_ss, int num_pix_slab_fs,
                   unsigned int asic_index_ss, unsigned int asic_index_fs, double *data,
                   double *binned_data, int num_pix_binned_fs, char *mask, int bin_size,
                   int min_good_pixel_count, double bad_pixel_value,
                   double saturation_value)
{
     for (int bin_origin_ss = 0; bin_origin_ss < asic_size_ss; bin_origin_ss += bin_size)
     {
          for (int bin_origin_fs = 0; bin_origin_fs < asic_size_fs; bin_origin_fs += bin_size)
          {
               int binned_pixel_ss = bin_origin_ss / bin_size;
               int binned_pixel_fs = bin_origin_fs / bin_size;
               int binned_pixel_index = binned_pixel_ss * num_pix_binned_fs + binned_pixel_fs;

               binned_data[binned_pixel_index] = process_bin(data, mask, bin_origin_ss,
                                                             bin_origin_fs, bin_size,
                                                             asic_index_ss, asic_index_fs,
                                                             asic_size_ss, asic_size_fs,
                                                             num_pix_slab_fs, min_good_pixel_count,
                                                             saturation_value,
                                                             bad_pixel_value);
          }
     }
}

void c_bin_detector_data(double *data, double *binned_data, char *mask, int bin_size,
                         int min_good_pixel_count, double bad_pixel_value,
                         double saturation_value, int asic_size_fs,
                         int asic_size_ss, int num_asics_fs, int num_asics_ss)
{
     int num_pix_slab_fs = asic_size_fs * num_asics_fs;
     int binned_asic_size_fs = (asic_size_fs + bin_size - 1) / bin_size;
     int num_pix_binned_fs = binned_asic_size_fs * num_asics_fs;
     for (int asic_index_ss = 0; asic_index_ss < num_asics_ss; asic_index_ss++)
     {
          for (int asic_index_fs = 0; asic_index_fs < num_asics_fs; asic_index_fs++)
          {
               process_panel(asic_size_fs, asic_size_ss, num_pix_slab_fs,
                             asic_index_ss, asic_index_fs, data, binned_data,
                             num_pix_binned_fs, mask, bin_size, min_good_pixel_count,
                             bad_pixel_value, saturation_value);
          }
     }
}

//     * Iterate over the data in steps of bin
//     * In each bin, for each pixel, check the mask:
//          * if the mask is 0, ignore
//          * if the mask is 1 keep
//          * if the pixel value is above saturation_value and saturation_value is positive:
//              * set the binned pixel to bad pixel value
//          * We count the good pixels
//          * If the good pixels are below min_good_pixel_count:
//               * stop and set the binned pixel to bad_pixel_value
//          * else
//               * Sum the good pixels
//               * Multiply by the ratio of good pixels