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

import datetime


slab_shape = (1480, 1552)


def num_events_in_file(evt):
    return 1


def timestamp_dataext(evt):
    return datetime.datetime.strptime(evt['filehandle'][
                                          '/LCLS/eventTimeString'][()].decode('ascii').strip(), '%a %b  %d %H:%M:%S %Y')


def raw_data_dataext(evt):
    return evt['filehandle']['/data/data'][()]


def detector_distance_dataext(evt):
    return float(evt['filehandle']['/LCLS/detector0-EncoderValue'][()])


def beam_energy_dataext(evt):
    return float(evt['filehandle']['/LCLS/photon_energy_eV'][()])


def filename_and_event_dataext(evt):
    return (evt['filehandle'], 0)
