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
Retrieval of Jungfrau 1M detector data from files.

This module contains functions that retrieve Jungfrau 1M detector data from HDF5 files
written by the detector itself.
"""
from typing import Any, Dict, Tuple, cast

import numpy  # type: ignore


def detector_data(event: Dict[str, Any]) -> numpy.ndarray:
    """
    Retrieves one Jungfrau 1M detector data frame from files.

    This function retrieves a single Jungfrau 1M frame from a set of HDF5 files written
    by the detector itself. It returns the frame as a 2D array storing pixel data.

    Arguments:

        event: A dictionary storing the event data.

    Returns:

        One frame of detector data.
    """
    # Returns the data from the Jungfrau HDF5 files
    h5files: Tuple[Any, Any] = event["additional_info"]["h5files"]
    h5_data_path: str = event["additional_info"]["h5_data_path"]
    index: Tuple[int, int] = event["additional_info"]["index"]

    data: numpy.ndarray = numpy.concatenate(
        [h5files[i][h5_data_path][index[i]] for i in range(len(h5files))]
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
    Gets a unique identifier for an event retrieved from a Jungfrau 1M detector.

    This function returns a label that unambiguously identifies, within an experiment,
    the data event currently being processed.

    For the Jungfrau 1M detector, the label is constructed by joining the following
    elements:

    - The full path to the file containing the data for the first detector panel (d0)

    - The index of the current frame within the file itself.

    The two parts of the label are separated by the "//" symbol.

    Arguments:

        event: A dictionary storing the event data.

    Returns:

        A unique event identifier.
    """
    return " // ".join(
        (
            event["additional_info"]["h5files"][0].filename,
            "{:04d}".format(event["additional_info"]["index"][0]),
        )
    )


def frame_id(event: Dict[str, Any]) -> str:
    """
    Gets a unique identifier for a Jungfrau 1M detector data frame.

    This function returns a label that unambiguously identifies, within an event, the
    frame currently being processed.

    For the Jungfrau 1M detector, each event corresponds to a single detector frame.
    The event label (returned by the [event_id]
    [om.data_retrieval_layer.functions_jungfrau1M.event_id] function) is therefore
    sufficient to unambiguously identify each frame. Because of this, this function
    always returns the string "0".

    Arguments:

        event: a dictionary storing the event data.

    Returns:

        A unique frame identifier (within an event).
    """
    return str(0)


def timestamp(event: Dict[str, Any]) -> numpy.float64:
    """
    Gets the timestamp of a Jungfrau 1M event.

    For the Jungfrau 1M detector, the timestamp for an event, which corresponds to a
    single detector frame, is defined according to the the creation times of the files
    from which the frame originates. The HDF5 file containing the data for the first
    detector panel (d0) is taken as reference. Its creation time is added to to the
    relative timestamp difference between the first frame in the file and the one
    being processed. The timestamp differences are determined by the detector's
    internal clock and stored in the HDF5 files themselves.

    Arguments:

        event: A dictionary storing the event data.

    Returns:

        The timestamp of the event in seconds from the Epoch.
    """
    # Returns the file creation time previously stored in the event.

    file_creation_time: float = event["additional_info"]["file_creation_time"]
    jf_clock_value: int = event["additional_info"]["jf_internal_clock"]
    # Jungfrau internal clock frequency in Hz (may not be entirely correct)
    jf_clock_frequency: int = 9721700
    return file_creation_time + jf_clock_value / jf_clock_frequency


def beam_energy(event: Dict[str, Any]) -> float:
    """
    Gets the beam energy for a Jungfrau 1M event.

    The files written by the Jungfrau 1M detector do not provide beam energy
    information. Therefore OM uses the value provided for the
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
    Gets the detector distance for a Jungfrau 1M event.

    The files written by the Jungfrau 1M detector do not provide detector distance
    information. Therefore OM uses the value provided for the
    'fallback_detector_distance_in_mm' entry in the 'data_retrieval_layer' parameter
    group of the configuration file.

    Arguments:

        event: A dictionary storing the event data.

    Returns:

        The detector distance in mm.
    """
    # Returns the value previously stored in the event.
    return cast(float, event["additional_info"]["detector_distance"])
