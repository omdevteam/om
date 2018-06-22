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
OnDA named tuples.

This module contains the implementation of several OnDA specific
named tuples.
"""
import collections


PeakList = collections.namedtuple(
    typename='PeakList',
    field_names=['fs', 'ss', 'intensity']
)
"""
Peaks detected in a detector frame.

A named tuple that stores the a list of peaks detected on a detector
frame. The first two fields, named 'fs' and 'ss' respectively, are
lists which store fractional indexes locating the detected peaks in
the slab-format detector frame data. The third field, named
'intensity', is a list storing the integrated intensity of each peak.
"""


QuadVmiPeaks = collections.namedtuple(
    typename='QuadVMIPeaks',
    field_names=['x_1', 'x_2', 'y_1', 'y_2']
)
"""
VMI peaks from a quad-type detector.

A named tuple that stores a set of peaks detected on quad-type VMI
detector's wires. Each of the four fields, named respectively 'x_1',
'x_2', 'y_1' and 'y_2', stores a fractional index locating the peak on
the waveform data of one of the detector wires (the wire that has the
same name as the field).
"""


VmiCoords = collections.namedtuple(
    typename='Coords',
    field_names=['x', 'y']
)
"""
Spatial coordinates of a VMI detector hit.

A named tuple that stores in its two fields ('x' and 'y' respectively)
the spatial coordinates of a VMI detector hit.
"""


VmiHit = collections.namedtuple(
    typename='VmiHit',
    field_names=['timestamp', 'coords', 'peaks']
)
"""
VMI detector hit information.

A named tuple that stores all information related to a VMI detector
hit. The first field, 'timestamp', is used to store the timestamp of
the hit (in epoch format). The second field, 'coords' is a
`:obj:VmiCoords` tuple and contains the spatial coordinates of the hit.
The third field, 'peaks' is a VmiPeak-style tuple - for example a
`:obj:QuadVmiPeaks` object) stores a set of peaks detected on the wires
of the VMI detector.
"""


FilenameAndFrameIndex = collections.namedtuple(
    typename='FilenameAndFrameIndex',
    field_names=['filename', 'frame_index']
)
"""
Information necessary to locate a data frame in a file.

A named tuple the storing information necessary to recover a data frame
from a file. The two fields, called 'filename' and 'frame_index'
respectively, store the path to the file where the frame can be found,
and the index of the frame in the data block containing the detector
data.
"""


Peakfinder8DetInfo = collections.namedtuple(
    typename='Peakfinder8DetectorInfo',
    field_names=['asic_nx', 'asic_ny', 'nasics_x', 'nasics_y']
)
"""
Peakfinder8-related information.

A named tuple where the four fields (named respectively 'asics_nx',
'asics_ny', 'nasics_x', and  'nasics_y)' are the four parameters used
by the peakfinder8 algorithm to describe the format of the input data.
"""


HidraInfo = collections.namedtuple(
    typename='HiDRAInfo',
    field_names=['query', 'targets', 'data_base_path']
)
"""
HiDRA initialization information.

A named tuple storing the information needed by HiDRA to initiate the
connection and the event retrieval. The 'query' field contains
information about the transfer type and the required data. The
'targets' field stores information about the worker nodes that will
receive data from HiDRA. The third field, 'data_base_path', contains
the base path to be used for locating files in the file system when
HiDRA sends relative paths to OnDA.
"""
