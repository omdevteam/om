OnDA
====

Real-time monitoring of x-ray imaging experiments

Copyright 2018 Deutsches Elektronen-Synchrotron DESY,
               a research centre of the Helmholtz Association.

<http://www.cfel.de>

**OnDA** (**On**line **D**ata **A**nalysis) is a software framework for the
development of programs that can monitor of X-ray imaging experiments in real-time.

OnDA provides users with a set of stable and efficient real-time monitors for the most
common types of x-ray imaging experiments. These can be used immediately without
modifications or can be easily adapted to meet the users’ requirements. In addition,
the project provides a set of modules that can be used to easily develop other
monitoring programs tailored to the characteristics of specific experiments.

OnDA can process imaging data in the broadest sense: multidimensional and
multiple-pixel data (for example, a diffraction pattern or a photoemission spectrum,
but also an image coming from a camera or a microscope), but also any kind of digital
output from an instrument or sensor (for example, a temperature readout, beam and
pulse energies, etc.).

OnDA focuses on scalability and portability, in order to facilitate its adoption for a
wide array of current and future instruments. It also strives for stability and
performance. In order to achieve these goals, OnDA implements a master/worker
parallelization paradigm using free and open-source libraries and protocols.

OnDA is written in Python. The use of the Python programming language, which is
particularly suited to prototyping and rapid development, makes OnDA easy to modify
and to adapt to the requirements of specific experiments.

OnDA also aims to keep the code base simple and as small as possible. The focus is on
providing a core set of functions, while allowing the framework to be expanded with
external software when possible, avoiding the need to reimplement already optimized
algorithms.

Requirements
------------

  **Python Modules: Backend**

  * CfelPyUtils
  * h5py
  * NumPy
  * SciPy
  * mpi4py
  * click
  * FabIO (optional, depending on the facility where OnDA is running)
  * psana (optional, depending on the facility where OnDA is running)


  **Python Modules: Graphical Interface (Optional)**

  * PyQt4 (depending on the facility where OnDA is running)
  * PyQt5 (depending on the facility where OnDA is running)
  * PyQtGraph

Support
-------

  * Report issues on the [GitHub issue tracker](https://github.com/ondateam/onda/issues)
