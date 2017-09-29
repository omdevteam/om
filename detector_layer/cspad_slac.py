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

from collections import namedtuple
import numpy


SlabShape = namedtuple('SlabShape', ['ss', 'fs'])
NativeShape = namedtuple('NativeShape', ['panel', 'ss', 'fs'])
RawData = namedtuple('RawData', ['adu', 'calib_info'])


slab_shape = SlabShape(1480, 1552)
native_shape = NativeShape(32, 185, 388)


def raw_data(event):

    cspad_np = event.detector['raw_data'].calib(event.psana_event)
    cspad_np_og = cspad_np.reshape((4, 8, 185, 388))
    cspad_ij = numpy.zeros(slab_shape, dtype=cspad_np_og.dtype)
    for i in range(cspad_np_og.shape[0]):
        cspad_ij[:, i * cspad_np_og.shape[3]: (i+1) * cspad_np_og.shape[3]] = cspad_np_og[i].reshape(
            (cspad_np_og.shape[1] * cspad_np_og.shape[2], cspad_np_og.shape[3]))

    return RawData(cspad_ij, None)


def raw_data_pedestals_only(event):
    cspad_np = event.detector['raw_data'].raw(event.psana_event)-event.detector['raw_data'].pedestals(event.psana_event)
    cspad_np_og = cspad_np.reshape((4, 8, 185, 388))
    cspad_ij = numpy.zeros(slab_shape, dtype=cspad_np_og.dtype)
    for i in range(cspad_np_og.shape[0]):
        cspad_ij[:, i * cspad_np_og.shape[3]: (i+1) * cspad_np_og.shape[3]] = cspad_np_og[i].reshape(
            (cspad_np_og.shape[1] * cspad_np_og.shape[2], cspad_np_og.shape[3]))

    return RawData(cspad_ij, None)

