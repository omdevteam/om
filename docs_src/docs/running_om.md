# Running OM


## Running OM at the LCLS Facility (MFX and CXI Beamlines)


### The `run_om.sh` File

At the MFX and CXI beamlines of the LCLS facility, OM must be run on a specific set of
machines known as *monitoring nodes*. Only on these machines the data stream can be
accessed in real time. The monitoring nodes have hostnames that match the following
scheme:

* Monitoring nodes at the CXI beamline: `daq-cxi-mon<XX>`
* Monitoring nodes at the MFX beamline: `daq-mfx-mon<XX>`

In these hostnames, `<XX>` is a zero-padded integer number. The specific monitoring
nodes that should be used to run OM can change for each experiment and sometimes even
within the same experiment. The beamline scientists can usually provide information
about the nodes that should be used at any given time.

Once access to the monitoring nodes has been obtained, a file called `run_om.sh` should
be created with the following content:

``` bash
# In the last lines, replace X with the number of OM nodes
# to run on each machine and Y with a comma-separated list
# of hostnames for machines on which OM should be launched.
source /cds/sw/ds/ana/conda1/manage/bin/psconda.sh -py3
echo Creating and Running $(pwd)/monitor_wrapper.sh
echo '#!/bin/bash' > $(pwd)/monitor_wrapper.sh
echo '# File automatically created by the' >> $(pwd)/monitor_wrapper.sh
echo '# run_om.sh script, please do not' >> $(pwd)/monitor_wrapper.sh
echo '# edit directly.' >> $(pwd)/monitor_wrapper.sh
echo 'source <OM> >> $(pwd)/monitor_wrapper.sh
echo "om_monitor.py 'shmem=psana.0:stop=no'" >> $(pwd)/monitor_wrapper.sh
chmod +x $(pwd)/monitor_wrapper.sh
$(which mpirun) --oversubscribe --map-by ppr:X:node \
                --host Y $(pwd)/monitor_wrapper.sh
```

In the last two lines, `X` must be replaced with the number of processes that OM should
start on each monitoring node, and `Y` with a comma-separated list of hostnames or IP
addresses of machines on which OM should be launched (This information is usually
provided by the beamline scientists).

Examples of `run_om.sh` files for the MFX and CXI beamlines can be found at the
following links:

  * [Example `run_om.sh` script for the MFX beamline](files/mfx/run_om.sh)
  * [Example `run_om.sh` script for the CXI beamline](files/cxi/run_om.sh)

!!! warning
    Please note that these files are are *just examples*. They might need to be
    modified before being used for specific experiments.

### The `monitor.yaml` File

In the same folder as the previous script, a `monitor.yaml` configuration file should
be created. (See [this section](configuring_om.md#the-configuration-file) for a full
discussion of the format and content of the configuration file).

Example configuration files for the MFX and CXI beamlines can be found at the following
links:

  * [Example `monitor.yaml` file for the MFX beamline](files/mfx/monitor.yaml)
  * [Example `monitor.yaml` file for the CXI beamline](files/cxi/monitor.yaml)

!!! warning
    Please note that these files are *just examples*. They might need to be modified
    before being used for specific experiments. This is particularly true for the
    entries in the file that define the *calibration directory* and the *detector
    name*, and for the ones that define the *epics variables* associated with beam
    energy and detector distance. These are usually all experiment-dependent.



### The Geometry File

In most cases, the `monitor.yaml` file will instruct OM to look for a
[CrystFEL geometry](https://www.desy.de/~twhite/crystfel/manual-crystfel_geometry.html)
file for the x-ray detector used at the beamline.

Example geometry files for several detectors used at the LCLS facility can be found at
the following link:

* [Example geometry files for LCLS detectors](files/geometry/index.md)

In their default setup, the MFX and CXI beamlines use the Epix10ka and Jungfrau1M
detectors. Example geometry files for these detectors can be found here:

  * [Epix10ka geometry file for the MFX beamline](files/geometry/epix10ka.geom)
  * [Jungfrau4M geometry file for the CXI beamline](files/geometry/jungfrau4M.geom)


### Running OM

Once everything is setup, OM can be launched by simply running the `run_om.sh` script
from a terminal. Please note that the script should be launched from a monitoring node
machine, or from a computer that has a direct connection to all the monitoring nodes.
At the MFX beamline, for example, `mfx-daq` and `mfx-monitor` are suitable hosts, as are
`cxi-daq` and `cxi-monitor` at the CXI beamline.

After OM has been started, please see
[this paragraph](#running-oms-graphical-interfaces) on how to run OM's graphical
interfaces.


## Running OM on a Laptop/Desktop

### Introduction

When OM is launched on an a standalone computer, it is often very hard or impossible to
connect to a facility's framework to retrieve data. Therefore, in the following
example, OM will process data coming from files stored on disk, rather than real-time
data from a facility. Specifically, this example will deal with files written by a
Pilatus x-ray detector in CBF format. These files have been chosen because they are
relatively small in size and easy to copy from one machine to the other.

This setup, where OM processes data coming from files rather than from a facility's
framework, is a very good solution for testing and debugging purposes.

!!! note
    Although it is possible to run OM on a small standalone computer, it should be
    noted that OM is not designed or optimized for the limited resources of a laptop or
    a small desktop computer.


### The Data Files

This example uses data files from an experiment performed by Ti-Yen Lan's research
group at the APS facility, part of the Argonne National Laboratory in the USA. These
files have been deposited in the
[Coherent X-ray Imaging Data Bank](http://cxidb.org/id-82.html), an online database of
data from Serial Crystallography experiments.

The following paragraphs assume that the file `data8.tar.gz` has been downloaded from
[here](http://portal.nersc.gov/archive/home/projects/cxidb/www/82/raw-data/data8.tar.gz)
and unpacked in a folder on the local computer.

!!! warning
    Beware of storage space limitation and long download times: the data, even
    compressed, has a size  24Gb !


### The `monitor.yaml` file

In oder to run OM, a `monitor.yaml` configuration file should be created on the local
computer (See [this section](configuring_om.md#the-configuration-file) for a full
discussion of the format and content of the configuration file). The following
file can be used for the dataset in this example:

  * [Example `monitor.yaml` file for Ti-Yen Lan's dataset](files/local/monitor.yaml)

!!! warning
    This configuration file has been adapted to the dataset in this example. Please
    note that a completely different configuration file might be needed for other
    datasets. Please consult the documentation linked above for a detailed explanation
    of each entry in the file. Also note that all the files mentioned in the
    configuration file (geometry file, masks, etc.) must be present and readable on
    the local computer for OM to work properly.


### The Geometry File

The `monitor.yaml` file linked above instructs OM to load a CrystFEL geometry file for
the x-ray detector used during the experiment.

Examples of geometry files for several detectors used at various facilities and
beamlines can be found at the following link:

* [Example geometry files for various x-ray detectors](files/geometry/index.md)

However, for the current example, just a Pilatus detector geometry file is needed:


  * [Pilatus geometry file](files/geometry/pilatus.geom)


### Running OM

In order to have OM work on data from files, it is necessary to let the program know
which files should be processed, and where to find them on the local computer. A list
of files that OM must process needs to be generated. Each file must be listed on a
separate line, each with its own full absolute or relative path. The list must then be
saved into yet another file. 

For this example, the list file can easily be created using the UNIX `find` command:

``` bash
find <PATH TO DATA> -name "*cbf" > files.lst
```

In this command, `<PATH TO DATA>` should point to the folder where the previously
downloaded data file has been unpacked.

Assuming that the files are in the `data8` subdirectory of the current working folder,
for example, the `files.lst` file should read:

```
data8/lysozyme2_test_000437.cbf
data8/lysozyme2_test_005699.cbf
data8/lysozyme2_test_001000.cbf
data8/lysozyme2_test_006581.cbf
data8/lysozyme2_test_006410.cbf
...
```

OM can finally be started from the folder where the `monitor.toml`, `pilatus.geom` and
`files.lst` files are located, using the following command:

```bash
mpirun -n <NUM NODES> om_monitor.py files.lst
```

In this command, `<NUM NODES>` must be replaced with the total number of nodes that
OM should use (several processing nodes and a collecting node). For a standalone
computer, and for testing purposes, a value of 3 (just 2 processing + 1 collecting
nodes) is recommended.

After OM has been started, please see
[this paragraph](#running-oms-graphical-interfaces) on how to run OM's graphical
interfaces.


## Running OM's Graphical Interfaces

### Broadcasting URL

As the monitor starts, it prints on the console a line that contains the following
string:

```bash
Broadcasting data at <URL>
```

In this message, `<URL>` is a string of the form `protocol://location`, and it
describes the protocol used by OM to broadcast the data (TCP or IPC), in addition to
the location where the data is being broadcast. With the TCP protocol, the location is
usually an IP address plus a port separated by a colon (`XXX.XXX.XXX.XXX:port`). When
the IPC protocol is used, the location is usually the absolute path to a filesystem
socket (`/path/to/socket`). 


### Launching the Graphical Interfaces

The broadcasting protocol and location are the only pieces of information needed to
launch most of OM's graphical interfaces. The GUIs can be started using a command with
the following format:

``` bash
<GUI COMMAND> <URL>
```

Where `<GUI COMMAND>` is the name of the GUI script, and `<URL>` is the string printed
out by OM at start up. For example, the Crystallography GUI and the Crystallography
Frame Viewer, could be launched with the following commands:

=== "TCP Protocol"

    ``` bash
    om_crystallography_gui.py tcp://127.0.0.1:12321
    ```

=== "IPC Protocol"

    ``` bash
    om_crystallography_gui.py ipc://mfxopr/om_socket
    ```

and

=== "TCP Protocol"

    ``` bash
    om_crystallography_frame_viewer.py tcp://127.0.0.1:12321
    ```

=== "IPC Protocol"

    ``` bash
    om_crystallography_frame_viewer.py ipc://mfxopr/om_socket
    ```


In general OM's graphical interfaces do not need to be launched on the same computer
where OM is running. However, the location where the data is broadcast should be
visible and reachable from the computer where the GUIs are running. Furthermore, some
specific graphical interfaces might need access to files or information that is only
present on the machine where OM is running. For example, OM's Crystallography Parameter
Tweaker needs to access the `monitor.yaml` file, so it must either be run from the same
computer and folder as OM, or the file must be copied over to the machine where the GUI
is running.


## Error Messages

When something does not work as expected, OM emits error messages.  Errors can be
fatal, in which case the monitor stops, or not, in which case OM just reports the error
and continues processing data.

OM errors are not reported as normal Python errors. They are clearly labelled as coming
from the monitor, and their traceback information is removed. The `--debug` option to 
the `om_monitor.py` script disables this behavior and forces OM to report all errors as
normal Python errors.

When the OM's Parallelization Engine is used, OM fatal errors are often reported
multiple times before the monitor finishes operating: it can happen that multiple nodes
report the same error independently before the MPI engine can stop.

A brief description of the most common error messages, and the measures needed to
mitigate them, can be found at the following link:

* [Most common error messages from OM](errors.md)
