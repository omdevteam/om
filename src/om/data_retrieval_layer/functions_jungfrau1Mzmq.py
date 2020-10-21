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
Retrieval of Jungfrau 1M detector data.

This module contains functions that retrieve data from a Jungfrau 1M x-ray detector.
"""
from typing import Any, Dict, Tuple, cast

import numpy  # type: ignore


def detector_data(event: Dict[str, Any]) -> numpy.ndarray:
    """
    Retrieves one frame of Jungfrau detector data from Jungfrau ZMQ receiver message.
    Arguments:
        event (Dict[str, Any]): a dictionary storing the event data.
    Returns:
        numpy.ndarray: one frame of detector data.
    """
    # Returns the data from the Jungfrau HDF5 files

    msg: Tuple[Dict[str, Any], Dict[str, Any]]
    msg = event["data"]

    data: numpy.ndarray = numpy.concatenate(
        [numpy.frombuffer(msg[i]["data"], dtype=numpy.int16).reshape((512, 1024)) for i in range(2)]
    )
    if event["additional_info"]["calibration"]:
        calibrated_data: numpy.ndarray = event["additional_info"][
            "calibration_algorithm"
        ].apply_calibration(data)
    else:
        calibrated_data = data

    return calibrated_data


def event_id(event: Dict[str, Any]) -> str:
    """
    Gets a unique identifier for an event retrieved from Jungfrau.
    Returns a label that unambiguously identifies, within an experiment, the event
    currently being processed. For the Jungfrau detector, frame number from the first
    panel is used as event identifier.

    Arguments:
        event (Dict[str, Any]): a dictionary storing the event data.

    Returns:
        str: a unique event identifier.
    """
    return str(event["data"][0]["frame_number"])


def frame_id(event: Dict[str, Any]) -> str:
    """
    Gets a unique identifier for a Jungfrau data frame.
    Returns a label that unambiguously identifies, within an event, the frame currently
    being processed.

    # TODO: Add documentations.

    Arguments:

        event (Dict[str, Any]): a dictionary storing the event data.

    Returns:

        str: a unique frame identifier (within an event).
    """
    return str(0)


def timestamp(event: Dict[str, Any]) -> numpy.float64:
    """
    Gets the timestamp of a Jungfrau data event retrieved from Jungfrau ZMQ receiver.

    Arguments:
        event (Dict[str, Any]): a dictionary storing the event data.
    Returns:
        numpy.float64: the timestamp of the event in seconds from the Epoch.
    """
    
    return event["data"][0]["timestamp"]


def beam_energy(event: Dict[str, Any]) -> float:
    """
    Gets the beam energy for a Jungfrau data event.
    OM currently supports Jungfrau data events originating from files, which do not
    provide beam energy information. OM uses the value provided for the
    'fallback_beam_energy_in_eV' entry in the configuration file, in the
    'data_retrieval_layer' parameter group.

    Arguments:
        event (Dict[str, Any]): a dictionary storing the event data.
    Returns:
        float: the energy of the beam in eV.
    """
    # Returns the value previously stored in the event.
    return cast(float, event["additional_info"]["beam_energy"])


def detector_distance(event: Dict[str, Any]) -> float:
    """
    Gets the detector distance for a Jungfrau data event.
    OM currently supports Jungfrau data events originating from files which do not
    provide detector distance information. OM uses the value provided for the
    'fallback_detector_distance_in_mm' entry in the configuration file, in the
    'data_retrieval_layer' parameter group.
    Arguments:
        event (Dict[str,Any]): a dictionary storing the event data.
    Returns:
        float: the detector distance in mm.
    """
    # Returns the value previously stored in the event.
    return cast(float, event["additional_info"]["detector_distance"])
