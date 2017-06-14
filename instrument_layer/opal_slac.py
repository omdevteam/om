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

import psana

SlabShape = namedtuple('SlabShape', ['ss', 'fs'])
NativeShape = namedtuple('NativeShape', ['ss', 'fs'])

slab_shape = (1024, 1024)
native_shape = (1024, 1024)


def opal_data(event):
    return event['evt'].get(psana.Camera.FrameV1,
                            psana.Source(event['monitor_params']['PsanaParallelizationLayer']['camera_psana_source'])).data16()
