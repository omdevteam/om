The Source String
-----------------

Information about the source of data events is provided to OnDA at start-up, in the
form of a command line argument to the 'onda_monitor.py' script.

.. code-block:: bash

    onda_monitor.py SOURCE_STRING

It usually consists of a string, the 'Source String', which encodes the information in
a way that depends on the specific Data Retrieval Layer implementation used by the
monitor. This information is usually provided by the developer that configured the
Data Retrieval Layer, and is often specific to the facility where the experiment is
taking place. The following is a list of the facilities currently officially supported
by OnDA, with a description of the typical format of the source string at each of
them.


Filesystem
^^^^^^^^^^

When the source of data for the monitor is the filesystem, the source string is the
relative or absolute path to a file containing a list of files that the monitor must
process. The files that must be process must be listed one per line, each with their
full relative or absolute path. Example: files.lst


LCLS
^^^^

When OnDA runs at the LCLS facility, the source string is a psana-style DataSource
string. Example: shmem=psana.0:stop=no


Petra III
^^^^^^^^^

When the monitor runs at the Petra III facility, the source string is the ip or
the hostname of the machine where HiDRA is running. Example: eval01.desy.de
