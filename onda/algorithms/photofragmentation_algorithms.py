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
'''
Algorithms for the processing of photofragmentation data.
'''

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from collections import namedtuple

import numpy

###############################
# DELAYLINE DETECTOR ANALYSIS #
###############################

VmiCoords = namedtuple('Coords', ['x', 'y'])
'''
Namedtuple storing coordinate information from a VMI detector.

The two fields are the x and y coordinates of a particle on a the
detector.
'''

QuadVmiPeaks = namedtuple('QuadVMIPeaks', ['x_1', 'x_2', 'y_1', 'y_2'])
'''
Namedtuple storing a set of peaks from a quad-type VMI detector.

Each field stores a peak detected on one of the four delaylines of
the quad-type VMI detector.
'''


VmiHit = namedtuple('VmiHit', ['timest', 'coords', 'peaks'])
'''
Namedtuple storing VMI hit information.

The first field is the timestamp of a particle hitting the VMI
detector. The second field is a :obj:`VmiCoords` object, representing
the spatial coordinates of the particle on the detector. The third
is a :obj:`QuadVmiPeaks` object, storing the set of peaks used to
compute the spatial coordinates.
'''


def _filter_hit(mcp_peak, x1_corr_peaks,
                x2_corr_peaks, y1_corr_peaks,
                y2_corr_peaks, min_sum_x,
                max_sum_x, min_sum_y,
                max_sum_y, max_radius):
    # Check all possible peak combinations and reject any set of peaks for
    # which the the delays along the wires are outside of the accepted range
    # provided by the user. Reject also all peaks combinations  for which the
    # spatial coordinates fall outside of the boundaries of the detector.
    # Use the first set of peaks, if one is found, that passes these checks
    # to compute the VMI hit information.

    # Nested iterations to look at all possible peak combinations.
    for x_1 in x1_corr_peaks:
        for x_2 in x2_corr_peaks:
            for y_1 in y1_corr_peaks:
                for y_2 in y2_corr_peaks:

                    # Compute sums along the x and y wires.
                    wires_x_sum = x_1 + x_2 - 2 * mcp_peak
                    wires_y_sum = y_1 + y_2 - 2 * mcp_peak

                    # Check if the sums are in the acceptable range.
                    if (
                            min_sum_x < wires_x_sum < max_sum_x and
                            min_sum_y < wires_y_sum < max_sum_y
                    ):
                        # Compute the spatial cordinates of the hit
                        # defined by the x_1, x_2, y_1, y_2 peaks, and
                        # create the VmiHit object.
                        peak = VmiHit(
                            mcp_peak,
                            VmiCoords(x_1 - x_2, y_1 - y_2),
                            QuadVmiPeaks(x_1, x_2, y_1, y_2)
                        )

                        # Check if the spatial coodrinates fall within the
                        # boundaries of the detector (the distance from
                        # the center of the detector is shorter than
                        # the value provided by the user).
                        if numpy.sqrt(
                                (
                                    peak.coords.x * peak.coords.x +
                                    peak.coords.y * peak.coords.y
                                ) < max_radius
                        ):

                            # If all test are passed, return the VmiHit
                            # information.
                            return peak

    # If all possible peak combinations have been rejected, return None.
    return None


class DelaylineDetectorAnalysis(object):
    '''
    Process particle hits on a delayline VMI detector.

    Only quad-type detectors are supported. For each peak in the MCP
    waveform, search for corresponding peaks in the x1, x2, y1 and y2
    delayline waveforms, then compute the spatial coordinates of the hit.
    If more than one corresponding peak is found in one of the delaylines,
    explore all possible peak combinations, and take the first one that
    generates plausible spatial coordinates and time delays as the real signal.
    '''

    def __init__(self, peak_search_delay, peak_search_tolerance,
                 peak_search_scaling_factor, min_sum_x, max_sum_x,
                 min_sum_y, max_sum_y, max_radius):
        '''
        Initialize the DelaylineDetectorAnalysis class.

        Args:

            peak_search_scaling_factor (int): scaling factor between the
                resolution of the MCP signal and the resolution of the
                delayline signals. Used when searching for peaks in
                delayline waveforms that correspond to a peak in the
                MCP waveform.

            peak_search_tolerance (int): tolerance interval (in pixels) around
                the MCP timestamp to search for corresponding peaks in the
                delayline waveforms.

            min_sum (float): minimum allowed sum of delayline times of flight.

            max_sum (float): maximum allowed sum of delayline times of flight.

            max_radius (float): maximum allowed distance of the spatial
                location of a particle from the center of the detector.
        '''

        # Read arguments and store them in attributes.
        self._peak_search_delay = peak_search_delay
        self._peak_search_scaling_factor = peak_search_scaling_factor
        self._peak_search_tolerance = peak_search_tolerance
        self._min_sum_x = min_sum_x
        self._max_sum_x = max_sum_x
        self._min_sum_y = min_sum_y
        self._max_sum_y = max_sum_y
        self._max_radius = max_radius

    def find_particle_hits(self, mcp_peaks, x1_peaks, x2_peaks, y1_peaks,
                           y2_peaks):
        '''
        Extract particle hits from peaks detected in waveforms.

        Starting from the list of detected peaks in the MCP and delayline
        waveforms, return a list of plausible VMI detector hits. When more
        than one peak can be found in one of the delayline waveforms for a
        single MCP peak, use the first set of peaks that return plausible
        spatial coordinates.

        Args:

            mcp_peaks (list): list storing the positions (indexes, as int
                numbers) of the peaks detected in the MCP waveform.

            x1_peaks (list): list storing the positions (indexes, as int
                numbers) of the peaks detected in the x1 waveform.

            x2_peaks (list): list storing the positions (indexes, as int
                numbers) of the peaks detected in the x2 waveform.

            y1_peaks (list): list storing the positions (indexes, as int
                numbers) of the peaks detected in the y2 waveform.

            y2_peaks (list): list storing the positions (indexes, as int
                numbers) of the peaks detected in the y2 waveform.

        Returns:

            list: a list of :obj:`VmiHit` objects, storing information about
            the VMI detector hits.
        '''

        # Create list that will store the hit information.
        hit_list = []

        # Iterate over the list of peaks detected in the mcp_peaks waveform.
        for mcp_peak in mcp_peaks:

            # Scale the index of the mcp peak to the resolution of the
            # delayline data.
            scaled_mcp_peak = (
                float(mcp_peak) / float(self._peak_search_scaling_factor)
            )

            # Look for peaks the x1 waveform with indexes that are close
            # to the scaled index of the mcp peak.
            x1_related_peaks = [
                x for x in x1_peaks if (
                    (
                        scaled_mcp_peak + self._peak_search_delay
                    ) < x < (
                        scaled_mcp_peak + self._peak_search_delay +
                        float(self._peak_search_tolerance)
                    )
                )
            ]

            # Look for peaks the x2 waveform with indexes that are close
            # to the scaled index of the mcp peak.
            x2_related_peaks = [
                x for x in x2_peaks if (
                    (
                        scaled_mcp_peak + self._peak_search_delay
                    ) < x < (
                        scaled_mcp_peak + self._peak_search_delay +
                        float(self._peak_search_tolerance)
                    )
                )
            ]

            # Look for peaks the y1 waveform with indexes that are close
            # to the scaled index of the mcp peak.
            y1_related_peaks = [
                x for x in y1_peaks if (
                    (
                        scaled_mcp_peak + self._peak_search_delay
                    ) < x < (
                        scaled_mcp_peak + self._peak_search_delay +
                        float(self._peak_search_tolerance)
                    )
                )
            ]

            # Look for peaks the y2 waveform with indexes that are close
            # to the scaled index of the mcp peak.
            y2_related_peaks = [
                x for x in y2_peaks if (
                    (
                        scaled_mcp_peak + self._peak_search_delay
                    ) < x < (
                        scaled_mcp_peak + self._peak_search_delay +
                        float(self._peak_search_tolerance)
                    )
                )
            ]

            # Call the function that filter the hits for plausibility.
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

            # If the function returns a valid VMI hit, add it to the list.
            if filtered_hit is not None:
                hit_list.append(filtered_hit)

        return hit_list
