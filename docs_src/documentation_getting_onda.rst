Getting OnDA
============


.. contents::
   :local:





Accessing OnDA at the LCLS and Petra III Facilities
---------------------------------------------------

OnDA comes pre-installed at some beamlines of the Petra III and LCLS facilities:

* At LCLS:

  - AMO Beamline
  - CXI Beamline

* At Petra III:

  - P11 Beamline

Beamline scientists can usually provide information on how to use OnDA at these
facilities. However, for reference, instructions are repeated here.


LCLS Facility - AMO and CXI Beamlines
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In order to run OnDA at these two beamlines, access to the *monitoring nodes* is
needed. These machines are the only ones that can access the real-time data stream.
On a monitoring node, the latest version of OnDA can be accessed by activating an
`Anaconda <https://anaconda.org/>`_  Python environment:

.. code-block:: bash

    # On one of the monitoring nodes, for example, daq-cxi-mon07
    source /reg/g/cfel/onda/onda.sh


Petra III - P11
^^^^^^^^^^^^^^^

OnDA is available at this beamline one the *eval01.desy.de* machine. On this machine,
the following command can be used to activate the `Anaconda <https://anaconda.org/>`_
Python environment where OnDA is installed:

.. code-block:: bash

    # On eval01.desy.de
    source /home/p11user/CfelSoft/onda/onda.sh





Installing OnDA on a Local Machine
----------------------------------

.. warning::

    Please notice that OnDA is currently supported only on the Linux operating system.

OnDA can be installed on any machine. It is available on the `Python Package Index
<https://pypi.org/>`_, and also as a package for the
`Anaconda <https://anaconda.org/>`_ Python distribution.


Installation from the Python Package Index
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OnDA can be installed from the Python Package Index (PyPI) using the 'pip' command.
This is the preferred installation method. The only requirements are:

* An actively supported version of Python (2.7, 3.5, 3.6, or 3.7).

* The 'pip' utility for the corresponding version of Python.

**Installation Instructions for Python 3:**

It is recommended to install OnDA in a clean Python virtual environment. The
environment should be created using the
`venv <https://docs.python.org/3/library/venv.html>`_ module from the Standard Library:

.. code-block:: bash

    python3 -m venv onda_env

It can then activated using the following command:

.. code-block:: bash

    source onda_env/bin/activate

Finally, OnDA can be installed in the environment using the 'pip' command. To install
only the monitoring part of OnDA, without the graphical interfaces, the following
command can be used:

.. code-block:: bash

    python3 -m pip install onda

To install OnDA together with the Qt5-based graphical interfaces, the following command
should be used instead:

.. code-block:: bash

    python3 -m pip install onda[GUI]

When the *mpi* Parallelization Layer of OnDA is used (currently the default), the
*mpi4py* module must also be installed. This requires a version of the MPI libraries
to be already installed on the machine.

.. code-block:: bash

    python3 -m pip install mpi4py


**Installation Instructions for Python 2:**

For Python 2, the installation process is very similar. However, the `virtualenv
<https://virtualenv.pypa.io/en/stable/>`_ tool is used to create the enviroment:


.. code-block:: bash

    python2 -m virtualenv onda_env

The environment must then be activated:

.. code-block:: bash

    source onda_env/bin/activate

Finally, OnDA can be installed:

.. code-block:: bash

    python2 -m pip install onda

To install the graphical interfaces together with OnDA, the following command should be
used instead:

.. code-block:: bash

    python2 -m pip install onda[GUI]

When the *mpi* Parallelization Layer of OnDA is used (currently the default), the
*mpi4py* module must also be installed. This requires a version of the MPI libraries
to be already installed on the machine: 

.. code-block:: bash

    python2 -m pip install mpi4py


Installation in Anaconda
^^^^^^^^^^^^^^^^^^^^^^^^

**Installation Instructions for Python 3:**

Packages for OnDA and its dependencies are available from the 'ondateam' channel of
https://anaconda.org. It is reccmmended to install OnDA in a clean Anaconda enviroment,
which can be created normally:

.. code-block:: bash

    conda create -n onda_env python=3

The enviroment can then be activated using the *conda activate* command:

.. code-block:: bash

    conda activate onda_env

Finally, OnDA can be installed using the *conda install* command:

.. code-block:: bash

    conda install --channel conda-forge --channel ondateam onda

**Installation Instructions for Python 2:**

For Python 2 the process is very similar:

.. code-block:: bash

    conda create -n onda_env python=2

Then:

.. code-block:: bash

    conda activate onda_env

Finally, OnDA can be installed with the following command:

.. code-block:: bash

    conda install --channel conda-forge --channel ondateam onda

