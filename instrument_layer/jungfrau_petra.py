from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import numpy


jungfrau_dtype = numpy.dtype([ ('framenum', numpy.uint64),
                               ('bunchid', numpy.uint64),
                               ('image', numpy.uint16, (128, 4096)) ])

slab_shape = (128, 4096)
native_shape = (128, 4096)


def num_events_in_file(evt):
    return evt['filesize']/104859


def raw_data(evt):

    evt['filehandle'].seek(evt['filesize'] - 104859 * evt['shot_offset'])
    frame = numpy.fromfile(evt['filehandle'], dtype=jungfrau_dtype, count=1)
    return numpy.bitwise_and(frame, 0x3fff).reshape(512, 1024)

def timestamp(evt):
    return evt['filectime']


def detector_distance(evt):
    return float(evt['monitor_params']['General']['fallback_detector_distance'])


def beam_energy(evt):
    return float(evt['monitor_params']['General']['fallback_beam_energy'])


def filename_and_event(evt):
    return (evt['filename'], evt['filesize'] - evt['shot_offset'])