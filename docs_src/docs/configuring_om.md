# Configuring OM


## Introduction

OM requires at minimum two pieces of information to operate: a source of data events,
and a set of configuration parameters. Information about the data source is usually
provided as an argument to the monitor’s start up script, in the form of a source
string. Configuration parameters, which fully determine the behavior of the monitor,
are instead stored in a configuration file that OM reads before starting.


##  The Source String

The source string contains information about the origin of the data events that OM will
process. The information is encoded in a string that is passed as a command line
argument to the `om_monitor.py` script:

``` bash
om_monitor.py <SOURCE_STRING>
```

The exact format of the string depends on the Data Retrieval Layer implementation used
by the monitor, and particularly by the specific Data Event Handler being used.

The correct format of the source string is typically part of the information provided
to the users by the beamline scientists that configured OM. The source code
documentation also provides details on the specific format required by each Data Event
Handler.

As a rule of thumb, the format of the source string is often tied to the facility where
the experiment is taking place. Broadly:

* **LCLS**: When OM runs at the LCLS facility, the source string is a psana-style
  DataSource string.

    Example source string: `shmem=psana.0:stop=no`

* **Local Desktop/Laptop**: When OM processes data from files, the source string is
  usually the relative or absolute path to a file containing a list of data files that
  OM should process. The data files to process must belisted one per line in the file,
  with their full relative or absolute path. 

    Example source string: `files.lst`

## The Configuration File

The behavior of an OM monitor is completely determined by the content of its
configuration file. By default, OM looks for a file called `monitor.yaml` in the
current working directory. However, the `--config` command line option of the 
`om_monitor.py` script allows a custom location for the configuration file to be
specified:

``` bash
om_monitor.py --config <PATH_TO_THE_CONFIGURATION_FILE> <SOURCE_STRING>
```

The parameters in the configuration file must be enconded following the rules of the
[YAML 1.2](https://yaml.org) language.

Additionally, the parameters are divided into groups. Each group contains a set of
parameters that are either related to each other (because they control related features
of OM) or apply to the same data processing algorithm. For example:

```YAML
crystallography:
  broadcast_ip: 127.0.0.1
  broadcast_port: 12321
  speed_report_interval: 1000
```

In this example, `crystallography` is the name of the parameter group, while
`broadcast_ip`, `broadcast_port` and `speed_report_interval` are all parameter names.
OM parameters can be **required** or **optional**.

* **Required parameters** are mandatory and must always be provided. OM usually shows
  an error and stops if a required parameter is not present in the   configuration file.

* **Optional parameters** usually control fine behavior of OM or its data processing
  algorithms, and are not required to be present in the configuration file. When an
  optional parameter is not listed in the configuration file, its  default value is
  usually assumed to be *false* or *null*.
 
An alphabetical list of all the parameters that can appearin the configuration file,
grouped by parameter group, is provided in a separate deocument:

* [List of all parameters and parameters groups](parameters.md)

A brief description is provided for each parameter, indicating if the parameter is
required or optional.

Please be aware that depending on which OM monitor is being run,
not all the parameter groups need to be present in the file at the same time.
Conversely, custom OM monitors might introduce additional parameter and even parameter
groups not described in the linked document.

A missing parameter or parameter group, or the wrong choice of a value for a parameter
can cause OM to emit error messages. Please see
[this paragraph](running_om.md#error-messages) for an in-depth discussion of OM's error
reporting.
