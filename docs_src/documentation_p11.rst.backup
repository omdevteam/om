Running OnDA at the PETRA III Facility - P11 Beamline
=====================================================


.. toctree::
   :hidden:

   example_p11_monitor_toml
   example_pilatus_geom


Accessing OnDA
--------------

OnDA must be run at this beamline on the *haspp11eval01* machine as the *p11user*.
Once logged in, the following command can be used to activate the Python environment
in which OnDA is installed:

.. code-block:: bash

    # On haspp11eval01.desy.de:
    source /home/p11user/CfelSoft/onda/onda.sh



Running OnDA
------------

.. warning::

    Please notice that all the *monitor.toml* configuration files and all the geometry
    files provided in this page are just examples. They might need to be modified to
    fit specific experiments.


In order to run OnDA on the *haspp11eval01* machine, a *monitor.toml* must be created
(See :doc:`here <documentation_configuration_file>` for a discussion of the format and
content of the configuration file).

* **Example monitor.toml for P11**: :doc:`monitor.toml <example_p11_monitor_toml>`

All the files mentioned in the configuration file (masks, bad_pixel_masks, etc.) must
be reachable and readable from the *p11user* user on *haspp11eval01.desy.de*.

* **Example pilatus.geom for the Pilatus detector**: :doc:`pilatus.geom
  <example_pilatus_geom>`

The OnDA monitor can then be started using the following command:

.. code-block:: bash
    
    # On eval01.desy.de
    mpirun -n <num_nodes> onda_monitor.py eval01.desy.de

In this command line, *num_nodes* should be replaced with the total number of OnDA 
nodes that the monitor should use (all workers plus a master). Usually a value of 17
(16 workers + 1 master) is fully sufficient to process the full data stream at P11.

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
