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
TODO: Docstring.
"""
from typing import Any, Dict, Tuple, Union

from om.utils.crystfel_geometry import TypeDetector
import numpy  # type: ignore
from scipy import constants, spatial  # type: ignore

##################
#                #
# FXS PIXEL MAPS #
#                #
##################


class FxsPixelMaps(object):
    """
    See __init__function for documentation.
    """

    def __init__(
        self, geometry: TypeDetector, pixel_maps: Dict[str, numpy.ndarray]
    ) -> None:
        """
        Computes expanded pixel maps for FXS data processing.

        This class augments the basic OM set of pixel maps with additional maps:
        a z-coordinate map adjusted for 'camera offset', a radial map corrected for
        pixel size, a q-coordinate map and a map that store the physical size of each
        pixel.

        Arguments:

            geometry: A dictionary storing information about the detector.

            pixel_maps: A dictionary storing precomputed pixel maps. The dictionary
                should contain:

                * a key named 'x' whose value is a pixel map for the x coordinate.

                * a key named 'y' whose value is a pixel map for the y coordinate.

                * a key named 'z' whose value is a pixel map for the z coordinate.

                * a key named 'radius' whose value is a pixel map  storing the distance
                  of each pixel from the center of the reference system.

                * a key named 'phi' whose value is a pixel map storing the amplitude of
                  the angle between each pixel, the center of the reference system, and
                  the x axis.
        """
        self._pixel_maps: Dict[str, numpy.ndarray] = pixel_maps

        self._theta_map: numpy.ndarray = numpy.zeros_like(
            self._pixel_maps["x"], dtype=numpy.float32
        )

        self._res_map: numpy.ndarray = numpy.zeros_like(
            self._pixel_maps["x"], dtype=numpy.float32
        )

        self._corrected_z: numpy.ndarray = numpy.zeros_like(
            self._pixel_maps["x"], dtype=numpy.float32
        )

        # Fill each panel section of the corrected_z_map and of the res_map
        # (pixel size map).
        pan: str
        for pan in geometry["panels"]:
            self._res_map[
                geometry["panels"][pan]["orig_min_ss"] : geometry["panels"][pan][
                    "orig_max_ss"
                ]
                + 1,
                geometry["panels"][pan]["orig_min_fs"] : geometry["panels"][pan][
                    "orig_max_fs"
                ]
                + 1,
            ] = geometry["panels"][pan]["res"]

            self._corrected_z[
                geometry["panels"][pan]["orig_min_ss"] : geometry["panels"][pan][
                    "orig_max_ss"
                ]
                + 1,
                geometry["panels"][pan]["orig_min_fs"] : geometry["panels"][pan][
                    "orig_max_fs"
                ]
                + 1,
            ] += geometry["panels"][pan]["coffset"]

    def compute_fxs_pixel_maps(
        self,
        detector_distance: float,
        wavelength: float,
        reference_detector_distance: float,
        reference_wavelength: float,
    ) -> Dict[str, numpy.ndarray]:
        """
        Computes the augmented pixel maps.

        Return the set of augmented pixel maps (the common OM pixel maps plus a pixel
        size map and a detector_distance map.

        Arguments:

            detector_distance: The distance between the detector and the sample
                interaction point in m.

            wavelength: The wavelength corresponding to the beam energy (in m^-1).

            reference_detector_distance: The fixed detector distance onto which the
                radial pixels are remapped

            reference_wavelength (float): The wavelength corresponding to a fixed
                reference energy.

        Returns:

            A dictionary containing the set of the augmented pixel map. The dictionary
            stores all the common OM pixel maps, additionally, the dictionary has:

            TODO: Describe the additional maps
        """
        # Compute a pixel map containing the angle between the pixel
        # and the optical axis that goes through the sample, in
        # radians (In crystallography, this is called two theta).
        self._theta_map = numpy.arctan2(
            numpy.abs(self._pixel_maps["r"]),
            (self._corrected_z + detector_distance) * self._res_map,
        )
        # Compute a pixel map for q (in m^-1 units).
        q_map: numpy.ndarray = (
            4.0 * numpy.pi * numpy.sin(0.5 * self._theta_map) / wavelength
        )

        # TODO: Clean up the following and the following lines.
        # TODO: If we interpolate on qgrid, we do not need this
        # Accounting for the fact that different panels could have
        # different offsets, and the detector distance and energy for this
        # shot could have changed, compute r_corr in pixel units using
        # the reference detector distance and wavelength. This way we can
        # interpolate in pixel units, and pick the "correct" radii.
        half_theta_ref: float = numpy.arcsin(
            q_map * reference_wavelength / (4.0 * numpy.pi)
        )
        r_corr_map: numpy.ndarray = (
            reference_detector_distance * self._res_map * numpy.tan(half_theta_ref)
        )

        # r_corr_map = (
        #    (reference_detector_distance * numpy.abs(self._pixel_maps.r)) /
        #    (self._corrected_z_map + detector_distance)
        # )

        return {
            "x": self._pixel_maps["x"],
            "y": self._pixel_maps["y"],
            "r": self._pixel_maps["r"],
            "phi": self._pixel_maps["phi"],
            "q": q_map,
            "r_corr": r_corr_map,
            "pix_size": 1.0 / self._res_map,
        }


class CartesianToPolarInterpolation:
    """
    See __init__function for documentation.
    """

    def __init__(
        self,
        num_radial_steps: int,
        num_phi_steps: int,
        interpolation_method: str,
        num_neighbors: int,
        correct_for_coffset: bool,
    ) -> None:
        """
        Convert data from cartesian to polar coordinates.

        Convert data from cartesian to polar coordinates. Use pixel
        units by default, but optionally take into account the
        distance between the detector and the sample interaction point,
        and use metric unit.s

        Args:

            num_radial_steps: number of radial steps in the Polar grid.

            num_phi_steps: number of phi steps in the Polar grid.

            interpolation method: Method used to interpolate the data. 'nearest' or
                'idw'.

            num_neighbors: Number of neighbors to use for the interpolation, when the
                method used is not 'nearest'.

            correct_for_offset: True if the interpolation should take into account the
                detector distance (metric units will then be used). False if it should
                not (pixel units will be used).
        """
        self._num_neighbors: int = num_neighbors
        self._interpolation_method: str = interpolation_method
        self._num_radial_steps: int = num_radial_steps
        self._phi: numpy.ndarray = numpy.linspace(
            0, 2.0 * numpy.pi, num_phi_steps, endpoint=False
        )

        if correct_for_coffset:
            self._radius_pixmap_key: str = "r_corr"
        else:
            self._radius_pixmap_key = "r"

        # store to save time later
        self._distance: Union[numpy.ndarray, None]
        self._index: Union[numpy.ndarray, None]
        self._distance, self._index = None, None

    def compute_interpolation_info(
        self,
        radii: numpy.ndarray,
        fxs_pixel_maps: Dict[str, numpy.ndarray],
        detector_distance_changed: bool,
    ) -> Dict[str, Any]:
        """
        Compute cartesian-polar interpolation information.

        Compute information that can be used to interpolate data in
        a cartesian system to polar coordinates.

        Args:

            radii: The radial coordinates on the polar grid.

            fxs_pixel_maps: A set of FXS-augmented pixel maps
                computed using the :obj:`FxsPixelMaps` algorithm.

            detector_distance_changed: True if the detector distance has changed and
                the internal parameters need to be recomputed. False otherwise.

        Returns:

            A dictionary containing the information needed to convert data from
            cartesian to polar coordinates.
        """
        radius_pix_map: numpy.ndarray = fxs_pixel_maps[self._radius_pixmap_key]

        x_grid: numpy.ndarray = radii[:, numpy.newaxis] * numpy.sin(self._phi)
        y_grid: numpy.ndarray = radii[:, numpy.newaxis] * numpy.cos(self._phi)

        # TODO: Name this.
        pts_grid: numpy.ndarray = numpy.array(
            (y_grid.ravel(), x_grid.ravel())
        ).transpose()

        if detector_distance_changed:
            # The detector distance has changed. The neighbor search
            # tree must be recomputed.

            # For non corrected radius, these are pixelmaps.x and
            # pixelmaps.y.
            x_pix: numpy.ndarray = radius_pix_map * numpy.sin(fxs_pixel_maps["phi"])
            y_pix: numpy.ndarray = radius_pix_map * numpy.cos(fxs_pixel_maps["phi"])

            # TODO: name this.
            pts_pix: numpy.ndarray = numpy.array(
                (y_pix.ravel(), x_pix.ravel())
            ).transpose()

            tree: spatial.KDTree = spatial.KDTree(pts_pix)

            distance: numpy.ndarray
            index: numpy.ndarray
            distance, index = tree.query(pts_grid, self._num_neighbors)

            # store to save time later
            self._distance, self._index = distance, index
        else:
            distance = self._distance
            index = self._index

        interpolation_info: Dict[str, Any] = {
            "distance": distance,
            "index": index,
        }

        if self._interpolation_method == "nearest":
            interpolation_info["weight"] = numpy.ones(index.shape)

            # TODO: Er... What?
            # a sort of dumb way of taking care of pixels that fall in
            # the gap.
            interpolation_info["weight"][numpy.where(distance > 1.0)] = 0.0
        else:
            interpolation_info["weight"] = 1.0 / (distance + numpy.finfo(float).eps)

        return interpolation_info

    class ConversionUtils:
        def __init__(self, energy: float, detector_distance: float):

            self._energy: float = energy
            self._detector_distance: float = detector_distance
            self._wavelength: float = (
                constants.h * constants.c / constants.e / self._energy
            )

        def pix2q(
            self, rxy: float, pixel_size: float, coffset: float
        ) -> Tuple[float, float]:
            """
            TODO: Fix documentation
            TODO: Check types

            Arguments:

                rxy: In plane radius of pixels

                pixel_size: The pixel size in metres

                coffset: Camera length offset from fixed detector distance

            Returns:

                A tuple whose first element is the q-value in inverse metres, and whose
                second element is the scattering angle (2 theta of crystallography).
            """
            z: float = self._detector_distance + coffset
            theta: float = numpy.arctan2(rxy * pixel_size, z)
            q_inv_m: float = 4.0 * numpy.pi * numpy.sin(0.5 * theta) / self._wavelength

            return q_inv_m, theta

        def q2pix(
            self, q: float, pixel_size: float, coffset: Union[float, None] = None
        ) -> float:
            """
            TODO: Fix documentation
            TODO: Check types

            Arguments:

                q: The q-value in inverse metres

                pixel_size: The pixel size in metres

                coffset: The detector distance offset in metres

            Returns:

                rxy: The in-plane radius
            """

            if coffset is None:
                coffset = numpy.zeros_like(q)

            z: float = self._detector_distance + coffset
            half_theta: float = numpy.arcsin(q * self._wavelength / 4.0 / numpy.pi)
            rxy: float = numpy.tan(2 * half_theta) * z / pixel_size

            return rxy
