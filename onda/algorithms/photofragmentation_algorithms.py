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
#
#    Copyright © 2014-2018 Deutsches Elektronen-Synchrotron DESY,
#    a research centre of the Helmholtz Association.
"""
Algorithms for the processing of photofragmentation data.

Uused to process data from Delayline VMI detectors.
"""
from __future__ import absolute_import, division, print_function

import numpy

from onda.utils import named_tuples


###############################
# DELAYLINE DETECTOR ANALYSIS #
###############################


def _filter_hit(
        mcp_peak,
        x1_corr_peaks,
        x2_corr_peaks,
        y1_corr_peaks,
        y2_corr_peaks,
        min_sum_x,
        max_sum_x,
        min_sum_y,
        max_sum_y,
        max_radius
):
    # This function checks all possible peak combinations and rejects
    # any set of peaks for which the the delays along the wires are
    # outside of the accepted range provided by the user. It also
    # rejects all the peaks combinations for which the spatial
    # coordinates fall outside of the boundaries of the detector.
    # The function then uses the first set of peaks that passes all the
    # checks (if there is one) to compute the VMI hit information. If
    # no peak combination passes the check, it returns None.
    for x_1 in x1_corr_peaks:
        for x_2 in x2_corr_peaks:
            for y_1 in y1_corr_peaks:
                for y_2 in y2_corr_peaks:

                    # These calculations come from standard formulas.
                    wires_x_sum = x_1 + x_2 - 2 * mcp_peak
                    wires_y_sum = y_1 + y_2 - 2 * mcp_peak
                    if (
                            min_sum_x < wires_x_sum < max_sum_x and
                            min_sum_y < wires_y_sum < max_sum_y
                    ):
                        peak = named_tuples.VmiHit(
                            timestamp=mcp_peak,
                            coords=named_tuples.VmiCoords(
                                # These calculations come from standard
                                # formulas.
                                x=x_1 - x_2,
                                y=y_1 - y_2
                            ),
                            peaks=named_tuples.QuadVmiPeaks(
                                x_1=x_1,
                                x_2=x_2,
                                y_1=y_1,
                                y_2=y_2
                            )
                        )

                        # Checks if the spatial coordinates fall within
                        # the boundaries of the detector.
                        if numpy.sqrt(
                                (
                                    peak.coords.x * peak.coords.x +
                                    peak.coords.y * peak.coords.y
                                ) < max_radius
                        ):
                            # The fist peak that passes all the tests
                            # is returned.
                            return peak

    return None


class DelaylineDetectorAnalysis(object):
    """
    Algorithm for the processing of Delayline VMI detector hits.

    For each particle hit (a peak in the detector 's MCP waveform),
    computes the most likely spatial coordinates of the particle.
    It looks for corresponding peaks in the other waveforms of the
    detector, then compiles a list of plausible VMI detector
    hits, with their corresponding spatial coordinates.
    """

    def __init__(
            self,
            peak_search_delay,
            peak_search_tolerance,
            peak_search_scaling_factor,
            min_sum_x,
            max_sum_x,
            min_sum_y,
            max_sum_y,
            max_radius
    ):
        """
        Intializes the DelayLineDetectorAnalysis.

        Args:

            peak_search_scaling_factor (int): scaling factor between
                the resolution of the MCP signal and the resolution of
                the delayline signals. Used when searching for peaks
                in the delayline waveforms that correspond to a peak
                in the MCP waveform.

            peak_search_tolerance (int): tolerance interval (in pixels)
                around the MCP timestamp when searching for
                corresponding peaks in the other delayline waveforms.

            min_sum (float): minimum allowed sum of delayline times of
                flight.

            max_sum (float): maximum allowed sum of delayline times of
                flight.

            max_radius (float): maximum allowed distance of the spatial
                location of a particle from the center of the detector.
        """
        self._peak_search_delay = peak_search_delay
        self._peak_search_scaling_factor = peak_search_scaling_factor
        self._peak_search_tolerance = peak_search_tolerance
        self._min_sum_x = min_sum_x
        self._max_sum_x = max_sum_x
        self._min_sum_y = min_sum_y
        self._max_sum_y = max_sum_y
        self._max_radius = max_radius

    def find_particle_hits(
            self,
            mcp_peaks,
            x1_peaks,
            x2_peaks,
            y1_peaks,
            y2_peaks
    ):
        """
        Extracts particle hit data from peaks detected in waveforms.

        For each peak in the detector's MCP waveform, searches for
        corresponding peaks in the x1, x2, y1 and y2 delayline
        waveforms, then computes the spatial coordinates of the
        particle hit, rejecting physically impossible results. When
        more than one set of results are compatible with an MCP peak,
        this function returns the first found set of plausible spatial
        coordinates.

        Args:

            mcp_peaks (List[int]): positions (indexes, as int numbers)
                of the peaks detected in the MCP waveform.

            x1_peaks (List[int]): positions (indexes, as int numbers)
               of the peaks detected in the x1 waveform.

            x2_peaks (List[int]): positions (indexes, as int numbers)
               of the peaks detected in the x2 waveform.

            y1_peaks (List[int]): positions (indexes, as int numbers)
               of the peaks detected in the y1 waveform.

            y2_peaks (List[int]): positions (indexes, as int numbers)
               of the peaks detected in the y2 waveform.

        Returns:

            List[VmiHit]: a list of
            :obj:`~onda.utils.named_tuples.VmiHit` objects storing
            information about all detected hits.
        """
        hit_list = []
        for mcp_peak in mcp_peaks:
            # Scales the index of the mcp peak to the resolution of the
            # delayline data.
            scaled_mcp_peak = (
                float(mcp_peak) / float(self._peak_search_scaling_factor)
            )

            # Looks for peaks in each waveform with indexes that are
            # close to the scaled index of the mcp peak.
            x1_related_peaks = [
                x for x in x1_peaks if (
                    (scaled_mcp_peak + self._peak_search_delay) < x < (
                        scaled_mcp_peak + self._peak_search_delay +
                        float(self._peak_search_tolerance)
                    )
                )
            ]

            x2_related_peaks = [
                x for x in x2_peaks if (
                    (scaled_mcp_peak + self._peak_search_delay) < x < (
                        scaled_mcp_peak + self._peak_search_delay +
                        float(self._peak_search_tolerance)
                    )
                )
            ]

            y1_related_peaks = [
                x for x in y1_peaks if (
                    (scaled_mcp_peak + self._peak_search_delay) < x < (
                        scaled_mcp_peak + self._peak_search_delay +
                        float(self._peak_search_tolerance)
                    )
                )
            ]

            y2_related_peaks = [
                x for x in y2_peaks if (
                    (scaled_mcp_peak + self._peak_search_delay) < x < (
                        scaled_mcp_peak + self._peak_search_delay +
                        float(self._peak_search_tolerance)
                    )
                )
            ]

            # Calls the function that filter the hits for plausibility.
            filtered_hit = _filter_hit(
                mcp_peak=scaled_mcp_peak,
                x1_corr_peaks=x1_related_peaks,
                x2_corr_peaks=x2_related_peaks,
                y1_corr_peaks=y1_related_peaks,
                y2_corr_peaks=y2_related_peaks,
                min_sum_x=self._min_sum_x,
                max_sum_x=self._max_sum_x,
                min_sum_y=self._min_sum_y,
                max_sum_y=self._max_sum_y,
                max_radius=self._max_radius
            )
            if filtered_hit:
                hit_list.append(filtered_hit)

        return hit_list
