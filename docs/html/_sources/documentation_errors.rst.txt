OnDA Errors and Warnings
========================

When something does not work as expected, an OnDA monitor usually reports an error.
Errors can be fatal, in which case the monitor stops, or not, in which case the monitor
just reports the error and continues processing data.

OnDA errors are not reported as normal python errors. They are clearly labelled as
coming from the monitor, and their traceback information is removed. The *--debug*
option to  the *onda_monitor.py* script disables this behavior and forces OnDA to
report all errors as normal python errors.

When the *mpi* Parallelization layer is used, OnDA fatal errors are often reported
multiple times before the monitor finishes operating: it can happen that multiple nodes
report the same error before the MPI engine can stop.

A list of the most common errors reported by OnDA follows, with a brief discussion of
each.


OndaConfigurationFileReadingError
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There was a problem finding or reading the configuration file. The file should exist
and be readable. OnDA looks by default for a file called *monitor.toml* in the current
working directory.


OndaConfigurationFileSyntaxError
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There is a syntax error in the configuration file, at the location specified by the
error. The file must follow the  `TOML <https://github.com/toml-lang/toml>`_ syntax.


OndaDataExtractionError
^^^^^^^^^^^^^^^^^^^^^^^

An error has happened during the extraction of data from an event. This error is
usually not fatal and can happen often if the data stream is corrupted. Usually OnDA
skips processing the event and retrieves a new one.


OndaHdf5FileReadingError
^^^^^^^^^^^^^^^^^^^^^^^^

An error has happened while reading an HDF5 file. The file should exists and be
readable.


OndaHidraAPIError
^^^^^^^^^^^^^^^^^

An error has happened during the connection with the HiDRA framework. It is possible
that HiDRA is not running or that the source string provided to OnDA points to the
wrong machine.


OndaInvalidSourceError
^^^^^^^^^^^^^^^^^^^^^^

The format of the source string is not valid. There could be typos in the string or
the format of the string might not match the facility where OnDA is running.


OndaMissingDependencyError
^^^^^^^^^^^^^^^^^^^^^^^^^^

One of the optional python module needed by OnDA is not installed. This error often
happens with python modules that are specific to facility frameworks (for example, the
psana module). One of the core developers should be contacted.


OndaMissingDataExtractionFunctionError
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

One of the Data Extraction Functions is not defined in the Data Retrieval Layer. One
of the core developers should be contacted.


OndaMissingEventHandlingFunctionError
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

One of the Event Handling Functions is not defined in the Data Retrieval Layer. One
of the core developers should be contacted.


OndaMissingHdf5PathError
^^^^^^^^^^^^^^^^^^^^^^^^

An internal path in the HDF5 file is not found. The file exists and can be read, but
the imternal path cannot be found. The internal HDF5 path is probably incorrect, or the
file is corrupted.


OndaMissingParameterError
^^^^^^^^^^^^^^^^^^^^^^^^^

A required parameter is missing from the configuration file.


OndaMissingParameterGroupError
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A parameter group (a section beginning with a string between square brackets - for
example, '[Onda]') is missing from the configuration file.


OndaMissingPsanaInitializationFunctionError
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

One of the psana Detector Interface Initialization Functions is not defined in the Data
Retrieval Layer. One of the core developers should be contacted.


OndaWrongParameterTypeError
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The type of the parameter in the configuration file does not match the requested one.
The type (string, float, int) of the parameter in the configuration file is probably
incorrect. The configuration file ,ust strictly follow the `TOML
<https://github.com/toml-lang/toml>`_ language specification. 
