Running OnDA on a Local Machine
===============================

.. toctree::
   :hidden:

   example_files_monitor_toml
   example_pilatus_geom


.. warning::

    Please notice that OnDA is currently supported only on the Linux operating system.


Installing OnDA
---------------

OnDA can easily be installed on a local machine from the `Python Package Index
<https://pypi.org/>`_. It is also available as a package for the `Anaconda
<https://anaconda.org/>`_ Python distribution.


Installation from the Python Package Index
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OnDA can be installed from the Python Package Index (PyPI) using the 'pip' command.
This is the preferred installation method. The only requirements are:

* An actively supported version of Python (2.7, 3.5, 3.6, or 3.7).

* The 'pip' utility for the corresponding version of python.

**Python 3:**

It is recommended to install OnDA in a clean Python virtual environment. The
environment can be created using  the
`venv <https://docs.python.org/3/library/venv.html>`_ module from the Python 3
Standard Library:

.. code-block:: bash

    python3 -m venv onda_env

The environment can be activated by sourcing a file:

.. code-block:: bash

    source onda_env/bin/activate

Finally, OnDA can be installed using the 'pip' command.
In order to install only the monitoring part of OnDA (without the graphical
interfaces):

.. code-block:: bash

    python3 -m pip install onda

In order to install OnDA together with the Qt5-based graphical interfaces:

.. code-block:: bash

    python3 -m pip install onda[GUI]

When the **mpi** Parallelization Layer is used (It is currently used by default), the
*mpi4py* module needs to be installed. This requires a version of the MPI libraries and
headers to be installed on the machine.

.. code-block:: bash

    python3 -m pip install mpi4py


**Python 2:**

For Python 2, the process, is very similar, except that the `virtualenv
<https://virtualenv.pypa.io/en/stable/>`_ tool must be used to create the enviroment:


.. code-block:: bash

    python2 -m virtualenv onda_env

The rest of the process is then identical:

.. code-block:: bash

    source onda_env/bin/activate

Then:

.. code-block:: bash

    python2 -m pip install onda

Or:

.. code-block:: bash

    python2 -m pip install onda[GUI]

When the *mpi* Parallelization Layer is used, the *mpi4py* module must also be
installed.

.. code-block:: bash

    python2 -m pip install mpi4py


Installation in Anaconda
^^^^^^^^^^^^^^^^^^^^^^^^

**Python 3:**

Packages for OnDA and its dependencies are available from the 'ondateam' channel of
https://anaconda.org. It is reccomended to install onda in a clean Python enviroment,
which can be created using the following command:

.. code-block:: bash

    conda create -n onda_env python=3

Or, for Python 2:

.. code-block:: bash

    conda create -n onda_env python=2

The enviroment can then be activated using the following command:

.. code-block:: bash

    conda activate onda_env

Finally, OnDA can be installed using the 'conda install' command:

.. code-block:: bash

    conda install --channel conda-forge --channel ondateam onda


Running OnDA
------------


.. warning::

    Please notice that all the *monitor.toml* configuration files and all the geometry
    files provided in this page are just examples. They might need to be modified to
    fit specific experiments.


Although it is possible to run OnDA on a local machine, it should be noted that OnDA is
not designed or optimized for the limited resources of a laptop or a small desktop
machine. Furthermore, when running OnDA locally, it is often very hard or impossible
to connect to the facility frameworks to retrieve data. Therefore, the following
paragraphs contain instructions aimed at running OnDA to process files written by the
Pilatus detector (relatively small in size), stored in a folder on the local machine. 
This is a good choice for debugging or demonstration purposes.

This example will use data files from an experiment performed at the APS facility, part
of the Argonne National Laboratory in the USA. These files have been deposited in the
`Coherent X-ray Imaging Data Bank <http://cxidb.org/id-82.html>`_, an online database
of data from Serial Crystallography experiments.

The following paragraphs assume that the file *data8.tar.gz* has been downloaded from
`here <http://cxidb.org/data/82/raw-data/>`_ and unpacked (Beware, the data, even
compressed, is 24Gb).

In order to run OnDA on your machine, create a *monitor.toml* configuration file.
(See :doc:`here <documentation_configuration_file>` for a discussion of the format
and content of the configuration file).

* **Example monitor.toml for the Ti-Yen Lan dataset from the CXIDB website**:
  :doc:`monitor.toml <example_files_monitor_toml>`

Make sure that all the files mentioned in the configuration file (masks,
bad_pixel_masks, etc.) are present on your machine.

* **Example pilatus.geom for the Pilatus detector**: :doc:`pilatus.geom
  <example_pilatus_geom>`

Then create a file with the list of files that onda will process, with their full
absolute or relative path, one file per line. This can easily be obtained using the
*find* command from bash:

.. code-block:: bash
    
    # Substitute <path> with the path to the downloaded files
    find <path> -name "*cbf" > files.lst

In the command line, *path* should be replaced with the absolute or relative path to
the directory where the files have been unpacked. For example, assuming that the files
had been unpacked in the *data8* subdirectory in the current folder, the first lines
of the *files.lst* file should read:

.. code-block:: text
    
    data8/lysozyme2_test_000437.cbf
    data8/lysozyme2_test_005699.cbf
    data8/lysozyme2_test_001000.cbf
    data8/lysozyme2_test_006581.cbf
    data8/lysozyme2_test_006410.cbf
    ...

From the folder where the *monitor.toml* and *files.lst* files are, the OnDA monitor
can be started using the following command:

.. code-block:: bash
    
    # Substitute <num_nodes> with the appropriate number of nodes
    mpirun -n <num_nodes> onda_monitor.py files.lst

In the command line, *num_nodes* should be replaced with the total number of OnDA nodes
that the monitor should use (all workers plus a master). For a local machine and for
testing purposes, a value of 3 (just 2 workers + 1 master) is advised.

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
    