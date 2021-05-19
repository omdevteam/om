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

This module contains functions that manipulate geometry data encoded with the format
used by the CrystFEL software package.
"""
import collections
import copy
import math
import re
import sys
from typing import Dict, List, TextIO, Tuple, Union

import numpy  # type: ignore
from mypy_extensions import TypedDict

from om.utils import exceptions


class TypeBeam(TypedDict):
    """
    A dictionary storing information about the x-ray beam.

    Base class : TypedDict

    Attributes:

        photon_energy: The photon energy of the beam in eV.

        photon_energy_from: The location of the photon energy information in an HDF5
            data file, in case the beam energy information is extracted from a file.

        photon_energy_scale: The scaling factor to be applied to the photon energy, in
            case the provided energy value is not in eV.
    """

    photon_energy: float
    photon_energy_from: str
    photon_energy_scale: float


class TypePanel(TypedDict, total=True):
    """
    A dictionary storing information about detector panels.

    Base class : TypedDict

    Attributes:

        cnx: The x location of the corner of the panel in the detector reference
            system.

        cny: The y location of the corner of the panel in the detector reference
            system.

        clen: The distance, as reported by the facility, of the sample interaction
            point from the corner of the first pixel in the panel.

        clen_from: The location of the 'clen' information in an HDF5 data file, in case
            the detector distance is extracted from a file.

        coffset: The offset to be applied to the nominal clen value reported by the
            facility in order to determine the real distance of the panel from the
            interaction point.

        mask: The location of the mask data for the panel in an HDF5 data file.

        mask_file: The name of the HDF5 data file in which the mask data for the panel
            can be found.

        satmap: The location of the per-pixel saturation map for the panel in an HDF5
            data file.

        satmap_file: The name of the HDF5 data file in which the per-pixel saturation
            map for the panel can be found.

        res: The resolution of the panel in pixels per meter.

        badrow: The readout direction for the panel, for filtering out clusters of
            peaks. The value corresponding to this key is either 'x' or 'y'.

        no_index: Wether the panel should be considered entirely bad. The panel will be
            considered bad if the value corresponding to this key is non-zero.

        adu_per_photon: The number of detector intensity units per photon for the
            panel.

        max_adu: The detector intensity unit value above which a pixel of the panel
            should be considered unreliable.

        data: The location, in an HDF5 data file, of the data block where the panel
            data is stored.

        adu_per_eV: The number of detector intensity units per eV of photon energy for
            the panel.

        dim_structure: A description of the layout of the data block for the panel. The
            value corresponding to this key is a list of strings describing the meaning
            of each axis in the data block. See the
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

        clen_for_centering: The distance from the interation point, as reported by the
            facility, of the origin of the detector reference system.

        xfs: The x->fs component of the matrix used to transform detector reference
            system coordinates into pixel indexes.

        yfs: The y->fs component of the matrix used to transform detector reference
            system coordinates into pixel indexes.

        xss: The x->ss component of the matrix used to transform detector reference
            system coordinates into pixel indexes.

        yss: The y->ss component of the matrix used to transform detector reference
            system coordinates into pixel indexes.

        orig_min_fs: The initial fs index of the panel data in the data block where it
            is stored.

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
    A dictionary storing information about bad regions in a detector.

    Base class : TypedDict

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
            x,y-based one) should be considered. If the value corresponding to this key
            is 1, the fs,ss-based definition of the bad region is considered the valid
            one. Otherwise, the definition in x,y coordinates is taken as valid.
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

    Base class : TypedDict

    Attributes:

        panels: The panels in the detector. The value corresponding to this key is a
            dictionary containing information about the panels that make up the
            detector. In the dictionary, the keys are the panel names, and the values
            are [TypePanel][om.utils.crystfel_geometry.TypePanel] dictionaries.

        bad: The bad regions in the detector. The value corresponding to this key is a
            dictionary containing information about the bad regions in the detector. In
            the dictionary, the keys are the bad region names, and the values are
            additional [TypeBadRegion][om.utils.crystfel_geometry.TypeBadRegion]
            dictionaries.

        mask_bad: The value used in a bad pixel mask to label a pixel as bad.

        mask_good: The value used in a bad pixel mask to label a pixel as good.

        rigid_groups: The rigid groups of panels in the detector. The value
            corresponding to this key is a dictionary containing information about the
            rigid groups. In the dictionary, the keys are the names of the rigid groups
            and the values are lists storing the names of the panels belonging to each
            group.

        rigid_group_collections: The collections of rigid groups of panels in the
            detector. The value corresponding to this key is a dictionary containing
            information about the rigid group collections. In the dictionary, the keys
            are the names of the rigid group collections and the values are lists
            storing the names of the rigid groups belonging to the collections.

        furthest_out_panel: The name of the panel where the furthest away pixel from
            the center of the detector reference system can be found.

        furthest_out_fs: The fs coordinate, within its panel, of the furthest away
            pixel from the center of the detector reference system.

        furthest_out_ss: The ss coordinate, within its panel, of the furthest away
            pixel from the center of the detector reference system.

        furthest_in_panel: The name of the panel where the closest pixel to the center
            of the detector reference system can be found.

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
    A dictionary storing a set of pixel maps.

    Base class : TypedDict

    Attributes:

        x: A pixel map for the x coordinate.

        y: A pixel map for the y coordinate.

        z: A pixel map for the z coordinate.

        radius: A pixel map storing the distance of each pixel from the center of the
            detector reference system.

        phi: A pixel map storing, for each pixel, the amplitude of the angle drawn by
            the pixel, the center of the detector reference system, and the x axis.
    """

    x: numpy.ndarray
    y: numpy.ndarray
    z: Union[numpy.ndarray, None]
    radius: Union[numpy.ndarray, None]
    phi: Union[numpy.ndarray, None]


def _assplode_algebraic(value: str) -> List[str]:
    # Re-implementation of assplode_algebraic from
    # /src/detector.c.
    items: List[str] = [
        item for item in re.split("([+-])", string=value.strip()) if item != ""
    ]
    if items and items[0] not in ("+", "-"):
        items.insert(0, "+")
    return ["".join((items[x], items[x + 1])) for x in range(0, len(items), 2)]


def _dir_conv(
    direction_x: float, direction_y: float, direction_z: float, value: str
) -> List[float]:
    # Re-implementation of dir_conv from libcrystfel/src/detector.c.
    direction: List[float] = [
        direction_x,
        direction_y,
        direction_z,
    ]
    items: List[str] = _assplode_algebraic(value)
    if not items:
        raise RuntimeError("Invalid direction: {}.".format(value))
    item: str
    for item in items:
        axis: str = item[-1]
        if axis not in ("x", "y", "z"):
            raise RuntimeError("Invalid Symbol: {} (must be x, y or z).".format(axis))
        if item[:-1] == "+":
            value = "1.0"
        elif item[:-1] == "-":
            value = "-1.0"
        else:
            value = item[:-1]
        if axis == "x":
            direction[0] = float(value)
        elif axis == "y":
            direction[1] = float(value)
        elif axis == "z":
            direction[2] = float(value)

    return direction


def _set_dim_structure_entry(key: str, value: str, panel: TypePanel) -> None:
    # Re-implementation of set_dim_structure_entry from libcrystfel/src/events.c.
    if panel["dim_structure"] is not None:
        dim: List[Union[int, str, None]] = panel["dim_structure"]
    else:
        dim = []
    try:
        dim_index: int = int(key[3])
    except IndexError:
        raise RuntimeError("'dim' must be followed by a number, e.g. 'dim0')")
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


def _parse_field_for_panel(  # noqa: C901
    key: str,
    value: str,
    panel: TypePanel,
    panel_name: str,
    detector: TypeDetector,
) -> None:
    # Re-implementation of parse_field_for_panel from libcrystfel/src/detector.c.
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
            panel["rail_x"], panel["rail_y"], panel["rail_z"] = _dir_conv(
                direction_x=panel["rail_x"],
                direction_y=panel["rail_y"],
                direction_z=panel["rail_z"],
                value=value,
            )
        except RuntimeError as exc:
            raise RuntimeError("Invalid rail direction. ", exc)
    elif key == "clen_for_centering":
        panel["clen_for_centering"] = float(value)
    elif key == "adu_per_eV":
        panel["adu_per_eV"] = float(value)
    elif key == "adu_per_photon":
        panel["adu_per_photon"] = float(value)
    elif key == "rigid_group":
        if value in detector["rigid_groups"]:
            if panel_name not in detector["rigid_groups"][value]:
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
        if not value.startswith("/"):
            raise RuntimeError("Invalid data location: {}".format(value))
        panel["data"] = value
    elif key == "mask":
        if not value.startswith("/"):
            raise RuntimeError("Invalid data location: {}".format(value))
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
            panel["fsx"], panel["fsy"], panel["fsz"] = _dir_conv(
                direction_x=panel["fsx"],
                direction_y=panel["fsy"],
                direction_z=panel["fsz"],
                value=value,
            )
        except RuntimeError as exc:
            raise RuntimeError("Invalid fast scan direction.", exc)
    elif key == "ss":
        try:
            panel["ssx"], panel["ssy"], panel["ssz"] = _dir_conv(
                direction_x=panel["ssx"],
                direction_y=panel["ssy"],
                direction_z=panel["ssz"],
                value=value,
            )
        except RuntimeError as exc:
            raise RuntimeError("Invalid slow scan direction.", exc)
    elif key.startswith("dim"):
        _set_dim_structure_entry(key=key, value=value, panel=panel)
    else:
        RuntimeError("Unrecognized field: {}".format(key))


def _parse_toplevel(  # noqa: C901
    key: str,
    value: str,
    detector: TypeDetector,
    beam: TypeBeam,
    panel: TypePanel,
    hdf5_peak_path: str,
) -> str:
    # Re-implementation of parse_toplevel from libcrystfel/src/detector.c.
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
    elif key == "coffset":
        panel["coffset"] = float(value)
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
    elif key.startswith("rigid_group") and not key.startswith("rigid_group_collection"):
        detector["rigid_groups"][key[12:]] = value.split(",")
    elif key.startswith("rigid_group_collection"):
        detector["rigid_group_collections"][key[23:]] = value.split(",")
    else:
        _parse_field_for_panel(
            key=key, value=value, panel=panel, panel_name="", detector=detector
        )

    return hdf5_peak_path


def _check_bad_fsss(bad_region: TypeBadRegion, is_fsss: int) -> None:
    # Re-implementation of check_bad_fsss from libcrystfel/src/detector.c.
    if bad_region["is_fsss"] == 99:
        bad_region["is_fsss"] = is_fsss
        return

    if is_fsss != bad_region["is_fsss"]:
        raise RuntimeError("You can't mix x/y and fs/ss in a bad region")


def _parse_field_bad(key: str, value: str, bad: TypeBadRegion) -> None:
    # Re-implementation of parse_field_bad from libcrystfel/src/detector.c.
    if key == "min_x":
        bad["min_x"] = float(value)
        _check_bad_fsss(bad_region=bad, is_fsss=False)
    elif key == "max_x":
        bad["max_x"] = float(value)
        _check_bad_fsss(bad_region=bad, is_fsss=False)
    elif key == "min_y":
        bad["min_y"] = float(value)
        _check_bad_fsss(bad_region=bad, is_fsss=False)
    elif key == "max_y":
        bad["max_y"] = float(value)
        _check_bad_fsss(bad_region=bad, is_fsss=False)
    elif key == "min_fs":
        bad["min_fs"] = int(value)
        _check_bad_fsss(bad_region=bad, is_fsss=True)
    elif key == "max_fs":
        bad["max_fs"] = int(value)
        _check_bad_fsss(bad_region=bad, is_fsss=True)
    elif key == "min_ss":
        bad["min_ss"] = int(value)
        _check_bad_fsss(bad_region=bad, is_fsss=True)
    elif key == "max_ss":
        bad["max_ss"] = int(value)
        _check_bad_fsss(bad_region=bad, is_fsss=True)
    elif key == "panel":
        bad["panel"] = value
    else:
        raise RuntimeError("Unrecognized field: {}".format(key))


def _check_point(
    panel_name: str,
    panel: TypePanel,
    fs: int,
    ss: int,
    min_d: float,
    max_d: float,
    detector: TypeDetector,
) -> Tuple[float, float]:
    # Re-implementation of check_point from libcrystfel/src/detector.c.
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

    return min_d, max_d


def _find_min_max_d(detector: TypeDetector) -> None:
    # Re-implementation of find_min_max_d from libcrystfel/src/detector.c.
    min_d: float = float("inf")
    max_d: float = 0.0
    panel_name: str
    panel: TypePanel
    for panel_name, panel in detector["panels"].items():
        min_d, max_d = _check_point(
            panel_name=panel_name,
            panel=panel,
            fs=0,
            ss=0,
            min_d=min_d,
            max_d=max_d,
            detector=detector,
        )
        min_d, max_d = _check_point(
            panel_name=panel_name,
            panel=panel,
            fs=panel["w"],
            ss=0,
            min_d=min_d,
            max_d=max_d,
            detector=detector,
        )
        min_d, max_d = _check_point(
            panel_name=panel_name,
            panel=panel,
            fs=0,
            ss=panel["h"],
            min_d=min_d,
            max_d=max_d,
            detector=detector,
        )
        min_d, max_d = _check_point(
            panel_name=panel_name,
            panel=panel,
            fs=panel["w"],
            ss=panel["h"],
            min_d=min_d,
            max_d=max_d,
            detector=detector,
        )


def load_crystfel_geometry(  # noqa: C901
    filename: str,
) -> Tuple[TypeDetector, TypeBeam, str]:  # noqa: C901
    """
    Loads a CrystFEL geometry file.

    This function is a re-implementation of the get_detector_geometry_2 function from
    CrystFEL. It reads information from a CrystFEL geometry file, which uses a
    key/value language format, fully documented in the relevant
    [man page](http://www.desy.de/~twhite/crystfel/manual-crystfel_geometry.html).
    This function returns a set of nested dictionaries whose content matches CrystFEL's
    internal representation of the information in the file (see the
    libcrystfel/src/detector.h and the libcrystfel/src/image.c files from CrystFEL's
    source code for more information).

    The code of this function is currently synchronized with the code of the function
    'get_detector_geometry_2' in CrystFEL at commit cff9159b4bc6.

    Arguments:

        filename: the absolute or relative path to a CrystFEL geometry file.

    Returns:

        A tuple with the information loaded from the file.

        * The first entry in the tuple is a
          [TypeDetector][om.utils.crystfel_geometry.TypeDetector] dictionary storing
          information related to the detector geometry.

        * The second entry in the tuple is a
          [TypeBeam] [om.utils.crystfel_geometry.TypeBeam] dictionary storing the beam
          properties.

        * The third entry is the location, within an HDF5 file, where Bragg peak
          information for the current detector can be found. If the CrystFEL geometry
          file does not provide this last piece information, this entry has the value
          of an empty string.
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
    try:
        file_handle: TextIO
        with open(filename, mode="r") as file_handle:
            line: str
            file_lines: List[str] = file_handle.readlines()
            for line in file_lines:
                if line.startswith(";"):
                    continue
                line_without_comments: str = line.strip().split(";")[0]
                line_items: List[str] = re.split(
                    pattern="([ \t])", string=line_without_comments
                )
                line_items = [
                    item for item in line_items if item not in ("", " ", "\t")
                ]
                if len(line_items) < 3:
                    continue
                value: str = "".join(line_items[2:])
                if line_items[1] != "=":
                    continue
                path: List[str] = re.split("(/)", line_items[0])
                path = [item for item in path if item not in "/"]
                if len(path) < 2:
                    hdf5_peak_path = _parse_toplevel(
                        key=line_items[0],
                        value=value,
                        detector=detector,
                        beam=beam,
                        panel=default_panel,
                        hdf5_peak_path=hdf5_peak_path,
                    )
                    continue
                if path[0].startswith("bad"):
                    if path[0] in detector["bad"]:
                        curr_bad: TypeBadRegion = detector["bad"][path[0]]
                    else:
                        curr_bad = copy.deepcopy(default_bad_region)
                        detector["bad"][path[0]] = curr_bad
                    _parse_field_bad(key=path[1], value=value, bad=curr_bad)
                else:
                    if path[0] in detector["panels"]:
                        curr_panel: TypePanel = detector["panels"][path[0]]
                    else:
                        curr_panel = copy.deepcopy(default_panel)
                        detector["panels"][path[0]] = curr_panel
                    _parse_field_for_panel(
                        key=path[1],
                        value=value,
                        panel=curr_panel,
                        panel_name=path[0],
                        detector=detector,
                    )
            if not detector["panels"]:
                raise RuntimeError("No panel descriptions in geometry file.")
            num_placeholders_in_panels: int = -1
            panel: TypePanel
            for panel in detector["panels"].values():
                if panel["dim_structure"] is not None:
                    curr_num_placeholders: int = panel["dim_structure"].count("%")
                else:
                    curr_num_placeholders = 0

                if num_placeholders_in_panels == -1:
                    num_placeholders_in_panels = curr_num_placeholders
                else:
                    if curr_num_placeholders != num_placeholders_in_panels:
                        raise RuntimeError(
                            "All panels' data and mask entries must have the same "
                            "number of placeholders."
                        )
            num_placeholders_in_masks: int = -1
            for panel in detector["panels"].values():
                if panel["mask"] is not None:
                    curr_num_placeholders = panel["mask"].count("%")
                else:
                    curr_num_placeholders = 0

                if num_placeholders_in_masks == -1:
                    num_placeholders_in_masks = curr_num_placeholders
                else:
                    if curr_num_placeholders != num_placeholders_in_masks:
                        raise RuntimeError(
                            "All panels' data and mask entries must have the same "
                            "number of placeholders."
                        )
            if num_placeholders_in_masks > num_placeholders_in_panels:
                raise RuntimeError(
                    "Number of placeholders in mask cannot be larger the number than "
                    "for data."
                )
            dim_length: int = -1
            panel_name: str
            for panel_name, panel in detector["panels"].items():
                if len(panel["dim_structure"]) == 0:
                    panel["dim_structure"] = copy.deepcopy(default_dim)
                found_ss: int = 0
                found_fs: int = 0
                found_placeholder: int = 0
                dim_index: int
                entry: Union[int, str, None]
                for dim_index, entry in enumerate(panel["dim_structure"]):
                    if entry is None:
                        raise RuntimeError(
                            "Dimension {} for panel {} is undefined.".format(
                                dim_index, panel_name
                            )
                        )
                    if entry == "ss":
                        found_ss += 1
                    elif entry == "fs":
                        found_fs += 1
                    elif entry == "%":
                        found_placeholder += 1
                if found_ss != 1:
                    raise RuntimeError(
                        "Exactly one slow scan dim coordinate is needed (found {} for "
                        "panel {}).".format(found_ss, panel_name)
                    )
                if found_fs != 1:
                    raise RuntimeError(
                        "Exactly one fast scan dim coordinate is needed (found {} for "
                        "panel {}).".format(found_fs, panel_name)
                    )
                if found_placeholder > 1:
                    raise RuntimeError(
                        "Only one placeholder dim coordinate is allowed. Maximum one "
                        "placeholder dim coordinate is allowed "
                        "(found {} for panel {})".format(found_placeholder, panel_name)
                    )
                if dim_length == -1:
                    dim_length = len(panel["dim_structure"])
                elif dim_length != len(panel["dim_structure"]):
                    raise RuntimeError(
                        "Number of dim coordinates must be the same for all panels."
                    )
                if dim_length == 1:
                    raise RuntimeError(
                        "Number of dim coordinates must be at least " "two."
                    )
            for panel_name, panel in detector["panels"].items():
                if panel["orig_min_fs"] < 0:
                    raise RuntimeError(
                        "Please specify the minimum fs coordinate for panel {}.".format(
                            panel_name
                        )
                    )
                if panel["orig_max_fs"] < 0:
                    raise RuntimeError(
                        "Please specify the maximum fs coordinate for panel {}.".format(
                            panel_name
                        )
                    )
                if panel["orig_min_ss"] < 0:
                    raise RuntimeError(
                        "Please specify the minimum ss coordinate for panel {}.".format(
                            panel_name
                        )
                    )
                if panel["orig_max_ss"] < 0:
                    raise RuntimeError(
                        "Please specify the maximum ss coordinate for panel {}.".format(
                            panel_name
                        )
                    )
                if panel["cnx"] is None:
                    raise RuntimeError(
                        "Please specify the corner X coordinate for panel {}.".format(
                            panel_name
                        )
                    )
                if panel["clen"] is None and panel["clen_from"] is None:
                    raise RuntimeError(
                        "Please specify the camera length for panel {}.".format(
                            panel_name
                        )
                    )
                if panel["res"] < 0:
                    raise RuntimeError(
                        "Please specify the resolution or panel {}.".format(panel_name)
                    )
                if panel["adu_per_eV"] is None and panel["adu_per_photon"] is None:
                    raise RuntimeError(
                        "Please specify either adu_per_eV or adu_per_photon for panel "
                        "{}.".format(panel_name)
                    )
                if panel["clen_for_centering"] is None and panel["rail_x"] is not None:
                    raise RuntimeError(
                        "You must specify clen_for_centering if you specify the rail "
                        "direction (panel {})".format(panel_name)
                    )
                if panel["rail_x"] is None:
                    panel["rail_x"] = 0.0
                    panel["rail_y"] = 0.0
                    panel["rail_z"] = 1.0
                if panel["clen_for_centering"] is None:
                    panel["clen_for_centering"] = 0.0
                panel["w"] = panel["orig_max_fs"] - panel["orig_min_fs"] + 1
                panel["h"] = panel["orig_max_ss"] - panel["orig_min_ss"] + 1
            bad_region_name: str
            bad_region: TypeBadRegion
            for bad_region_name, bad_region in detector["bad"].items():
                if bad_region["is_fsss"] == 99:
                    raise RuntimeError(
                        "Please specify the coordinate ranges for bad "
                        "region {}.".format(bad_region_name)
                    )
            group: str
            for group in detector["rigid_groups"]:
                name: str
                for name in detector["rigid_groups"][group]:
                    if name not in detector["panels"]:
                        raise RuntimeError(
                            "Cannot add panel to rigid_group. Panel not "
                            "found: {}".format(name)
                        )
            group_collection: str
            for group_collection in detector["rigid_group_collections"]:
                group_name: str
                for group_name in detector["rigid_group_collections"][group_collection]:
                    if group_name not in detector["rigid_groups"]:
                        raise RuntimeError(
                            "Cannot add rigid_group to collection. Rigid group not "
                            "found: {}".format(name)
                        )

            for panel in detector["panels"].values():
                d: float = panel["fsx"] * panel["ssy"] - panel["ssx"] * panel["fsy"]
                if d == 0.0:
                    raise RuntimeError("Panel {} transformation is singular.")
                panel["xfs"] = panel["ssy"] / d
                panel["yfs"] = panel["ssx"] / d
                panel["xss"] = panel["fsy"] / d
                panel["yss"] = panel["fsx"] / d
            _find_min_max_d(detector)
    except (IOError, OSError) as exc:
        # TODO: Fix type check
        exc_type, exc_value = sys.exc_info()[:2]
        raise exceptions.OmConfigurationFileReadingError(
            "The following error occurred while reading the {0} geometry"
            "file {1}: {2}".format(
                filename,
                exc_type.__name__,  # type: ignore
                exc_value,
            )
        ) from exc

    return detector, beam, hdf5_peak_path


def compute_pix_maps(geometry: TypeDetector) -> TypePixelMaps:
    """
    Computes pixel maps from CrystFEL geometry information.

    This function takes as input the geometry information read from a `CrystFEL
    <http://www.desy.de/~twhite/crystfel/manual-crystfel_geometry.html>`_ geometry
    file, and returns a set of pre-computed pixel maps.

    The origin and the orientation of the reference system for the pixel maps are set
    according to conventions used by CrystFEL:

    * The center of the reference system is the beam interaction point.

    * +z is the beam direction, and points along the beam (i.e. away from the source).

    * +y points towards the zenith (ceiling).

    * +x completes the right-handed coordinate system.

    Arguments:

        geometry: A [TypeDetector][om.utils.crystfel_geometry.TypeDetector] dictionary
            returned by the [load_crystfel_geometry]
            [om.utils.crystfel_geometry.load_crystfel_geometry] function, storing the
            detector geometry information.

    Returns:

        A [TypePixelMaps][om.utils.crystfel_geometry.TypePixelMaps] dictionary storing
        the pixel maps.
    """
    max_fs_in_slab: int = numpy.array(
        [geometry["panels"][k]["orig_max_fs"] for k in geometry["panels"]]
    ).max()
    max_ss_in_slab: int = numpy.array(
        [geometry["panels"][k]["orig_max_ss"] for k in geometry["panels"]]
    ).max()

    x_map: numpy.ndarray = numpy.zeros(
        shape=(max_ss_in_slab + 1, max_fs_in_slab + 1), dtype=numpy.float32
    )
    y_map: numpy.ndarray = numpy.zeros(
        shape=(max_ss_in_slab + 1, max_fs_in_slab + 1), dtype=numpy.float32
    )
    z_map: numpy.ndarray = numpy.zeros(
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

        ss_grid: numpy.ndarray
        fs_grid: numpy.ndarray
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
        y_panel: numpy.ndarray = (
            ss_grid * geometry["panels"][panel_name]["ssy"]
            + fs_grid * geometry["panels"][panel_name]["fsy"]
            + geometry["panels"][panel_name]["cny"]
        )
        x_panel: numpy.ndarray = (
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

    r_map: numpy.ndarray = numpy.sqrt(numpy.square(x_map) + numpy.square(y_map))
    phi_map: numpy.ndarray = numpy.arctan2(y_map, x_map)

    return {
        "x": x_map,
        "y": y_map,
        "z": z_map,
        "radius": r_map,
        "phi": phi_map,
    }


def compute_visualization_pix_maps(geometry: TypeDetector) -> TypePixelMaps:
    """
    Computes pixel maps for data visualization from CrystFEL geometry information.

    This function takes as input the geometry information read from a [CrystFEL
    geometry file](http://www.desy.de/~twhite/crystfel/manual-crystfel_geometry.html),
    and returns a set of pre-computed pixel maps that can be used to display data
    in a Qt ImageView widget (from the [PyQtGraph](http://pyqtgraph.org) library).

    These pixel maps are different from the ones generated by the
    :func:`~compute_pix_maps` function. The main differences are:

    * The origin of the reference system is not the beam interaction point, but the top
      left corner of the array used to visualize the data.

    * Only the x and y pixel maps are available. The other keys in the returned typed
      dictionary (z, r and phi) have a value of None.

    Arguments:

        geometry: A [TypeDetector][om.utils.crystfel_geometry.TypeDetector] dictionary
            returned by the [load_crystfel_geometry]
            [om.utils.crystfel_geometry.load_crystfel_geometry] function, storing the
            detector geometry information.

    Returns:

        A [TypePixelMaps][om.utils.crystfel_geometry.TypePixelMaps] dictionary storing
        the pixel maps. Only the values corresponding to the 'x' and 'y' keys are
        defined. All other dictionary values are set to None.
    """
    # Shifts the origin of the reference system from the beam position to the top-left
    # of the image that will be displayed. Computes the size of the array needed to
    # display the data, then use this information to estimate the magnitude of the
    # shift.
    pixel_maps: TypePixelMaps = compute_pix_maps(geometry)
    x_map: numpy.ndarray
    y_map: numpy.ndarray
    x_map, y_map = (
        pixel_maps["x"],
        pixel_maps["y"],
    )
    y_minimum: int = 2 * int(max(abs(y_map.max()), abs(y_map.min()))) + 2
    x_minimum: int = 2 * int(max(abs(x_map.max()), abs(x_map.min()))) + 2
    min_shape: Tuple[int, int] = (y_minimum, x_minimum)
    new_x_map: numpy.ndarray = (
        numpy.array(object=pixel_maps["x"], dtype=numpy.int) + min_shape[1] // 2 - 1
    )
    new_y_map: numpy.ndarray = (
        numpy.array(object=pixel_maps["y"], dtype=numpy.int) + min_shape[0] // 2 - 1
    )

    return {
        "x": new_x_map,
        "y": new_y_map,
        "z": None,
        "radius": None,
        "phi": None,
    }


def apply_geometry_to_data(
    data: numpy.ndarray, geometry: TypeDetector
) -> numpy.ndarray:
    """
    Applies CrystFEL geometry information to some data.

    This function takes as input the geometry information read from a `CrystFEL
    <http://www.desy.de/~twhite/crystfel/manual-crystfel_geometry.html>`_ geometry
    file, and some data on which the geometry information should be applied. It returns
    an array that can be displayed using libraries like
    `matplotlib <https://matplotlib.org/>`_ or `PyQtGraph <http://pyqtgraph.org/>`_.

    The shape of the returned array is big enough to display all the pixel values in
    the input data, and is symmetric around the center of the detector reference system
    (i.e: the beam interaction point).

    These restrictions often cause the returned array to be bigger than the minimum
    size needed to store the physical layout of the pixels in the detector,
    particularly if the detector is not centered at the beam interaction point.

    Arguments:

        data: The data on which the geometry information should be applied.

        geometry: A [TypeDetector][om.utils.crystfel_geometry.TypeDetector] dictionary
            storing the detector geometry information.

    Returns:

        An array containing the data with the geometry information applied.
    """
    pixel_maps: TypePixelMaps = compute_pix_maps(geometry)
    x_map: numpy.ndarray
    y_map: numpy.ndarray
    x_map, y_map = (
        pixel_maps["x"],
        pixel_maps["y"],
    )
    y_minimum: int = 2 * int(max(abs(y_map.max()), abs(y_map.min()))) + 2
    x_minimum: int = 2 * int(max(abs(x_map.max()), abs(x_map.min()))) + 2
    min_shape: Tuple[int, int] = (y_minimum, x_minimum)
    visualization_array: numpy.ndarray = numpy.zeros(min_shape, dtype=float)
    visual_pixel_maps: TypePixelMaps = compute_visualization_pix_maps(geometry)
    visualization_array[
        visual_pixel_maps["y"].flatten(), visual_pixel_maps["x"].flatten()
    ] = data.ravel().astype(visualization_array.dtype)

    return visualization_array
