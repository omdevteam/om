Running OnDA
============

.. toctree::
   :hidden:

   example_amo_monitor_toml
   example_cxi_monitor_toml
   example_p11_monitor_toml
   example_files_monitor_toml
   example_cspad_geom
   example_pnccd_geom
   example_pilatus_geom
   documentation_source_string
   documentation_configuration_file
   documentation_errors


.. contents::
   :local:


.. warning::

    Please notice that all the *monitor.toml* configuration files and all the geometry
    files provided in this page are just examples. They might need to be modified to
    fit specific experiments.





Running OnDA at the LCLS and Petra III Facilities
-------------------------------------------------

OnDA comes pre-installed at some beamlines of the Petra III and LCLS facilities:

* At LCLS:

  - AMO Beamline
  - CXI Beamline

* At Petra III:

  - P11 Beamline

Instructions on how to access OnDA at these beamlines can be found :doc:`here
<documentation_getting_onda>`. The following documentation focuses on running the OnDA
monitor for Serial Crystallography at the supported facilities. 


LCLS Facility - AMO and CXI Beamlines
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

At these beamlines, OnDA must be run on the group of machines known as *monitoring
nodes*. Only these computers can access the data stream in real time. The monitoring
nodes have hostnames that match the following scheme:

* **Monitoring nodes at CXI**: daq-cxi-monXX
* **Monitoring nodes at AMO**: daq-amo-monXX

where XX is a zero-padded number. The set of specific monitoring nodes available to run
OnDA can be different for every experiment (Sometimes it can change even during the
course of a single experiment). The beamline scientists can provide information about
which monitoring nodes should be used at any given time.

In order to run OnDA, after logging into one of the monitoring nodes, a file called
'**run_onda_crystallography_lcls.sh**' must be created with the following content:

.. code-block:: bash

    # In the last line, replace **X** with the number of OnDA nodes to run on each
    # machine and **Y** with a comma-separated list of hostnames corresponding to the
    # machines on which OnDA should run.
    source /reg/g/cfel/onda/onda.sh
    echo Creating and Running $(pwd)/monitor_wrapper.sh
    echo '#!/bin/bash' > $(pwd)/monitor_wrapper.sh
    echo '# File automatically created by the'  >> $(pwd)/monitor_wrapper.sh 
    echo '# run_onda_crystallography_lcls.sh script' >> $(pwd)/monitor_wrapper.sh
    echo 'source /reg/g/cfel/onda/onda.sh' >> $(pwd)/monitor_wrapper.sh
    echo "onda_monitor.py 'shmem=psana.0:stop=no'" >> $(pwd)/monitor_wrapper.sh
    chmod +x $(pwd)/monitor_wrapper.sh
    $(which mpirun) --oversubscribe --map-by ppr:X:node \
                    --host Y $(pwd)/monitor_wrapper.sh

In the last line, *X* should be replaced with the number of OnDA nodes that should be
instantiated each machine, while *Y* with a comma-separated list of hostnames
corresponding to the monitoring nodes to be used by OnDA (As already mentioned, the
beamline scientists can provide this information).

In the same folder, a *monitor.toml* configuration file should be created (See
:doc:`here <documentation_configuration_file>` for a discussion of the format and
content of the configuration file).

* **Example monitor.toml for CXI**: :doc:`monitor.toml <example_cxi_monitor_toml>`
* **Example monitor.toml for AMO**: :doc:`monitor.toml <example_amo_monitor_toml>`

All the additional files mentioned in the configuration file (masks, bad_pixel_maps,
etc.) should also obviously be reachable and readable from all the monitoring nodes.

* **Example cspad.geom for the cspad detector**: :doc:`cspad.geom <example_cspad_geom>`

The OnDA Monitor for Serial Crystallography can be then be started by running the
*run_onda_crystallography_lcls.sh* script on the first monitoring node:

.. code-block:: bash
    
    # On one of the first monitoring node, for example, daq-cxi-mon07
    ./run_onda_crystallography_lcls.sh

As the monitor starts, it prints on the console the following line: "Broadcasting data
at <ip>:<port>", where <ip> is an IP address (a string with the following format:
XXX.XXX.XXX.XXX) and <port> is a port number. These values are needed to start the
graphical interfaces of OnDA. The OnDA GUI for Crystallography can be started with
the following command:

.. code-block:: bash
    
    # Replace <geometry_file>,<ip> and <port> with appropriate values
    onda_crystallography_gui.py <geometry_file> <ip> <port>

In this command line, *geometry_file* should be replaced with the name of the geometry
file to be used for visualization, and *ip* and *port* with the information provided by
the starting monitor.

The OnDA Frame Viewer for Crystallography can instead be started using the following
similar command:

.. code-block:: bash
    
    # Replace <geometry_file>,<ip> and <port> with appropriate values
    onda_crystallography_frame_viewer.py <geometry_file> <ip> <port>



PETRA III Facility - P11 Beamtime
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

At the P11 beamline, OnDA must run on the *eval01.desy.de* machine as the *p11user*
user. The P11 beamline scientists can provide information on how to access this
machine.

In order to run the OnDA Monitor for Serial Crystallography, a *monitor.toml* file
must be created (See :doc:`here <documentation_configuration_file>` for a discussion
of the format and content of the configuration file).

* **Example monitor.toml for P11**: :doc:`monitor.toml <example_p11_monitor_toml>`

All the files mentioned in the configuration file (masks, bad_pixel_maps, etc.) must
obviously be reachable and readable from the *p11user*.

* **Example pilatus.geom for the Pilatus detector**: :doc:`pilatus.geom
  <example_pilatus_geom>`

The OnDA monitor can then be started using the following command:

.. code-block:: bash
    
    # On eval01.desy.de
    mpirun -n <num_nodes> onda_monitor.py eval01.desy.de

In the command line, *num_nodes* should be replaced with the total number of OnDA 
nodes that the monitor should use (all workers plus a master). Usually a value of 9
(8 workers + 1 master) is fully sufficient to process the full data stream at P11.

As the monitor starts, it prints on the console the following line: "Broadcasting data
at <ip>:<port>", where <ip> is an IP address (a string with the following format:
XXX.XXX.XXX.XXX) and <port> is a port number. These values are needed to start the
graphical interfaces of OnDA. The OnDA GUI for Crystallography can be started with
the following command:

.. code-block:: bash
    
    # Replace <geometry_file>,<ip> and <port> with appropriate values
    onda_crystallography_gui.py <geometry_file> <ip> <port>

In this command line, *geometry_file* should be replaced with the name of the geometry
file to be used for visualization, and *ip* and *port* with the information provided by
the starting monitor.

The OnDA Frame Viewer for Crystallography can instead be started using the following
similar command:

.. code-block:: bash
    
    # Replace <geometry_file>,<ip> and <port> with appropriate values
    onda_crystallography_frame_viewer.py <geometry_file> <ip> <port>





Running OnDA on a Local Machine
-------------------------------

.. warning::

    Please notice that OnDA is currently supported only on the Linux operating system.

Although it is possible to run OnDA on a local machine, it should be noted that OnDA is
not designed or optimized for the limited resources of a laptop or a small desktop
computer. Furthermore, when running OnDA locally, it is often very hard or impossible
to connect to the facility frameworks to retrieve data. Therefore, the following
paragraphs contain instructions aimed at running OnDA to process files written by the
Pilatus detector (relatively small in size), stored in a folder on the local machine. 
This is a good choice for debugging or demonstration purposes.

Instructions on how to install OnDA on a local machine can be found :doc:`here
<documentation_getting_onda>`.

This example will use data files from an experiment performed at the APS facility, part
of the Argonne National Laboratory in the USA. The files have been deposited in the
`Coherent X-ray Imaging Data Bank <http://cxidb.org/id-82.html>`_, an online database
of data from Serial Crystallography experiments. The following paragraphs assume that
the file *data8.tar.gz* has been downloaded from
`here <http://cxidb.org/data/82/raw-data/>`_ and unpacked (Beware, the data, even
compressed, is 24Gb).

In order to run the OnDA Monitor for Serial Crystallography on a local machine, a
*monitor.toml* configuration file should be created. (See :doc:`here
<documentation_configuration_file>` for a discussion of the format and content of the
configuration file).

* **Example monitor.toml for the Ti-Yen Lan dataset from the CXIDB website**:
  :doc:`monitor.toml <example_files_monitor_toml>`

All the files mentioned in the configuration file (masks, bad_pixel_maps, etc.) should
also obviously be present on the local machine.

* **Example pilatus.geom for the Pilatus detector**: :doc:`pilatus.geom
  <example_pilatus_geom>`

OnDA needs then a file containing a list of files that the monitor should process. The
list should contain one file per line, each with its full absolute or relative path.
This file can easily be generated using the Unix *find* command (the following example
creates a file named *files.lst*):

.. code-block:: bash
    
    # Substitute <path> with the path to the downloaded files
    find <path> -name "*cbf" > files.lst

In this command line, *path* should be replaced with the absolute or relative path to
the directory where the data files have been unpacked. For example, assuming that the
files have been unpacked in the *data8* subdirectory of the current folder, the first
lines of the list should read:

.. code-block:: text
    
    data8/lysozyme2_test_000437.cbf
    data8/lysozyme2_test_005699.cbf
    data8/lysozyme2_test_001000.cbf
    data8/lysozyme2_test_006581.cbf
    data8/lysozyme2_test_006410.cbf
    ...

From the folder where the *monitor.toml* and *files.lst* files are, the OnDA monitor
can be finally be started using the following command:

.. code-block:: bash
    
    # Substitute <num_nodes> with the appropriate number of nodes
    mpirun -n <num_nodes> onda_monitor.py files.lst

In the command line, *num_nodes* should be replaced with the total number of OnDA nodes
that the monitor should use (all workers plus a master). For a local machine and for
testing purposes, a value of 3 (just 2 workers + 1 master) is advised.

As the monitor starts, it prints on the console the following line: "Broadcasting data
at <ip>:<port>", where <ip> is an IP address (a string with the following format:
XXX.XXX.XXX.XXX) and <port> is a port number. These values are needed to start the
graphical interfaces of OnDA. The OnDA GUI for Crystallography can be started with
the following command:

.. code-block:: bash
    
    # Replace <geometry_file>,<ip> and <port> with appropriate values
    onda_crystallography_gui.py <geometry_file> <ip> <port>

In this command line, *geometry_file* should be replaced with the name of the geometry
file to be used for visualization, and *ip* and *port* with the information provided by
the starting monitor.

The OnDA Frame Viewer for Crystallography can instead be started using the following
similar command:

.. code-block:: bash
    
    # Replace <geometry_file>,<ip> and <port> with appropriate values
    onda_crystallography_frame_viewer.py <geometry_file> <ip> <port>





The Source String and the Configuration File
--------------------------------------------

In general, OnDA is started using a command that has the following syntax:

.. code-block:: bash

    onda_monitor.py --config CONFIGURATION_FILE SOURCE_STRING

Or, when the 'mpi' implementation of the Parallelization Layer is used:

.. code-block:: bash

    mpirun -n <NUM NODES> onda_monitor.py --config CONFIGURATION_FILE SOURCE_STRING

An OnDA monitor requires two pieces of information to operate: a source of data events,
and a set of configuration parameters. Information about the data source is usually
provided as an argument to the monitor's start up script, in the form of a *source
string*. Configuration parameters, which fully determine the behavior of the monitor,
are instead stored in a configuration file that OnDA reads before starting.


The Source String
^^^^^^^^^^^^^^^^^

See :doc:`here <documentation_source_string>` for an in-depth discussion of the format
of the *source string*.


The Configuration File
^^^^^^^^^^^^^^^^^^^^^^

See :doc:`here <documentation_configuration_file>` for a detailed description of the
configuration file format and its content.





Errors
------

When something does not work as expected, OnDA prints warning and error messages to the
console. A list of the most common errors and their mitigation strategies can be found
:doc:`here <documentation_errors>`.
