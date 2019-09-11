Running OnDA at the LCLS Facility - AMO and CXI Beamlines
=========================================================


.. toctree::
   :hidden:

   example_amo_monitor_toml
   example_cxi_monitor_toml
   example_cspad_geom
   example_pnccd_geom


Accessing OnDA
--------------

At these beamlines, OnDA must be run on some machines known as *monitoring nodes*. Only
on these machines the data stream can be accessed in real time. The monitoring nodes
have hostnames that match the following scheme:

* **Monitoring nodes at CXI**: daq-cxi-monXX
* **Monitoring nodes at AMO**: daq-amo-monXX

where XX is a zero-padded number. The specific monitoring nodes available for OnDA can
change for every experiment and sometimes even during an experiment. The beamline
scientists can usually provide information about the monitoring nodes that should be
used at any given time.

Once access has to the monitoring nodes have been obtained, the latest version of OnDA
can be accessed by activating an `Anaconda python
environment <https://anaconda.org/>`_ :

.. code-block:: bash

    # On one of the monitoring nodes, for example, daq-cxi-mon07
    source /reg/g/cfel/onda/onda.sh


Running OnDA
------------


.. warning::

    Please notice that all the *monitor.toml* configuration files and all the geometry
    files provided in this page are just examples. They might need to be modified to
    fit specific experiments.


In order to run OnDA, after logging into the first monitoring node (following
instructions provided by the beamline scientists), a file called
'**run_onda_crystallography_lcls.sh**' should be created with the following content:

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

In the last line, *X* must be replaced with the number of OnDA nodes that should be
instantiated each machine, while *Y* with a comma-separated list of hostnames
corresponding to the monitoring nodes to be used (As already mentioned, the beamline
scientists can provide this information).

In the same folder as the previous script, a *monitor.toml* configuration file should
be created (See :doc:`here <documentation_configuration_file>` for a discussion of the
format and content of the configuration file).

* **Example monitor.toml for CXI**: :doc:`monitor.toml <example_cxi_monitor_toml>`
* **Example monitor.toml for AMO**: :doc:`monitor.toml <example_amo_monitor_toml>`

All the files mentioned in the configuration file (masks, bad_pixel_masks, etc.) must
be reachable and readable from all the monitoring nodes.

* **Example cspad.geom for the cspad detector**: :doc:`cspad.geom <example_cspad_geom>`

The OnDA monitor can be then be started by running the
*run_onda_crystallography_lcls.sh* script on the first monitoring node:

.. code-block:: bash
    
    # On one of the first monitoring node, for example, daq-cxi-mon07
    ./run_onda_crystallography_lcls.sh

As the monitor starts, it prints on the console a line that contains the following
string: "Broadcasting data at <ip>:<port>" (where <ip> is an IP address string of the
form XXX.XXX.XXX.XXX, and <port> is a number). These values are needed to start the
graphical interfaces of OnDA. The OnDA GUI for Crystallography can be started using
the following command:

.. code-block:: bash
    
    # Replace <geometry_file>,<ip> and <port> with appropriate values
    onda_crystallography_gui.py <geometry_file> <ip> <port>

In this command line, *geometry_file* should be replaced with the name of the geometry
file to be used for the visualization, and *ip* and *port* with the information
provided by the starting monitor.

The OnDA Frame Viewer for Crystallography can instead be started using the following
similar command:

.. code-block:: bash
    
    # Replace <geometry_file>,<ip> and <port> with appropriate values
    onda_crystallography_frame_viewer.py <geometry_file> <ip> <port>