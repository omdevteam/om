# Advanced


## What is OM?

OM's focus is on real-time (or quasi-real time) processing of experimental data.
Real-time monitoring programs retrieve data from a facility as soon as possible, often
immediately after data has been collected, before it is saved to disk. Some fast,
simple analysis is usually performed on the data. The goal is to provide enough
information to take quick decisions to the people running an experiment. These
decisions can often change the direction of the experiment itself while it is still
running, adapting it to new conditions and circumstances.

Usually, it is not necessary to process all the data being collected in order to
provide enough information for the decision making. For example, the hit rate for a
Serial Crystallography experiment can be computed with high accuracy by analyzing only
a portion of the collected data. It is however crucial that the information provided is
up to date. Because of this, OM always prioritizes the processing of **recently
collected data** over the processing of all collected data. Completeness is not the
main priority, **low latency** in providing the information is. Additionally, the goal
of OM is strictly to provide quick information to the people running the experiment,
not any long-term analysis of the data: after the information is delivered, the data is
discarded without being saved to disk, and new data is retrieved.

In order to achieve high speed in data processing, OM takes advantage of a multi-node
parallel architecture. Several processing units (**processing nodes** in OM
terminology) retrieve data events (a single frame or a collection of frames presented
as a single unit) from a facility, and process them. A **collecting node** aggregates
information from the processing nodes and performs computations over multiple events
(averaging, etc.). The reduced data is finally presented the users in the console or
sent to external programs for visualization.

OM is mostly written using the **Python** programming language, however, some
processing routines are implemented in other languages (**C**, **C++**) for performance
reasons.


## Goals of the OM Project

The goal of the OM project is to provide users with a collection of modules that can
can be used to easily build real-time monitoring programs. However, the project also
aims at providing a set of stable and efficient real-time monitors for the most common
types of x-ray imaging experiments. These programs can be used immediately without
modifications or can be easily adapted to meet the users’ requirements. Currently, only
one of these monitoring programs is distributed with OM, focused on Serial
Crystallography. Several others are currently under development and will be added as
soon as they are ready.

## The Three Layers

In the OM framework, a monitoring program is split into three cleanly separate parts
(or **Layers**, in OM terminology):

* A part that deals with the retrieval of data from a facility and with the extraction
  of information from it. This is the **Data Retrieval Layer**.

* A part which deals with the running logic of the program (set up and finalization of
  the processing and collecting nodes, communication between the nodes, etc.). This is
  called **Parallelization Layer**.

* A part that deals with the scientific processing of the extracted data. This is
  called the **Processing Layer**.

The first two layers are usually different for each facility or beamline. The last
layer, however, encodes the logic of the scientific processing of the data. When the
same type of monitor is run at different facilities, the same Processing Layer code is
run. The interface between the Processing Layer and the other layers is very clearly
defined, and the latter layers can be swapped for different implementations without
affecting the former.

This clean separation is the reason why a developer who wants to write a monitoring
program for a supported facility does not need to worry how data is retrieved, or
passed around the nodes. All he or she needs to learn is how the data can be accessed
and manipulated in the Processing Layer. No knowledge of the other two layers is
required. Furthermore, a monitoring program written for a facility can in most cases be
run at other facilities just by switching to different implementations of the Data
Retrieval and Parallelization layers, keeping the same Processing Layer.

Layers are usually implemented as Python classes. All the available Processing layer
classes can be found in the `om.processing_layer` module. All the available
Data Retrieval layer classes can be found in the `om.data_retrieval_layer` module, and
of course all the available Parallelization Layer classes can be found in the
`om.parallelization_layer` module.

(om-s-workflow)=
## OM's Workflow

When OM starts, it first initializes all the processing and collecting nodes, on a
single or multiple machines, according to the user's wishes. The first process to start
on the first machine usually takes the role of the collecting node, while all the
others become processing nodes.

At start-up, each node reads the configuration file. By default, OM looks for a file
called `monitor.yaml` in the current working directory (or a for a different file
specified by the user via a command-line argument).

Every node imports the Python classes for the Parallelization, Processing and Data
Retrieval layers listed in the configuration file.

The processing nodes start retrieving *data events* from the data source, as dictated
by the Data Retrieval Layer After retrieving and unpacking an event, each processing
node extracts all the data requested by the configuration file (specified in the
`required_data` entry in the `data_retrieval_layer` parameter group). It then stores
the retrieved data in a Python dictionary and calls the `process_data` function
implemented in the Processing Layer, passing the dictionary as an argument.

When the function finishes running and processing the data, the processing node
transmits the returned Python tuple to the collecting node. How the nodes communicate
with each other, and which protocol they use to do so (MPI, ZMQ, etc.) is determined by
the Parallelization Layer.

Once a processing node  has transferred the data to the collecting node, it retrieves
the next data event and the cycle begins again.

The collecting node executes the `collect_data` function, implemented in the Processing
Layer, every time it receives data from a processing node, passing the received tuple
as input to the function.

This process continues indefinitely, or until the data stream ends. In the latter case,
some end-of-processing functions, implemented in the Processing Layer, are called on
all nodes. OM then shuts down.


## Analyzing Data in the Processing Layer

Writing a monitoring program consists mainly in writing a Python class (a *Monitor*
class), that lives in the Processing Layer and implements a data analysis pipeline.
The whole processing logic should be implemented in this class, which must be a
subclass of the
[`OmProcessingProtocol`][om.protocols.processing_layer.OmProcessingProtocol] abstract
class.

The Monitor class must implement all the methods that are abstract in the base class.
A developer just needs to write the implementation for these methods, but it never
needs to call any of them. When OM runs, the methods are automatically called
at the right moment, according to the logic described in the
[Workflow section](om-s-workflow).

The methods are:

  * **initialize_processing_node**: This function is executed on each processing node
    when OM starts. All the initialization code for the processing node should go into
    this function: the relevant class properties should be initialized here.
    Additionally, code that loads external files (for example, a geometry file, or a
    file containing a bad pixel mask) should also be placed in this function: the
    external data should be read and stored in class properties so that the other class
    methods can access it.

  * **initialize_collecting_node**: This function is executed on the collecting node
    when OM starts. This is the equivalent of the previous function for the collecting
    node, and all initialization code for this type of node should be placed into this
    function. In particular, network sockets that are later used to broadcast data to
    external programs are usually opened and initialized in this function.

  * **process_data**: this function is executed on each processing node when data is
    retrieved from the data source. The retrieved data gets passed to this function as
    an argument.

    All the logic related to the processing of a single data event should be
    implemented in this method. The output of this function is transferred by OM to the
    collecting node. Ideally, data should be reduced in this function and the raw,
    unprocessed information should not be sent to the collecting node.

    The function must return a tuple, where the first entry is a dictionary containing
    all the data that should be sent to the collecting node for aggregation, and the
    second entry is the rank of the processing node sending the data. This allows OM to
    keep track of which node is transferring the data.
   
  * **collect_data**: this function is executed on the collecting node every time data
    is received from a processing node. The data received from the processing node is
    passed to this function as an argument.

    This function should implement all the processing logic that involves more than one
    event (for example: averaging over many events, accumulation of events, etc.).
   
    The developer can choose what to do with the result of the aggregated data
    processing. There is no fixed path. Often the information is broadcasted to a
    graphical interface via a network socket, but this is not mandatory. The information
    could also be, for example, printed on the console. 

There are two more methods that are not abstract in the base class, but can be
overridden to implement some custom end-of-data-processing actions (For example:
printing a final summary, etc.). Please note that if OM processes an endless stream of
data (for example, most live data streams) these functions are never called.

  * **end_processing_on_processing_node**: this function is executed on the processing
    node when OM finishes processing all the data in the data source.

    The default implementation of this function just prints a message to the console
    and exits. However, a developer can provide his own implementation, with a
    different behavior.

    This function can optionally return data, which is transferred to the collecting
    node and processed one last time by the `collect_data` function before OM shuts
    down.

5. **end_processing_on_collection_node**: this function is executed on the collecting
   node when OM finishes processing all data in the data source.

    The default implementation of this function just prints a message to the console
    and exits, but a developer can override the default behavior. This function is
    often used to perform some clean-up task on the collecting node.

**Tips and Tricks**
 
The data being processed should ideally be reduced in the `process_data` function on
each processing node. Transferring large amount of data between the nodes is not
efficient and should be avoided whenever possible. For example, when crystallography
data is processed and Bragg peaks are extracted from detector frame data, only the list
of peaks should be sent to the collecting node. Obviously, this strategy cannot be
applied to all cases (a frame viewer GUI, for example, would need the full frame data),
but developers should strive to perform as much data reduction as possible on the 
processing nodes.

The Monitor class should be carefully designed and code should be optimized. For
example, only variables that need to be accessed from more than one method should
become class properties. All others can remain simple local variables. Creating class
properties that are not accessed by other methods will clutter the namespace of the
class, and can result in performance degradation.


## Algorithms

OM can process data using *Algorithms*. These are essentially Python classes which
implement some data processing logic. Since they are stateful objects, algorithms can
be used for operations that must be applied multiple times on different data, but need
to keep track of an internal state between applications. For example, the averaging of
detector frames can be implemented in OM as an algorithm. The algorithm can keep
track of the internal intermediate average, storing it in its internal state, and can
update it each time a new detector frame is processed.

Algorithms should be used mainly for two types of data processing operations:

1. Operations in which an action defined by the same set of parameters is applied to
   each data item retrieved by the monitor. In this case, the internal state can be
   used to store the parameters. A good example of this case is a peak finding
   algorithm, which is initialized with some parameters and then applied to each frame
   data retrieved by the monitor. Another good example is a a dark frame correction
   algorithm, where the same dark calibration data (loaded when the algorithm is
   initialized) is applied to each retrieved detector frame.

2. Operations in which an action applied to each data item updates the internal state.
   A good example of this case is an algorithm that computes a running average: every
   time the algorithm is applied to some new data, the current average, stored in the
   internal state, is updated.

OM provides some pre-packaged algorithms for common data processing operations (peak
finding, data accumulation, etc.) in the [`algorithms`][om.algorithms] sub-package.

**Tips and Tricks**

For data processing operations that don't fall in the two cases described above, and
do not need to keep track of an internal state, functions can often be used in place
of algorithms. For example, the computation of an autocorrelation, the sum of the
intensity observed in a detector frame, are both operations that do not need to store
any persistent information when applied multiple times. They can be implemented as
simple functions instead of algorithms.
