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


slab_shape = (352, 128, 512)
native_shape = (352, 128, 512)


def num_events_in_file(_):
    return 1


def raw_data(evt):
    _ = evt['filehandle']['/entry/instrument/detector/data'][351, 127, 511]
    return evt['filehandle']['/entry/instrument/detector/data'][::2, :, :]


def timestamp(evt):
    return evt['filectime']


def detector_distance(evt):
    return float(evt['monitor_params']['General']['fallback_detector_distance'])


def beam_energy(evt):
    return float(evt['monitor_params']['General']['fallback_beam_energy'])


def filename_and_event(evt):
    return (evt['filename'], 0)
