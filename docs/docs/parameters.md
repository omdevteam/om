# OM's Configuration Parameters


This document provides a list of all of OM's configuration parameters, sorted by
parameter group, with a brief description of each.


## binning

This parameter group contains parameters that control how OM performs binning of a
detector data frame using the [`Binning`][om.algorithms.generic.Binning] algorithm.

**bad_pixel_map_filename (str or None)**
:  The absolute or relative path to an HDF5 file containing a bad pixel map. The map is
   used to mark areas of the data frame that must be excluded from the calculation of
   the binned detector image. Each pixel in the map must have a value of either 0,
   meaning that the corresponding pixel in the data frame must be ignored, or 1,
   meaning that the corresponding pixel must be included in the calculation. 
   If the value of these parameter is *None*, no area is excluded from the calculation.

     Example: `bad_pixel_mask.h5`
  
**bad_pixel_map_hdf5_path (str or None)**
:  The internal HDF5 path to the data block where the bad pixel map is stored. If the
   value of the `bad_pixel_map_filename` parameter is not *None*, this parameter must
   also be provided, and cannot be *None*. Otherwise it is ignored.

     Example: `/data/data`

**bad_pixel_value**
:  The value written in the pixels of the binned detector image which are considered
   "bad". A pixel of the binned image is considered "bad" if the number of "good"
   pixels (pixels where the bad pixel map value is 1) in the original bin is lower than
   `min_good_pix_count`.

     Example: `-1`

**bin_size**
:  The bin size in pixels.

     Example: `2`

**detector_type (str)**
:  The type of detector on which the binning algorithm will be applied. The detector
   types currently supported are:

     * `cspad`
     * `pilatus`
     * `jungfrau1M`
     * `jungfrau4M`
     * `epix10k2M`
     * `rayonix`

     Example: `eiger16M`

**min_good_pix_count**
:  The minimum number of "good" pixels (pixels where the bad pixel map value is 1) in
   the bin required for the resulting pixel of the binned image to be considered
   "good". The default vaule of this parameter is `bin_size` squared, i.e. all the
   pixels in the bin must be "good" for the resulting pixel of the binned image to be
   considered "good" by default. 

     Example: `3`


## cheetah

This parameter group contains parameters that control the behavior of the Cheetah
software package.

**class_sum_filename_prefix (str or None)**
:  A string that will be prepended to the name of the output files. If the value of
   this argument is *None*, the string `processed_` will be used as prefix.

     Example: `run0001`

**class_sums_sending_interval (int or None)**
:  This parameter determines how often processing nodes send accumulated class sums to
   the collecting node. If the value of this parameter is *None*, no class sums are ever
   sent. If the value is a number, it is the number of frames that *each processing
   node* sums up before sending the accumulated sums to the collecting node to be saved
   in the class sum HDF5 files.

     Example: `100`

**class_sums_update_interval (int)**
:  This parameter determines how often collecting node writes class sums to the output
   files. This parameter is considered only if `write_class_sums` parameter is *True*.
   The value is the number of times collecting node receives accumulated sums of
   frames from the processing nodes before writing them to files. For example, if the
   value of this parameter is 5 and the value of `class_sums_sending_interval` is 100,
   the collecting node updates the written files every 5 times it receives the
   accumulated sum of 100 frames from the processing nodes (i.e. every 500 processed
   frames).

     Example: `5`

**hdf5_fields (dict)**
:  A dictionary storing information about the internal HDF5 path where each data entry
   will be written.
  
   * The keys in the dictionary must store the names of data entries to
     write.
   * The corresponding dictionary values must contain the internal HDF5
     paths where the entries will be written.

     Example:

     ```
     detector_data: "/data/data"
     event_id: "/data/event_id"
     beam_energy: "/data/photon_energy_eV"
     detector_distance: "/data/detector_distance"
     timestamp: "/data/timestamp"
     peak_list: "/data/peaks"
     ```
     
     Example for `.cxi` files (compatible with 
     [cxiview](https://www.desy.de/~barty/cheetah/Cheetah/cxiview.html)):

     ```
     detector_data: "/entry_1/data_1/data"
     event_id: "/LCLS/fiducial"
     beam_energy: "/LCLS/photon_energy_eV"
     detector_distance: "/LCLS/detector_1/EncoderValue"
     timestamp: "/LCLS/timestamp"
     peak_list: "/entry_1/result_1"
     pixel_size: "/entry_1/instrument_1/detector_1/x_pixel_size"
     ```

**hdf5_file_compression (str or None)**
:  Compression filter to be applied to the data in the output file. If the value of
   this parameter is *None*, no compression is applied. The value of this parameter is
   ...ed to the 
   [h5py.Group.create_dataset](https://docs.h5py.org/en/stable/high/group.html#h5py.Group.create_dataset).
   function of the `h5py` python module. For a list of available compression filters
   please see
   [h5py documentation](https://docs.h5py.org/en/stable/high/dataset.html#lossless-compression-filters).

     Example: `gzip`

**hdf5_file_compression_opts (int or None)**
:  The compression level to be used if data compression is applied. This parameter is
   considered only if the `hdf5_file_compression` parameter is not *None*. If the value
   of this parameter is *None*, the compression level will be set to 4. The value of
   this parameter is ...ed to [h5py.Group.create_dataset](https://docs.h5py.org/en/stable/high/group.html#h5py.Group.create_dataset).

     Example: `6`

**hdf5_file_compression_shuffle (bool or None)**
:  Whether the shuffle filter is applied. If the value of this parameter is *None* the
   shuffle filter is not applied. The value of this parameter is ...ed to the
   [h5py.Group.create_dataset](https://docs.h5py.org/en/stable/high/group.html#h5py.Group.create_dataset).
   function of the `h5py` python module. For a list of available compression filters
   please see
   [h5py documentation](https://docs.h5py.org/en/stable/high/dataset.html#lossless-compression-filters).
  
     Example: `true`

**hdf5_file_data_type (str or None)**
:  The numpy type of the detector data that will be written to the output files. If the
   value of this parameter is *None*, the data is written in `float32`.

     Example: `int16`

**hdf5_file_max_num_peaks (int or None)**
:  The maximum number of detected Bragg peaks that should be written in the HDF5 file
   for each frame. Optional. If the value of this parameter is *None*, only the first
   1024 detected peaks will be written in the output file for each frame.

     Example: `2000`

**processed_directory (str)**
:  A relative or absolute path to the directory where the output files with the
   processed data will be written.

     Example: `/experiment/data/processed/`

**processed_filename_extension (str or None)**
:  A extension string that is appended to the name of the output files. If the value of
   this argument is *None*, the string `h5` is used as extension.

     Example: `cxi`

**processed_filename_prefix (str or None)**
:  A string that is prepended to the name of the output files. If the value of this
   argument is *None*, the string `processed_` is used as prefix.

     Example: `run0001`

**status_file_update_interval (int or None)**
:  This parameter determines how often the collecting node updates the `status.txt`,
   file which [Cheetah GUI](https://www.desy.de/~barty/cheetah/Cheetah/GUI.html) can
   inspect to determine the advancement of the processing work. If the value of this
   parameter is *None*, the `status.txt` file will not be written.

     Example: `100`

**write_class_sums (bool)**
:  Whether class sum HDF5 files will be written. Class sum files contain sums of
   detector data frames belonging to different powder classes (typically, class `0`
   for non-hits and  class `1` for hits). Additionally, the files contain the
   corresponding virtual powder patterns. They can be inspected in the
   [Cheetah GUI](https://www.desy.de/~barty/cheetah/Cheetah/GUI.html) while data
   is still being processed by Cheetah.

     Example: `true`


## crystallography

This parameter group contains parameters used specifically by the OnDA Monitor for
Crystallography.

**binning**
:  Whether to apply pixel binning to the detector data or not.

     Example: `true`

**binning_before_peakfinding**
:  Whether detector data should be binned before the Bragg peak search or after. If the
   value of the `binning` parameter is *False* this parameter will be ignored.

     Example: `false`

**data_broadcast_url (str or None)**
:  The URL of the socket where OM broadcasts data to external programs. The parameter
   should have the format `tcp://hostname:port` or the format `ipc:///path/to/socket`,
   depending on the protocol used for the broadcast. If the value of this parameter is
   *None*, the TCP protocol is used by default, the IP address of the host is detected
   automatically and the broadcast URL is set to `tcp://<IP_ADDRESS>:12321`.

     Example: `tcp://127.0.0.1:8080`

**geometry_file (str)**
:  The absolute or relative path to a geometry file in
   [CrystFEL format](http://www.desy.de/~twhite/crystfel/manual-crystfel_geometry.html).

     Example: `files/pilatus.geom`

**geometry_is_optimized (bool)**
:  Whether the detector geometry is optimized. This information is broadcast by the
   monitor and  can be used by external programs. For example, the Crystallography GUI
   uses this information to decide if the resolution rings should be displayed or not
   (if the geometry is not optimized, the rings are not reliable).

     Example: `false`

**hit_frame_sending_interval (int or None)**
:  This parameter determines how often the monitor sends *full detector frames*  (as
   opposed to reduced data) to external programs. It only applies to frames that have
   not been labelled as hits. If the value of this parameter is *None*, no hit frames
   are ever sent. If the value is a number, it is the number of hit frames that
   *each processing node* skips before sending the next frame to the collecting node to
   be broadcast. If, for example, the value of this parameter is 5, each processing
   node sends every 5th hit frame to the collecting node for broadcasting.

     Example: `10`

**max_num_peaks_for_hit (int)**
:  The maximum number of Bragg peaks that must be found in a detector frame for the
   frame to be labelled as a hit.

     Example: `500`

**min_num_peaks_for_hit (int)**
:  The minimum number of Bragg peaks that need to be found in a detector frame for the
   frame to be labelled as a hit.

     Example: `10`

**non_hit_frame_sending_interval (int or None)**
:  This parameter determines how often the monitor sends *full detector frames*  (as
   opposed to reduced data) to external programs. It only applies to frames that have
   not been labelled as hits. If the value of this parameter is *None*, no non-hit
   frames are ever sent. If value is a number, it is the number of non-hit frames that
   *each processing node* skips before sending the next frame to the collecting node to
   be broadcast. If, for example, the value of this parameter is 100, each processing
   node sends every 100th non-hit frame to the collecting node for broadcasting.

     Example: `1000`

**running_average_window_size (int)**
:  The size of the running window used by the monitor to compute the average hit rate
 . OM computes the average rate over the number of most recent events specified by this
   parameter.

     Example: `100`

**speed_report_interval (int)**
:  The number of events that must ... between consecutive speed reports from OM. This
   parameter determines how often OM prints the "Processed: ..." message that provides
   information for about the processing speed.
  
     Example: `100`

**data_broadcast_interval (int)**
:  The number of events that must ... between consecutive data broadcasts from OM.
   This parameter determines how often OM sends data to external programs. It should
   not be set to a value that is too low: if data is transferred too frequently, the
   network bandwidth could be saturated and OM could interfere with other running
   applications.

     Example: `120`



## data_retrieval_layer

This parameter group contains parameters that control OM's Data Retrieval Layer,
influencing the way OM retrieves data events from the data source (a file, a facility
framework, etc.). Please note that some parameters apply to all Data Event Handlers,
while others only apply to a subset of Handlers, or have different meaning for
different Handlers.


!!! warning
    Please exercise caution when changing the values of the parameters in this group: a
    wrong choice can severely impact data retrieval and result in OM not working
    correctly.


### All Data Event Handlers

The parameters in this subsection apply to all Data Event Handlers

**required_data (List[str])**
: The data that the current monitor should retrieve for each event. For each type of
  data listed here, an extraction function must be available for the Data Event Handler
  that OM is currently using. If this condition is met, the data will be retrieved
  and made available for processing, otherwise an error will be raised an OM will stop
  running. For a list of all data types that each Data Event Handler can currently
  retrieve, please see the following document:

    * [List of data types available for each Data Event Handler](data.md)

    Example: [detector_data, detector_distance, beam_energy, timestamp]


### Psana-based Data Event Handlers

The parameters in this section apply only to the psana-based Data Event Handlers,
specifically:

  * `CxiLclsDataEventHandler`
  * `CxiLclsCspadDataEventHandler`
  * `MfxLclsDataEventHandler`
  * `MfxLclsRayonixDataEventHandler`

**active_optical_laser_evr_code (int)**
:  EVR event code corresponding to an active optical laser. To determine if the optical
   laser is active, OM checks if the code provided by this parameter matches one
   of the EVR event codes associated with the current event.

     Example: `92`

**active_xray_evr_code (int)**
:  EVR event code corresponding to the x-rays being active. To determine if the x-rays
   are active, OM checks if the code provided by this parameter matches one of the
   EVR event codes associated with the current event.

     Example: `42`

**calibration (bool)** 
:  Whether to retrieve calibrated or non calibrated x-ray detector data from psana.
   This parameter switches on and off the internal calibration provided by psana.

     Example: `true`

**psana_calibration_directory (str)**
:  The path to the directory where psana stores all calibration information for the
   current experiment.

     Example: `/reg/d/psdm/mfx/mfxc00118/calib`

**psana_detector_name (str)**
:  The name of the main x-ray detector from which psana retrieves data.

     Example: `DscCsPad`

**psana_detector_distance_epics_name (str)**
:  The name of the Epics variable from which psana retrieves detector distance
   information for the main x-ray detector.

     Example: `CXI:DS1:MMS:06.RBV`

**psana_digitizer_name (str)**
:  The name of the main digitizer device from which psana retrieves information.

     Example: `Acqiris`

**psana_evr_source_name (str)**
:  The name of the EVR source from which psana retrieves information.

     Example: `evr0`

**psana_opal_name (str)**
:  The name of the Opal camera from which psana retrieves information.

     Example: `Opal1`

**psana_timetool_epics_name (str)**
:  The name of the Epics variable from which psana retrieves timetool information.

    Example: `CXI:DS1:MMS:06.RBV`


### Filesystem-based Data Event Handlers

The parameters in this section apply only to the file-based Data Event Handlers, and
specifically to the following Handlers:

* `PilatusFilesDataEventHandler`
* `Jungfrau1MFilseDataEventHandler`
* `Eiger16MFilesDataEventHandler`

**calibration(bool)**
:  Whether to calibrate the retrieved x-ray detector data or not. When reading from
   files, the calibration of the detector data is usually performed by OM. OM often
   needs external information to perform the calibration, and retrieves it from a set
   of files defined by the `calibration_dark_filenames` and
   `calibration_gain_filenames` parameters. In some cases, additional parameters (for
   example `calibration_photon_energy_kev`) must also be provided to further define the
   calibration process.
   
     Example: `true`

**calibration_dark_filenames (Union[str, List[str]])**
:  File or list of files containing dark frame information for the calibration of x-ray
   detector data. If dark frame information is needed by the detector being calibrated,
   OM will read the information from the files specified by this parameter. If,
   however, the calibration is not performed or if the Data Event Handler does not need
   dark frame information for the calibration, this parameter is ignored.

     Example: `dark_info.h5` or `[dark_info_panel0.h5, dark_info_panel1.h5]`

**calibration_gain_filenames (Union[str, List[str]])**
:  File or list of files containing gain information for the calibration of x-ray
   detector data. If gain information is needed by the detector being calibrated, OM
   will read the information from the files specified by this parameter. If,
   however, the calibration is not performed or if the Data Event Handler does not need
   gain information for the calibration, this parameter is ignored.

     Example: `gain_info.h5` or `[gain_info_panel0.h5, gain_info_panel1.h5]`

**calibration_photon_energy_kev (float)**
:  The photon energy for which the x-ray detector data should be calibrated.
   The exact values of the calibration constants for a detector often depend on the
   photon energy at which the detector is operated. If a calibration algorithm needs
   this information, OM will take the value provided by this parameter.  If, however,
   the calibration is not performed or if the Data Event Handler does not need this
   kind of information for the calibration, this parameter is ignored.

     Example: `9.1`

**fallback_beam_energy_in_eV (float)**
:  The beam energy *in eV*. OM uses this fallback value when the the relevant
   information is not present in the data files.
  
     Example: `12000`

**fallback_detector_distance_in_mm (float)**
:  The detector distance *in mm*. OM uses this fallback value when the the relevant
   information is not present in the data files.

     Example: `250`

**num_frames_in_event_to_process (int)**
:  The number of frames in an event that OM should process. Sometimes data events
   contain multiple frames but OM does not need to process them all. This parameter
   specifies how many frames OM should consider. Please note that OM will give
   precedence to the frames in the event that were collected more recently. If, for
   example, this parameter specifies that OM should process n frames, OM will process
   the *last* n frames in the event.

     Example: `1`


## om

!!! warning
    This section determines the core behavior of the OM monitor. The value of these
    parameters should be changed only by an expert. A wrong parameter choice is likely
    to leave OM in a non-working state.

**data_event_handler (str)**
:  The name of the class implementing the Data Event Handler currently used by OM. The
   class should be defined in the Data Retrieval Layer module file specified by the
   `data_retrieval_layer` parameter in this group.

     Example: `MfxLclsDataEventHandler`

**data_retrieval_layer (str)**
:  The name of the python module with the implementation of the Data Retrieval Layer
   currently used by OM.

     Example: `data_handlers_psana`

**monitor (str)**
:  The name of the class implementing the Monitor currently used by OM. The class
   should be defined in the Processing Layer module file specified by the
   `processing_layer` parameter in this group.

     Example: `Crystallography`

**parallelization_engine (str)**
:  The name of the class implementing the Parallelization Engine currently used by OM.
   The class should be defined in the Parallelization Layer module file specified by
   the `parallelization_layer` parameter in this group.

     Example: `MpiParallelizationEngine`

**parallelization_layer (str)**
:  The name of the python module with the implementation of the Parallelization Layer
   currently used by OM.

     Example: `mpi`

**processing_layer (str)**
:  The name of the python module with the implementation of the Processing Layer
   currently used by OM.

     Example: `crystallography`


## peakfinder8_peak_detection

This parameter group contains parameters that control how OM performs peak finding on a
detector data frame using the
[`Peakfinder8PeakDetection`][om.algorithms.crystallography.Peakfinder8PeakDetection]
algorithm.

**adc_threshold (float)**
:  The minimum ADC threshold for peak detection.

     Example: `200`

**bad_pixel_map_filename (str or None)**
:  The absolute or relative path to an HDF5 file containing a bad pixel map. The map is
   used to mark areas of the data frame that must be excluded from the peak search.
   Each pixel in the map must have a value of either 0, meaning that the corresponding
   pixel in the data frame must be ignored, or 1, meaning that the corresponding pixel
   must be included in the search. The map is only used to exclude areas from the peak
   search: the data is not modified in any way. If the value of these parameter is
   *None*, no area is excluded from the peak search.

     Example: `bad_pixel_mask.h5`
  
**bad_pixel_map_hdf5_path (str or None)**
:  The internal HDF5 path to the data block where the bad pixel map is stored. If the
   value of the `bad_pixel_map_filename` parameter is not *None*, this parameter must
   also be provided, and cannot be *None*. Otherwise it is ignored.

     Example: `/data/data`

**detector_type (str)**
:  The type of detector on which the peak finding algorithm will be applied. The
   detector types currently supported are:

     * `cspad`
     * `pilatus`
     * `jungfrau1M`
     * `jungfrau4M`
     * `epix10k2M`
     * `rayonix`
     * `eiger16M`

     Example: `cspad` 

**max_num_peaks (int)**
:  The maximum number of peaks that will be retrieved from each detector data frame.
   Additional peaks will be ignored.

     Example: `2048`

**local_bg_radius (int)**
:  The radius (in pixels) for the estimation of the local background.

     Example: `3`

**max_pixel_count (int)**
:  The maximum size of a peak in pixels.

    Example: `10`

**max_res (int)**
:  The maximum resolution (in pixels) at which a peak will be found.

    Example: `800`

**min_pixel_count (int)**
:  The minimum size of a peak in pixels.

     Example: `1`

**minimum_snr (float)**
:  The minimum signal-to-noise ratio for peak detection.
  
     Example: `5.0`

**min_res (int):**
:  The minimum resolution for a peak in pixels.

     Example: `20`
