Example *monitor.toml* for Pilatus Files from the Filesystem
------------------------------------------------------------

.. code-block:: ini

    [Onda]
    processing_layer = 'crystallography'
    data_retrieval_layer = 'filesystem_pilatus'
    required_data = ['detector_data', 'detector_distance', 'beam_energy', 'timestamp', 'event_id', 'frame_id']

    [DataRetrievalLayer]
    fallback_detector_distance_in_mm = 156
    fallback_beam_energy_in_eV = 20000
    num_of_most_recent_frames_in_event_to_process = 100

    [Crystallography]
    # broadcast_ip =
    # broadcast_port =
    speed_report_interval = 1
    geometry_file = 'pilatus.geom'
    max_saturated_peaks = 1
    min_num_peaks_for_hit = 10
    max_num_peaks_for_hit = 500
    saturation_value = 5000
    running_average_window_size = 20
    geometry_is_optimized = true
    hit_frame_sending_interval = 1
    non_hit_frame_sending_interval = 5

    [DetectorCalibration]
    # calibration_algorithm =
    # calibration_filename =

    [Correction]
    # dark_filename =
    # dark_hdf5_path =

    [Peakfinder8PeakDetection]
    max_num_peaks = 2048
    adc_threshold = 25.0
    minimum_snr = 5
    min_pixel_count = 2
    max_pixel_count = 40
    local_bg_radius = 3
    # bad_pixel_map_filename =
    # bad_pixel_map_hdf5_path =
    min_res = 150
    max_res = 1250

    [DataAccumulator]
    num_events_to_accumulate = 5
