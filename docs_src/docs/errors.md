# OM's Errors And Warnings


This document contains a list of the most common errors reported by OM, with a brief
discussion of each.


`OmConfigurationFileReadingError`
:  There was a problem finding or reading the configuration file. The file should exist
   and be readable. OM looks by default for a file called `monitor.yaml` in the current
   working directory.


`OmConfigurationFileSyntaxError`
:  There is a syntax error in the configuration file, at the location specified by the
   error. The file should follow the [YAML 1.2](https://yaml.org) language syntax.


`OmDataExtractionError`
:  An error has happened during the extraction of data from a data event. This error is
   usually not fatal and can happen often if the data stream is corrupted. Usually OM
   skips processing the event and retrieves a new one.


`OmHdf5FileReadingError`
:  An error has happened while reading an HDF5 file. The file should exists and be
   readable.

`OmInvalidDataBroadcastUrl`
:  The format of the `data_broadcast_url` parameter in the `crystallography` section of
   the configuration file is not valid. The parameter should either have the format
   `tcp://hostname:port` or the format `ipc:///path/to/socket`. Additionally, if the
   IPC protocol is used, OM must have the correct permissions to access the ipc socket.


`OmInvalidSourceError`
:  The format of the source string is not valid. There could be typos in the string or
   the format of the string might not match the facility where OM is running.


`OmMissingDependencyError`
:  One of the optional Python module needed by OM is not installed. This error often
   happens with python modules that are tied to a specific facility's framework (for
   example, the `psana` module). One of the core developers should be contacted.


`OmMissingDataExtractionFunctionError`
:  One of the Data Extraction Functions is not defined in the Data Retrieval Layer. One
   of the core developers should be contacted.


`OmMissingHdf5PathError`
:  An internal path in the HDF5 file is not found. The file exists and can be read, but
   the internal path cannot be found. The internal HDF5 path is probably incorrect, or
   the file is corrupted.


`OmMissingParameterError`
:  A required parameter is missing from the configuration file.


`OmMissingParameterGroupError`
:  A parameter group is missing from the configuration file.


`OmWrongParameterTypeError`
:  The type of the parameter in the configuration file does not match the requested
   one. The type (string, float, int) of the parameter in the configuration file is
   probably incorrect. The configuration file must strictly follow the
   [YAML 1.2](https://yaml.org) language specification. 
