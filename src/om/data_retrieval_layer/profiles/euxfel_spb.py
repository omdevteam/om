# This file is part of OM.
#
# OM is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# OM is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with OnDA.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2020 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Data retrieval at the SPB beamline of the European XFEL.
"""
from __future__ import absolute_import, division, print_function

from ..data_sources.agipd_1m_karabo import (
    # Utility functions.
    get_peakfinder8_info,
    # Event handling functions.
    get_num_frames_in_event,
    # Data extraction functions.
    detector_data,
    detector_gain,
)

from ..frameworks.karabo_euxfel import (
    # Event handling functions.
    close_event,
    event_generator,
    initialize_event_source,
    open_event,
    # Data extraction functions.
    beam_energy,
    detector_distance,
    timestamp,
    event_id,
    frame_id,
)
