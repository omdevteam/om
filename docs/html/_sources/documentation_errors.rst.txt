OnDA Errors and Warnings
========================


.. contents::
   :local:





When something does not work as expected, an OnDA monitor can report an error. Errors
can be fatal, in which case the monitor simply exits, or not, in whcih case the monitor
simply reports the error and continues processing data.

OnDA errors are not reported as normal python errors. They are clearly labelled as
coming from the monitor, and their traceback information is removed. The '--debug'
options of the 'onda_monitor.py' script disables this behavior and forces OnDa to
report all errors as normal python errors.

When the *mpi* Parallelization layer is used, OnDA fatal errors are often reported
multiple times before the monitor stops: it can happen that multiple nodes report the
same error before the MPI engine can stop.

A list of the most common errors reported by OnDA follows, with a brief discussion of
each.


OndaConfigurationFileReadingError
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There was a problem finding or reading the configuration file. Please check that the
file exists and is readable. Remember that OnDA looks by default for a file called
'monitor.toml' in the current working directory.


OndaConfigurationFileSyntaxError
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There is a syntax error in the configuration file, where specified by the error. Make
sure that the file follows the  `TOML <https://github.com/toml-lang/toml>`_ syntax.


OndaDataExtractionError
^^^^^^^^^^^^^^^^^^^^^^^

An error has happned during the extraction of data from an event. This error is usualy
not fatal and can happen often if the data stream is corrupted. Usually OnDA skips
processing the event and retrieves a new one.


OndaHdf5FileReadingError
^^^^^^^^^^^^^^^^^^^^^^^^

An error has happened while reading an HDF5 file. Please check that the file exists and
is readable.


OndaHidraAPIError
^^^^^^^^^^^^^^^^^

An error has happened during the connection with the HiDRA framework. Check that HiDRA
is running at that the source string specifies the correct machine.


OndaInvalidSourceError
^^^^^^^^^^^^^^^^^^^^^^

The format of the source string is not valid. Check that there are no typos in the
string and that you are not using a string for a different facility.


OndaMissingDependencyError
^^^^^^^^^^^^^^^^^^^^^^^^^^

One of the optional python module needed by OnDA at some facilities is not installed.
This error often happens with python modules from facility frameworks (for example,
the psana module). Please contact one of the developers.


OndaMissingDataExtractionFunctionError
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

One of the Data Extraction Functions is not defined in the Data Retrieval Layer. Please
contact one of the developers.


OndaMissingEventHandlingFunctionError
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

One of the Event Handling Functions is not defined in the Data Retrieval Layer. Please
contact one of the developers.


OndaMissingHdf5PathError
^^^^^^^^^^^^^^^^^^^^^^^^

An internal path in the HDF5 file is not found. The file exists and can be read, but
the iternal path cannot be found. Please check that the HDF5 path is correct.


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
Retrieval Layer. Please contact one of the developers.


OndaWrongParameterTypeError
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The type of the parameter in the configuration file does not match the requested one.
Check if the type (string, float, int) of the parameter in the configuration file is
correct. 
