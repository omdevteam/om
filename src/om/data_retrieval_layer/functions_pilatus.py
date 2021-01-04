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
# Copyright 2020 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
Retrieval of Pilatus detector data.

This module contains functions that retrieve data from a Pilatus x-ray detector.
"""
from typing import Any, Dict, cast

import numpy  # type: ignore


def detector_data(event: Dict[str, Any]) -> numpy.ndarray:
    """
    Retrieves one Pilatus detector data frame from files or the HiDRA framework.

    Arguments:

        event: A dictionary storing the event data.

    Returns:

        One frame of detector data.
    """
    # Returns the data from the fabio cbf_obj object previously stored in the event.
    return event["data"].data


def event_id(event: Dict[str, Any]) -> str:
    """
    Gets a unique identifier for an event retrieved from a Pilatus detector.

    This function retrives a label that unambiguously identifies, within an experiment,
    the event currently being processed. For the Pilatus detector, each HiDRA or file
    event corresponds to a single CBF data file, and the full path to the file is used
    as identifier.

    Arguments:

        event: A dictionary storing the event data.

    Returns:

        A unique event identifier.
    """
    return cast(str, event["additional_info"]["full_path"])


def frame_id(event: Dict[str, Any]) -> str:
    """
    Gets a unique identifier for a Pilatus detector data frame.

    This function returns a label that unambiguously identifies, within an event, the
    frame currently being processed. For the Pilatus detector, the index of the frame
    within the event is used as identifier. However, each Pilatus event only contains
    only one frame, so this function always returns the string "0".

    Arguments:

        event: A dictionary storing the event data.

    Returns:

        A unique frame identifier (within an event).
    """
    return str(0)


def timestamp(event: Dict[str, Any]) -> numpy.float64:
    """
    Gets the timestamp of a Pilatus data event.

    OM currently supports Pilatus data events originating from files or recovered from
    HiDRA. In both cases, an event corresponds to a single CBF data file written by the
    detector and the creation date and time of the file is used as timestamp for the
    event.

    Arguments:

        event: A dictionary storing the event data.

    Returns:

        The timestamp of the event in seconds from the Epoch.
    """
    # Returns the file creation time previously stored in the event.
    return cast(numpy.float64, event["additional_info"]["file_creation_time"])


def beam_energy(event: Dict[str, Any]) -> float:
    """
    Gets the beam energy for a Pilatus event.

    OM currently supports Pilatus data events originating from files or recovered from
    HiDRA. Neither provide beam energy information. OM uses the value provided for the
    'fallback_beam_energy_in_eV' entry in the 'data_retrieval_layer' parameter group of
    the configuration file.

    Arguments:

        event: A dictionary storing the event data.

    Returns:

        The energy of the beam in eV.
    """
    # Returns the value previously stored in the event.
    return cast(float, event["additional_info"]["beam_energy"])


def detector_distance(event: Dict[str, Any]) -> float:
    """
    Gets the detector distance for a Pilatus data event.

    OM currently supports Pilatus data events originating from files or recovered from
    HiDRA. Neither provide detector distance information. OM uses the value provided
    for the 'fallback_detector_distance_in_mm' entry in the 'data_retrieval_layer'
    parameter group of the configuration file.

    Arguments:

        event (Dict[str,Any]): a dictionary storing the event data.

    Returns:

        float: the detector distance in mm.
    """
    # Returns the value previously stored in the event.
    return cast(float, event["additional_info"]["detector_distance"])
