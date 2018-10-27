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
#    Copyright ©
#
"""
OnDA Monitor for SWAXS.
"""
from __future__ import absolute_import, division, print_function

import collections
import sys
import time

import numpy
from cfelpyutils import crystfel_utils, geometry_utils

from onda.algorithms import calibration_algorithms as calib_algs
from onda.algorithms import generic_algorithms as gen_algs
from onda.parallelization_layer import mpi
from onda.utils import zmq as zmq_utils
from onda.utils import swaxs as swaxs_utils


class OndaMonitor(mpi.ParallelizationEngine):
    """
    An OnDA real-time monitor for serial crystallography experiments.

    TODO: Describe what the monitor does.

    Broadcast reduced data for visualization. Optionally also broadcast
    corrected frame data for visualization.
    """

    def __init__(self, source, monitor_parameters):
        """
        Initializes the OndaMonitor class.

        Args:

            source (str): A string describing the data source. The
                exact format of the string depends on the data recovery
                layer used by the monitor (e.g:the string could be a
                psana experiment descriptor at the LCLS facility, the
                IP of the machine where HiDRA is running at the
                PetraIII facility, etc.)

            monitor_params (MonitorParams): a
                :obj:`~onda.utils.parameters.MonitorParams` object
                containing the monitor parameters from the
                configuration file.
        """
        super(OndaMonitor,
              self).__init__(
                  process_func=self.process_data,
                  collect_func=self.collect_data,
                  source=source,
                  monitor_params=monitor_parameters
              )

        # Reads information for profile averaging.
        num_profiles = monitor_parameters.get_param(
            section='Radial',
            parameter='num_profiles_to_average',
            type_=int,
            required=True
        )

        num_radial_bins = monitor_parameters.get_param(
            section='Radial',
            parameter='num_radial_bins',
            type_=int,
            required=True
        )

        # Loads the geometry data and compute the pixel maps.
        geometry_filename = monitor_parameters.get_param(
            section='General',
            parameter='geometry_file',
            type_=str,
            required=True
        )

        geometry = crystfel_utils.load_crystfel_geometry(geometry_filename)

        self.geometry = geometry

        pixel_maps = geometry_utils.compute_pix_maps(geometry)
        radius_pixel_map = pixel_maps.r

        # Creates a pixel map in which each data pixel is labelled
        # according to the radial bins it belongs to. Used for radial
        # averagning. Also computes the readial bin size.
        radial_bin_info = swaxs_utils.calculate_radial_bin_info(
            radius_pixel_map=radius_pixel_map,
            num_bins=num_radial_bins
        )

        self._radial_bin_pixel_map = radial_bin_info.radial_bin_pixel_map
        self._radial_bin_size = radial_bin_info.radial_bin_size

        # Redefines the number of radial bins to the number of radial
        # bins for which at least a pixel is present. Bins that willl
        # never be filled are removed.
        self._radial_bins = numpy.unique(self._radial_bin_pixel_map)
        num_radial_bins = len(self._radial_bins)
        self.num_radial_bins = num_radial_bins

        # Reads in the scaling information from the configuration file.
        self._scale = monitor_parameters.get_param(
            section='Radial',
            parameter='scale',
            type_=bool,
            required=True
        )

        self._scale_region_begin = monitor_parameters.get_param(
            section='Radial',
            parameter='scale_region_begin',
            type_=int,
            required=True
        )

        self._scale_region_end = monitor_parameters.get_param(
            section='Radial',
            parameter='scale_region_end',
            type_=int,
            required=True
        )

        # Reads from the configuration file the total intensity
        # threshold for a detector frame to be considered a hit.
        self._intensity_threshold_for_hit = monitor_parameters.get_param(
            section='Radial',
            parameter='intensity_threshold_for_hit_detection',
            type_=float,
            required=True
        )

        # Reads from the configuration file the information used to
        # draw the intensity sum histogram.
        intensity_sum_hist_min = monitor_parameters.get_param(
            section='Radial',
            parameter='intensity_sum_histogram_minimum',
            type_=float,
            required=True
        )

        intensity_sum_hist_max = monitor_parameters.get_param(
            section='Radial',
            parameter='intensity_sum_histogram_maximum',
            type_=float,
            required=True
        )

        intensity_sum_hist_num_bins = monitor_parameters.get_param(
            section='Radial',
            parameter='num_bins_in_intensity_sum_histogram',
            type_=int,
            required=True
        )

        self._intensity_sum_hist_bins = numpy.linspace(
            intensity_sum_hist_min,
            intensity_sum_hist_max,
            intensity_sum_hist_num_bins
        )

        # Creates an empty intensity sum histogram.
        self._intensity_sum_hist, self._intensity_sum_hist_bins = (
            numpy.histogram(
                [0],
                self._intensity_sum_hist_bins
            )
        )

        if self.role == 'worker':
            requested_calib_alg = monitor_parameters.get_param(
                section='DetectorCalibration',
                parameter='calibration_algorithm',
                type_=str
            )
            if requested_calib_alg is not None:
                calibration_alg_class = getattr(
                    calib_algs,
                    requested_calib_alg
                )

                self._calibration_alg = calibration_alg_class(
                    calibration_file=monitor_parameters.get_param(
                        section='DetectorCalibration',
                        parameter='calibration_file',
                        type_=str,
                        required=True
                    )
                )
            else:
                # If no calibration is required, stores None in the
                # 'calibration_alg' attribute.
                self._calibration_alg = None

            # Reads from the configuration file all the parameters
            # needed to instantiate the dark calibration correction
            # algorithm, then instatiate the algorithm.
            dark_cal_fname = monitor_parameters.get_param(
                section='DarkCalCorrection',
                parameter='filename',
                type_=str,
                required=True
            )

            dark_cal_hdf5_pth = monitor_parameters.get_param(
                section='DarkCalCorrection',
                parameter='hdf5_path',
                type_=str,
                required=True
            )

            dark_cal_mask_fname = monitor_parameters.get_param(
                section='DarkCalCorrection',
                parameter='mask_filename',
                type_=str
            )

            dark_cal_mask_hdf5_pth = monitor_parameters.get_param(
                section='DarkCalCorrection',
                parameter='mask_hdf5_path',
                type_=str
            )

            dark_cal_gain_map_fname = monitor_parameters.get_param(
                section='DarkCalCorrection',
                parameter='gain_map_filename',
                type_=str
            )

            dark_cal_gain_map_hdf5_pth = monitor_parameters.get_param(
                section='DarkCalCorrection',
                parameter='gain_map_hdf5_path',
                type_=str
            )

            self._dark_cal_corr_alg = gen_algs.DarkCalCorrection(
                darkcal_filename=dark_cal_fname,
                darkcal_hdf5_path=dark_cal_hdf5_pth,
                mask_filename=dark_cal_mask_fname,
                mask_hdf5_path=dark_cal_mask_hdf5_pth,
                gain_map_filename=dark_cal_gain_map_fname,
                gain_map_hdf5_path=dark_cal_gain_map_hdf5_pth
            )

            # Reads from the configuration file the information for
            # profile subtraction.
            profile_for_subtr_fname = monitor_parameters.get_param(
                section='Radial',
                parameter='subtract_profile_filename',
                type_=str
            )
            if profile_for_subtr_fname:
                self._profile_for_subtraction = numpy.loadtxt(
                    profile_for_subtr_fname,
                    usecols=(0,
                             1)
                )
            else:
                self._profile_for_subtraction = None

            print("Starting worker: {0}.".format(self.rank))
            sys.stdout.flush()

        if self.role == 'master':
            # Reads from the configuration file whether the experiment
            # is pump-probe or not.
            self._pump_probe = monitor_parameters.get_param(
                section='Radial',
                parameter='pump_probe_experiment',
                type_=bool,
                required=True
            )

            # TODO: Maybe move this to a new algorithm.
            self._recent_profiles = numpy.zeros(
                (num_profiles, num_radial_bins)
            )

            self._recent_pumped_profiles = numpy.zeros(
                (num_profiles,
                 num_radial_bins)
            )
            self._recent_dark_profiles = numpy.zeros(
                (num_profiles,
                 num_radial_bins)
            )

            self._speed_report_interval = monitor_parameters.get_param(
                section='General',
                parameter='speed_report_interval',
                type_=int,
                required=True
            )

            self._geometry_is_optimized = monitor_parameters.get_param(
                section='General',
                parameter='geometry_is_optimized',
                type_=bool,
                required=True
            )

            # Reads from the configuration file how many events should
            # be accumulated by the master node before broadcasting the
            # acccumulated data. Then instantiates the data
            # accumulator.
            da_num_events_to_accumulate = monitor_parameters.get_param(
                section='DataAccumulator',
                parameter='num_events_to_accumulate',
                type_=int,
                required=True
            )

            self._data_accumulator = gen_algs.DataAccumulator(
                num_events_to_accumulate=da_num_events_to_accumulate
            )

            # Initializes some counters and arrays that will store
            # the accumulated data.
            self._num_events = 0
            self._num_pumped = 0
            self._num_dark = 0
            self._old_time = time.time()
            self._time = None
            self._run_avg_wdw_size = monitor_parameters.get_param(
                section='General',
                parameter='running_average_window_size',
                type_=int,
                required=True
            )

            self._hit_rate_run_wdw = collections.deque(
                [0.0] * self._run_avg_wdw_size,
                maxlen=self._run_avg_wdw_size
            )

            self._avg_hit_rate = 0

            self._pumped_hit_rate_run_wdw = collections.deque(
                [0.0] * self._run_avg_wdw_size,
                maxlen=self._run_avg_wdw_size
            )

            self._pumped_avg_hit_rate = 0

            self._dark_hit_rate_run_wdw = collections.deque(
                [0.0] * self._run_avg_wdw_size,
                maxlen=self._run_avg_wdw_size
            )

            self._dark_avg_hit_rate = 0

            self._cumulative_radial = numpy.zeros(num_radial_bins)
            self._cumulative_pumped = numpy.zeros(num_radial_bins)
            self._cumulative_pumped_avg = numpy.zeros(num_radial_bins)
            self._recent_pumped_avg = numpy.zeros(num_radial_bins)
            self._cumulative_dark = numpy.zeros(num_radial_bins)
            self._cumulative_dark_avg = numpy.zeros(num_radial_bins)
            self._recent_dark_avg = numpy.zeros(num_radial_bins)
            self._cumulative_radial_avg = numpy.zeros(num_radial_bins)
            self._recent_radial_avg = numpy.zeros(num_radial_bins)
            self._cumulative_unscaled_radial = numpy.zeros(num_radial_bins)
            self._cumulative_unscaled_radial_sq = numpy.zeros(num_radial_bins)
            self._cumulative_unscaled_radial_mean = numpy.zeros(
                num_radial_bins
            )
            self._cumulative_unscaled_radial_std = numpy.zeros(
                num_radial_bins
            )

            num_frames_per_event = monitor_parameters.get_param(
                section='DataRetrievalLayer',
                parameter='num_frames_per_event',
                type_=int,
                required=True
            )

            self._frame_idx = numpy.arange(num_frames_per_event)

            self._frame_ids_with_active_optical_laser = (
                monitor_parameters.get_param(
                    section='DataRetrievalLayer',
                    parameter='frame_ids_with_active_optical_laser',
                    type_=list,
                    required=True
                )
            )

            self._cumulative_unscaled_stack = numpy.zeros(
                (num_frames_per_event,
                 num_radial_bins)
            )

            self._cumulative_scaled_stack = numpy.zeros(
                (num_frames_per_event,
                 num_radial_bins)
            )

            self._cumulative_diff_stack = numpy.zeros(
                (num_frames_per_event,
                 num_radial_bins)
            )

            # Reads from the configuration file the information used
            # to set up the broadcasting socket.
            broadcast_socket_ip = monitor_parameters.get_param(
                section='General',
                parameter='publish_ip',
                type_=str
            )

            broadcast_socket_port = monitor_parameters.get_param(
                section='General',
                parameter='publish_port',
                type_=int
            )
            self._data_broadcast_socket = zmq_utils.DataBroadcaster(
                publish_ip=broadcast_socket_ip,
                publish_port=broadcast_socket_port
            )

            print("Starting the monitor...")
            sys.stdout.flush()

    def process_data(self, data):
        """
        Processes frame information.

        Performs detector and dark calibration corrections, if
        required, computes the radial average and converts the
        radial average to q coordinates.

        Args:

            data (Dict): a dictionary containing the frame raw data.
                Keys in the dictionary correspond to entries in the
                required_data list in the configuration file (e.g.:
                'detector_distance', 'beam_energy', 'detector_data',
                etc.).

        Returns:

            Tuple: a tuple where the first field is a dictionary
            containing the data that should be sent to the master node,
            and the second is the rank of the current worker.
        """
        results_dict = {}
        if self._calibration_alg is not None:
            calib_det_data = self._calibration_alg.apply_calibration(
                calibration_file_name=data['detector_data']
            )
        else:
            calib_det_data = data['detector_data']

        corr_det_data = numpy.nan_to_num(
            self._dark_cal_corr_alg.apply_darkcal_correction(
                data=calib_det_data
            )
        )

        unscaled_radial = swaxs_utils.calculate_avg_radial_intensity(
            corr_det_data,
            self._radial_bin_pixel_map
        )
        results_dict['unscaled_radial'] = unscaled_radial

        intensity_sum = numpy.median(corr_det_data.ravel())

        # Determine if the the frame is a hit candidate'.
        candidate_hit = (intensity_sum > self._intensity_threshold_for_hit)

        if self._scale:
            radial = swaxs_utils.scale_profile(
                radial_profile=unscaled_radial,
                min_radial_bin=self._scale_region_begin,
                max_radial_bin=self._scale_region_end
            )
        else:
            radial = unscaled_radial

        if self._profile_for_subtraction:
            subtracted_profile = radial - self._profile_for_subtraction
        else:
            subtracted_profile = radial

        # Tries to extract the coffset and res information from the
        # geometry. The geometry allows these two values to be defined
        # individually for each panel, but the GUI just needs simple
        # values for the whole detector. This code uses the values from
        # the first panel.
        pixel_size = 1. / list(self.geometry['panels'].items())[0][1]['res']
        coffset = list(self.geometry['panels'].items())[0][1]['coffset']

        q_bins = swaxs_utils.pixel_bins_to_q_bins(
            detector_distance=data['detector_distance'],
            beam_energy=data['beam_energy'],
            pixel_size=pixel_size,
            pixel_radial_bins=self._radial_bins,
            coffset=coffset,
            radial_bin_size=self._radial_bin_size
        )

        results_dict['q_bins'] = q_bins
        results_dict['radial'] = subtracted_profile
        results_dict['intensity_sum'] = intensity_sum
        results_dict['cand_hit_flag'] = candidate_hit
        results_dict['timestamp'] = data['timestamp']
        results_dict['detector_distance'] = data['detector_distance']
        results_dict['beam_energy'] = data['beam_energy']
        results_dict['native_data_shape'] = data['detector_data'].shape
        results_dict['optical_laser_active'] = data['optical_laser_active']
        results_dict['frame_id'] = data['frame_id']

        return results_dict, self.rank

    def collect_data(self, data):
        """
        Computes aggregated data statistics and broadcast the data.

        Accumulates the data received from the worker nodes and
        computes statistics on the aggregated data (e.g.: averages and
        cumulative averages, etc.) Finally, broadcasts the reduced data
        for visualization.

        Args:

            data (Tuple): a tuple where the first field is a dictionary
                containing the data received from a worker node, and
                the second is the rank of the worker node sending the
                data.
        """
        results_dict, _ = data
        self._num_events += 1

        # Computes the intensity sum histogram.
        self._intensity_sum_hist += numpy.histogram(
            results_dict['intensity_sum'],
            self._intensity_sum_hist_bins
        )[0]

        results_dict['intensity_sum_hist'] = self._intensity_sum_hist
        results_dict['intensity_sum_hist_bins'] = (
            self._intensity_sum_hist_bins[1:]
        )

        # Sums up the unscaled_radials to make the cumulative average
        # rather than scaling first and then averaging. This should
        # help to mitigate noise from weak profiles.
        radial = results_dict['radial']
        unscaled_radial = results_dict['unscaled_radial']

        # Runs a second hit finder. This second hit finder filters out
        # frames whose radial profile in the scaling region is more
        # than 3 standard deviations d outside of the mean. It does
        # this on a per bin basis.
        self._cumulative_unscaled_radial += unscaled_radial
        self._cumulative_unscaled_radial_mean = (
            self._cumulative_unscaled_radial / self._num_events
        )
        self._cumulative_unscaled_radial_sq += unscaled_radial**2
        self._cumulative_unscaled_radial_std = (
            numpy.sqrt(
                (
                    self._cumulative_unscaled_radial_sq /
                    self._num_events
                ) - self._cumulative_unscaled_radial_mean**2
            )
        )
        radial_subset = unscaled_radial[self._scale_region_begin:self.
                                        _scale_region_end]
        mean_subset = self._cumulative_unscaled_radial_mean[
            self._scale_region_begin:self._scale_region_end]
        std_subset = self._cumulative_unscaled_radial_std[
            self._scale_region_begin:self._scale_region_end]

        std_dev_hit = numpy.all(
            radial_subset < numpy.
            abs(radial_subset - (mean_subset + 3 * std_subset))
        )

        hit_flag = numpy.logical_and(
            results_dict['cand_hit_flag'],
            std_dev_hit
        )

        self._hit_rate_run_wdw.append(float(hit_flag))

        # Divides by the window size to compute the average hit rate,
        # but only if the window has already been filled with events.
        # Otherwise takes the number of events that the window already
        # contains.
        avg_hit_rate = (
            sum(self._hit_rate_run_wdw) /
            min(self._run_avg_wdw_size,
                self._num_events)
        )
        results_dict['hit_rate'] = avg_hit_rate

        if self._pump_probe:
            # Calculates separate statistics for 'light' and 'dark'
            # profiles.
            if results_dict['optical_laser_active']:
                self._num_pumped += 1

                # Calculates the average of all (cumulative) events
                # and, separately, of recent events
                if hit_flag:
                    self._cumulative_pumped += unscaled_radial
                    self._cumulative_pumped_avg = (
                        self._cumulative_pumped / self._num_pumped
                    )

                    # Calculates the running average of recently
                    # collected profiles only.
                    self._recent_pumped_profiles = numpy.roll(
                        self._recent_pumped_profiles,
                        -1,
                        axis=0
                    )
                    self._recent_pumped_profiles[-1] = unscaled_radial
                    self._recent_pumped_avg = numpy.mean(
                        self._recent_pumped_profiles,
                        axis=0
                    )

                    # Scales if necessary.
                    if self._scale:
                        self._cumulative_pumped_avg = (
                            swaxs_utils.scale_profile(
                                self._cumulative_pumped_avg,
                                self._scale_region_begin,
                                self._scale_region_end
                            )
                        )
                        self._recent_pumped_avg = swaxs_utils.scale_profile(
                            self._recent_pumped_avg,
                            self._scale_region_begin,
                            self._scale_region_end
                        )

                # Calculates the hit rate for pumped events.
                self._pumped_hit_rate_run_wdw.append(float(hit_flag))

                # Divides by the window size to compute the average hit
                # rate, but only if the window has already been filled
                # with events. Otherwise takes the number of events
                # that the window already contains.
                pumped_avg_hit_rate = (
                    sum(self._pumped_hit_rate_run_wdw) /
                    min(self._run_avg_wdw_size,
                        self._num_pumped)
                )
                results_dict['pumped_hit_rate'] = pumped_avg_hit_rate

                # The GUI cannot read the configuration file, so it
                # does not know if the experiment is pump probe or not.
                # A None value sent to the GUI if the experiment is not
                # pump probe.
                results_dict['dark_hit_rate'] = -1

            else:
                self._num_dark += 1
                if hit_flag:
                    self._cumulative_dark += unscaled_radial
                    self._cumulative_dark_avg = (
                        self._cumulative_dark / self._num_dark
                    )

                    # Calculates the running average of recently
                    # collected profiles only.
                    self._recent_dark_profiles = numpy.roll(
                        self._recent_dark_profiles,
                        -1,
                        axis=0
                    )
                    self._recent_dark_profiles[-1] = unscaled_radial
                    self._recent_dark_avg = numpy.mean(
                        self._recent_dark_profiles,
                        axis=0
                    )

                    # Scales if necessary.
                    if self._scale:
                        self._cumulative_dark_avg = swaxs_utils.scale_profile(
                            self._cumulative_dark_avg,
                            self._scale_region_begin,
                            self._scale_region_end
                        )
                        self._recent_dark_avg = swaxs_utils.scale_profile(
                            self._recent_dark_avg,
                            self._scale_region_begin,
                            self._scale_region_end
                        )

                self._dark_hit_rate_run_wdw.append(float(hit_flag))

                # Divides by the window size to compute the average hit
                # rate, but only if the window has already been filled
                # with events. Otherwise takes the number of events
                # that the window already contains.
                dark_avg_hit_rate = (
                    sum(self._dark_hit_rate_run_wdw) /
                    min(self._run_avg_wdw_size,
                        self._num_dark)
                )
                results_dict['dark_hit_rate'] = dark_avg_hit_rate

                # The GUI cannot read the configuration file, so it
                # does not know if the experiment is pump probe or not.
                # A None value sent to the GUI if the experiment is not
                # pump probe.
                results_dict['pumped_hit_rate'] = -1

            self._cumulative_radial_avg = (
                self._cumulative_pumped_avg - self._cumulative_dark_avg
            )
            self._recent_radial_avg = (
                self._recent_pumped_avg - self._recent_dark_avg
            )

            diff = (radial - self._cumulative_dark_avg)
            results_dict['cumulative_pumped_avg'] = self._cumulative_pumped_avg
            results_dict['cumulative_dark_avg'] = self._cumulative_dark_avg
            results_dict['diff'] = diff

            # TODO: Check this. What is going on?
            # Any frame_id greater than expected in the list of frames
            # is piled into the last frame expected.
            frame_id = min(
                int(results_dict['frame_id']),
                self._cumulative_unscaled_stack.shape[0]
            )

            self._cumulative_unscaled_stack[frame_id] += (unscaled_radial)

            if self._scale:
                self._cumulative_scaled_stack[frame_id] = (
                    swaxs_utils.scale_profile(
                        self._cumulative_unscaled_stack[frame_id],
                        self._scale_region_begin,
                        self._scale_region_end
                    )
                )
            else:
                self._cumulative_scaled_stack[frame_id] = (
                    self._cumulative_unscaled_stack[frame_id]
                )

            self._cumulative_diff_stack[frame_id] = (
                self._cumulative_scaled_stack[frame_id] -
                self._cumulative_dark_avg
            )

            results_dict['cumulative_diff_stack'] = self._cumulative_diff_stack

        else:
            if hit_flag:
                self._cumulative_radial += unscaled_radial
                self._cumulative_radial_avg = (
                    self._cumulative_radial / self._num_events
                )

                self._recent_profiles = numpy.roll(
                    self._recent_profiles,
                    -1,
                    axis=0
                )

                self._recent_profiles[-1] = unscaled_radial
                self._recent_radial_avg = numpy.mean(
                    self._recent_profiles,
                    axis=0
                )
            results_dict['pumped_hit_rate'] = -1
            results_dict['dark_hit_rate'] = -1
            results_dict['diff'] = radial * 0
            results_dict['cumulative_pumped_avg'] = radial * 0
            results_dict['cumulative_dark_avg'] = radial * 0

            results_dict['cumulative_diff_stack'] = self._cumulative_diff_stack

        results_dict['cumulative_radial'] = (self._cumulative_radial_avg)
        results_dict['recent_radial'] = self._recent_radial_avg

        # Injects additional information into the dictionary that will
        # be stored in the data accumulator end eventually sent out
        # from the master.
        results_dict['geometry_is_optimized'] = self._geometry_is_optimized

        if 'detector_data' in results_dict:
            # If detector frame data is found in the data received from
            # a worker node, the frame must be broadcasted to the
            # frame viewer. Before that, the frame is wrapped into a
            # list because GUIs expect lists of aggregated events as
            # opposed to single events.
            self._data_broadcast_socket.send_data(
                tag=u'ondaframedata',
                message=[results_dict]
            )

        # Removes the detector frame data from the dictionary that will
        # be stored in the data accumulator (it doesn't need to be sent
        # to any other receiver).
        if 'detector_data' in results_dict:
            del results_dict['detector_data']

        collected_data = self._data_accumulator.add_data(data=results_dict)
        if collected_data:
            self._data_broadcast_socket.send_data(
                tag=u'ondadata',
                message=collected_data
            )

        if self._num_events % self._speed_report_interval == 0:
            now_time = time.time()
            speed_report_msg = (
                "Processed: {0} in {1:.2f} seconds ({2:.2f} Hz)".format(
                    self._num_events,
                    now_time - self._old_time,
                    (
                        float(self._speed_report_interval) /
                        float(now_time - self._old_time)
                    )
                )
            )

            print(speed_report_msg)
            sys.stdout.flush()
            self._old_time = now_time
