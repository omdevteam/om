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


from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from onda.cfelpyutils import cfel_hdf5


#######################
# LAMBDA CALIBRATION  #
#######################


class LambdaCalibration:
    """Calibration of a Lambda detector module, with flatfield correction.

    Implements a calibration procedure for a Lambda detector module, with
    flatfield correction.
    """

    def __init__(self, calibration_file_name):
        """Initializes the calibration algorithm.

        Args:

            calibration filename (str): name of the hdf5 file with the
                calibration data.
        """

        self._flatfield = cfel_hdf5.load_nparray_from_hdf5_file(
            data_file_name=calibration_file_name,
            data_hdf5_group='/flatfieldcorrect'
        )

    def apply_calibration(self, raw_data):
        """Applies the calibration.

        Applies the calibration to the data provided by the user.

        Args:

            raw_data (numpy.ndarray): the data on which the calibration must
                be applied, in 'slab' format.

        Returns:

            corrected_data(numpy.ndarray):  the calibrated data
        """

        return raw_data * self._flatfield
