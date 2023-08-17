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
# Copyright 2020 -2023 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
CrystFEL's geometry utilities.

This module contains functions and classes that manipulate geometry information.
"""
import collections
import copy
import math
from pathlib import Path
from typing import Dict, List, Tuple, TypedDict, Union

import numpy
from numpy.typing import NDArray

from om.lib.exceptions import OmGeometryError, OmWrongArrayShape


class TypeBeam(TypedDict, total=True):
    """
    A dictionary storing information about the x-ray beam.

    Attributes:

        photon_energy: The photon energy of the beam in eV.

        photon_energy_from: The internal path to the photon energy information in an
            HDF5 data file, in case the beam energy information is extracted from it.

        photon_energy_scale: The scaling factor to be applied to the photon energy, in
            case the provided energy value is not in eV.
    """

    photon_energy: float
    photon_energy_from: str
    photon_energy_scale: float


class TypePanel(TypedDict, total=True):
    """
    A dictionary storing information about a detector panel.

    Attributes:

        cnx: The x coordinate of the corner of the panel in the detector reference
            system.

        cny: The y coordinate of the corner of the panel in the detector reference
            system.

        clen: The perpendicular distance, as reported by the facility, of the sample
            interaction point from the corner of the panel.

        clen_from: The internal path to the `clen` information in an HDF5 data file, in
            case the information is extracted from it.

        coffset: The offset to be applied to the `clen` value reported by the facility
            in order to determine the real perpendicular distance of the panel from the
            interaction point.

        mask: The internal path, in an HDF5 data file, to the mask data for the panel.

        mask_file: The name of the HDF5 data file in which the mask data for the panel
            can be found.

        satmap: The internal path, in an HDF5 data file, to the per-pixel saturation
            map for the panel.

        satmap_file: The name of the HDF5 data file in which the per-pixel saturation
            map for the panel can be found.

        res: The size of the pixels that make up the the panel (in pixels per meter).

        badrow: The readout direction for the panel, for filtering out clusters of
            peaks. The value corresponding to this key must be either `x` or `y`.

        no_index: Wether the panel should be considered entirely bad. The panel will be
            considered bad if the value corresponding to this key is non-zero.

        adu_per_photon: The number of ADUs per photon for the panel.

        max_adu: The ADU value above which a pixel of the panel should be considered
            unreliable.

        data: The internal path, in an HDF5 data file, to the data block where the
            panel data is stored.

        adu_per_eV: The number of ADUs per eV of photon energy for the panel.

        dim_structure: A description of the internal layout of the data block storing
            the panel's data. The value corresponding to this key is a list of strings
            which define the role of each axis in the data block. See the
            [crystfel_geometry](http://www.desy.de/~twhite/crystfel/manual-crystfel_geometry.html)
            man page for a detailed explanation.

        fsx: The fs->x component of the matrix used to transform pixel indexes into
            detector reference system coordinates.

        fsy: The fs->y component of the matrix used to transform pixel indexes into
            detector reference system coordinates.

        fsz: The fs->z component of the matrix used to transform pixel indexes into
            detector reference system coordinates.

        ssx: The ss->x component of the matrix used to transform pixel indexes into
            detector reference system coordinates.

        ssy: The ss->y component of the matrix used to transform pixel indexes into
            detector reference system coordinates.

        ssz: The ss->z component of the matrix used to transform pixel indexes into
            detector reference system coordinates.

        rail_x: The x component, in the detector reference system, of the direction of
            the rail along which the detector moves.

        rail_y: The y component, in the detector reference system, of the direction of
            the rail along which the detector moves.

        rail_z: The z component, in the detector reference system, of the direction of
            the rail along which the detector moves.

        clen_for_centering: The perpendicular distance of the origin of the detector
            reference system from the interaction point, as reported by the facility,

        xfs: The x->fs component of the matrix used to transform detector reference
            system coordinates into pixel indexes.

        yfs: The y->fs component of the matrix used to transform detector reference
            system coordinates into pixel indexes.

        xss: The x->ss component of the matrix used to transform detector reference
            system coordinates into pixel indexes.

        yss: The y->ss component of the matrix used to transform detector reference
            system coordinates into pixel indexes.

        orig_min_fs: The initial fs index of the panel data in the data block where
            it is stored.

        orig_max_fs: The final (inclusive) fs index of the panel data in the data block
            where it is stored.

        orig_min_ss: The initial ss index of the panel data in the data block where it
            is stored.

        orig_max_ss: The final (inclusive) fs index of the panel data in the data block
            where it is stored.

        w: The width of the panel in pixels.

        h: The height of the panel in pixels.
    """

    cnx: float
    cny: float
    clen: float
    clen_from: str
    coffset: float
    mask: str
    mask_file: str
    satmap: str
    satmap_file: str
    res: float
    badrow: str
    no_index: bool
    adu_per_photon: float
    max_adu: float
    data: str
    adu_per_eV: float
    dim_structure: List[Union[int, str, None]]
    fsx: float
    fsy: float
    fsz: float
    ssx: float
    ssy: float
    ssz: float
    rail_x: float
    rail_y: float
    rail_z: float
    clen_for_centering: float
    xfs: float
    yfs: float
    xss: float
    yss: float
    orig_min_fs: int
    orig_max_fs: int
    orig_min_ss: int
    orig_max_ss: int
    w: int
    h: int


class TypeBadRegion(TypedDict, total=True):
    """
    A dictionary storing information about a bad region of a detector.

    Attributes:

        panel: The name of the panel in which the bad region lies.

        min_x: The initial x coordinate of the bad region in the detector reference
            system.

        max_x: The final x coordinate of the bad region in the detector reference
            system.

        min_y: The initial y coordinate of the bad region in the detector reference
            system.

        max_y: The final y coordinate of the bad region in the detector reference
            system.

        min_fs: The initial fs index of the bad region in the block where the panel
            data is stored.

        max_fs: The final (inclusive) fs index of the bad region in the block where the
            panel data is stored.

        min_ss: The initial ss index of the bad region in the block where the panel
            data is stored.

        max_ss: The final (inclusive) ss index of the bad region in the block where the
            panel data is stored.

        is_fsss: Whether the fs,ss definition of the bad region (as opposed to the
            x,y-based one) should be considered. In the first case, the min_fs, max_fs,
            min_ss, and max_ss entries in this dictionary will define the bad region.
            In the second case, the min_x, max_x, min_y, and max_y entries will. If the
            value corresponding to this key is 1, the fs,ss-based definition will be
            considered valid. Otherwise, the x,y definition will be used.
    """

    panel: str
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    min_fs: int
    max_fs: int
    min_ss: int
    max_ss: int
    is_fsss: int


class TypeDetector(TypedDict):
    """
    A dictionary storing information about a detector.

    Attributes:

        panels: The panels in the detector. The value corresponding to this key is
            dictionary containing information about the panels that make up the
            detector. In the dictionary, the keys are the panel names, and the values
            are [TypePanel][om.lib.geometry.TypePanel] dictionaries.

        bad: The bad regions in the detector. The value corresponding to this key is a
            dictionary containing information about the bad regions in the detector. In
            the dictionary, the keys are bad region names, and the values are
            [TypeBadRegion][om.lib.geometry.TypeBadRegion] dictionaries.

        mask_bad: The value used in a bad pixel mask to label a pixel as bad.

        mask_good: The value used in a bad pixel mask to label a pixel as good.

        rigid_groups: The rigid groups of panels in the detector. The value
            corresponding to this key is a dictionary containing information about the
            rigid groups. In the dictionary, the keys are names of rigid groups and the
            values are lists storing the names of the panels belonging to each group.

        rigid_group_collections: The collections of rigid groups of panels in the
            detector. The value corresponding to this key is a dictionary containing
            information about the rigid group collections. In the dictionary, the keys
            are names of rigid group collections and the values are lists storing the
            names of the rigid groups belonging to the each collection.

        furthest_out_panel: The name of the panel which contains the pixel that is the
            furthest away from the center of the detector reference system.

        furthest_out_fs: The fs coordinate, within its panel, of the pixel that is the
            furthest away from the center of the detector reference system.

        furthest_out_ss: The ss coordinate, within its panel, of the pixel that is the
            furthest away from the center of the detector reference system.

        furthest_in_panel: The name of the panel which contains the closest pixel to
            the center of the detector reference system.

        furthest_in_fs: The fs coordinate, within its panel, of the closest pixel to
            the center of the detector reference system.

        furthest_in_ss: The ss coordinate, within its panel, of the closest pixel to
            the center of the detector reference system.
    """

    panels: Dict[str, TypePanel]
    bad: Dict[str, TypeBadRegion]
    mask_bad: int
    mask_good: int
    rigid_groups: Dict[str, List[str]]
    rigid_group_collections: Dict[str, List[str]]
    furthest_out_panel: str
    furthest_out_fs: float
    furthest_out_ss: float
    furthest_in_panel: str
    furthest_in_fs: float
    furthest_in_ss: float


class TypeDetectorLayoutInformation(TypedDict, total=True):
    """
    Detector layout information for the peakfinder8 algorithm.

    This typed dictionary stores information about the internal data layout of a
    detector data frame (number and size of ASICs, etc.). The information
    is needed by the
    [`Peakfinder8PeakDetection`][om.algorithms.crystallography.Peakfinder8PeakDetection]
    algorithm, and is usually retrieved via the
    [`get_layout_info`][om.lib.geometry.GeometryInformation.get_layout_info]
    function.

    Attributes:

        asic_nx: The fs size in pixels of each detector panel in the data frame.

        asic_ny: The ss size in pixels of each detector panel in the data frame.

        nasics_x: The number of detector panels along the fs axis of the data frame.

        nasics_y: The number of detector panels along the ss axis of the data frame.
    """

    asic_nx: int
    asic_ny: int
    nasics_x: int
    nasics_y: int


class TypePixelMaps(TypedDict):
    """
    A dictionary storing a set of pixel maps

    This dictionary stores a set of look-up pixels maps. Each map stores, for each
    pixel in a detector data frame, the value of a specific coordinate. All coordinates
    in this set of maps are assumed to be relative to the detector's reference system.

    Attributes:

        x: A pixel map for the x coordinate.

        y: A pixel map for the y coordinate.

        z: A pixel map for the z coordinate.

        radius: A pixel map storing the distance of each pixel from the center of the
            detector reference system.

        phi: A pixel map storing, for each pixel, the amplitude of the angle drawn by
            the pixel, the center of the detector reference system, and the x axis.
    """

    x: NDArray[numpy.float_]
    y: NDArray[numpy.float_]
    z: NDArray[numpy.float_]
    radius: NDArray[numpy.float_]
    phi: NDArray[numpy.float_]


class TypeVisualizationPixelMaps(TypedDict):
    """
    # TODO: Fix documentation

    A dictionary storing a set of pixel maps used for visualization.

    This dictionary stores a set of look-up pixels maps. Each map stores, for each
    pixel in a detector data frame, the value of a specific coordinate. This set of
    pixel maps is supposed to be used for visualization: all coordinates are assumed to
    refer to a cartesian reference system mapped on a 2D array storing pixel
    information, with origin in the top left corner of the array

    Attributes:

        x: A pixel map for the x coordinate.

        y: A pixel map for the y coordinate.
    """

    x: NDArray[numpy.int_]
    y: NDArray[numpy.int_]


def _parse_direction(
    # Parses a string of the format: 4x-0.9y+1.3z
    *,
    string_to_parse: str,
    direction_x: float,
    direction_y: float,
    direction_z: float,
) -> List[float]:
    direction: List[float] = [
        direction_x,
        direction_y,
        direction_z,
    ]
    items: List[str] = []
    character: str
    current_string: List[str] = []
    for character in string_to_parse:
        if character not in ("+", "-"):
            current_string.append(character)
        else:
            joined_string: str = "".join(current_string)
            if joined_string != "":
                items.append(joined_string.strip())
            current_string = []
            current_string.append(character)
    joined_string = "".join(current_string)
    if joined_string != "":
        items.append(joined_string.strip())
    for item in items:
        axis: str = item[-1]
        if axis not in ("x", "y", "z"):
            raise OmGeometryError()
        if item[:-1] == "-":
            value = "-1.0"
        elif item[:-1] == "":
            value = "1.0"
        else:
            value = item[:-1]
        if axis == "x":
            direction[0] = float(value)
        elif axis == "y":
            direction[1] = float(value)
        elif axis == "z":
            direction[2] = float(value)
    return direction


def _parse_panel_entry(
    key: str,
    value: str,
    panel: TypePanel,
    panel_name: str,
    detector: TypeDetector,
) -> None:
    # Parses entries in the geometry file that refer to panels
    if key == "min_fs":
        panel["orig_min_fs"] = int(value)
    elif key == "max_fs":
        panel["orig_max_fs"] = int(value)
    elif key == "min_ss":
        panel["orig_min_ss"] = int(value)
    elif key == "max_ss":
        panel["orig_max_ss"] = int(value)
    elif key == "corner_x":
        panel["cnx"] = float(value)
    elif key == "corner_y":
        panel["cny"] = float(value)
    elif key == "rail_direction":
        try:
            panel["rail_x"], panel["rail_y"], panel["rail_z"] = _parse_direction(
                direction_x=panel["rail_x"],
                direction_y=panel["rail_y"],
                direction_z=panel["rail_z"],
                string_to_parse=value,
            )
        except OmGeometryError:
            raise OmGeometryError("Invalid rail direction. ")
    elif key == "clen_for_centering":
        panel["clen_for_centering"] = float(value)
    elif key == "adu_per_eV":
        panel["adu_per_eV"] = float(value)
    elif key == "adu_per_photon":
        panel["adu_per_photon"] = float(value)
    elif key == "rigid_group":
        if value in detector["rigid_groups"]:
            if panel_name != "" and panel_name not in detector["rigid_groups"][value]:
                detector["rigid_groups"][value].append(panel_name)
        else:
            detector["rigid_groups"][value] = [
                panel_name,
            ]
    elif key == "clen":
        try:
            panel["clen"] = float(value)
            panel["clen_from"] = ""
        except ValueError:
            panel["clen"] = -1
            panel["clen_from"] = value
    elif key == "data":
        panel["data"] = value
    elif key == "mask":
        panel["mask"] = value
    elif key == "mask_file":
        panel["mask_file"] = value
    elif key == "saturation_map":
        panel["satmap"] = value
    elif key == "saturation_map_file":
        panel["satmap_file"] = value
    elif key == "coffset":
        panel["coffset"] = float(value)
    elif key == "res":
        panel["res"] = float(value)
    elif key == "max_adu":
        panel["max_adu"] = float(value)
    elif key == "badrow_direction":
        if value == "x":
            panel["badrow"] = "f"
        elif value == "y":
            panel["badrow"] = "s"
        elif value == "f":
            panel["badrow"] = "f"
        elif value == "s":
            panel["badrow"] = "s"
        elif value == "-":
            panel["badrow"] = "-"
        else:
            print("badrow_direction must be x, t, f, s, or '-'")
            print("Assuming '-'.")
            panel["badrow"] = "-"
    elif key == "no_index":
        panel["no_index"] = bool(value)
    elif key == "fs":
        try:
            panel["fsx"], panel["fsy"], panel["fsz"] = _parse_direction(
                direction_x=panel["fsx"],
                direction_y=panel["fsy"],
                direction_z=panel["fsz"],
                string_to_parse=value,
            )
        except OmGeometryError:
            raise OmGeometryError("Invalid fast scan direction.")
    elif key == "ss":
        try:
            panel["ssx"], panel["ssy"], panel["ssz"] = _parse_direction(
                direction_x=panel["ssx"],
                direction_y=panel["ssy"],
                direction_z=panel["ssz"],
                string_to_parse=value,
            )
        except OmGeometryError:
            raise OmGeometryError("Invalid slow scan direction.")
    elif key.startswith("dim"):
        if panel["dim_structure"] is not None:
            dim: List[Union[int, str, None]] = panel["dim_structure"]
        else:
            dim = []
        try:
            dim_index: int = int(key[3])
        except IndexError:
            raise OmGeometryError("'dim' must be followed by a number, (e.g. 'dim0')")
        except ValueError:
            raise OmGeometryError("Invalid dimension number {}".format(key[3]))
        if dim_index > len(dim) - 1:
            for _ in range(len(dim), dim_index + 1):
                dim.append(None)
        if value in ("ss", "fs", "%"):
            dim[dim_index] = value
        elif value.isdigit():
            dim[dim_index] = int(value)
        else:
            raise OmGeometryError("Invalid dim entry: {}.".format(value))
        panel["dim_structure"] = dim
    else:
        OmGeometryError(f"Unrecognized field: {key}")


def _validate_detector_geometry(detector: TypeDetector) -> None:
    # Validates the geometry file, checking for errors
    if not detector["panels"]:
        raise OmGeometryError("No panel descriptions in geometry file.")
    panel: TypePanel
    panel_name: str
    num_placeholders_in_panels: int = -1
    num_placeholders_in_masks: int = -1
    dim_length: int = -1
    for panel_name, panel in detector["panels"].items():
        if panel["dim_structure"] is not None:
            curr_num_placeholders: int = panel["dim_structure"].count("%")
        else:
            curr_num_placeholders = 0

        if num_placeholders_in_panels == -1:
            num_placeholders_in_panels = curr_num_placeholders
        else:
            if curr_num_placeholders != num_placeholders_in_panels:
                raise OmGeometryError(
                    "All panels' data and mask entries must have the same "
                    "number of placeholders."
                )

        if panel["mask"] is not None:
            curr_num_placeholders = panel["mask"].count("%")
        else:
            curr_num_placeholders = 0

        if num_placeholders_in_masks == -1:
            num_placeholders_in_masks = curr_num_placeholders
        else:
            if curr_num_placeholders != num_placeholders_in_masks:
                raise OmGeometryError(
                    "All panels' data and mask entries must have the same "
                    "number of placeholders."
                )

        found_ss: int = 0
        found_fs: int = 0
        found_placeholder: int = 0
        dim_index: int
        entry: Union[int, str, None]
        for dim_index, entry in enumerate(panel["dim_structure"]):
            if entry is None:
                raise OmGeometryError(
                    f"Dimension {dim_index} for panel {panel_name} is " "undefined."
                )
            if entry == "ss":
                found_ss += 1
            elif entry == "fs":
                found_fs += 1
            elif entry == "%":
                found_placeholder += 1
        if found_ss != 1:
            raise OmGeometryError(
                "Exactly one slow scan dim coordinate is needed (found "
                f"{found_ss} for panel {panel_name})."
            )
        if found_fs != 1:
            raise OmGeometryError(
                "Exactly one fast scan dim coordinate is needed (found "
                f"{found_fs} for panel {panel_name})."
            )
        if found_placeholder > 1:
            raise OmGeometryError(
                "Only one placeholder dim coordinate is allowed. Maximum one "
                "placeholder dim coordinate is allowed "
                f"(found {found_placeholder} for panel {panel_name})"
            )
        if dim_length == -1:
            dim_length = len(panel["dim_structure"])
        elif dim_length != len(panel["dim_structure"]):
            raise OmGeometryError(
                "Number of dim coordinates must be the same for all panels."
            )
        if dim_length == 1:
            raise OmGeometryError("Number of dim coordinates must be at least two.")

        if panel["orig_min_fs"] < 0:
            raise OmGeometryError(
                "Please specify the minimum fs coordinate for panel " f"{panel_name}."
            )
        if panel["orig_max_fs"] < 0:
            raise OmGeometryError(
                "Please specify the maximum fs coordinate for panel " f"{panel_name}."
            )
        if panel["orig_min_ss"] < 0:
            raise OmGeometryError(
                "Please specify the minimum ss coordinate for panel " f"{panel_name}."
            )
        if panel["orig_max_ss"] < 0:
            raise OmGeometryError(
                "Please specify the maximum ss coordinate for panel " f"{panel_name}."
            )
        if panel["cnx"] is None:
            raise OmGeometryError(
                "Please specify the corner X coordinate for panel " f"{panel_name}."
            )
        if panel["clen"] is None and panel["clen_from"] is None:
            raise OmGeometryError(
                f"Please specify the camera length for panel {panel_name}."
            )
        if panel["res"] < 0:
            raise OmGeometryError(
                f"Please specify the resolution or panel {panel_name}."
            )
        if panel["adu_per_eV"] is None and panel["adu_per_photon"] is None:
            raise OmGeometryError(
                "Please specify either adu_per_eV or adu_per_photon for panel "
                f"{panel_name}."
            )

        if (panel["fsx"] * panel["ssy"] - panel["ssx"] * panel["fsy"]) == 0.0:
            raise OmGeometryError(f"Panel {panel_name} transformation is singular.")

    if num_placeholders_in_masks > num_placeholders_in_panels:
        raise OmGeometryError(
            "Number of placeholders in mask cannot be larger the number than "
            "for data."
        )

    bad_region_name: str
    bad_region: TypeBadRegion
    for bad_region_name, bad_region in detector["bad"].items():
        if bad_region["is_fsss"] == 99:
            raise OmGeometryError(
                "Please specify the coordinate ranges for bad "
                f"region {bad_region_name}."
            )
    group: str
    for group in detector["rigid_groups"]:
        name: str
        for name in detector["rigid_groups"][group]:
            if name not in detector["panels"]:
                raise OmGeometryError(
                    "Cannot add panel to rigid_group. Panel not " f"found: {name}."
                )
    group_collection: str
    for group_collection in detector["rigid_group_collections"]:
        group_name: str
        for group_name in detector["rigid_group_collections"][group_collection]:
            if group_name not in detector["rigid_groups"]:
                raise OmGeometryError(
                    "Cannot add rigid_group to collection. Rigid group not "
                    f"found: {group_name}."
                )


def _read_crystfel_geometry_from_text(  # noqa: C901
    *,
    text_lines: List[str],
) -> Tuple[TypeDetector, TypeBeam, str]:  # noqa: C901
    """
    Reads CrystFEL geometry information from text data.

    This function is a Python re-implementation of the `get_detector_geometry_2` C
    function from CrystFEL. It reads some CrystFEL geometry information provided in the
    form of text data (and encoded using a format fully documented in the relevant
    [man page](http://www.desy.de/~twhite/crystfel/manual-crystfel_geometry.html)),
    and returns a set of nested dictionaries whose content matches CrystFEL's internal
    representation of the information in the file.

    This function expects instead the geometry data to be provided in the format of
    lines of text. It is designed for cases in which the content of a CrystFEL geometry
    file has already been read and has been stored in memory in text format.

    Arguments:

        text_lines: a list of strings with geometry information in text format (usually
            corresponding to the content of a CrystFEL geometry file).

    Returns:

        A tuple with the information loaded from the file.

            * The first entry in the tuple is a
              [TypeDetector][om.lib.geometry.TypeDetector] dictionary storing
              information related to the detector geometry.

            * The second entry in the tuple is a
              [TypeBeam] om.lib.geometry.TypeBeam] dictionary storing information about
              the x-ray beam.

            * The third entry is the internal path, in an HDF5 data file, of the
              location where Bragg peak information can be found. This is only used if
              CrystFEL extracts Bragg peak information from files. If the geometry
              file does not provide this information, this entry is just an empty
              string.

    Raises:

        OmGeometryError: Raised when an error is encountered during the parsing of the
            geometry information.
    """
    beam: TypeBeam = {
        "photon_energy": 0.0,
        "photon_energy_from": "",
        "photon_energy_scale": 1.0,
    }
    detector: TypeDetector = {
        "panels": collections.OrderedDict(),
        "bad": collections.OrderedDict(),
        "mask_good": 0,
        "mask_bad": 0,
        "rigid_groups": {},
        "rigid_group_collections": {},
        "furthest_out_panel": "",
        "furthest_out_fs": float("NaN"),
        "furthest_out_ss": float("NaN"),
        "furthest_in_panel": "",
        "furthest_in_fs": float("NaN"),
        "furthest_in_ss": float("NaN"),
    }
    default_panel: TypePanel = {
        "cnx": float("NaN"),
        "cny": float("NaN"),
        "coffset": 0.0,
        "clen": float("NaN"),
        "clen_from": "",
        "mask": "",
        "mask_file": "",
        "satmap": "",
        "satmap_file": "",
        "res": -1.0,
        "badrow": "-",
        "no_index": False,
        "adu_per_photon": float("NaN"),
        "max_adu": float("inf"),
        "data": "",
        "adu_per_eV": float("NaN"),
        "dim_structure": [],
        "fsx": 1.0,
        "fsy": 0.0,
        "fsz": 0.0,
        "ssx": 0.0,
        "ssy": 1.0,
        "ssz": 0.0,
        "rail_x": float("NaN"),
        "rail_y": float("NaN"),
        "rail_z": float("NaN"),
        "clen_for_centering": float("NaN"),
        "xfs": 0.0,
        "yfs": 1.0,
        "xss": 1.0,
        "yss": 0.0,
        "orig_min_fs": -1,
        "orig_max_fs": -1,
        "orig_min_ss": -1,
        "orig_max_ss": -1,
        "w": 0,
        "h": 0,
    }
    default_bad_region: TypeBadRegion = {
        "panel": "",
        "min_x": float("NaN"),
        "max_x": float("NaN"),
        "min_y": float("NaN"),
        "max_y": float("NaN"),
        "min_fs": 0,
        "max_fs": 0,
        "min_ss": 0,
        "max_ss": 0,
        "is_fsss": 99,
    }
    default_dim: List[Union[int, str, None]] = ["ss", "fs"]
    hdf5_peak_path: str = ""
    line: str
    for line in text_lines:
        if len(line.strip()) == 0:
            continue
        if line.strip().startswith(";"):
            continue
        try:
            line_without_comments: str = line.strip().split(";")[0]
            line_parts: List[str] = line_without_comments.split("=")
            if len(line_parts) != 2:
                raise OmGeometryError("The line does not have the format 'key=value'")
            key: str = line_parts[0].strip()
            value: str = line_parts[1].strip()
            key_parts: List[str] = key.split("/")
            if len(key_parts) < 2:
                if key == "mask_bad":
                    try:
                        detector["mask_bad"] = int(value)
                    except ValueError:
                        detector["mask_bad"] = int(value, base=16)
                elif key == "mask_good":
                    try:
                        detector["mask_good"] = int(value)
                    except ValueError:
                        detector["mask_good"] = int(value, base=16)
                elif key == "photon_energy":
                    if value.startswith("/"):
                        beam["photon_energy"] = 0.0
                        beam["photon_energy_from"] = value
                    else:
                        beam["photon_energy"] = float(value)
                        beam["photon_energy_from"] = ""
                elif key == "photon_energy_scale":
                    beam["photon_energy_scale"] = float(value)
                elif key == "peak_info_location":
                    hdf5_peak_path = value
                elif key.startswith("rigid_group") and not key.startswith(
                    "rigid_group_collection"
                ):
                    detector["rigid_groups"][key[12:]] = value.split(",")
                elif key.startswith("rigid_group_collection"):
                    detector["rigid_group_collections"][key[23:]] = value.split(",")
                else:
                    _parse_panel_entry(
                        key=key,
                        value=value,
                        panel=default_panel,
                        panel_name="",
                        detector=detector,
                    )
                continue
            if key_parts[0].startswith("bad"):
                bad_region_name: str = key_parts[0]
                bad_region_key: str = key_parts[1]
                if bad_region_name not in detector["bad"]:
                    detector["bad"][bad_region_name] = copy.deepcopy(default_bad_region)
                curr_bad_region: TypeBadRegion = detector["bad"][bad_region_name]
                if curr_bad_region["is_fsss"] == 99:
                    if bad_region_key in ("min_ss", "min_fs", "max_ss", "max_fs"):
                        curr_bad_region["is_fsss"] = 1
                    else:
                        curr_bad_region["is_fsss"] = 0
                if curr_bad_region["is_fsss"] == 1 and bad_region_key in (
                    "min_x",
                    "min_y",
                    "max_x",
                    "max_y",
                ):
                    raise OmGeometryError("You can't mix x/y and fs/ss in a bad region")
                if bad_region_key == "min_x":
                    curr_bad_region["min_x"] = float(value)
                elif bad_region_key == "max_x":
                    curr_bad_region["max_x"] = float(value)
                elif bad_region_key == "min_y":
                    curr_bad_region["min_y"] = float(value)
                elif bad_region_key == "max_y":
                    curr_bad_region["max_y"] = float(value)
                elif bad_region_key == "min_fs":
                    curr_bad_region["min_fs"] = int(value)
                elif bad_region_key == "max_fs":
                    curr_bad_region["max_fs"] = int(value)
                elif bad_region_key == "min_ss":
                    curr_bad_region["min_ss"] = int(value)
                elif bad_region_key == "max_ss":
                    curr_bad_region["max_ss"] = int(value)
                elif bad_region_key == "panel":
                    curr_bad_region["panel"] = value
                else:
                    raise OmGeometryError("Unrecognized field: {}".format(key))
            else:
                panel_name: str = key_parts[0]
                panel_key: str = key_parts[1]
                if key_parts[0] not in detector["panels"]:
                    detector["panels"][panel_name] = copy.deepcopy(default_panel)
                curr_panel: TypePanel = detector["panels"][panel_name]
                _parse_panel_entry(
                    key=panel_key,
                    value=value,
                    panel=curr_panel,
                    panel_name=panel_name,
                    detector=detector,
                )
        except OmGeometryError as exp:
            raise OmGeometryError(
                "Cannot interpret the following line in the geometry file: "
                f" {line.strip()}\n"
                f"Reason: {str(exp)}",
            )

    panel: TypePanel
    for panel in detector["panels"].values():
        if len(panel["dim_structure"]) == 0:
            panel["dim_structure"] = copy.deepcopy(default_dim)

    _validate_detector_geometry(detector)

    min_d: float = float("inf")
    max_d: float = 0.0
    for panel_name, panel in detector["panels"].items():
        if panel["rail_x"] is None:
            panel["rail_x"] = 0.0
            panel["rail_y"] = 0.0
            panel["rail_z"] = 1.0

        if panel["clen_for_centering"] is None:
            panel["clen_for_centering"] = 0.0

        d: float = panel["fsx"] * panel["ssy"] - panel["ssx"] * panel["fsy"]
        panel["xfs"] = panel["ssy"] / d
        panel["yfs"] = panel["ssx"] / d
        panel["xss"] = panel["fsy"] / d
        panel["yss"] = panel["fsx"] / d
        panel["w"] = panel["orig_max_fs"] - panel["orig_min_fs"] + 1
        panel["h"] = panel["orig_max_ss"] - panel["orig_min_ss"] + 1

        fs: int
        ss: int
        for fs in range(0, panel["w"] + 1, panel["w"]):
            for ss in range(0, panel["h"] + 1, panel["h"]):
                xs: float = fs * panel["fsx"] + ss * panel["ssx"]
                ys: float = fs * panel["fsy"] + ss * panel["ssy"]
                rx: float = (xs + panel["cnx"]) / panel["res"]
                ry: float = (ys + panel["cny"]) / panel["res"]
                dist: float = math.sqrt(rx * rx + ry * ry)
                if dist > max_d:
                    detector["furthest_out_panel"] = panel_name
                    detector["furthest_out_fs"] = fs
                    detector["furthest_out_ss"] = ss
                    max_d = dist
                elif dist < min_d:
                    detector["furthest_in_panel"] = panel_name
                    detector["furthest_in_fs"] = fs
                    detector["furthest_in_ss"] = ss
                    min_d = dist

    return detector, beam, hdf5_peak_path


def _compute_pix_maps(*, geometry: TypeDetector) -> TypePixelMaps:
    # Computes pixel maps from CrystFEL geometry information.

    max_fs_in_slab: int = numpy.array(
        [geometry["panels"][k]["orig_max_fs"] for k in geometry["panels"]]
    ).max()
    max_ss_in_slab: int = numpy.array(
        [geometry["panels"][k]["orig_max_ss"] for k in geometry["panels"]]
    ).max()

    x_map: NDArray[numpy.float_] = numpy.zeros(
        shape=(max_ss_in_slab + 1, max_fs_in_slab + 1), dtype=numpy.float32
    )
    y_map: NDArray[numpy.float_] = numpy.zeros(
        shape=(max_ss_in_slab + 1, max_fs_in_slab + 1), dtype=numpy.float32
    )
    z_map: NDArray[numpy.float_] = numpy.zeros(
        shape=(max_ss_in_slab + 1, max_fs_in_slab + 1), dtype=numpy.float32
    )

    # Iterates over the panels. For each panel, determines the pixel indices, then
    # computes the x,y vectors. Finally, copies the panel pixel maps into the
    # detector-wide pixel maps.
    panel_name: str
    for panel_name in geometry["panels"]:
        if "clen" in geometry["panels"][panel_name]:
            first_panel_camera_length: float = geometry["panels"][panel_name]["clen"]
        else:
            first_panel_camera_length = 0.0

        ss_grid: NDArray[numpy.int_]
        fs_grid: NDArray[numpy.int_]
        ss_grid, fs_grid = numpy.meshgrid(
            numpy.arange(
                geometry["panels"][panel_name]["orig_max_ss"]
                - geometry["panels"][panel_name]["orig_min_ss"]
                + 1
            ),
            numpy.arange(
                geometry["panels"][panel_name]["orig_max_fs"]
                - geometry["panels"][panel_name]["orig_min_fs"]
                + 1
            ),
            indexing="ij",
        )
        y_panel: NDArray[numpy.float_] = (
            ss_grid * geometry["panels"][panel_name]["ssy"]
            + fs_grid * geometry["panels"][panel_name]["fsy"]
            + geometry["panels"][panel_name]["cny"]
        )
        x_panel: NDArray[numpy.float_] = (
            ss_grid * geometry["panels"][panel_name]["ssx"]
            + fs_grid * geometry["panels"][panel_name]["fsx"]
            + geometry["panels"][panel_name]["cnx"]
        )
        x_map[
            geometry["panels"][panel_name]["orig_min_ss"] : geometry["panels"][
                panel_name
            ]["orig_max_ss"]
            + 1,
            geometry["panels"][panel_name]["orig_min_fs"] : geometry["panels"][
                panel_name
            ]["orig_max_fs"]
            + 1,
        ] = x_panel
        y_map[
            geometry["panels"][panel_name]["orig_min_ss"] : geometry["panels"][
                panel_name
            ]["orig_max_ss"]
            + 1,
            geometry["panels"][panel_name]["orig_min_fs"] : geometry["panels"][
                panel_name
            ]["orig_max_fs"]
            + 1,
        ] = y_panel
        z_map[
            geometry["panels"][panel_name]["orig_min_ss"] : geometry["panels"][
                panel_name
            ]["orig_max_ss"]
            + 1,
            geometry["panels"][panel_name]["orig_min_fs"] : geometry["panels"][
                panel_name
            ]["orig_max_fs"]
            + 1,
        ] = first_panel_camera_length

    r_map: NDArray[numpy.float_] = numpy.sqrt(numpy.square(x_map) + numpy.square(y_map))
    phi_map: NDArray[numpy.float_] = numpy.arctan2(y_map, x_map)

    return {
        "x": x_map,
        "y": y_map,
        "z": z_map,
        "radius": r_map,
        "phi": phi_map,
    }


def _compute_min_array_shape(*, pixel_maps: TypePixelMaps) -> Tuple[int, int]:
    # Computes the minimum shape of an array that can hold the pixel information for
    # the image representation of a detector data frame (starting from CrystFEL
    # geometry information).
    y_minimum: int = (
        2 * int(max(abs(pixel_maps["y"].max()), abs(pixel_maps["y"].min()))) + 2
    )
    x_minimum: int = (
        2 * int(max(abs(pixel_maps["x"].max()), abs(pixel_maps["x"].min()))) + 2
    )
    return (y_minimum, x_minimum)


def _compute_visualization_pix_maps(
    *, pixel_maps: TypePixelMaps
) -> TypeVisualizationPixelMaps:
    # Computes pixel maps that be used for data visualization starting from a set of
    # pixel maps that refer to the reference system of the detector.

    # Shifts the origin of the reference system from the beam position to the top-left
    # of the image that will be displayed. Computes the size of the array needed to
    # display the data, then use this information to estimate the magnitude of the
    # shift.
    min_shape: Tuple[int, int] = _compute_min_array_shape(pixel_maps=pixel_maps)
    new_x_map: NDArray[numpy.int_] = (
        numpy.array(object=pixel_maps["x"], dtype=int) + min_shape[1] // 2 - 1
    )
    new_y_map: NDArray[numpy.int_] = (
        numpy.array(object=pixel_maps["y"], dtype=int) + min_shape[0] // 2 - 1
    )

    return {
        "x": new_x_map,
        "y": new_y_map,
    }


def _retrieve_layout_info_from_geometry(
    *, geometry: TypeDetector
) -> TypeDetectorLayoutInformation:
    # Retrieves information about the internal data layout of a detector data frame,
    # Starting from CrystFEL geometry information.
    panels: List[TypePanel] = list(geometry["panels"].values())
    panel_fs_size: int = panels[0]["orig_max_fs"] - panels[0]["orig_min_fs"] + 1
    panel_ss_size: int = panels[0]["orig_max_ss"] - panels[0]["orig_min_ss"] + 1

    total_fs_size: int = max((panel["orig_max_fs"] for panel in panels))
    total_ss_size: int = max((panel["orig_max_ss"] for panel in panels))

    return {
        "asic_nx": panel_fs_size,
        "asic_ny": panel_ss_size,
        "nasics_x": (total_fs_size + 1) // panel_fs_size,
        "nasics_y": (total_ss_size + 1) // panel_ss_size,
    }


class GeometryInformation:
    """
    See documentation for the `__init__` function.
    """

    def __init__(
        self,
        *,
        geometry_description: List[str],
        geometry_format: str,
    ) -> None:
        """
        Detector geometry information.

        This class stores the all the information describing the geometry of an area
        detector. It is initialized with a block of text containing the description of
        the geometry of thr detector (usually the content of a geometry file), and with
        a string specifying the format of the provided information.

        Once the class has been initialized, methods can be invoked to recover
        information about the geometry: lookup-pixel maps, detector's pixel size, etc.

        Arguments:

            geometry_description: a block of text describing the detector's geometry

            geometry_format: a string describing the format of the provided geometry
                description. Currently the following formats are supported:

                * `crystfel`: the geometry format used by the CrystFEL software
                  package.processing of crystallography data. The format is fully
                  documented in CrystFEL's
                  [man pages](http://www.desy.de/~twhite/crystfel/manual-crystfel_geometry.html)

        Raises:

            OmGeometryError: Raised if the format of the provided geometry information
                is not supported.
        """

        if geometry_format == "crystfel":
            geometry: TypeDetector
            geometry, _, __ = _read_crystfel_geometry_from_text(
                text_lines=geometry_description
            )

            self._layout_info: TypeDetectorLayoutInformation = (
                _retrieve_layout_info_from_geometry(geometry=geometry)
            )
            self._pixel_maps: TypePixelMaps = _compute_pix_maps(geometry=geometry)

            # Theoretically, the pixel size could be different for every module of the
            # detector. The pixel size of the first module is taken as the pixel size
            # of the whole detector.
            res_first_panel: float = geometry["panels"][
                tuple(geometry["panels"].keys())[0]
            ]["res"]

            # res from crystfel, which is 1/pixel_size
            self._pixel_size: float = 1.0 / res_first_panel

            # Theoretically, panel coffset could be different for every module of the
            # detector. The panel coffset of the first module is taken as the pixel
            # size of the whole detector.
            self._detector_distance_offset: float = geometry["panels"][
                list(geometry["panels"].keys())[0]
            ]["coffset"]
        else:
            raise OmGeometryError("Geometry format is not supported.")

    @classmethod
    def from_file(
        cls, *, geometry_filename: str, geometry_format: Union[str, None] = None
    ) -> "GeometryInformation":
        """
        Reads geometry description from file.

        This class method initializes the
        [GeometryInformation][om.lib.geometry.GeometryInformation] class from a file,
        rather than from a block of text.

        Arguments:

            geometry_filename: the relative or absolute path to file containing the
                description of the geometry of an area detector

            geometry_format: a string describing the format of the geometry
                description. Currently the following formats are supported:

                * `crystfel`: the geometry format used by the CrystFEL software
                  package. The format is fully documented in the CrystFEL's
                  [man pages](http://www.desy.de/~twhite/crystfel/manual-crystfel_geometry.html)

        Raises:

            OmGeometryError: Raised if the format of the geometry file cannot be
                inferred from the file's extension.
        """

        format_extension_dict: Dict[str, str] = {".geom": "crystfel"}

        if geometry_format is None:
            extension = Path(geometry_filename).suffix
            try:
                geometry_format = format_extension_dict[extension]
            except KeyError:
                raise OmGeometryError(
                    "Cannot infer the geometry file format from the file extension "
                    f"'{extension}'. Supported extensions are: "
                    f"{list(format_extension_dict.keys())}"
                )

        with open(Path(geometry_filename), "r") as file_handle:
            geometry_file_content: List[str] = file_handle.readlines()

        return cls(
            geometry_description=geometry_file_content,
            geometry_format=geometry_format,
        )

    def get_pixel_maps(self) -> TypePixelMaps:
        """
        Retrieves pixel maps.

        This function retrieves look-up pixel maps storing coordinate information for
        each pixel of a detector data frame.

        Returns:

            The set of look-up pixel maps.
        """
        return self._pixel_maps

    def get_layout_info(self) -> TypeDetectorLayoutInformation:
        """
        Retrieves detector layout information for the peakfinder8 algorithm.

        This function retrieves information about the internal layout of a detector
        data frame (number and size of ASICs, etc.). This information is needed by the
        [peakfinder8][om.algorithms.crystallography.Peakfinder8PeakDetection] peak
        detection algorithm.

        Returns:

            Internal layout of a detector data frame.
        """
        return self._layout_info

    def get_detector_distance_offset(self) -> float:
        """
        Retrieves detector distance offset information.

        This function retrieves the offset that should be added to the nominal
        detector distance provided by the facility to obtain the real detector distance
        (i.e., the distance between the sample interaction point and the area detector
        where data is recorded. This value is often stored together with the geometry
        information, but if it is not available, the function returns None.

        Returns:

            The detector distance offset in meters, or None if the information is not
            available.
        """
        return self._detector_distance_offset

    def get_pixel_size(self) -> float:
        """
        Retrieves the size of an area detector pixel.

        This function retrieves information about the size of each pixel making up an
        area detector. All pixels in the detector are assumed to have the same size,
        and have a square shape. The value returned by this function describes the
        length of the side of each pixel.

        Returns:

            Length of the pixel's side in meters.
        """
        return self._pixel_size


class DataVisualizer:
    """
    See documentation for the `__init__` function.
    """

    def __init__(
        self,
        *,
        pixel_maps: TypePixelMaps,
    ):
        """
        Visualization of detector data with geometry applied.

        This class stores all the information needed to display detector data with
        geometry applied to it. Once the class has been initialized, it can be invoked
        to retrieve visualization look-up pixel maps and other information needed to
        display the data. A detector frame is assumed to be visualized in the form of a
        2D image showing an approximate representation of the physical layout of the
        detector.

        Arguments:

            pixel_maps: A set of look-up pixel maps storing coordinate information for
                each pixel in detector data frame.
        """
        self._pixel_maps = pixel_maps
        self._visualization_pixel_maps: TypeVisualizationPixelMaps = (
            _compute_visualization_pix_maps(pixel_maps=self._pixel_maps)
        )
        self._min_array_shape: Tuple[int, int] = _compute_min_array_shape(
            pixel_maps=self._pixel_maps
        )

    def get_pixel_maps(self) -> TypePixelMaps:
        """
        Retrieves pixel maps.

        This function just returns the pixel maps that were used to initialize the
        class.

        Returns:

            A set of look-up pixel maps storing coordinate information for each pixel
            in detector data frame.
        """
        return self._pixel_maps

    def get_visualization_pixel_maps(self) -> TypeVisualizationPixelMaps:
        """
        Retrieves visualization pixel maps.

        This function retrieves a set of visualization look-up pixel maps. These pixel
        maps store the information needed to display a detector data frame. with
        geometry information applied to it, in the form of a 2D image.

        Returns:

            A set of look-up pixel maps storing the information needed to display a
            detector data frame as a 2D image.
        """
        return self._visualization_pixel_maps

    def get_min_array_shape_for_visualization(self) -> Tuple[int, int]:
        """
        Retrieves the minimum shape of an array that can store a detector frame image.

        Computes the minimum size of an array that can hold the pixel information for
        the image representation of a detector data frame. The size of the array is
        enough to include the full representation of the data frame with geometry
        applied. The size of the array also calculated assuming that the center of the
        detector's reference system is kept at the center of the detector image.

        Returns:

            The minimum shape, in numpy format, of an array storing the image
            representation of a detector data frame.
        """
        return self._min_array_shape

    def visualize_data(
        self,
        *,
        data: Union[NDArray[numpy.int_], NDArray[numpy.float_]],
        array_for_visualization: Union[
            NDArray[numpy.int_], NDArray[numpy.float_], None
        ] = None,
    ) -> Union[NDArray[numpy.int_], NDArray[numpy.float_]]:
        """
        Applies geometry information to a detector data frame.

        This function applies the geometry information stored by the class to a
        provided detector data frame. It returns a 2D array storing the pixel
        information of an image representing the data frame with geometry applied.

        If a pre-existing visualization array is provided, with exactly the shape
        returned by the
        [get_min_array_shape_for_visualization][om.lib.geometry.DataVisualizer.get_min_array_shape_for_visualization]
        function, this function can used it to store the pixel information. Otherwise
        the function creates a new array with the appropriate shape.

        Arguments:

            data: The detector data frame on which geometry should be applied.

            array_for_visualization: Either a pre-existing array of the correct size,
                in which case the array is used to store the pixel information of
                the detector data frame image, or None. If the value of this argument
                is None, an array with the appropriate shape is generated by the
                function. Optional. Defaults to None.

        Returns:

            An array containing pixel information for the image representation of the
            provided detector data frame.

        Raises:

            OmWrongArrayShape: Raised if the provided array has the wrong shape and
                cannot be used to store the pixel information.
        """
        if array_for_visualization is None:
            visualization_array: Union[
                NDArray[numpy.float_], NDArray[numpy.int_]
            ] = numpy.zeros(self._min_array_shape, dtype=float)
        else:
            if array_for_visualization.shape != self._min_array_shape:
                raise OmWrongArrayShape(
                    "The provided array does not fit the data."
                    "Please check the array size"
                )
            visualization_array = array_for_visualization

        visualization_array[
            self._visualization_pixel_maps["y"].flatten(),
            self._visualization_pixel_maps["x"].flatten(),
        ] = data.ravel().astype(visualization_array.dtype)

        return visualization_array
