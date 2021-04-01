OnDA
====

Real-time monitoring of x-ray imaging experiments

Copyright 2020 SLAC National Accelerator Laboratory

Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
                a research centre of the Helmholtz Association.

<https://www.ondamonitor.com>

**OM** (\ **O**\ nda \ **M**\ onitor) is a software tool for the the **development** of
programs that can monitor of x-ray imaging experiments in **real-time**, and also a set
of **monitoring programs** ready for use.

It is the spiritual successor of the **OnDA** project and it is maintained mostly by
the same team of developers.

OM provides users with a set of stable and efficient real-time monitors for the most
common types of x-ray imaging experiments. These **can be used immediately** without
modifications or **can be easily adapted** to meet the users’ requirements. In
addition, the project provides a set of modules that can be used to easily develop
other monitoring programs tailored to the characteristics of specific experiments.

OM can process imaging data in the broadest sense: multidimensional and
multiple-pixel data (for example, a diffraction pattern or a photoemission spectrum,
but also an image coming from a camera or a microscope), and any kind of digital output
from an instrument or sensor (for example, a temperature readout, beam and pulse
energies, etc.).

OM focuses on **scalability and portability**, in order to facilitate its adoption
for a wide array of current and future instruments. It also strives for **stability and
performance**. In order to achieve these goals, OM implements a multi-node
parallelization paradigm using free and open-source libraries and protocols.

OM is written in Python. The use of the Python programming language, which is
particularly suited to prototyping and rapid development, makes OM easy to modify and
to adapt to the requirements of specific experiments.

OM also aims to keep the code base **simple and as small as possible**. The focus is
on providing a core set of functions, while allowing the framework to be expanded with
external software when possible, avoiding the need to reimplement already optimized
algorithms.


Recommended Citation
--------------------

If you use OM in your experiment, please keep citing the original OnDA paper until a
new publication for OM is available:

  Mariani V., Morgan A., Yoon C.H., Lane T.J., White T.A., O'Grady C., Kuhn M., Aplin
  S., Koglin J., Barty A., Chapman H.N., **OnDA: online data analysis and feedback for
  serial x-ray imaging.**, J. *Appl. Crystallogr.* 2016 May 23;49(Pt 3):1073-1080.
  (https://www.ncbi.nlm.nih.gov/pubmed/27275150)


Authors
-------

OM is currently developed at the Linac Coherent Light Source facility of the SLAC
National Accelerator Laboratory (https://lcls.slac.stanford.edu).

Many people from different institutions worldwide contribute code, testing and support
to the project:

* **Valerio Mariani** ([Corresponding author](https://github.com/valmar)
* Anton Barty
* Thomas Grant
* Jason Koglin
* Thomas J. Lane
* Andrew Morgan
* Christopher O'Grady
* Kanupriya Pande
* Alexandra Tolstikova
* Thomas A. White
* Chun Hong Yoon

Support
-------

  * Report issues on the [GitHub issue tracker](https://github.com/ondateam/onda/issues)
