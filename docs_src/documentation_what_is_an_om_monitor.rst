What Is An OM Monitor?
========================


Real-time Monitoring
--------------------

OM is a tool for the development of programs that can monitor experiments in
real-time (or quasi-real time). This kind of programs retrieve data from a facility as
soon as possible after data is collected, and perform some fast, simple analysis on it.
The goal is to provide the people running the experiment with enough information to
take quick decisions. These can often change the direction of the experiment while it
is still running, adapting it to new conditions and circumstances.

Usually, it is not necessary to process all the data being collected in order to
provide enough information for the decision making. For example, the hit rate for a
Serial Crystallography experiment can be computed with high accuracy by analyzing only
a portion of the collected data. It is however crucial that the information provided
is up to date. Because of this, OM always prioritizes the processing of *recently
collected data* over the processing of *all* collected data. Completeness is not the
main priority, low latency in providing the information is. Additionally, the goal of
OM is strictly to provide quick information to the people running the experiment, not
any long-term analysis of the data: after the information is delivered, the data is
discarded without being saved to disk, and new data is retrieved.

In order to achieve its goals of speed and high throughput data processing, OM takes
advantage of a master / worker parallel architecture. Several processing units
(**worker nodes** in OM parlance) retrieve data events (a single frame or a
collection of frames presented as a single unit) from a facility, and process them.
A **master node** collects information from the workers and performs computations over
multiple events (averaging, aggregation, etc.). The reduced data is finally presented
to the users in the console or sent to external programs for visualization.

OM is mostly written using the Python programming language, however, some processing
routines are implemented in other languages (C, C++) for performance reasons.


The Three Layers
----------------

In the OM framework, a monitoring program is split into three cleanly separate parts
(or **Layers**, in OM parlance):

* A part which deals with the running logic of the program (set up and finalization of
  the worker and master nodes, communication between the nodes, etc.). This is called
  **Parallelization Layer**.

* A part that deals with the retrieval of data from a facility and with the extraction
  of information from it. This is the **Data Retrieval Layer**.

* A part that deals with the scientific processing of the extracted data. This is
  called the **Processing Layer**.

The first two layers are usually different for each facility or beamline. The last
layer, however, encodes the logic of the scientific processing of the data. When the
same type of monitor is run at different facilities, the same Processing Layer code is
run. The interface between the Processing Layer and the other layers is very clearly
defined, and the latter can be swapped for different implementations without affecting
the former.

This clean separation is the reason why a developer who wants to write an OM
monitoring program for a supported facility does not need to worry how data is
retrieved, or passed around the nodes. All he or she needs to learn is how the data
can be accessed and manipulated in the Processing Layer. No knowledge of the other two
layers is required. Furthermore, a monitoring program implementation written for a
facility can in most cases be run at other facilities just by switching to different
implementations of the Data Retrieval and Parallelization layers, keeping the same
Processing Layer.


The OM Project
--------------

The goal of the OM project is to provide users with a collection of modules that can
can be used to easily build real-time monitoring programs. However, the project also
aims at providing a set of stable and efficient real-time monitors for the most common
types of x-ray imaging experiments. These programs can be used immediately without
modifications or can be easily adapted to meet the users’ requirements. Currently, only
one of these monitoring programs is distributed with OM: the OM Monitor for Serial
Crystallography. Several others are currently under development and will be added as
soon as they are ready.

