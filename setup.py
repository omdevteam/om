# This file is part of OM.
#
# OM is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# OM is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with OM.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2020 -2023 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
# type: ignore
"""
setup.py file for OM
"""
import os

import numpy
from setuptools import Extension, find_packages, setup

OM_USE_CYTHON = os.getenv("OM_USE_CYTHON")

if OM_USE_CYTHON:
    ext = ".pyx"
else:
    ext = ".c"

peakfinder8_ext = Extension(
    name="om.algorithms._crystallography",
    include_dirs=[numpy.get_include()],
    libraries=["stdc++"],
    sources=[
        "src/cython/peakfinder8.cpp",
        "src/cython/_crystallography.pyx",
    ]
    if OM_USE_CYTHON
    else [
        "src/cython/_crystallography.cpp",
        "src/cython/peakfinder8.cpp",
    ],
    language="c++",
)
peakfinder8_ext.cython_directives = {"embedsignature": True}

binning_ext = Extension(
    name="om.algorithms._generic",
    libraries=["stdc++"],
    sources=[
        "src/cython/binning.cpp",
        "src/cython/_generic.pyx",
    ]
    if OM_USE_CYTHON
    else [
        "src/cython/_generic.cpp",
        "src/cython//binning.cpp",
    ],
    language="c++",
)
binning_ext.cython_directives = {"embedsignature": True}


if OM_USE_CYTHON:
    from Cython.Build import cythonize

    extensions = cythonize([peakfinder8_ext, binning_ext], annotate=True)
else:
    extensions = [peakfinder8_ext, binning_ext]

version_fh = open("src/om/__init__.py", "r")
version = version_fh.readlines()[-1].split("=")[1].strip().split('"')[1]
version_fh.close()
setup(
    name="ondamonitor",
    version=version,
    url="https://www.ondamonitor.com",
    license="GNU General Public License v3.0",
    author="OM Dev Team",
    author_email="valmar@slac.stanford.edu",
    description="Real-time monitoring of x-ray imaging experiments",
    long_description=(
        """
        OM (OnDA Monitor) is a software framework for the development of
        programs that can monitor of x-ray imaging experiments in real-time.

        It is the spiritual successor of the OnDA project and it is mantained mostly
        by the same team of developers.

        OM provides users with a set of stable and efficient real-time monitors for
        the most common types of x-ray imaging experiments. These can be used
        immediately without modifications or can be easily adapted to meet the users'
        requirements. In addition, the project provides a set of modules that can be
        used to easily develop other monitoring programs tailored to the
        characteristics of specific experiments.

        OM can process imaging data in the broadest sense: multidimensional and
        multiple-pixel data (for example, a diffraction pattern or a photoemission
        spectrum, but also an image coming from a camera or a microscope), but also
        any kind of digital output from an instrument or sensor (for example, a
        temperature readout, beam and pulse energies, etc.).

        OM focuses on scalability and portability, in order to facilitate its
        adoption for a wide array of current and future instruments. It also strives
        for stability and performance. In order to achieve these goals, OM
        uses free and open-source libraries and protocols.

        OM is written in Python. The use of the Python programming language, which
        is particularly suited to prototyping and rapid development, makes OM easy
        to modify and to adapt to the requirements of specific experiments.

        OM also aims to keep the code base simple and as small as possible. The
        focus is on providing a core set of functions, while allowing the framework to
        be expanded with external software when possible, avoiding the need to
        reimplement already optimized algorithms.
        """
    ),
    install_requires=[
        "click",
        "cython",
        "fabio",
        "hdf5plugin",
        "h5py",
        "msgpack",
        "msgpack_numpy",
        "numpy",
        "pillow",
        "pyyaml",
        "pyzmq",
        "rich",
        "ruamel.yaml",
        "scipy",
    ],
    extras_require={
        "qt": ["pyqt5", "pyqtgraph"],
        "docs": [
            "mkdocs",
            "mkdocstring",
            "mkdocstring-python",
            "mkdocs-click",
            "mkdocs-material",
            "mkdocs-material-extensions",
        ],
    },
    entry_points={
        "console_scripts": [
            "om_monitor.py=om.monitor:main",
            "om_jungfrau_dark.py=om.tools.jungfrau_dark:main",
            "om_jungfrau_zmq_receiver.py=om.tools.jungfrau_zmq_receiver:main",
        ],
        "gui_scripts": [
            "om_crystallography_gui.py=om.graphical_interfaces.crystallography_gui:main",
            "om_frame_viewer.py=om.graphical_interfaces.frame_viewer:main",
            "om_crystallography_parameter_tweaker.py=om.graphical_interfaces."
            "crystallography_parameter_tweaker:main",
            "om_xes_gui.py=om.graphical_interfaces." "xes_gui:main",
            "om_swaxs_gui.py=om.graphical_interfaces." "swaxs_gui:main",
        ],
    },
    ext_modules=extensions,
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    platforms="any",
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Natural Language :: English",
        "Intended Audience :: Science/Research",
    ],
)
