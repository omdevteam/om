The Source String
-----------------

Information about the source of data events is provided to OM at start-up, in the
form of the *Source String*, a command line argument to the *om_monitor.py* script:

.. code-block:: bash

    om_monitor.py SOURCE_STRING

The exact format of the string depends on the Data Retrieval Layer implementation used
by the monitor, and is usually part of the information provided to the user by the
developer that configured the OM monitor. The format is often tied to the facility
where the experiment is taking place: the following is a list of facilities that are
currently officially supported by OM, with a description of the typical format of the
source string at each of them.


Filesystem
^^^^^^^^^^

When the source of data for the monitor is the filesystem, the source string is the
relative or absolute path to a file containing a list of files that the monitor must
process. The files should be listed one per line, each with their
full relative or absolute path. Example source string: files.lst


LCLS
^^^^

When OM is run at the LCLS facility, the source string is a psana-style DataSource
string. Example source string: shmem=psana.0:stop=no


Petra III
^^^^^^^^^

When a monitor is used at the Petra III facility, the source string is the ip or the
hostname of the machine where HiDRA is running. Example source
string: haspp11eval01.desy.de
