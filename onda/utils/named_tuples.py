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
"""
Named tuples for OnDA.

This module contains the implementation of several named tuples used
in OnDA.
"""
from __future__ import absolute_import, division, print_function
import collections


PeakList = collections.namedtuple(
    typename='PeakList',
    field_names=[
        'fs',
        'ss',
        'intensity'
    ]
)
"""
A list of peaks detected in a detector frame.

The first two fields, named 'fs' and 'ss' respectively, are
lists which store fractional indexes locating the detected peaks in
the slab-format detector frame data. The third field, named
'intensity', is a list storing the integrated intensity of each peak.
"""


QuadVmiPeaks = collections.namedtuple(
    typename='QuadVmiPeaks',
    field_names=[
        'x_1',
        'x_2',
        'y_1',
        'y_2'
    ]
)
"""
A set of peaks from a VMI quad-type detector.

Each of the four fields, named respectively 'x_1', 'x_2', 'y_1' and
'y_2', stores a fractional index locating the peak on the waveform data
of the detector wire with the same name.
"""


VmiCoords = collections.namedtuple(
    typename='VmiCoords',
    field_names=[
        'x',
        'y'
    ]
)
"""
Spatial coordinates of a VMI detector hit.

Its two fields ('x' and 'y' respectively) store the spatial coordinates
of a VMI detector hit.
"""


VmiHit = collections.namedtuple(
    typename='VmiHit',
    field_names=[
        'timestamp',
        'coords',
        'peaks'
    ]
)
"""
VMI detector hit information.

The first field, 'timestamp', is used to store the timestamp of the
hit (in epoch format). The second field, 'coords' is a
:obj:`VmiCoords` tuple and contains the spatial coordinates of the hit.
The third field, 'peaks' is a VmiPeak-style tuple (for example a
:obj:`QuadVmiPeaks` object) and stores a set of peaks detected on the
wires of the detector.
"""


FilenameAndFrameIndex = collections.namedtuple(
    typename='FilenameAndFrameIndex',
    field_names=[
        'filename',
        'frame_index'
    ]
)
"""
Information necessary to locate a data frame in a file.

The two fields, called 'filename' and 'frame_index' respectively, store
the path to the file where the frame is stored, and the index of the
frame within the file.
"""


Peakfinder8DetInfo = collections.namedtuple(
    typename='Peakfinder8DetInfo',
    field_names=[
        'asic_nx',
        'asic_ny',
        'nasics_x',
        'nasics_y'
    ]
)
"""
Peakfinder8-related information.

The four fields (named respectively 'asics_nx', 'asics_ny', 'nasics_x',
and  'nasics_y)' are the four parameters used by the peakfinder8
algorithm to describe the format of the input data.
"""


HidraInfo = collections.namedtuple(
    typename='HidraInfo',
    field_names=[
        'query',
        'targets',
        'data_base_path'
    ]
)
"""
HiDRA initialization information.

Information needed by HiDRA to initiate the connection and the event
retrieval. The 'query' field contains information about the transfer
type and the required data. The 'targets' field stores information
about the worker nodes that will receive data from HiDRA. The
'data_base_path' field contains the base path to be used for locating
files in the file system when HiDRA sends relative paths to OnDA.
"""


OpticalLaserStateDataRetrievalInfo = collections.namedtuple(
    typename='OpticalLaserStateDataRetrievalInfo',
    field_names=[
        'psana_detector_handle',
        'active_laser_evr_code'
    ]
)
"""
Optical laser state data retrieval information.

Information needed to receover from psana the inforamtion about the
state of the optical laser. The first field,
'psana_detector_handle', contains the handle of the psana Detector
interface for the retrieval of EVR code information, while the second
field, 'active_optical_laser_evr_code', stores the EVR code that
corresponds, at the LCLS facility, to the optical laser being
active.
"""
