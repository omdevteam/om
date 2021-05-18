# OM's Configuration Parameters


This document provides a list of all of OM's configuration parameters, sorted by
parameter group, with a brief description of each.


## correction

This parameter group contains parameters that control how OM applies corrections on
detector data frames using the [`Correction`][om.algorithms.generic.Correction]
algorithm.

**dark_filename (str or None)**
:  The relative or absolute path to an HDF5 file containing a dark data frame. If this
   and the `dark_hdf5_path` parameters are not *None*, the dark data is loaded and
   applied to the detector frame.
   
     Example: `run21_dark.h5`

**dark_hdf5_path (str or None)**
:  The internal HDF5 path to the data block where the dark data frame is located. If
   the `dark_filename` parameter is not *None*, this parameter must also be provided,
   and cannot be *None*. Otherwise it is ignored.
   
     Example: `/data/data`

**gain_filename (str or None)**
:  The relative or absolute path to an HDF5 file containing a gain map. If this and the
   `gain_hdf5_path` parameters are not *None*, the gain map is loaded and applied to
   the detector frame. Each pixel in the gain map must store the gain factor that will
   be applied to the corresponding pixel in the detector frame.

     Example: `files/cspad_gain_map.h5`

**gain_hdf5_path (str or None)**
:  The internal HDF5 path to the data block where the gain map data is located. If the
   `gain_filename` parameter is not *None*, this parameter must also be provided, and
   cannot be *None*. Otherwise it is ignored.
  
     Example: `/data/data`

**mask_filename (str or None)**
:  The relative or absolute path to an HDF5 file containing a mask. If this and the
   `mask_hdf5_path` parameters are not *None*, the mask is loaded and applied to the
   detector frame. The pixels in the mask must have a value of either 0, meaning that
   the corresponding pixel in the detector frame must be set to 0, or 1, meaning that
   the value of the corresponding pixel must be left alone.

     Example: `files/run18_mask.h5`

**mask_hdf5_path (str or None)**
:  The internal HDF5 path to the data block where the mask data is located. If the
   `mask_filename` parameter is not *None*, this parameter must also be provided, and
   cannot be *None*. Otherwise it is ignored.
     
     Example: `/data/data`


## crystallography

This parameter group contains parameters used specifically by the OnDA Monitor for
Crystallography.

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
:  The number of events that must pass between consecutive speed reports from OM. This
   parameter determines how often OM prints the "Processed: ..." message that provides
   information for about the processing speed.
  
     Example: `100`

**data_broadcast_interval (int)**
:  The number of events that must pass between consecutive data broadcasts from OM.
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
  data listed here, a corresponding Data Extraction Function must be defined for the
  Data Event Layer that OM is currently using. If this condition is met, the data will
  be retrieved by OM and made available for processing, otherwise an error will be
  raised an OM will stop running. For a list of Data Extraction Functions that are
  available for each Data Event Handler, please see the following document:

    * [List of Data Extraction Functions available for each Data Event Handler](data_extraction_functions.md)

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
* `JungFrau1MDataEventHandler`

**calibration(bool)**
:  Whether to calibrate the retrieved  x-ray detector data or not. When reading from
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
     * `Rayonix`

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
