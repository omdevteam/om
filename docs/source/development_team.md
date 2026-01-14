# Development Team

## Active Developers

OM is currently developed at the Linac Coherent Light Source facility
[(LCLS)](https://lcls.slac.stanford.edu) of the SLAC National Accelerator Laboratory.

However, several collaborators from different institutions all over the world
contribute code, testing and support to the project.

The current core development team includes the following people:

* **Valerio Mariani** (corresponding developer:
  [valmar@slac.stanford.edu](mailto:valmar@slac.stanford.edu))
* Alexandra Tolstikova
* Thomas Grant


## Contributors

Several people have, over the years, contributed to the development and testing of OM
with code, bug reports, ideas, etc. Some still do, occasionally. The following list
might not be exhaustive:

* Abdullah Al Maruf
* Steve Aplin
* Anton Barty
* Henry Chapman
* Jason Koglin
* Manuela Kuhn
* Luca Gelisio
* Mia Lahey-Rudolph
* Thomas J. Lane
* Andrew Morgan
* Christopher O'Grady
* Kanupriya Pande
* Thomas A. White
* Chun Hong Yoon


## Guidelines for Contributions

New contributors to OM are always welcome!

This section contains some guidelines about coding style, language versions, etc.
Please follow these guidelines whenever possible when contributing to the development
of OM.

### Version Control

* OM is developed using the [Git](https://git-scm.com/) version control system.

* OM's versioning scheme follows the [Calendar Versioning](https://calver.org) system.
  Specifically, OM's version number uses the following format: `YY.MM.MINOR.[MICRO]`

* OM's development takes place on [GitHub](https://github.com), and follows the
  [GitHub workflow](https://guides.github.com/introduction/flow).

* Bugs, issues, ideas for improvement, etc should be reported on the
  [issue tracker of OM's main repository](https://github.com/omdevteam/om/issues)
  

### Python

* OM is mainly developed using the [Python](https://www.python.org) programming
  language.

* All of OM's code should run with with all actively supported versions of Python
  (currently 3.6 to 3.9), with the only exception of facility-related code that
  requires a specific version of Python to run.

* The [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
  should be followed for all matters related to coding style and coding conventions.

* All docstrings should be written according to the
  [Google Style](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html).

* Before code is submitted to the main repository, the following linters and formatters
  should be run on it:

    * [**Flake8**](https://flake8.pycqa.org/en/latest/): in the root folder of the OM
      repository, the setup.cfg file stores the settings that should be applied when
      linting OM’s code with Flake8.
    * [**Black**](https://github.com/psf/black): the default options should be used.

### C/C++

* Some OM extensions and plugins can, for performance reason, be written using the
  C++ or C programming languages.

* All the C++ code in OM should follow at most the C++98 ISO standard, and the code
  should compile on a Linux RHEL7/CentOS7 platform using the development stack that
  comes with a standard installation of the system.

* Part of the C++11 standard can be used when writing extensions. However, it must be
  possible to compile the code using version 4.8 of the gcc compiler (This requirement
  and the previous one are imposed by the OS version that must be used to create
  official Linux Python wheels).

* All the C code in OM should follow at most the C99 ISO standard, and the code should
  compile on a Linux RHEL7/CentOS7 platform using the development stack that comes with
  a standard installation of the system (This requirement also comes from the OS
  version used to create the official Linux Python wheels).

* The [Cython](https://cython.org) framework should be used to interface C/C++ code
  with Python.

