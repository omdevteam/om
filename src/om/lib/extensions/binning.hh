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
#ifndef BINNING_H
#define BINNING_H

void c_bin_detector_data(double *data, double *binned_data, char *mask, int bin_size,
                         int min_good_pixel_count, double bad_pixel_value,
                         double saturation_value, int asic_size_fs,
                         int asic_size_ss, int num_asics_fs, int num_asics_ss);

#endif // BINNING_H