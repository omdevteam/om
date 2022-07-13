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
CrystFEL's geometry utilities.

This module contains functions that manipulate geometry information stored in the
format used by the CrystFEL software package.
"""
import collections
import copy
import math
import re
import sys
from typing import Any, Dict, List, TextIO, Tuple, Union

import numpy
from mypy_extensions import TypedDict
from numpy.typing import NDArray

from om.utils import exceptions
from om.utils.rich_console import console


class TypeBeam(TypedDict):
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

        adu_per_eV: The number of ADUs per eV of photon energy for
            the panel.

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
            reference system from the interation point, as reported by the facility,

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
            are [TypePanel][om.utils.crystfel_geometry.TypePanel] dictionaries.

        bad: The bad regions in the detector. The value corresponding to this key is a
            dictionary containing information about the bad regions in the detector. In
            the dictionary, the keys are bad region names, and the values are
            [TypeBadRegion][om.utils.crystfel_geometry.TypeBadRegion] dictionaries.

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


class TypePixelMaps(TypedDict):
    """
    A dictionary storing a set of pixel maps,

    Attributes:

        x: A pixel map for the x coordinate.

        y: A pixel map for the y coordinate.

        z: A pixel map for the z coordinate.

        radius: A pixel map storing the distance of each pixel from the center of the
            detector reference system.

        phi: A pixel map storing, for each pixel, the amplitude of the angle drawn by
            the pixel, the center of the detector reference system, and the x axis.
    """

    x: Union[NDArray[numpy.float_], NDArray[numpy.int_]]
    y: Union[NDArray[numpy.float_], NDArray[numpy.int_]]
    z: Union[NDArray[numpy.float_], None]
    radius: Union[NDArray[numpy.float_], None]
    phi: Union[NDArray[numpy.float_], None]


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
            raise RuntimeError()
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
        except RuntimeError:
            raise exceptions.OmGeometryError("Invalid rail direction. ")
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
        except RuntimeError:
            raise RuntimeError("Invalid fast scan direction.")
    elif key == "ss":
        try:
            panel["ssx"], panel["ssy"], panel["ssz"] = _parse_direction(
                direction_x=panel["ssx"],
                direction_y=panel["ssy"],
                direction_z=panel["ssz"],
                string_to_parse=value,
            )
        except RuntimeError:
            raise RuntimeError("Invalid slow scan direction.")
    elif key.startswith("dim"):
        if panel["dim_structure"] is not None:
            dim: List[Union[int, str, None]] = panel["dim_structure"]
        else:
            dim = []
        try:
            dim_index: int = int(key[3])
        except IndexError:
            raise RuntimeError("'dim' must be followed by a number, (e.g. 'dim0')")
        except ValueError:
            raise RuntimeError("Invalid dimension number {}".format(key[3]))
        if dim_index > len(dim) - 1:
            for _ in range(len(dim), dim_index + 1):
                dim.append(None)
        if value in ("ss", "fs", "%"):
            dim[dim_index] = value
        elif value.isdigit():
            dim[dim_index] = int(value)
        else:
            raise RuntimeError("Invalid dim entry: {}.".format(value))
        panel["dim_structure"] = dim
    else:
        RuntimeError(f"Unrecognized field: {key}")


def _validate_detector_geometry(detector: TypeDetector) -> None:
    # Validates the geometry file, checking for errors
    if not detector["panels"]:
        raise exceptions.OmGeometryError("No panel descriptions in geometry file.")
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
                raise exceptions.OmGeometryError(
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
                raise exceptions.OmGeometryError(
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
                raise exceptions.OmGeometryError(
                    f"Dimension {dim_index} for panel {panel_name} is " "undefined."
                )
            if entry == "ss":
                found_ss += 1
            elif entry == "fs":
                found_fs += 1
            elif entry == "%":
                found_placeholder += 1
        if found_ss != 1:
            raise exceptions.OmGeometryError(
                "Exactly one slow scan dim coordinate is needed (found "
                f"{found_ss} for panel {panel_name})."
            )
        if found_fs != 1:
            raise exceptions.OmGeometryError(
                "Exactly one fast scan dim coordinate is needed (found "
                f"{found_fs} for panel {panel_name})."
            )
        if found_placeholder > 1:
            raise exceptions.OmGeometryError(
                "Only one placeholder dim coordinate is allowed. Maximum one "
                "placeholder dim coordinate is allowed "
                f"(found {found_placeholder} for panel {panel_name})"
            )
        if dim_length == -1:
            dim_length = len(panel["dim_structure"])
        elif dim_length != len(panel["dim_structure"]):
            raise exceptions.OmGeometryError(
                "Number of dim coordinates must be the same for all panels."
            )
        if dim_length == 1:
            raise exceptions.OmGeometryError(
                "Number of dim coordinates must be at least two."
            )

        if panel["orig_min_fs"] < 0:
            raise exceptions.OmGeometryError(
                "Please specify the minimum fs coordinate for panel " f"{panel_name}."
            )
        if panel["orig_max_fs"] < 0:
            raise exceptions.OmGeometryError(
                "Please specify the maximum fs coordinate for panel " f"{panel_name}."
            )
        if panel["orig_min_ss"] < 0:
            raise exceptions.OmGeometryError(
                "Please specify the minimum ss coordinate for panel " f"{panel_name}."
            )
        if panel["orig_max_ss"] < 0:
            raise exceptions.OmGeometryError(
                "Please specify the maximum ss coordinate for panel " f"{panel_name}."
            )
        if panel["cnx"] is None:
            raise exceptions.OmGeometryError(
                "Please specify the corner X coordinate for panel " f"{panel_name}."
            )
        if panel["clen"] is None and panel["clen_from"] is None:
            raise exceptions.OmGeometryError(
                f"Please specify the camera length for panel {panel_name}."
            )
        if panel["res"] < 0:
            raise exceptions.OmGeometryError(
                f"Please specify the resolution or panel {panel_name}."
            )
        if panel["adu_per_eV"] is None and panel["adu_per_photon"] is None:
            raise exceptions.OmGeometryError(
                "Please specify either adu_per_eV or adu_per_photon for panel "
                f"{panel_name}."
            )

        if (panel["fsx"] * panel["ssy"] - panel["ssx"] * panel["fsy"]) == 0.0:
            raise exceptions.OmGeometryError(
                f"Panel {name} transformation is singular."
            )

    if num_placeholders_in_masks > num_placeholders_in_panels:
        raise exceptions.OmGeometryError(
            "Number of placeholders in mask cannot be larger the number than "
            "for data."
        )

    bad_region_name: str
    bad_region: TypeBadRegion
    for bad_region_name, bad_region in detector["bad"].items():
        if bad_region["is_fsss"] == 99:
            raise exceptions.OmGeometryError(
                "Please specify the coordinate ranges for bad "
                f"region {bad_region_name}."
            )
    group: str
    for group in detector["rigid_groups"]:
        name: str
        for name in detector["rigid_groups"][group]:
            if name not in detector["panels"]:
                raise exceptions.OmGeometryError(
                    "Cannot add panel to rigid_group. Panel not " f"found: {name}."
                )
    group_collection: str
    for group_collection in detector["rigid_group_collections"]:
        group_name: str
        for group_name in detector["rigid_group_collections"][group_collection]:
            if group_name not in detector["rigid_groups"]:
                raise exceptions.OmGeometryError(
                    "Cannot add rigid_group to collection. Rigid group not "
                    f"found: {name}."
                )


def read_crystfel_geometry(  # noqa: C901
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
    representation of the information in the file (see the libcrystfel/src/detector.h
    and the libcrystfel/src/image.c source code files from CrystFEL for more
    information). While the original `get_detector_geometry_2` function required the
    name of a crystfel geometry file as input, this function expects instead the
    geometry data to be provided in the format of lines of text. It is designed for
    cases in which the content of a crystfel geometry file has already been read and
    has been stored in memory in text format.

    Arguments:

        text_lines: a list of strings with geometry information in text format (usually
            corresponding to the content of a CrystFEL geometry file).

    Returns:

        A tuple with the information loaded from the file.

            * The first entry in the tuple is a
            [TypeDetector][om.utils.crystfel_geometry.TypeDetector] dictionary storing
            information related to the detector geometry.

            * The second entry in the tuple is a
            [TypeBeam] [om.utils.crystfel_geometry.TypeBeam] dictionary storing
            information about the beam properties.

            * The third entry is the internal path, in an HDF5 data file, to the
            location where Bragg peak information for the current detector can be
            found. This is only used if CrystFEL extracts Bragg peak information from
            files. If the geometry file does not provide this information, this entry
            has the value of an empty string.
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
                raise RuntimeError("The line does not have the format 'key=value'")
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
                    raise RuntimeError("You can't mix x/y and fs/ss in a bad region")
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
                    raise RuntimeError("Unrecognized field: {}".format(key))
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

        except RuntimeError as exp:
            raise exceptions.OmGeometryError(
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


def compute_pix_maps(*, geometry: TypeDetector) -> TypePixelMaps:
    """
    Computes pixel maps from CrystFEL geometry information.

    This function takes as input the geometry information read from a
    [CrystFEL geometry file](http://www.desy.de/~twhite/crystfel/manual-crystfel_geometry.html),
    and returns a set of pixel maps. The pixel maps can be used to determine the
    exact coordinates, in the detector reference system, of each pixel of the array
    that stores the detector data.

    The origin and the orientation of the reference system for the pixel maps are set
    according to conventions used by CrystFEL:

    * The center of the reference system is assumed to be the beam interaction point.

    * +z is the beam direction, and points along the beam (i.e. away from the source).

    * +y points towards the zenith (ceiling).

    * +x completes the right-handed coordinate system.

    Arguments:

        geometry: A dictionary returned by the
            [load_crystfel_geometry][om.utils.crystfel_geometry.load_crystfel_geometry]
            function, storing the detector geometry information.

    Returns:

        A dictionary storing the pixel maps.
    """
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
        y_panel: NDArray[numpy.int_] = (
            ss_grid * geometry["panels"][panel_name]["ssy"]
            + fs_grid * geometry["panels"][panel_name]["fsy"]
            + geometry["panels"][panel_name]["cny"]
        )
        x_panel: NDArray[numpy.int_] = (
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


def load_crystfel_geometry(  # noqa: C901
    *,
    filename: str,
) -> Tuple[TypeDetector, TypeBeam, str]:  # noqa: C901
    """
    Loads a CrystFEL geometry file.

    This function is a Python re-implementation of the `get_detector_geometry_2` C
    function from CrystFEL. It reads information from a CrystFEL geometry file (which
    uses a format fully documented in the relevant
    [man page](http://www.desy.de/~twhite/crystfel/manual-crystfel_geometry.html)),
    and returns a set of nested dictionaries whose content matches CrystFEL's internal
    representation of the information in the file (see the libcrystfel/src/detector.h
    and the libcrystfel/src/image.c source code files from CrystFEL for more
    information).

    This function currently re-implements the `get_detector_geometry_2` function from
    CrystFEL as it was at commit cff9159b4bc6.

    Arguments:

        filename: The absolute or relative path to a CrystFEL geometry file.

    Returns:

        A tuple with the information loaded from the file.

            * The first entry in the tuple is a
            [TypeDetector][om.utils.crystfel_geometry.TypeDetector] dictionary storing
            information related to the detector geometry.

            * The second entry in the tuple is a
            [TypeBeam] [om.utils.crystfel_geometry.TypeBeam] dictionary storing
            information about the beam properties.

            * The third entry is the internal path, in an HDF5 data file, to the
            location where Bragg peak information for the current detector can be
            found. This is only used if CrystFEL extracts Bragg peak information from
            files. If the geometry file does not provide this information, this entry
            has the value of an empty string.
    """
    try:
        file_handle: TextIO
        with open(filename, mode="r") as file_handle:
            file_lines: List[str] = file_handle.readlines()
    except (IOError, OSError) as exc:
        exc_type, exc_value = sys.exc_info()[:2]
        raise exceptions.OmConfigurationFileReadingError(
            f"The following error occurred while reading the "  # type: ignore
            f"{filename} geometry file {exc_type.__name__}: {exc_value}"
        ) from exc
    return read_crystfel_geometry(text_lines=file_lines)


def compute_visualization_pix_maps(*, geometry: TypeDetector) -> TypePixelMaps:
    """
    Computes pixel maps for data visualization from CrystFEL geometry information.

    This function takes as input the geometry information read from a
    [CrystFEL geometry file](http://www.desy.de/~twhite/crystfel/manual-crystfel_geometry.html),
    and returns a set of pixel maps that can be used to display the detector data in a
    Qt ImageView widget (from the [PyQtGraph](http://pyqtgraph.org) library). These
    pixel maps are different from the ones generated by the
    [`compute_pix_maps`][om.utils.crystfel_geometry.compute_pix_maps]
    function. The main differences are:

    * The origin of the reference system is not the beam interaction point, but first
      pixel of the array used to visualize the data.

    * Only the `x` and `y` pixel maps are available. The other keys in the returned
      dictionary (`z`, `r` and `phi`) have a value of None.

    Arguments:

        geometry: A dictionary returned by the
            [load_crystfel_geometry][om.utils.crystfel_geometry.load_crystfel_geometry]
            function, storing the detector geometry information.

    Returns:

        A dictionary storing the pixel maps. Only the values corresponding to the `x`
            and `y` keys are defined. The values for all other keys are set to None.
    """
    # Shifts the origin of the reference system from the beam position to the top-left
    # of the image that will be displayed. Computes the size of the array needed to
    # display the data, then use this information to estimate the magnitude of the
    # shift.
    pixel_maps: TypePixelMaps = compute_pix_maps(geometry=geometry)
    x_map: Union[NDArray[numpy.float_], NDArray[numpy.int_]]
    y_map: Union[NDArray[numpy.float_], NDArray[numpy.int_]]
    x_map, y_map = (
        pixel_maps["x"],
        pixel_maps["y"],
    )
    y_minimum: int = 2 * int(max(abs(y_map.max()), abs(y_map.min()))) + 2
    x_minimum: int = 2 * int(max(abs(x_map.max()), abs(x_map.min()))) + 2
    min_shape: Tuple[int, int] = (y_minimum, x_minimum)
    new_x_map: NDArray[numpy.int_] = (
        numpy.array(object=pixel_maps["x"], dtype=int) + min_shape[1] // 2 - 1
    )
    new_y_map: NDArray[numpy.int_] = (
        numpy.array(object=pixel_maps["y"], dtype=int) + min_shape[0] // 2 - 1
    )

    return {
        "x": new_x_map,
        "y": new_y_map,
        "z": None,
        "radius": None,
        "phi": None,
    }


def pixel_maps_from_geometry_file(
    *,
    filename: str,
) -> TypePixelMaps:
    """
    Loads a CrystFEL geometry file and computes pixel maps.

    This function takes as input the absolute or relative path to a
    [CrystFEL geometry file](http://www.desy.de/~twhite/crystfel/manual-crystfel_geometry.html),
    and returns a set of pre-computed pixel maps. The pixel maps can be used to
    determine the exact coordinates, in the detector reference system, of each pixel of
    the detector data array.

    The origin and the orientation of the reference system for the pixel maps are set
    according to conventions used by CrystFEL:

    * The center of the reference system is the beam interaction point.

    * +z is the beam direction, and points along the beam (i.e. away from the source).

    * +y points towards the zenith (ceiling).

    * +x completes the right-handed coordinate system.

    Arguments:

        filename: The absolute or relative path to a CrystFEL geometry file.

    Returns:

        A dictionary storing the pixel maps.
    """
    geometry: TypeDetector
    _: Any
    __: Any
    geometry, _, __ = load_crystfel_geometry(filename=filename)
    return compute_pix_maps(geometry=geometry)


def visualization_pixel_maps_from_geometry_file(
    *,
    filename: str,
) -> TypePixelMaps:
    """
    Loads a CrystFEL geometry file and computes pixel maps for data visualization.

    This function takes as input the absolute or relative path to a
    [CrystFEL geometry file](http://www.desy.de/~twhite/crystfel/manual-crystfel_geometry.html),
    and returns a set of pre-computed pixel maps that can be used to display data in a
    Qt ImageView widget (from the [PyQtGraph](http://pyqtgraph.org) library).

    These pixel maps are different from the ones generated by the
    [`pixel_maps_from_geometry_file`][om.utils.crystfel_geometry.pixel_maps_from_geometry_file]
    function. The main differences are:

    * The origin of the reference system is not the beam interaction point, but first
      pixel of the array used to visualize the data.

    * Only the `x` and `y` pixel maps are available. The other keys in the returned
      dictionary (`z`, `r` and `phi`) have a value of None.

    Arguments:

        filename: the absolute or relative path to a CrystFEL geometry file.

    Returns:

        A dictionary storing the pixel maps. Only the values corresponding to the `x`
            and `y` keys are defined. The values for all other keys are set to None.
    """
    geometry: TypeDetector
    _: Any
    __: Any
    geometry, _, __ = load_crystfel_geometry(filename=filename)
    return compute_visualization_pix_maps(geometry=geometry)


def apply_geometry_to_data(
    *, data: NDArray[numpy.float_], geometry: TypeDetector
) -> NDArray[numpy.float_]:
    """
    Applies CrystFEL geometry information to some data.

    This function takes as input the geometry information read from a
    [`CrystFEL geometry file`](http://www.desy.de/~twhite/crystfel/manual-crystfel_geometry.html)
    and some data to which the geometry information should be applied. It returns
    an array that can be displayed using libraries like
    [`matplotlib`](https://matplotlib.org/) or [`PyQtGraph`](http://pyqtgraph.org).

    The shape of the returned array is big enough to display all the pixel values in
    the input data, and is symmetric around the center of the detector reference system
    (i.e: the beam interaction point). These restrictions often cause the returned
    array to be bigger than the minimum size needed to store the physical layout of the
    pixels in the detector, particularly if the beam interaction point does not lie
    close to the center of the detector.

    Arguments:

        data: The data to which the geometry information should be applied.

        geometry: A dictionary storing the detector geometry information.

    Returns:

        An array containing the detector data, with geometry information applied to it.
    """
    pixel_maps: TypePixelMaps = compute_pix_maps(geometry=geometry)
    x_map: Union[NDArray[numpy.float_], NDArray[numpy.int_]]
    y_map: Union[NDArray[numpy.float_], NDArray[numpy.int_]]
    x_map, y_map = (
        pixel_maps["x"],
        pixel_maps["y"],
    )
    y_minimum: int = 2 * int(max(abs(y_map.max()), abs(y_map.min()))) + 2
    x_minimum: int = 2 * int(max(abs(x_map.max()), abs(x_map.min()))) + 2
    min_shape: Tuple[int, int] = (y_minimum, x_minimum)
    visualization_array: NDArray[numpy.float_] = numpy.zeros(min_shape, dtype=float)
    visual_pixel_maps: TypePixelMaps = compute_visualization_pix_maps(geometry=geometry)
    visualization_array[
        visual_pixel_maps["y"].flatten(), visual_pixel_maps["x"].flatten()
    ] = data.ravel().astype(visualization_array.dtype)

    return visualization_array
