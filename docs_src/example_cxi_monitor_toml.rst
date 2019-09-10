Example *monitor.toml* for the CXI beamline at the LCLS facility
----------------------------------------------------------------

.. code-block:: ini

    [Onda]
    processing_layer = "crystallography"
    data_retrieval_layer = "lcls_cxi"
    required_data = ["detector_data", "beam_energy", "detector_distance", "timestamp"]

    [DataRetrievalLayer]
    psana_detector_name = "DscCsPad"
    psana_detector_distance_epics_name = "CXI:DS1:MMS:06.RBV"
    psana_calibration_directory = "/reg/d/psdm/cxi/cxilt4317/calib"
    num_of_most_recent_frames_in_event_to_process = 1

    [Crystallography]
    # broadcast_ip =
    # broadcast_port =
    geometry_file = "cspad.geom"
    max_saturated_peaks = 10
    min_num_peaks_for_hit = 10
    max_num_peaks_for_hit = 5000
    saturation_value = 14000
    running_average_window_size = 200
    geometry_is_optimized = true
    speed_report_interval = 1
    hit_frame_sending_interval = 1
    non_hit_frame_sending_interval = 20

    [DetectorCalibration]
    # calibration_algorithm =
    # calibration_file =

    [Correction]
    # dark_filename =
    # dark_hdf5_path =

    [Peakfinder8PeakDetection]
    max_num_peaks = 2048
    adc_threshold = 250.0
    minimum_snr = 7.0
    min_pixel_count = 2
    max_pixel_count = 300
    local_bg_radius = 4
    # bad_pixel_map_filename =
    # bad_pixel_map_hdf5_path =
    min_res = 0
    max_res = 900

    [DataAccumulator]
    num_events_to_accumulate = 20
