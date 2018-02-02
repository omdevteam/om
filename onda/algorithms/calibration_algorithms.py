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

'''
Algorithms for detector calibration.
'''

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import h5py
from future.utils import raise_from


#######################
# LAMBDA CALIBRATION  #
#######################


class SingleModuleLambdaCalibration(object):
    '''
    Calibrate a single-module Lambda detector.

    Simply apply flatfield correction.
    '''

    def __init__(self, calibration_filename):
        '''
        Initializes the SingleModuleLambdaCalibration algorithm.

        Args:

            calibration_filename (str): name of an HDF5 file with the
                calibration data. The file must store the flatfield data
                for the module in the '/flatfield' data entry.
        '''

        # Load the flatfield information from the file and store it in
        # an attribute.
        try:
            with h5py.File(name=calibration_filename, mode='r') as fhandle:
                self._flatfield = fhandle['/flatfield']
        except OSError:
            raise_from(
                exc=RuntimeError(
                    'Error reading the {} HDF5 file.'.format(
                        calibration_filename
                    )
                ),
                source=None
            )

    def apply_calibration(self, data):
        """Appy the calibration.

        Subtract the flatfield from the module data.

        Args:

            data (ndarray): the module data on which the calibration must
                be applied.

        Returns:

            ndarray:  the corrected data.
        """

        # Multiply the data with the flatfield and return the result.
        return data * self._flatfield
