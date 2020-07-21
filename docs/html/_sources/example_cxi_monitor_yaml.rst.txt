Example *monitor.yaml* for the CXI Beamline at the LCLS Facility
----------------------------------------------------------------

.. code-block:: yaml

    om:
      processing_layer: crystallography
      data_retrieval_layer: lcls_cxi
      required_data:
        - detector_data
        - beam_energy
        - detector_distance
        - timestamp

    data_retrieval_layer:
      psana_detector_name: DscCsPad
      psana_detector_distance_epics_name: 'CXI:DS1:MMS:06.RBV'
      psana_calibration_directory: /reg/d/psdm/cxi/cxilt4317/calib'
      event_rejection_threshold: null

    crystallography:
      num_frames_in_ev¼ent_to_process: 1
      broadcast_ip: null
      broadcast_port: null
      geometry_file: cspad.geom
      max_saturated_peaks: 10
      min_num_peaks_for_hit: 10
      max_num_peaks_for_hit: 5000
      saturation_value: 14000
      running_average_window_size: 200
      geometry_is_optimized: true
      speed_report_interval: 1
      hit_frame_sending_interval: null
      non_hit_frame_sending_interval: null

    calibration:
      calibration_algorithm: null 
      calibration_file: nul

    correction:
      dark_filename: null
      dark_hdf5_path: null

    peakfinder8_peak_detection:
      max_num_peaks: 2048
      adc_threshold: 250.0
      minimum_snr: 7.0
      min_pixel_count: 2
      max_pixel_count: 300
      local_bg_radius: 4
      bad_pixel_map_filename: null
      bad_pixel_map_hdf5_path: /data/data
      min_res: 0
      max_res: 900

    data_accumulator:
      num_events_to_accumulate: 10