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
# You should have received a copy of the GNU General Public License along with OM.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2020 -2021 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
"""
from typing import Any, Dict, cast

from scipy import constants

import numpy  # type: ignore
import ceedee

def detector_data(*, event: Dict[str, Any]) -> numpy.ndarray:
    """

    Arguments:

        event: A dictionary storing the event data.

    Returns:

        One frame of detector data.
    """
    return ceedee.deserialize(event["data"], event["metadata"]["meta"]["_data_format"])


def event_id(*, event: Dict[str, Any]) -> str:
    """

    Arguments:

        event: A dictionary storing the event data.

    Returns:

        A unique event identifier.
    """
    return "{}_{}".format(event["additional_info"]["stream_name"], event["metadata"]["_id"])


def frame_id(*, event: Dict[str, Any]) -> str:
    """

    Arguments:

        event: A dictionary storing the event data.

    Returns:

        A unique frame identifier (within an event).
    """
    return str(0)


def timestamp(*, event: Dict[str, Any]) -> numpy.float64:
    """

    Arguments:

        event: A dictionary storing the event data.

    Returns:

        The timestamp of the event in seconds from the Epoch.
    """
    # Returns the file creation time previously stored in the event.
    return cast(numpy.float64, event["metadata"]["timestamp"] / 1e9)


def beam_energy(*, event: Dict[str, Any]) -> float:
    """

    Arguments:

        event: A dictionary storing the event data.

    Returns:

        The energy of the beam in eV.
    """
    wavelength: float = event["additional_info"]["stream_metadata"]["entry"]["instrument"]["beam"]["incident_wavelength"]["()"]
    
    return cast(float, constants.h * constants.c / (wavelength * constants.e))

def detector_distance(*, event: Dict[str, Any]) -> float:
    """

    Arguments:

        event (Dict[str,Any]): a dictionary storing the event data.

    Returns:

        float: the detector distance in mm.
    """
    # Returns the value previously stored in the event.
    return cast(float, event["additional_info"]["stream_metadata"]["entry"]["instrument"]["detector"]["distance"]["()"]*1e3)
