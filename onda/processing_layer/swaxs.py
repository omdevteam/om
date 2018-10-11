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
"""
OnDA Monitor for serial solution scatterin.

This module contains the implementation of an OnDA real-time monitor
for x-ray solution scattering experiments.
"""
from __future__ import absolute_import, division, print_function

import collections
import sys
import time
from builtins import str  # pylint: disable=W0622

import numpy


from cfelpyutils import crystfel_utils, geometry_utils
from onda.algorithms import calibration_algorithms as calib_algs
from onda.algorithms import crystallography_algorithms as cryst_algs
from onda.algorithms import generic_algorithms as gen_algs
from onda.parallelization_layer import mpi
from onda.utils import zmq as onda_zmq
from onda.utils import swaxs


class OndaMonitor(mpi.ParallelizationEngine):
    """
    An OnDA real-time monitor for serial crystallography experiments.

    TODO: Describe what the monitor does.

    Broadcast reduced data for visualization. Optionally also broadcast
    corrected frame data for visualization.
    """

    def __init__(self, source, monitor_parameters):
        """
        Initialize the OndaMonitor class.

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

        # Read information for profile averaging.
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

        # Load the geometry data and compute the pixel maps.
        geometry_filename = monitor_parameters.get_param(
            section='General',
            parameter='geometry_file',
            type_=str,
            required=True
        )

        geometry = crystfel_utils.load_crystfel_geometry(
            geometry_filename
        )

        pixel_maps = geometry_utils.compute_pix_maps(geometry)
        radius_pixel_map = pixel_maps.r

        # TODO: Fix this comment.
        # Creates array labeling each pixel with bin value for
        # radial averaging.
        self._radial_bin_pixel_map = (
            swaxs.calculate_radial_bin_pixel_map(
                radius_pixel_map=radius_pixel_map,
                num_bins=num_radial_bins
            )
        )

        # TODO: Fix this comment.
        # Redefine number of bins from bins included in labels
        # self.rpixbins
        num_radial_bins = len(numpy.unique(self._radial_bin_pixel_map))

        # Read in scaling information.
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

        # TODO: Fix this comment.
        # Read threshold information
        self._intensity_threshold = monitor_parameters.get_param(
            section='Radial',
            parameter='intensity_threshold_for_hit_detection',
            type_=float,
            required=True
        )

        # Read information for the intensity sum histogram.
        intensity_sum_hist_min = monitor_parameters.get_param(
            section='Radial',
            parameter='intensity_sum_histogram_minimum',
            type_=int,
            required=True
        )

        intensity_sum_hist_max = monitor_parameters.get_param(
            section='Radial',
            parameter='intensity_sum_histogram_maximum',
            type_=int,
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

        # Create an empty histogram
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
                # If no calibration is required store None in the
                # 'calibration_alg' attribute.
                self._calibration_alg = None

            # Initialize the non_hit_frame_sending_counter and the
            # hit_frame_sending_counter to keep track of how often the
            # detector frame data needs to be sent to the master
            # worker.
            self._hit_frame_sending_counter = 0
            self._non_hit_frame_sending_counter = 0

            # Read from the configuration file all the parameters
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

            # Read in radial averaging information.
            sigma_threshold = monitor_parameters.get_param(
                section='Radial',
                parameter='sigma_threshold',
                type_=float,
                required=True
            )

            # Read information for profile subtraction.
            profile_for_subtr_fname = monitor_parameters.get_param(
                section='Radial',
                parameter='subtract_profile_filename',
                type_=str
            )
            if profile_for_subtr_fname:
                self._profile_for_subtraction = numpy.loadtxt(
                    profile_for_subtr_fname,
                    usecols=(0, 1)
                )
            else:
                self._profile_for_subtraction = None

            self._hit_frame_sending_interval = monitor_parameters.get_param(
                section='General',
                parameter='hit_frame_sending_interval',
                type_=int,
            )

            self._non_hit_frame_sending_interval = (
                monitor_parameters.get_param(
                    section='General',
                    parameter='non_hit_frame_sending_interval',
                    type_=int,
                )
            )

            print("Starting worker: {0}.".format(self.rank))
            sys.stdout.flush()

        if self.role == 'master':

            # Read information related to the pump-probe nature of
            # the experiment.
            self._pump_probe = monitor_parameters.get_param(
                section='Radial',
                parameter='pump_probe_experiment',
                type_=bool,
                required=True
            )

            # TODO: Maybe move this to a new algorithm.
            self._profiles_to_average = numpy.zeros(
                (num_profiles, num_radial_bins)
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

            # Read from the configuration file how many events should
            # be accumulated by the master node before broadcasting the
            # acccumulated data. Then instantiate the peak accumulator.
            da_num_events_to_accumulate = monitor_parameters.get_param(
                section='DataAccumulator',
                parameter='num_events_to_accumulate',
                type_=int,
                required=True
            )

            self._data_accumulator = cryst_algs.DataAccumulator(
                num_events_to_accumulate=da_num_events_to_accumulate
            )

            self._data_accumulator = cryst_algs.DataAccumulator(
                num_events_to_accumulate=da_num_events_to_accumulate
            )

            self._num_events = 0
            self._num_pumped = 0
            self._num_dark = 0
            self.intensity_sums = []
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

            self._cumulative_radial = numpy.zeros(num_radial_bins)
            self._cumulative_pumped = numpy.zeros(num_radial_bins)
            self._cumulative_pumped_avg = numpy.zeros(num_radial_bins)
            self._cumulative_dark = numpy.zeros(num_radial_bins)
            self._cumulative_dark_avg = numpy.zeros(num_radial_bins)

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
            self._data_broadcast_socket = onda_zmq.DataBroadcaster(
                publish_ip=broadcast_socket_ip,
                publish_port=broadcast_socket_port
            )

            print("Starting the monitor...")
            sys.stdout.flush()

    def process_data(self, data):
        """
        Process frame information.

        Perform detector and dark calibration corrections, extract the
        peak information and evaluate the extracted data. Return the
        data that need to be sent to the master node.

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

        corr_det_data = self._dark_cal_corr_alg.apply_darkcal_correction(
            data=calib_det_data
        )

        unscaled_radial = swaxs.calculate_avg_radial_intensity(
            corr_det_data,
            self._radial_bin_pixel_map
        )
        results_dict['unscaled_radial'] = unscaled_radial

        intensity_sum = numpy.nansum(unscaled_radial)

        # Determine if the the frame should be labelled as a 'hit'.
        hit = (
            intensity_sum >
            self._intensity_threshold
        )

        if self._scale:
            radial = swaxs.scale_profile(
                radial_profile=unscaled_radial,
                min_radial_bin=self._scale_region_begin,
                max_radial_bin=self._scale_region_end
            )

        if self._profile_for_subtraction:
            subtracted_profile = radial - self._profile_for_subtraction
        else:
            subtracted_profile = radial

        results_dict['radial'] = subtracted_profile
        results_dict['intensity_sum'] = intensity_sum
        results_dict['hit_flag'] = hit
        results_dict['timestamp'] = data['timestamp']
        results_dict['detector_distance'] = data['detector_distance']
        results_dict['beam_energy'] = data['beam_energy']
        results_dict['native_data_shape'] = data['detector_data'].shape
        results_dict['optical_laser_active'] = data['optical_laser_active']

        if hit:
            if self._hit_frame_sending_interval:
                self._hit_frame_sending_counter += 1

                if (
                        self._hit_frame_sending_counter ==
                        self._hit_frame_sending_interval
                ):
                    # If the frame is a hit, and if the
                    # 'hit_sending_interval' attribute says we should
                    # send the detector frame data to the master node,
                    # add it to the dictionary (and reset the counter).
                    self._hit_frame_sending_counter = 0

        else:
            if self._non_hit_frame_sending_interval:
                self._non_hit_frame_sending_counter += 1

                if (
                        self._non_hit_frame_sending_counter ==
                        self._non_hit_frame_sending_interval
                ):
                    # If the frame is not a  hit, and if the
                    # 'frame_sending_interval' attribute says we should
                    # send the detector frame data to the master node,
                    # add it to the dictionary (and reset the counter).
                    self._non_hit_frame_sending_counter = 0

        return results_dict, self.rank

    def collect_data(self, data):
        """
        Compute aggregated data statistics and broadcast the data.

        Accumulate the data received from the worker nodes and compute
        statistics on the aggregated data (e.g.: hit rate,
        saturation_rate). Finally, broadcast the reduced data for
        visualization.

        Args:

            data (Tuple): a tuple where the first field is a dictionary
                containing the data received from a worker node, and
                the second is the rank of the worker node sending the
                data.
        """
        results_dict, _ = data
        self._num_events += 1

        self._hit_rate_run_wdw.append(
            float(
                results_dict['hit_flag']
            )
        )

        # Divide by the window size, but only if the window has already
        # been filled with events. Otherwise take the number of events
        # that the window actually contains.
        avg_hit_rate = (
            sum(self._hit_rate_run_wdw) /
            min(self._run_avg_wdw_size, self._num_events)
        )

        radial = results_dict['radial']

        # TODO: Danger! Does this list grow indefinitely?
        self.intensity_sums.append(results_dict['intensity_sum'])

        self._intensity_sum_hist += numpy.histogram(
            results_dict['intensity_sum'],
            self._intensity_sum_hist_bins
        )[0]

        results_dict['intensity_sum_hist'] = self._intensity_sum_hist
        results_dict['intendity_sum_hist_bins'] = self._intensity_sum_hist_bins
        results_dict['intensity_sums'] = self.intensity_sums
        unscaled_radial = results_dict['unscaled_radial']
        results_dict['hit_rate'] = avg_hit_rate

        # Sum up the unscaled_radials to make the cumulative average
        # rather than scaling first and then averaging. This should
        # help to mitigate noise from weak profiles.

        if self._pump_probe:

            if results_dict['optical_laser_active']:
                self._num_pumped += 1
                self._cumulative_pumped += unscaled_radial
                self._cumulative_pumped_avg = (
                    self._cumulative_pumped / self._num_pumped
                )
                if self._scale:
                    self._cumulative_pumped_avg = swaxs.scale_profile(
                        self._cumulative_pumped_avg,
                        self._scale_region_begin,
                        self._scale_region_end,
                    )
            else:
                self._num_dark += 1
                self._cumulative_dark += unscaled_radial
                self._cumulative_dark_avg = (
                    self._cumulative_dark / self._num_dark
                )
                if self._scale:
                    self._cumulative_dark_avg = swaxs.scale_profile(
                        self._cumulative_dark_avg,
                        self._scale_region_begin,
                        self._scale_region_end,
                    )

            self._cumulative_radial_avg = (
                self._cumulative_pumped_avg - self._cumulative_dark_avg
            )

            results_dict['radial'] = radial - self._cumulative_dark_avg

        else:
            self._cumulative_radial += unscaled_radial
            self._cumulative_radial_avg = self._cumulative_radial / self._num_events

        results_dict['cumulative_radial'] = self._cumulative_radial_avg

        # Inject additional information into the dictionary that will
        # be stored in the data accumulator end eventually sent out
        # from the master.
        results_dict['geometry_is_optimized'] = self._geometry_is_optimized

        if 'detector_data' in results_dict:
            # If detector frame data is found in the data received from
            # a worker node, the frame must be broadcasted to the
            # frame viewer. The frame is wrapped into a list because
            # GUIs expect list aggregated events as opposed to single
            # events.
            self._data_broadcast_socket.send_data(
                tag=u'ondaframedata',
                message=[results_dict]
            )

        # Remove the detector frame data from the dictionary that will
        # be stored in the data accumulator (it doesn't need to sent to
        # any other receiver.
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
