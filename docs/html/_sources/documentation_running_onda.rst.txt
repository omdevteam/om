Running OnDA
============

.. toctree::
   :hidden:

   example_amo_monitor_toml
   example_cxi_monitor_toml


.. contents::
   :local:





Running OnDA at the LCLS and Petra III Facilities
-------------------------------------------------

OnDA comes pre-installed at some beamlines of the Petra III and LCLS facilities:

* LCLS:

  - AMO
  - CXI

* Petra III

  - P11

Please see :doc:`here <documentation_getting_onda>` how to access OnDA at each of these
facilities.  The following sections focus on running an OnDA monitor at the supported
beamlines. 


LCLS - AMO and CXI
^^^^^^^^^^^^^^^^^^

At these beamtimes, OnDA must be run on some machines known as 'monitoring nodes'. Only
on these machines the data stream can be accessed before it is saved to disc.

The monitoring nodes machine have hostnames that match the following scheme:

* **Monitoring nodes at CXI**: daq-cxi-monXX
* **Monitoring nodes at AMO**: daq-amo-monXX

where XX is a zero-padded number.

The beamline scientists can provide information about which specific monitoring nodes
are available for OnDA.

In order to run OnDA, create a file called '**run_onda_crystallography_lcls.sh**'
with the following content:

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

In the last line, replace *X* with the number of OnDA nodes to run on each machine
and *Y* with a comma-separated list of hostnames corresponding to the machines on
which OnDA should run (As already mentioned, the beamline scientists can provide this
information).

In the same folder, create a *monitor.toml* configuration file. (See :doc:`here
<documentation_configuration_file>` for a discussion of the format and content of the
configuration file).

* **Example monitor.toml for CXI**: :doc:`monitor.toml <example_cxi_monitor_toml>`
* **Example monitor.toml for AMO**: :doc:`monitor.toml <example_amo_monitor_toml>`

.. warning::

    The files above are provided only as example. They might need to be modified to
    fit specific experiments.

Make sure that all the files mentioned in the configuration file (masks,
bad_pixel_masks, etc.) are present and can be read from the monitoring nodes.

The OnDA monitor can be started by running the *run_onda_crystallography_lcls.sh*
script:

.. code-block:: bash
    
    # On one of the monitoring nodes, for example, daq-cxi-mon07
    ./run_onda_crystallography_lcls.sh

As the monitor starts, it prints on the console a line that contains the following
string: 'Broadcasting data at <ip>:<port>'. The OnDA GUI for Crystallography can be
started using the following command:

.. code-block:: bash
    
    # Replace <geometry_file>,<ip> and <port> with appropriate values
    onda_crystallography_gui.py <geometry_file> <ip> <port>

In the command line, replace *geometry_file* with the name of the geometry file to be
used for the visualization, and *ip* and *port* with the information provided by the
starting monitor.

The OnDA Frame Viewer for Crystallography can be started using a similar command:

.. code-block:: bash
    
    # Replace <geometry_file>,<ip> and <port> with appropriate values
    onda_crystallography_frame_viewer.py <geometry_file> <ip> <port>


