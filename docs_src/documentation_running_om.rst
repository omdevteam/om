Running OM
==========

.. toctree::
   :hidden:

   documentation_lcls
   documentation_p11
   documentation_local
   documentation_source_string
   documentation_configuration_file
   documentation_errors


Running OM
----------

OM comes pre-installed at some beamlines of the Petra III and LCLS facilities:

* At the **LCLS** facility:

  - See :doc:`here <documentation_lcls>` for information on the **CXI** Beamline

* At the **Petra III** facility:

  - See :doc:`here <documentation_p11>` for information on the **P11** Beamline

OM can also be run on a local desktop or laptop machine.

* On a **local machine**:

  - See :doc:`here <documentation_local>` for instructions

    
Configuring OM: the Source String and the Configuration File
------------------------------------------------------------

An OM monitor requires two pieces of information to operate: a source of data events,
and a set of configuration parameters. Information about the data source is usually
provided as an argument to the monitor's start up script, in the form of a *source
string*. Configuration parameters, which fully determine the behavior of the monitor,
are instead stored in a configuration file that OM reads before starting.


The Source String
^^^^^^^^^^^^^^^^^

See :doc:`here <documentation_source_string>` for an in-depth discussion of the format
of the *source string*.


The Configuration File
^^^^^^^^^^^^^^^^^^^^^^

See :doc:`here <documentation_configuration_file>` for a detailed description of the
configuration file format and its content.


Warnings And Errors
-------------------

When something does not work as expected, OM prints warning and error messages to the
console. A list of the most common errors and a brief discussion of each of them can be
found :doc:`here <documentation_errors>`.
