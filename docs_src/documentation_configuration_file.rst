The Configuration File
----------------------

The behaviour of an OnDA monitor is completely determined by the content of its
configuration file. By default, OnDA looks for a file called **monitor.toml** in the
current working directory. However, the *--config* command line option to the
*onda_monitor.py* script allows a custom location for the configuration file to be
specified.

.. code-block:: bash

    onda_monitor.py --config PATH_TO_CONFIG_FILE SOURCE_STRING

The content of the configuration file must formatted according to the rules of the 
`TOML <https://github.com/toml-lang/toml>`_ language. This language is not very
different from the one traditionally used by Python's  *ini* files. The main
differences are:

* Strings (including file and directory paths) must be always enclosed within single or
  double quotes (' or ").

* The *True* and *False* keywords are spelled without a capital first letter (*true*
  and *false* respectively)

* There is no *None* value. To set a parameter value to *None*, the parameter must
  be commented out or completely omitted from the configuration file.

The parameters in the configuration file are divided into groups (*Tables* in TOML
parlance). Each group contains a set of parameters that are related to each other
(maybe because they apply to the same OnDA algorithm, or because they control the same
feature of the monitor). For example:

.. code-block:: ini

    [General]
    broadcast_ip = '127.0.0.1'
    broadcast_port = 12321
    speed_report_interval = 1000

The following is an alphabetical list of the parameter groups that can be found in the
configuration file. Depending on which OnDA monitor is being run, not all the groups
need to be present in the file at the same time. Conversely, custom OnDA monitors might
introduce additional groups not described here. For each group, a list of the available
parameters is provided. While some parameters are strictly required and must be
explicitely set (again depending on the type of OnDA monitor), others are optional, and
OnDA chooses a value for them if they cannot be found in the file. In general the
default value of an unspecified optional paramerer is considered to be *None*.


.. warning::

   When a parameter is a physical constant, it is assumed to be expressed in SI units
   unless the parameter name says otherwise!!


[Correction]
^^^^^^^^^^^^

This parameter group contains information used by OnDA for the correction of detector
frames (using the :class:`Correction <onda.algorithms.generic_algorithms.Correction>`
algorithm).

* **dark_filename (str or None):** the relative or absolute path to an HDF5 file
  containing a dark data frame. Defaults to *None*. If this and the *dark_hdf5_path*
  parameters are not *None*, the dark data is loaded and later applied to the detector 
  frame. Example: 'run21_dark.h5'

* **dark_hdf5_path (str or None):** the internal HDF5 path to the data block where the
  dark data frame is located. If the *dark_filename* parameter is not *None*, this
  parameter must also be provided, and cannot be *None*. Otherwise it is ignored.
  Example: '/data/data'

* **gain_filename (str or None):** the relative or absolute path to an HDF5 file
  containing a gain map. If this and the *gain_hdf5_path* parameters are not *None*,
  the gain map is loaded and later applied to the detector frame. Each pixel in the
  gain map must store the gain factor that will be applied to the corresponing pixel in
  the detector frame. Example: 'cspad_gain_map.h5'

* **gain_hdf5_path (str or None)** the internal HDF5 path to the data block where the
  gain map data is located. If the *gain_filename* parameter is not *None*, this
  parameter must also be provided, and cannot be *None*. Otherwise it is ignored.
  Example: '/data/data'

* **mask_filename (str or None):** the relative or absolute path to an HDF5 file
  containing a mask. If this and the *mask_hdf5_path* arguments are not *None*, the
  mask is loaded and later applied to the detector frame. The pixels in the mask must
  have a value of either 0, meaning that the corresponfing pixel in the detector frame
  must be set to 0, or 1, meaning that the value of the corresponding pixel must be
  left alone. Example: 'run18_mask.h5'

* **mask_hdf5_path (str or None):** the internal HDF5 path to the data block where the
  mask data is located. If the *mask_filename* parameter is not *None*, this parameter
  must also be provided, and cannot be *None*. Otherwise it is ignored.
  Example: '/data/data'


[Crystallography]
^^^^^^^^^^^^^^^^^

This group contains parameters used by the OnDA Monitor for Crystallography.

* **broadcast_ip (str or None):** the hostname or ip address where the monitor
  broadcasts data to external programs. If the value of this parameter is *None*, the
  ip address is autodetected. This is usually fine. An ip address or ahostname needs
  usually to be manually specified only in exceptional cases (e.g: multiple network
  interfaces on the same machine). Example: '127.0.0.1'

* **broadcast_port (int or None):** the port where the monitor broadcasts data to
  external programs. If the value of this parameter is *None*, port 12321 is used. 
  Example: 12322

* **geometry_file (str):** the absolute or relative path to a geometry file in
  `CrystFEL <http://www.desy.de/~twhite/crystfel/manual-crystfel_geometry.html>`_
  format. Example: 'pilatus.geom'.

* **geometry_is_optimized (bool):** whether the geometry is optimized. This information
  is broadcasted by the monitor and used by external programs. For example, the OnDA
  GUI for Crystallography uses this information to decide if the drawing of
  resolution rings should be allowed or not (if the geometry is not optimized, the
  rings are not reliable). Example: false.

* **hit_frame_sending_interval (int or None):** this parameter determines how often the
  monitor sends *full detector frames* to external programs (as opposed to reduced
  data). It applies only to frames labelled as hits. If the value of this parameter is
  *None*, no hit frames are ever sent. If the value is a number, it is the number of
  hit frames that *each worker* skips before sending the next frame to the master node
  to be broadcasted. If, for example, the value of this parameter is 5, each worker
  sends every 5th hit frame to the master for broadcasting. Example: 10

* **max_num_peaks_for_hit (int):** the maximum number of Bragg peaks that can be found
  in a detector frame for the frame to be labelled as a hit. Example: 500.

* **max_saturated_peaks (int):** the maximum number of saturated Bragg peaks that can
  be found in a detector frame before the frame itself is labelled as saturated. A
  saturated Bragg peak is a peak whose integrated intensity (in ADUs) goes beyond the
  value specified by the *saturation_value* parameter in this same group.

* **min_num_peaks_for_hit (int):** the minimum number of Bragg peaks that need to be
  found in a detector frame for the frame to be labelled as a hit. Example: 10

* **non_hit_frame_sending_interval (int or None):** this parameter determines how often
  the monitor sends *full detector frames* to external programs (as opposed to reduced
  data). It applies only to frames that have not been labelled as hits. If the value of
  this parameter is *None*, no non-hit frames are ever sent. If value is a number, it
  is the number of non-hit frames that *each worker* skips before sending the next
  frame to the master node to be broadcasted. If, for example, the value of this
  parameter is 100, each worker sends every 100th non-hit frame to the master for
  broadcasting. Example: 1000

* **running_average_window_size (int):** the size of the running window used by the
  monitor to compute the average hit and saturation rates. The rates are computed
  over the number of most recent events specified by this parameter. Example: 100.

* **saturation_value (float):** the minimum value (in ADUs) of the integrated intensity
  of a Bragg peak for the peak to be labelled as saturated. The value of this parameter
  usually depends on the specific detector being used. Example: 5000.5.

* **speed_report_interval (int):** the number of events that must pass between
  consecutive speed reports from OnDA. This parameter determines how often OnDA prints
  the "Processed: ..: message that provides information for about the processing speed.
  Exaple: 100


[DataAccumulator]
^^^^^^^^^^^^^^^^^

This group contains a parameter that dictates how OnDA aggregates events in the master
node before sending them to external programs. It refers to the :class:`DataAccumulator
<onda.algorithms.generic_algorithms.DataAccumulator>` algorithm.

* **num_events_to_accumulate (int):** number of events for which data is accumulated in
  the master node. The master node broadcasts the accumulated data in a single
  transmission, then starts accumulating data again.  Example: 20


[DataRetrievalLayer]
^^^^^^^^^^^^^^^^^^^^

This parameter group contains information that determines how the Data Retrieval Layer
extracts data from a facility framework.


.. warning::

   Please exercise caution when changing the parameters in this group: a wrong choice
   can severly interfere with data retrieval and extraction.


* **fallback_beam_energy_in_eV (float)** the beam energy *in eV*. OnDA uses this
  fallback value when the framework does not provide beam energy information.
  Example: 12000

* **fallback_detector_distance_in_mm (float)** the detector distance *in mm*. OnDA
  uses this fallback value when the framework does not provide detector distance
  information. Example: 250

* **hidra_base_port (int):** the base port used by the HiDRA framework to send data
  to the worker nodes. HiDRA will use this port and the following ones (one per node)
  to contact the workers. The machine where OnDA is running and the one where HiDRA is
  running should be able to reach each other at this port and the immediately following
  ones. Example: 52000

* **hidra_transfer_type ('data' or 'metadata'):** the transfer type used by the HiDRA
  framework for the current monitor. If this parameter has a value of *'data'*, OnDA
  asks HiDRA to stream the detector data to the monitor. If instead the value is
  *'metadata'*, OnDA asks HiDRA to just stream information on where in the filesystem
  the most recent data can be found. Usually it is automatically determined from the
  detector(s) model currently used by the monitor, but it can be overridden using
  this parameter. Example: 'data'

* **karabo_detector_label (str):** the label of the main x-ray detector from which 
  the Karabo framework retrieves data. Example:
  'SPB_DET_AGIPD1M-1/CAL/APPEND_CORRECTED'

* **karabo_max_event_age (float or None):** the maximum age (in seconds) that a data
  event retrieved from Karabo must have in order to be processed. If the age of the
  event, defined as the time between data collection and the retrieval of the event by
  OnDA, is higher than this threshold, the event is not processed and a new event is
  retrieved. If the value of this parameter is *None*, all events are processed.
  Example: 0.5

* **num_of_most_recent_frames_in_event_to_process (int or None):** number of frames for
  each event to process. It should be noted that these are the *most recent* events: if
  the value of this paramerer is, for example, *100*, only the *last* 100 frames in the
  event are processed. If the value of this parameter is *None*, all frames in the
  event are processed. Example: 0.5

* **psana_detector_name (str):** * **karabo_detector_label (str):** the name of the
  main x-ray detector from which the psana framework retrieves data. Example:
  'DscCsPad'

* **psana_detector_distance_epics_name (str):** the name of the Epics device from which
  the psana framework retrieves detector distance information for the main x-ray
  detector. Example: 'CXI:DS1:MMS:06.RBV'

* **psana_digitizers_name (str):** the name of the main digitizer device from which
  the psana framework retrieves information.

* **psana_evr_source (str):** name of the EVR source from which the psana framework
  retrieves information.

* **psana_opal_name (str):** the name of the Opal camera from which the psana framework
  retrieves information.

* **psana_timetool_epics_name (str):** the name of the Epics device from which
  the psana framework retrieves timetool information.

* **psana_max_event_age (float or None):** the maximum age (in seconds) that a data
  event retrieved from psana must have in order to be processed. If the age of the
  event, defined as the time between data collection and the retrieval of the event by
  OnDA, is higher than this threshold, the event is not processed and a new event is
  retrieved. If the value of this parameter is *None*, all events are processed.
  Example: 0.5


[DetectorCalibration]
^^^^^^^^^^^^^^^^^^^^^

This parameter group contains information used by OnDA for the calibration of
detector frames, using one of the calibration algorithms defined
:doc:`here <onda.algorithms.calibration_algorithms>`.

* **calibration_algorithm (str or None):** the name of the calibration algorithm that
  the current monitor should use to calibrate the detector frames. The value of this
  parameter  must match one of the names of the calibration algorithms (or be *None*).
  If the value is *None*, no calibration will be performed.
  Example: 'Agipd1MCalibration'

* **calibration_filename (str or None):** absolute or relative path to an HDF5 file
  containing the calibration parameters. The exact format of this file depends on the
  calibration algorithm being used. Please consult the documentation for the specific
  algorithm. If no calibration is performed, this parameter is ignored. Example:
  'agipd_calibration_params.h5'


[Onda]
^^^^^^

.. DANGER::

   !! This section determines the core behavior of the OnDA monitor. The value of
   these parameters should be changed only by an expert !!

* **data_retrieval_layer (str):** name of the python module with the implementation of
  the Data Retreival Layer for the current monitor. Example: 'lcls_spb'

* **paralelization_layer (str):** name of the python module with the implementation of
  the Parallelization Layer for the current monitor. Example: 'mpi'

* **processing_layer (str):** name of the python module with the implementation of the
  Processing Layer for the current monitor. Example: 'crystallography'

* **required_data (List[str]):** data that the current monitor should retrieve for
  each event. For each type of data, a corresponding Data Extraction Function must be
  defined in the Data Retrieval Layer. If this condition is met, the extracted data
  will be available in the 'data' object in the Processing layer.
  Example: ['detector_data', 'detector_distance', 'beam_energy','timestamp']


[Peakfinder8PeakDetection]
^^^^^^^^^^^^^^^^^^^^^^^^^^

This parameter group contains parameters used by the OnDA monitor to perform Bragg peak
finding on a detector frame, using the (using the :class:`Peakfinder8PeakDetection\ 
<onda.algorithms.crystallography_algorithms.Peakfinder8PeakDetection>` algorithm).

* **adc_threshold (float):** the minimum ADC threshold for peak detection. Example: 200

* **bad_pixel_map_filename (str or None):** the absolute or relative path to an HDF5
  file containing a bad pixel map. The map is used mark areas of the data frame that
  must be excluded from the peak search. Each pixel in the map must have a value of
  either 0, meaning that the corresponding pixel in the data frame must be ignored, or
  1, meaning that the corresponding pixel must be included in the search. The map is
  only used to exclude areas from the peak search: the data is not modified in any way.
  if the value of these parameter is *None*, no area is excluded from the peak search.
  Example: 'bad_pixel_mask.h5'
  
* **bad_pixel_map_hdf5_path (str or None):** the internal HDF5 path to the data block
  where the bad pixel map is stored. If the value of the *bad_pixel_map_filename*
  parameter is not *None*, this parameter must also be provided, and cannot be *None*.
  Example: '/data/data'

* **max_num_peaks (int):** the maximum number of peaks that will be retrieved from each
  detector data frame. Additional peaks will be ignored. Example: 2048

* **local_bg_radius (int):** the radius (in pixels) for the estimation of the local
  background. Example: 3

* **max_pixel_count (int):** the maximum size of a peak in pixels. Example: 10

* **max_res (int):** the maximum resolution (in pixels) at which a peak will be found.
  Example: 800

* **min_pixel_count (int):** the minimum size of a peak in pixels. Example: 1

* **minimum_snr (float):** the minimum signal-to-noise ratio for peak detection.
  Example: 5.0

* **min_res (int):** the minimum resolution for a peak in pixels. Example: 20

