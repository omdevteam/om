Advanced Documentation
======================

.. toctree::
   :hidden:

   onda

Code Documentation
------------------

Documentation from the code of OnDA can be found :doc:`here <onda>`.


Guidelines for Contributors
---------------------------

Version Control
^^^^^^^^^^^^^^^

OnDA is developed using the `Git <https://git-scm.com>` version control system.

OnDA uses the branching strategy proposed by Vincent Driessen and commonly known as
`Gitflow <https://nvie.com/posts/a-successful-git-branching-model>`.


Python
^^^^^^

OnDA is mainly developed in `Python  <https://www.python.org>`.

* All code in OnDA must run with both version 2 and 3 of Python, except for
  facility-specific code that specifically requires one of the two versions (for example,
  Python 2 for the LCSL facility). The code must specifically support all the currently
  active versions of python:

  * Python 2

    * 2.7

  * Python 3

    * 3.5
    * 3.6
    * 3.7

* The `python-future <https://python-future.org>`_ project should be used to ensure that
  code contributed to the OnDA project is compatible with all the supported versions of
  Python.

* The Python coding style should follow for the most part the `Google Python \
  Coding Style <https://github.com/google/styleguide/blob/gh-pages/pyguide.md>`_.

* All docstrings should be written following the `Google Style \
  <https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html>`_.

* `Pylint <https://www.pylint.org>`_ should be run on the code before
  submission, as stated in the Google Python Coding Style Guide. In the root
  folder of the OnDA repository, contributors can find  a 'pylintrc' file with
  the settings that should be applied when linting OnDA's code. Please see `here
  <http://pylint.pycqa.org/en/latest/user_guide/run.html?highlight=pylintrc>`_ how to
  use the pylintrc file.


C/C++
^^^^^

Some extension to OnDA can, for performance reason, be written using the 
`C++ <https://en.wikipedia.org/wiki/C%2B%2B>`_ or 
`C <https://en.wikipedia.org/wiki/C_(programming_language)>`_ programming languages.

* All C++ code in OnDA should follow at most the C++98 ISO standard, and the code should
  be able to compile on a Linux RHEL7/CentOS7 platform using the development stack that
  comes with a standard installation of these systems.

* Part of the C++11 standard can be used when writing extensions. However, it must be
  possible to compile the code using version 4.8 of the 'gcc' compiler (in order to
  create the Linux binary Python wheel).

* All C code in OnDA should follow at most the C99 ISO standard, and should the same
  and the code should be able to compile on a Linux RHEL7/CentOS7 platform using the
  development stack that comes with a standard installation of these systems.

* The `Cython <http://cython.org>`_ project should be used to interface C/C++ code with
  Python.



Other Advanced Topics
---------------------


The Processing Layer
^^^^^^^^^^^^^^^^^^^^

Writing a monitoring program OnDA consists mainly in writing a Processing Layer Python
module that implements a data analysis pipeline. The Processing Layer module should
contain, apart from some helper functions, just one class: the 'OndaMonitor' class. The
processing logic should be implemented in this class.

The 'OndaMonitor' class should have only three methods, for all of which the
implementation must be written. It can also have a fourth optional method, which a
developer can choose to implement or not. A developer just needs to write the
implementation for these methods, but never needs to call any of them. When the
monitoring program runs, the methods are automatically called when appropriate.

The methods are:

1. **'init'**: the constructor. This method is executed on both the master and the
   worker nodes when the monitor starts. All the monitor initialization code should go
   in this method. All the class properties needed by the monitor should also be
   initialized here. Code that reads external files that only read once (for example, a
   geometry file, or a file containing a bad pixel mask) should also be placed in this
   method.

   This method consists usually of three sections. The first is a common section which
   contains initialization code that should be run on both the master and the worker
   nodes. The second and the third, introduced by the statements 'if role == master '
   and 'if role == worker' respectively, contain initialization code that should run
   only on one type of node or the other.

2. **'process_data'**: this function is executed on each worker node when data is
   retrieved from the facility. The retrieved data are passed to this function via the
   'data' argument. This argument is a dictionary whose keys are the data entries
   specified in the configuration file under the 'required_data' entry, and whose
   values are the data items themselves.

   All the logic related to processing a single 'event' should be implemented in this
   function. Ideally, data should be reduced in this function and the raw, unprocessed
   information should not be sent to the master node.

   The function returns a tuple, where the first entry, usually called 'results_dict'
   for historical reasons, is a dictionary containing all the data that should be sent
   to the master node for aggregation, while the second entry is the rank of the worker
   node sending the data. The developer does not need to worry about how the data is
   transferred to the master node: the parallelization layer takes care of this.

3. **'collect_data'**: this function is executed on the master node every time
   data is received from a worker node. The tuple sent by the worker node is passed to
   this function via the 'data' argument.

   This function should implement all the processing logic that involves more than one
   event (for example: averaging over many events, accumulation of events, etc.).
   Ideally, the master node should never received raw, unprocessed data, but only
   reduced data from the worker node.

   What the developer wants to do with the collected data is up to him/her. There is no
   fixed path. The collected data is usually streamed outside of the OnDA monitor via a
   network socket, but this is not an obligatory path at all. The data could be, for
   example, printed on the console. If the developer wants to stream data outside of
   the OnDA monitor, he/she will need to setup and manage a socket by him/herself
   (although OnDA provides utilities for this in the 'onda.utils.zmq' module).

4. **'end_processing'**: this function is executed when the monitoring program finishes
   processing the input data, if the input data has and end. Please notice that when
   the monitor processes an infinite stream of data (and most live data streams
   provided by facilities don't really have a well-defined end), this function is never
   called.

   The OnDA framework contains a default implementation of this function, which just
   prints a message to the console and exits. However, a developer can redefine this
   function in the Processing Layer, and if he/she does, the redefined version will
   automatically be called.

   This function is the ideal place for code that cleans up the running environment:
   code that closes files, brings down network sockets, etc.

* Attention should be paid to where the initialization code is placed. Variables that
  are initialized, or operations that are carried out, on a type of node where they are
  not needed waste resources, especially memory, and might result in sub-optimal code.
  The developer should carefully place the  initialization code in the relevant part
  ('master', 'worker' or 'common') of the 'init' function.

* The data being processed should ideally be reduced in the 'process_data' function on
  each worker node. Transferring large amount of data between the nodes is not
  efficient and should be avoided whenever possible. For example, when crystallography
  data is processed and Bragg peaks are extracted from the detector frame data, only
  the list of peas should be sent to the master node, while the frame data should be
  dropped. Obviously, this strategy cannot be applied to all cases (a hit viewer, for
  example), but developers should strive to perform as much data reduction as possible
  on the worker nodes.

* OnDA gives a developer tools to stream data out of the monitoring program, for
  example to send it to a graphical interface for visualization, if the developer
  chooses to do so. It is enough to create an instance of the 'DataBroadcaster' class
  from the 'onda.utils.zmq' module, which creates and to use its 'send_data' method to
  broadcast the data.

* The 'OndaMonitor' class should be carefully designed. Only variables that need to be
  accessed from more than one method should become class properties. All others can
  remain simple local variables. Creating class properties that are not used across
  methods clutters the namespace of the class, and can result


Algorithms
^^^^^^^^^^

In order to process retrieved data, the OnDA framework allows developers to write
algorithms, and even comes a small algorithm library. Algorithms are essentially
entities which implement one single data processing step. An algorithm can be applied
multiple times to different data items, and can remember an internal state between
applications. For example, the averaging of detector frame data could be implemented in
OnDA as an algorithm. The algorithm would keep track of the internal intermediate
average, and update it each time it is applied to new frame data.

In the OnDA framework, algorithms are implemented using Python classes. They should be
used mainly for two types of data processing operations:

1. Operations where an action defined by the same set of parameters is applied to each
   data item retrieved by the monitor. In this case, the internal state is the set of
   parameter with which the algorithm is initialized. A good example of this case is a
   peak finding algorithm, which is initialized with a set of parameters and then
   applied to each frame data retrieved by the monitor. Another good example is a dark
   calibration correction algorithm, where the same dark calibration frame (with which
   the algorithm is initialized) is applied to each frame.

2. Operations where an action applied to each retrieved data item updates the internal
   state. An good example of this case is an algorithm that computes a running average:
   every time the algorithm is applied to retrieved data, the internal current average
   is updated.

OnDA provides some pre-packaged algorithms for common data processing operations (peak
finding, data accumulation, etc.) in the 'onda.algorithms' Python subpackage.


* For data processing actions that don't fall in the two cases described above,
  functions can often be used in place of algorithms. For example, a function that
  computes autocorrelation, or another that computes the sum of the intensity on a
  detector frame, does not need to be initialized with any parameters, so it should
  remain implemented as functions and not turned into an algorithm.


The OnDA Monitor Workflow
^^^^^^^^^^^^^^^^^^^^^^^^^

When an OnDA monitor starts, it first initializes all the worker and master nodes, on a
single or multiple machines, according to the user's wishes. The first process to
start on the first machine usually takes the role of the master node, while all the
others become workers nodes.

Each node parses the command line arguments, and recovers the source string. It then
reads the configuration file. By default, it looks for a file called 'monitor.ini' in
the current working directory. However, a different configuration file can be specified
by the user.

Every node imports the relevant modules for the Processing and Data Retrieval Layer, as
specified in the configuration file, then it executes the 'init' function defined in
the Processing Layer.

Subsequently, each worker retrieves a 'data event' from the specified source. After
retrieving and unpacking the event, it extracts all the data items specified in the
'required_data' entry of the configuration file. It stores them in a Python dictionary
and calls the 'process_data' function defined in the Processing Layer, passing the
dictionary as an argument.

When the function finished running, the monitor transmits the Python tuple returned by
the function to the master node. The worker then retrieves the next event. The master
node executes the 'collect_data' function defined in the Processing Layer every time
that it receives data from a worker, passing their received data as an argument to the
function itself.

This process continues indefinitely, or until the data stream ends. In the latter case,
if the 'end_processing' function has been redefined in the Processing Layer, it is
called. Otherwise its default implementation is run. All nodes then exit and the
monitor stops.




