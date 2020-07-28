Advanced Documentation
======================

.. toctree::
   :hidden:

   om

Code Documentation
------------------

Automatically generated documentation from the code of OM can be found
:doc:`here <om>`.


Guidelines for Contributors
---------------------------


Version Control
^^^^^^^^^^^^^^^

OM is developed using the `Git <https://git-scm.com>`_ version control system.

OM follows the `CalVer <http://www.calver.org>`_ versioning system. Specifically, it
follows the scheme: *YY.MM.MINOR.[MICRO]*

Python
^^^^^^

OM is mainly developed in `Python  <https://www.python.org>`_.

* All code in OM must run with both version 2 and 3 of Python, except for
  facility-specific code that specifically requires one of the two versions (for example,
  Python 2 for the LCLS facility). The code must specifically support all the currently
  active versions of python:

  * Python 2

    * 2.7

  * Python 3

    * 3.6
    * 3.7
    * 3.8

* The `python-future <https://python-future.org>`_ project should be used to ensure that
  code contributed to the OM project is compatible with all the supported versions of
  Python.

* The Python coding style should follow for the most part the `Google Python
  Coding Style <https://github.com/google/styleguide/blob/gh-pages/pyguide.md>`_.

* All docstrings should be written following the `Google Style
  <https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html>`_.

* `Flake8 <https://gitlab.com/pycqa/flake8>`_ should be run on the code before
  submission. In the root folder of the OM repository, the setup.cfg file stores
  the settings that should be applied when linting OM's code with Flake8.

* All submitted code should be formatted using the `Black
  <https://github.com/psf/black>`_ code formatter.


C/C++
^^^^^

Some extension to OM can, for performance reason, be written using the 
`C++ <https://en.wikipedia.org/wiki/C%2B%2B>`_ or `C
<https://en.wikipedia.org/wiki/C_(programming_language)>`_ programming languages.

* All C++ code in OM should follow at most the C++98 ISO standard, and the code
  should compile on a Linux 
  7/CentOS7 platform using the development stack that
  comes with a standard installation of the system.

* Part of the C++11 standard can be used when writing extensions. However, it must be
  possible to compile the code using version 4.8 of the *gcc* compiler (in order to
  create the Linux binary Python wheel).

* All C code in OM should follow at most the C99 ISO standard, and the code should
  compile on a Linux RHEL7/CentOS7 platform using the development stack that comes with
  a standard installation of the system.

* The `Cython <http://cython.org>`_ project should be used to interface C/C++ code with
  Python.


Other Advanced Topics
---------------------

This section contains a collection of short essays on several OM-related topics.


The OM Workflow
^^^^^^^^^^^^^^^

When an OM monitor starts, it first initializes all the processing and collecting
nodes, on a single or multiple machines, according to the user's wishes. The first
process to start on the first machine usually takes the role of the collecting node,
while all the others become processing nodes.

Each node parses the command line arguments, and recovers the source string. It then
reads the configuration file. By default, OM looks for a file called *monitor.yaml*
in the current working directory (or a for a different file specified by the user via a
command-line argument).

Every node then imports the Python modules for the Parallelization, Processing and Data
Retrieval layers, as specified in the configuration file. After that, the
DataEventHandler and Monitor implementations requested in the configuration file are
recovered from the DataRetrievalLayer, and Processing Layer respectively. The monitor
is then started.

Subsequently, each worker retrieves a *data event* from the data source. After
retrieving and unpacking the event, it extracts all the data items specified in the
*required_data* entry of the configuration file. It stores them in a Python dictionary
and calls the *process_data* function defined in the Processing Layer, passing the
dictionary as an argument.

When the function finishes running, the monitor transmits the Python tuple returned by
the *process_data* function to the collecting node. The worker then retrieves the next
event. The collecting node executes the *collect_data* function defined in the
Processing Layer every time it receives data from a worker, passing the received data
as an argument to the function.

This process continues indefinitely, or until the data stream ends. In the latter case,
the *end_processing* function, defined in the Parallelization layer, and optionally
overridden in the Processing Layer is called. All nodes then exit and the monitor
stops.


The Processing Layer
^^^^^^^^^^^^^^^^^^^^

Writing an OM monitoring program consists mainly in writing a Python module, the
Processing Layer, that implements a data analysis pipeline. The Processing Layer module
should contain, apart from some helper functions, just one class. The processing logic
should be implemented in this class. The class must be a subclass of the OmMonitor
abstract class from the Processing Layer.

The class must implement the three abstract methods of the base class. A developer
just needs to write the implementation for these methods, but it never needs to call
any of them. When the monitoring program runs, the methods are automatically called
when appropriate.

The methods are:

1. initialize_node. This function is executed on both the processing and collecting
   nodes when the monitor starts. All the monitor initialization code should go in it.
   All the class properties needed by the monitor should be initialized in this
   function. Additionally, code that loads external files (for example, a geometry
   file, or a file containing a bad pixel mask) should also be placed in this
   function: the external data should be read and stored in class properties so that
   the other class methods can access it.

   This method should usually be divided in three sections. The first should be a
   common section with code that should be run on both the processing and the
   collecting nodes. The second and the third, introduced respectively by the code
   statements '"if role == "processing"' and 'if role == "collecting"', should contain
   initialization code specific to one type of node.

2. **process_data**: this function is executed on each processing node when data is
   retrieved from the data source. The retrieved data gets passed to this function.

   All the logic related to processing a single data event should be implemented in
   this method. Ideally, data should be reduced in this function and the raw,
   unprocessed information should not be sent to the collecting node.

   The function must return a tuple, where the first entry is a dictionary containing
   all the data that should be sent to the collecting node for aggregation, and the
   second entry is the rank of the worker node sending the data.
   
   The developer show not concern himself with how the data is transferred to the
   collecting node: the Parallelization Layer takes care of the transmission.

3. **collect_data**: this function is executed on the collecting node every time
   data is received from a worker node. The data received from the processing node is
   passed to this function, and the function should implement all the processing logic
   that involves more than one event (for example: averaging over many events,
   accumulation of events, etc.).
   
   The developer can choose what to do with the result of the aggregated data
   processing. There is no fixed path. Often the information is broadcasted to a
   graphical interface via a network socket, but this is not an obligatory path at all.
   The information could also be, for example, printed on the console. If the developer
   wants to stream data outside of the OM monitor, OM provides utilities for this
   in the *om.utils.zmq_monitor* module.

There is a fourth method that is already implemented in the base class, but can be
overridden in the class that implements the monitor:

4. **end_processing**: this function is executed when the monitoring program finishes
   processing the input data, if the input data stream has an end. When the monitor
   processes an endless stream of data (for example, most live data streams provided by
   the facilities)  this function is never called.

   The default implementation of this function, just prints a message to the console
   and exits. However, a developer can provide his own implementation, with a different
   behavior.

   This function is the ideal place for code that cleans up the running environment:
   code that closes files, brings down network sockets, etc.

**Notes:**

* Attention should be paid to where the initialization code is placed. The developer
  should carefully place the  initialization code in the relevant section (Processing
  node, collecting node or both) of the *initialize_node* function. Variables that are
  initialized, or operations that are carried out, on a node where they are not needed
  waste resources, especially memory, and might result in sub-optimal code.
 
* The data being processed should ideally be reduced in the *process_data* function on
  each processing node. Transferring large amount of data between the nodes is not
  efficient and should be avoided whenever possible. For example, when crystallography
  data is processed and Bragg peaks are extracted from the detector frame data, only
  the list of peaks should be sent to the collecting node, while the frame data should
  be dropped. Obviously, this strategy cannot be applied to all cases (a frame viewer,
  for example, would need the full frame data), but developers should strive to perform
  as much data reduction as possible on the worker nodes.

* The zmq_monitor class should be carefully designed and code should be optimized. For
  example:
  
  - Only variables that need to be accessed from more than one method should become
    class properties. All others can remain simple local variables. Creating class
    properties that are not accessed by other methods will clutter the namespace of the
    class, and can result in performance degradation.


Algorithms
^^^^^^^^^^

In order to perform data processing, OM allows developers to write *Algorithms*.
Algorithms are essentially Python classes which implement one single data processing
step. Algorithms should be used for operations that must be applied multiple times to
different data items, and need to remember an internal state between applications.
For example, the averaging of detector frame data can be implemented in OM as an
algorithm. The algorithm would keep track of the internal intermediate average, and
update it each time it is applied to new frame data.

Algorithms should be used mainly for two types of data processing operations:

1. Operations where an action defined by the same set of parameters is applied to each
   data item retrieved by the monitor. In this case, the internal state is the set of
   parameter with which the algorithm is initialized. A good example of this case is a
   peak finding algorithm, which is initialized with a set of parameters and then
   applied to each frame data retrieved by the monitor. Another good example is a dark
   calibration correction algorithm, where the same dark calibration data (with which
   the algorithm is initialized) is applied to each retrieved detector data frame.

2. Operations where an action applied to each retrieved data item updates the internal
   state. An good example of this case is an algorithm that computes a running average:
   every time the algorithm is applied to retrieved data, the internal current average
   is updated.

OM provides some pre-packaged algorithms for common data processing operations (peak
finding, data accumulation, etc.) in the *om.algorithms* Python sub-package.

**Notes:**

* For data processing actions that don't fall in the two cases described above,
  and do not need to keep track of an internal state, functions can often be used in
  place of algorithms. For example, the computation of an autocorrelation, the sum of
  the intensity observed in a detector frame, are operations that do not store to store
  any persistent information when applied multiple times. They can be implemented as
  simple functions instead of algorithms.
