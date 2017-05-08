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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import numpy


###############################
# DELAYLINE DETECTOR ANALYSIS #
###############################

class DelaylineDetectorAnalysis:
    """Processes data from delayline detectors.

    Processes data from delayline detectors (Currently only quad type detectors
    are supported), returning spatial coordinates of particle hits.

    """

    def __init__(self, peak_search_delay, peak_search_tolerance, peak_search_scaling_factor, min_sum_x, max_sum_x,
                 min_sum_y, max_sum_y, max_radius):
        """Initializes the minima finding algorithm.

        Args:

            peak_search_scaling_factor (int): scaling factor between the resolution of the mcp
            signal and the resolution of the delayline signals. Used when searching for
            corresponding peaks in delayline waveforms.

            peak_search_tolerance (int): tolerance interval (in pixels) around the MCP time position
            when searching for corresponding peaks in delayline waveforms.

            min_sum (float): minimum allowed sum of delayline times of flight.

            max_sum (float): maximum allowed sum of delayline times of flight.

            max_radius (float): maximum allowed radial distance for detecte hits
        """

        self.peak_search_delay = peak_search_delay
        self.peak_search_scaling_factor = peak_search_scaling_factor
        self.peak_search_tolerance = peak_search_tolerance
        self.min_sum_x = min_sum_x
        self.max_sum_x = max_sum_x
        self.min_sum_y = min_sum_y
        self.max_sum_y = max_sum_y
        self.max_radius = max_radius

        self.pst = float(peak_search_tolerance)

    def find_particle_hits(self, mcp_peaks, x1_peaks, x2_peaks, y1_peaks, y2_peaks):
        """Finds particle hits.

        Finds particle hits given detected peaks in the MCP and delayline waveforms.
        Performs some sanity check on the sum of the times of flights of the detected
        particle hits.

         Args:

            mcp_peaks (list of int): peaks detected in the MCP waveform

            x1_peaks (list of int): peaks detected in the x1 waveform

            x2_peaks (list of int): peaks detected in the x2 waveform

            y1_peaks (list of int): peaks detected in the y1 waveform

            y2_peaks (list of int): peaks detected in the y1 waveform

        Returns:

            hit_list (list of tuples): returns a list of tuples. Each tuple
            contains the time of flight as first element, and a list of
            (x,y) tuples for all set of coordinates that passed the sanity
            checks as second element.
        """

        hit_list = []

        for mcp_peak in mcp_peaks:

            scaled_mcp_peak = float(mcp_peak) / float(self.peak_search_scaling_factor)

            x1_corr_peak = [x for x in x1_peaks if
                            scaled_mcp_peak + self.peak_search_delay < x <
                            scaled_mcp_peak + self.peak_search_delay + self.pst]
            x2_corr_peak = [x for x in x2_peaks if
                            scaled_mcp_peak + self.peak_search_delay < x <
                            scaled_mcp_peak + self.peak_search_delay + self.pst]
            y1_corr_peak = [x for x in y1_peaks if
                            scaled_mcp_peak + self.peak_search_delay < x <
                            scaled_mcp_peak + self.peak_search_delay + self.pst]
            y2_corr_peak = [x for x in y2_peaks if
                            scaled_mcp_peak + self.peak_search_delay < x <
                            scaled_mcp_peak + self.peak_search_delay + self.pst]

            y = time_sum_radius_rejection(scaled_mcp_peak, x1_corr_peak,
                                          x2_corr_peak, y1_corr_peak,
                                          y2_corr_peak, self.min_sum_x,
                                          self.max_sum_x, self.min_sum_y,
                                          self.max_sum_y, self.max_radius)
            if y is not None:
                hit_list.append(y)

        return hit_list


def time_sum_radius_rejection(mcp_peak, x1_corr_peak,
                              x2_corr_peak, y1_corr_peak,
                              y2_corr_peak, min_sum_x,
                              max_sum_x, min_sum_y,
                              max_sum_y, max_radius):
    for x1 in x1_corr_peak:
        for x2 in x2_corr_peak:
            for y1 in y1_corr_peak:
                for y2 in y2_corr_peak:

                    # candidate hit
                    x = (x1, x2, y1, y2)

                    # is the time sum acceptable?
                    if ((min_sum_x < (x[0] + x[1] - 2 * mcp_peak) < max_sum_x) and
                        and (min_sum_y < (x[2] + x[3] - 2 * mcp_peak) < max_sum_y)):

                        # is x,y the position of the peak within the detector?
                        y = (mcp_peak, (x[0] - x[1], x[2] - x[3]), (x[0], x[1], x[2], x[3]))
                        if numpy.sqrt((y[1][0] * y[1][0] + y[1][1] * y[1][1])) < max_radius:
                            return y
    return None
