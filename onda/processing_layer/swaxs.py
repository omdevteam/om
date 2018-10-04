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
OnDA Monitor for serial x-ray crystallography.

This module contains the implementation of an OnDA real-time monitor
for serial x-ray crystallography experiments.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

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
from onda.utils import named_tuples
from onda.utils.dynamic_import import get_peakfinder8_info
import onda.algorithms.swaxs_algorithms as swaxs_algs


class OndaMonitor(mpi.ParallelizationEngine):
    """
    An OnDA real-time monitor for serial crystallography experiments.

    Provide real time hit and saturation rate information, plus a
    virtual powder pattern-style plot of the processed data.
    Optionally, apply detector calibration, dark calibration and gain
    map correction to each frame.

    Carry out the peak finding using the peakfinder8 algorithm from the
    Cheetah software package:

    A. Barty, R. A. Kirian, F. R. N. C. Maia, M. Hantke, C. H. Yoon,
    T. A. White, and H. N. Chapman, "Cheetah: software for
    high-throughput reduction and analysis of serial femtosecond X-ray
    diffraction data," J Appl Crystallogr, vol. 47,
    pp. 1118-1131 (2014).

    Broadcast reduced data for visualization. Optionally also broadcast
    corrected frame data for visualization.
    """
    def __init__(self,
                 source,
                 monitor_parameters):
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
        super(OndaMonitor, self).__init__(
            process_func=self.process_data,
            collect_func=self.collect_data,
            source=source,
            monitor_params=monitor_parameters
        )

        # Read in Radial Section of monitor.ini file
        self.scale_region_begin = monitor_parameters.get_param(
                section='Radial',
                parameter='min_bin_to_scale',
                type_=int,
                required=True
                )

        self.scale_region_end = monitor_parameters.get_param(
                section='Radial',
                parameter='max_bin_to_scale',
                type_=int,
                required=True
                )

        self.n_sigma = monitor_parameters.get_param(
                section='Radial',
                parameter='n_sigma',
                type_=float,
                required=True
                )

        self.num_bins = monitor_parameters.get_param(
                section='Radial',
                parameter='num_bins',
                type_=int,
                required=True
                )

        self.num_profiles = monitor_parameters.get_param(
                section='Radial',
                parameter='num_profiles_to_average',
                type_=int,
                required=True
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

            # Load the geometry data and compute the pixel maps.
            geometry_filename = monitor_parameters.get_param(
                section='General',
                parameter='geometry_file',
                type_=str,
                required=True
            )

            geometry = crystfel_utils.load_crystfel_geometry(geometry_filename)
            self.geometry = geometry
            pixelmaps = geometry_utils.compute_pix_maps(geometry)
            radius_pixel_map = pixelmaps.r

            #Creates array labeling each pixel with bin value for radial averaging
            self.rbins, dr = swaxs_algs.calculate_rbins(radius_pixel_map, self.num_bins)

            #Redefine number of bins from bins included in labels self.rpixbins
            self.num_bins = len(numpy.unique(self.rbins))

            self.coffset = list(self.geometry['panels'].items())[0][1]['coffset']


            # Recovers the peakfinder8 information for the detector
            # being used.
            pf8_detector_info = get_peakfinder8_info(
                monitor_params=self._mon_params,
                detector='detector_data',
            )

            # Read from the configuration file all the parameters
            # needed to instantiate the peakfinder8 algorithm. Then
            # instantiate the algorithm.
            pf8_max_num_peaks = monitor_parameters.get_param(
                section='Peakfinder8PeakDetection',
                parameter='max_num_peaks',
                type_=int,
                required=True
            )

            pf8_adc_threshold = monitor_parameters.get_param(
                section='Peakfinder8PeakDetection',
                parameter='adc_threshold',
                type_=float,
                required=True
            )

            pf8_minimum_snr = monitor_parameters.get_param(
                section='Peakfinder8PeakDetection',
                parameter='minimum_snr',
                type_=float,
                required=True
            )

            pf8_min_pixel_count = monitor_parameters.get_param(
                section='Peakfinder8PeakDetection',
                parameter='min_pixel_count',
                type_=int,
                required=True
            )

            pf8_max_pixel_count = monitor_parameters.get_param(
                section='Peakfinder8PeakDetection',
                parameter='max_pixel_count',
                type_=int,
                required=True
            )

            pf8_local_bg_radius = monitor_parameters.get_param(
                section='Peakfinder8PeakDetection',
                parameter='local_bg_radius',
                type_=int,
                required=True
            )

            pf8_min_res = monitor_parameters.get_param(
                section='Peakfinder8PeakDetection',
                parameter='min_res',
                type_=int,
                required=True
            )

            pf8_max_res = monitor_parameters.get_param(
                section='Peakfinder8PeakDetection',
                parameter='max_res',
                type_=int,
                required=True
            )

            pf8_bad_pixel_map_fname = monitor_parameters.get_param(
                section='Peakfinder8PeakDetection',
                parameter='bad_pixel_map_filename',
                type_=str,
                required=True
            )

            pf8_bad_pixel_map_hdf5_path = monitor_parameters.get_param(
                section='Peakfinder8PeakDetection',
                parameter='bad_pixel_map_hdf5_path',
                type_=str,
                required=True
            )

            self._peakfinder8_peak_det = cryst_algs.Peakfinder8PeakDetection(
                max_num_peaks=pf8_max_num_peaks,
                asic_nx=pf8_detector_info.asic_nx,
                asic_ny=pf8_detector_info.asic_ny,
                nasics_x=pf8_detector_info.nasics_x,
                nasics_y=pf8_detector_info.nasics_y,
                adc_threshold=pf8_adc_threshold,
                minimum_snr=pf8_minimum_snr,
                min_pixel_count=pf8_min_pixel_count,
                max_pixel_count=pf8_max_pixel_count,
                local_bg_radius=pf8_local_bg_radius,
                min_res=pf8_min_res,
                max_res=pf8_max_res,
                bad_pixel_map_filename=pf8_bad_pixel_map_fname,
                bad_pixel_map_hdf5_path=pf8_bad_pixel_map_hdf5_path,
                radius_pixel_map=radius_pixel_map
            )

            self._max_saturated_peaks = monitor_parameters.get_param(
                section='General',
                parameter='max_saturated_peaks',
                type_=int,
                required=True
            )

            self._min_num_peaks_for_hit = monitor_parameters.get_param(
                section='General',
                parameter='min_num_peaks_for_hit',
                type_=int,
                required=True
            )

            self._max_num_peaks_for_hit = monitor_parameters.get_param(
                section='General',
                parameter='max_num_peaks_for_hit',
                type_=int,
                required=True
            )

            self._saturation_value = monitor_parameters.get_param(
                section='General',
                parameter='saturation_value',
                type_=int,
                required=True
            )

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

            # Initialize SWAXS stuff
            self.q_space_convert = swaxs_algs.PixelSpaceQSpaceConversion(numpy.unique(self.rbins), self.coffset, dr)
            self.scale = monitor_parameters.get_param(
                section='Radial',
                parameter='scale',
                type_=bool,
                required=True
                )

            # Load profile to be subtracted from Radial Intensity profile
            self.sub = monitor_parameters.get_param(
                section='Radial',
                parameter='subtract_profile_filename',
                type_=str
                )
            if self.sub is not None:
                self.sub_profile = numpy.loadtxt(
                    self.sub,
                    usecols=(0, 1)
                    )
            else:
                self.sub_profile = None

            print("Starting worker: {0}.".format(self.rank))
            sys.stdout.flush()

        if self.role == 'master':

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
            pa_num_events_to_accumulate = monitor_parameters.get_param(
                section='PeakAccumulator',
                parameter='num_events_to_accumulate',
                type_=int,
                required=True
            )

            self._data_accumulator = cryst_algs.DataAccumulator(
                num_events_to_accumulate=pa_num_events_to_accumulate
            )

            self._num_events = 0
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

            self._saturation_rate_run_wdw = collections.deque(
                [0.0] * self._run_avg_wdw_size,
                maxlen=self._run_avg_wdw_size
            )

            self._avg_hit_rate = 0
            self._avg_sat_rate = 0

            #SWAXS stuff
            self.intensity_threshold = monitor_parameters.get_param(
                section='Radial',
                parameter='intensity_threshold',
                type_=float,
                required=True
            )

            self.profiles_to_average = numpy.zeros((self.num_profiles,self.num_bins))
            self.cumulative_average = numpy.zeros(self.num_bins)

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

        peak_list = self._peakfinder8_peak_det.find_peaks(corr_det_data)

        #SWAXS processing
        #calculate radial profile
        unscaled_radial = swaxs_algs.calculate_average_radial_intensity(corr_det_data, self.rbins)
        results_dict['unscaled_radial'] = unscaled_radial

        #scale radial profile if self.scale is True
        radial, _ = swaxs_algs.scale_profile(unscaled_radial, self.scale_region_begin, self.scale_region_end, self.scale)

        #subtract a given radial profile
        if self.sub_profile is not None:
            prof_subtract = self.sub_profile[:,1]
        else:
            prof_subtract = numpy.zeros(len(radial))
        results_dict['radial'] = radial - prof_subtract

        intensity_sum = numpy.nansum(radial)
        results_dict['intensity_sum'] = intensity_sum

        # Determine if the the frame should be labelled as 'saturated'.
        sat = len(
            [x for x in peak_list.intensity if x > self._saturation_value]
        ) > self._max_saturated_peaks

        # Determine if the the frame should be labelled as a 'hit'.
        hit = (
            self._min_num_peaks_for_hit <
            len(peak_list.intensity) <
            self._max_num_peaks_for_hit
        )

        hit = (
            intensity_sum >
            100 #self.intensity_threshold
        )

        results_dict['timestamp'] = data['timestamp']
        results_dict['saturation_flag'] = sat
        results_dict['hit_flag'] = hit
        results_dict['detector_distance'] = data['detector_distance']
        results_dict['beam_energy'] = data['beam_energy']
        results_dict['native_data_shape'] = data['detector_data'].shape
        if hit:
            results_dict['peak_list'] = peak_list

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
                    results_dict['detector_data'] = corr_det_data
                    self._hit_frame_sending_counter = 0

        else:
            # If the frame is not a hit, send an empty peak list
            results_dict['peak_list'] = named_tuples.PeakList(
                fs=[],
                ss=[],
                intensity=[]
            )
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
                    results_dict['detector_data'] = corr_det_data
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

        radial = results_dict['radial']
        intensity_sum = results_dict['intensity_sum']
        unscaled_radial_profile = results_dict['unscaled_radial']

        self._hit_rate_run_wdw.append(
            float(
                results_dict['hit_flag']
            )
        )

        self._saturation_rate_run_wdw.append(
            float(
                results_dict['saturation_flag']
                )
        )

        avg_hit_rate = (
            sum(self._hit_rate_run_wdw) /
            self._run_avg_wdw_size
        )

        avg_sat_rate = (
            sum(self._saturation_rate_run_wdw) /
            self._run_avg_wdw_size
        )

        # Inject additional information into the dictionary that will
        # be stored in the data accumulator end eventually sent out
        # from the master.
        results_dict['hit_rate'] = avg_hit_rate
        results_dict['saturation_rate'] = avg_sat_rate
        results_dict['geometry_is_optimized'] = self._geometry_is_optimized

        # Since the data will be sent out of the master node using
        # msgpack, NamedTuple structures will not be preserved.
        # The peak list is here converted to a dictionary, which
        # suvives the msgpack conversion and allows introspection ont
        # the receiver side.
        results_dict['peak_list'] = {
            'fs': results_dict['peak_list'].fs,
            'ss': results_dict['peak_list'].ss,
            'intensity': results_dict['peak_list'].intensity
        }

        if 'detector_data' in results_dict:

            # If detector frame data is found in the data received from
            # a worker node, the frame must be broadcasted to the
            # frame viewer. The frame is wrapped into a list because
            # GUIs expect list aggregated events as opposed to single
            # events.
            self._data_broadcast_socket.send_data(
                tag='ondaframedata',
                message=[results_dict]
            )

        # Remove the detector frame data from the dictionary that will
        # be stored in the data accumulator (it doesn't need to sent to
        # any other receiver.
        if 'detector_data' in results_dict:
            del results_dict['detector_data']

        collected_data = self._data_accumulator.add_data(
            data=results_dict
        )
        if collected_data:
            self._data_broadcast_socket.send_data(
                tag='ondadata',
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
