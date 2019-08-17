Getting OnDA
============


.. contents::
   :local:





OnDA at the LCLS and Petra III Facilities
-----------------------------------------

OnDA comes pre-installed at some beamlines of the Petra III and LCLS facilities:

* LCLS:

  - AMO
  - CXI

* Petra III

  - P11

Beamline scientists can provide information on how to access and use OnDA. However, for
reference, instructions can also be found in the following paragraphs.


LCLS - AMO and CXI
^^^^^^^^^^^^^^^^^^

In order to run OnDA at these beamlines, access to the monitoring nodes is needed. They
are the only machines which can access the real-time data stream. Once access has been
granted, the latest version of OnDA can be reached by activating an `Anaconda
<https://anaconda.org/>`_ python environment:

.. code-block:: bash

    source /reg/g/cfel/onda/onda.sh


Petra III - P11
^^^^^^^^^^^^^^^

OnDA is available at this beamline on the 'eval01' machine and must be run on it. Once
logged in, the following command can be used to activate the `Anaconda
<https://anaconda.org/>`_ python environment in which OnDA is installed:

.. code-block:: bash

    source /home/p11user/CfelSoft/onda/onda.sh





OnDA on a Local Machine
-----------------------

OnDA can easily be installed on a local machine from the `Python Package Index
<https://pypi.org/>`_. It is also available as a package for the `Anaconda
<https://anaconda.org/>`_ Python distribution.


Installation from the Python Package Index
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OnDA can be installed from the Python Package Index (PyPI) using the 'pip' command.
This is the preferred installation method. The only requirements are:

* An actively supported version of Python (2.7, 3.5, 3.6, or 3.7).

* The 'pip' utility for the corresponding version of python.

It is recommended to install OnDA in a clean Python virtual environment. The
environment can be created using the Python 2 `virtualenv
<https://virtualenv.pypa.io/en/stable/>`_ tool:

.. code-block:: bash

    python2 -m virtualenv onda_env

Or the `venv <https://docs.python.org/3/library/venv.html>`_ module from the
Python 3 Standard Library:

.. code-block:: bash

    python3 -m venv onda_env

It can be then activated by sourcing a file:

.. code-block:: bash

    source onda_env/bin/activate

Finally, OnDA can be installed using the 'pip' command.

For Python 2:

.. code-block:: bash

    python2 -m pip install onda

For Python 3:

.. code-block:: bash

    python3 -m pip install onda


Installation in Anaconda
^^^^^^^^^^^^^^^^^^^^^^^^


Packages for OnDA and its dependencies are available from the 'ondateam' channel of
https://anaconda.org. It is reccomended to install onda in a clean Python enviroment,
which can be created using the following command for Python 2:

.. code-block:: bash

    conda create -n onda_env python=2

Or the following for Python 3:

.. code-block:: bash

    conda create -n onda_env python=3

The enviroment can then be activated using the following command:

.. code-block:: bash

    conda activate onda_env

Finally, OnDA can be installed using the 'conda install' command:


.. code-block:: bash

    conda install --channel conda-forge --channel ondateam onda
