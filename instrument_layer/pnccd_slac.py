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
NativeShape = namedtuple('NativeShape', ['panel','ss', 'fs'])

slab_shape = SlabShape(1024, 1024)
native_shape = NativeShape(4, 512, 512)


def raw_data(event):
    pnccd_np = event.detector['opal_data'].calib(event.evt)
    pnccd_ij = numpy.zeros(slab_shape, dtype=pnccd_np.dtype)
    pnccd_ij[0:512, 0:512] = pnccd_np[0]
    pnccd_ij[512:1024, 0:512] = pnccd_np[1][::-1, ::-1]
    pnccd_ij[512:1024, 512:1024] = pnccd_np[2][::-1, ::-1]
    pnccd_ij[0:512, 512:1024] = pnccd_np[3]
    return pnccd_ij
