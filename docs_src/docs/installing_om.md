# Installing OM


## OM at Facilities

OM comes pre-installed at some beamlines and facilties.

At the **LCLS** facility, OM is already installed at the following beamlines:

  - MFX beamline
  - CXI beamline

OM can be used directly at at these beamlines and facilities. However, the users
should always notify in advance the beamline scientists at each facility of their
intention to use OM during an experiment.


## OM on a Laptop/Desktop

There are three ways to instal OM on a standalone Deskop/Laptop computer.

!!! warning
    It will only be possible to insall OM on a standalone computer after the first
    stable release, which is currently being prepared.


### Installation from PyPI

OM is available on PiPY:

* [OM on PyPI](https://fill.in.url) 

It can be installed using the `pip` command:

``` bash
pip install ondamonitor
```

### Installation from CondaForge

OM is available in the [CondaForge](https://conda-forge.org) package collection and can
be installed using the `conda install` command:

``` bash
conda install -c conda-forge ondamonitor
```

### Installation from Source

OM can be also be installed from source. As a first step, the source code should be
retrieved from GitHub. A compressed code archive for each stable release can be found
the following page:

* [OM's release archives](https://github.com/omdevteam/om-internal/releases)

Alternatively, the source code can be retrieved directly from the GitHub repository
using the `git clone` command:

``` bash
git clone https://github.com/omdevteam/om
```

OM can then be installed using the `pip` command from the root directory of the
retrieved source code (the directory that contains the `setup.py` file):

``` bash
pip install --prefix=<INSTALLATION PATH> .
```

In this command,`<INSTALLATION PATH>` is a relative or absolute path to the directory
where OM should be installed. A Python development-style installation can also be
peformed using the `pip` command:

``` bash
pip install --editable --prefix=<INSTALLATION PATH> .
```

When OM is installed from source, some additional configuration is needed for the local 
operating system to subsequently find the installation directory. Typically, on Linux,
the following environment variables need to be set:

```bash
export PATH=<INSTALLATION PATH>/bin
export PYTHONPATH=<INSTALLATION PATH>/lib/python<PYVER>/site-pacakges
```

Here,  `<INSTALLATION_DIR>` is the directory where OM has been installed, and `<PYVER>`
is the version of Python used by the system (only the major and minor components of the
version number). The Python version number can be obtained using the `python -V`
command, which outputs a string in the following format: `Python X.Y.Z`. The `<PYVER>`
entry in the command above corresponds to the `X.Y` part of this string.


## MPI

When using OM's MPI Parallelization Engine (the default Parallelization Engine), an MPI
framework must be installed on the system where OM is launched. The most popular
choices are OpenMPI and MPICH.

* [OpenMPI](https://www.open-mpi.org)
* [MPICH](https://www.mpich.org)

The precise instructions for the installation of these frameworks are complex,
operating system-dependent, and outside of the scope of this documentation. Please
note that in addition to one of the MPI frameworks, the corresponding `mpi4py` module
for the Python interpreter used by OM must also be installed.








