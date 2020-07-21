OM Errors and Warnings
======================

When something does not work as expected, an OM monitor usually reports an error.
Errors can be fatal, in which case the monitor stops, or not, in which case the monitor
just reports the error and continues processing data.

OM errors are not reported as normal python errors. They are clearly labelled as
coming from the monitor, and their traceback information is removed. The *--debug*
option to  the *om_monitor.py* script disables this behavior and forces OM to
report all errors as normal python errors.

When the *mpi* Parallelization layer is used, OM fatal errors are often reported
multiple times before the monitor finishes operating: it can happen that multiple nodes
report the same error before the MPI engine can stop.

A list of the most common errors reported by OM follows, with a brief discussion of
each.


OmConfigurationFileReadingError
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There was a problem finding or reading the configuration file. The file should exist
and be readable. OM looks by default for a file called *monitor.toml* in the current
working directory.


OmConfigurationFileSyntaxError
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There is a syntax error in the configuration file, at the location specified by the
error. The file must follow the  `YAML 1.2 <https://yaml.org>`_ syntax.


OmDataExtractionError
^^^^^^^^^^^^^^^^^^^^^

An error has happened during the extraction of data from an event. This error is
usually not fatal and can happen often if the data stream is corrupted. Usually OM
skips processing the event and retrieves a new one.


OmHdf5FileReadingError
^^^^^^^^^^^^^^^^^^^^^^

An error has happened while reading an HDF5 file. The file should exists and be
readable.


OmHidraAPIError
^^^^^^^^^^^^^^^

An error has happened during the connection with the HiDRA framework. It is possible
that HiDRA is not running or that the source string provided to OM points to the
wrong machine.


OmInvalidSourceError
^^^^^^^^^^^^^^^^^^^^

The format of the source string is not valid. There could be typos in the string or
the format of the string might not match the facility where OM is running.


OmMissingDependencyError
^^^^^^^^^^^^^^^^^^^^^^^^

One of the optional python module needed by OM is not installed. This error often
happens with python modules that are specific to facility frameworks (for example, the
psana module). One of the core developers should be contacted.


OmMissingDataExtractionFunctionError
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

One of the Data Extraction Functions is not defined in the Data Retrieval Layer. One
of the core developers should be contacted.


OmMissingEventHandlingFunctionError
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

One of the Event Handling Functions is not defined in the Data Retrieval Layer. One
of the core developers should be contacted.


OmMissingHdf5PathError
^^^^^^^^^^^^^^^^^^^^^^

An internal path in the HDF5 file is not found. The file exists and can be read, but
the internal path cannot be found. The internal HDF5 path is probably incorrect, or the
file is corrupted.


OmMissingParameterError
^^^^^^^^^^^^^^^^^^^^^^^

A required parameter is missing from the configuration file.


OmMissingParameterGroupError
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A parameter group (*for data_retrieval_layer:*) is missing from the configuration file.


OmMissingPsanaInitializationFunctionError
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

One of the psana Detector Interface Initialization Functions is not defined in the Data
Retrieval Layer. One of the core developers should be contacted.


OmWrongParameterTypeError
^^^^^^^^^^^^^^^^^^^^^^^^^

The type of the parameter in the configuration file does not match the requested one.
The type (string, float, int) of the parameter in the configuration file is probably
incorrect. The configuration file ,ust strictly follow the `YAML 1.2 
<https://yaml.org>`_ language specification. 
