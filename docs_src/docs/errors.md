# OM's Errors And Warnings


A list of the most common errors reported by OM, with a brief discussion of each one.


`OmConfigurationFileReadingError`
:  There was a problem finding or reading the configuration file. The file should exist
   and be readable. OM looks by default for a file called *monitor.toml* in the current
   working directory.


`OmConfigurationFileSyntaxError`
:  There is a syntax error in the configuration file, at the location specified by the
   error. The file must follow the [YAML 1.2](https://yaml.org) syntax.


`OmDataExtractionError`
:  An error has happened during the extraction of data from an event. This error is
   usually not fatal and can happen often if the data stream is corrupted. Usually OM
   skips processing the event and retrieves a new one.


`OmHdf5FileReadingError`
:  An error has happened while reading an HDF5 file. The file should exists and be
   readable.


`OmHidraAPIError`
:  An error has happened during the connection with the HiDRA framework. It is possible
  that HiDRA is not running or that the source string provided to OM points to the
  wrong machine.


`OmInvalidDataBroadcastUrl`
:  The format of the provided data broadcasting URL (the parameter *data_broadcast_url*
   in the *crystallography* section of the configuration file) is not valid. The URL
   must be in a format accepted by the ZeroMQ library. If the ipc protocol is used with
   ZeroMQ, the user running OM must additionally have the correct permissions to access
   the ipc socket.


`OmInvalidSourceError`
:  The format of the source string is not valid. There could be typos in the string or
   the format of the string might not match the facility where OM is running.


`OmMissingDependencyError`
:  One of the optional python module needed by OM is not installed. This error often
   happens with python modules that are specific to facility frameworks (for example,
   the psana module). One of the core developers should be contacted.


`OmMissingDataExtractionFunctionError`
:  One of the Data Extraction Functions is not defined in the Data Retrieval Layer. One
   of the core developers should be contacted.


`OmMissingEventHandlingFunctionError`
:  One of the Event Handling Functions is not defined in the Data Retrieval Layer. One
   of the core developers should be contacted.


`OmMissingHdf5PathError`
:  An internal path in the HDF5 file is not found. The file exists and can be read, but
   the internal path cannot be found. The internal HDF5 path is probably incorrect, or
   the file is corrupted.


`OmMissingParameterError`
:  A required parameter is missing from the configuration file.


`OmMissingParameterGroupError`
:  A parameter group (*for data_retrieval_layer:*) is missing from the configuration
   file.


`OmMissingPsanaInitializationFunctionError`
:  One of the psana Detector Interface Initialization Functions is not defined in the
   Data Retrieval Layer. One of the core developers should be contacted.


`OmWrongParameterTypeError`
:  The type of the parameter in the configuration file does not match the requested
   one. The type (string, float, int) of the parameter in the configuration file is
   probably incorrect. The configuration file must strictly follow the
   [YAML 1.2](https://yaml.org) language specification. 
