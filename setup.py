# This file is part of OnDA.
#
# OnDA is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# OnDA is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with OnDA.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
# pylint: disable=invalid-name
"""
setup.py file for OnDA
"""
from __future__ import absolute_import, division, print_function

import os

import numpy
from setuptools import Extension, setup

ONDA_USE_CYTHON = os.getenv("ONDA_USE_CYTHON")

ext = ".pyx" if ONDA_USE_CYTHON else ".c"  # pylint: disable=invalid-name

peakfinder8_ext = Extension(  # pylint: disable=invalid-name
    name="onda.algorithms.peakfinder8_extension.peakfinder8_extension",
    include_dirs=[numpy.get_include()],
    libraries=["stdc++"],
    sources=[
        "src/peakfinder8_extension/peakfinder8.cpp",
        "src/peakfinder8_extension/peakfinder8_extension.pyx",
    ]
    if ONDA_USE_CYTHON
    else [
        "src/peakfinder8_extension/peakfinder8_extension.cpp",
        "src/peakfinder8_extension/peakfinder8.cpp",
    ],
    language="c++",
)

if ONDA_USE_CYTHON:
    from Cython.Build import cythonize

    extensions = cythonize(peakfinder8_ext)  # pylint: disable=invalid-name
else:
    extensions = [peakfinder8_ext]  # pylint: disable=invalid-name

version_fh = open("onda/__init__.py", "r")
version = version_fh.readlines()[-1].split("=")[1].strip().split('"')[1]
version_fh.close()
setup(
    name="onda",
    version=version,
    url="https://www.ondamonitor.com",
    license="GNU General Public License v3.0",
    author="OnDA Team",
    author_email="valerio.mariani@desy.de",
    description="Real-time monitoring of x-ray imaging experiments",
    long_description=(
        """
        OnDA (Online Data Analysis) is a software framework for the development of
        programs that can monitor of X-ray imaging experiments in real-time.

        OnDA provides users with a set of stable and efficient real-time monitors for
        the most common types of x-ray imaging experiments. These can be used
        immediately without modifications or can be easily adapted to meet the users'
        requirements. In addition, the project provides a set of modules that can be
        used to easily develop other monitoring programs tailored to the
        characteristics of specific experiments.

        OnDA can process imaging data in the broadest sense: multidimensional and
        multiple-pixel data (for example, a diffraction pattern or a photoemission
        spectrum, but also an image coming from a camera or a microscope), but also
        any kind of digital output from an instrument or sensor (for example, a
        temperature readout, beam and pulse energies, etc.).

        OnDA focuses on scalability and portability, in order to facilitate its
        adoption for a wide array of current and future instruments. It also strives
        for stability and performance. In order to achieve these goals, OnDA
        implements a master/worker parallelization paradigm using free and
        open-source libraries and protocols.

        OnDA is written in Python. The use of the Python programming language, which
        is particularly suited to prototyping and rapid development, makes OnDA easy
        to modify and to adapt to the requirements of specific experiments.

        OnDA also aims to keep the code base simple and as small as possible. The
        focus is on providing a core set of functions, while allowing the framework to
        be expanded with external software when possible, avoiding the need to
        reimplementalready optimized algorithms.
        """
    ),
    install_requires=[
        "cfelpyutils>=1.0.0",
        "click>=7.0",
        "fabio>=0.9.0",
        "future>=0.17.1",
        "h5py>=2.9.0",
        "msgpack>=0.6.1",
        "msgpack-numpy>=0.4.4.3",
        "numpy>=1.16.4",
        "pyzmq>=18.0.2",
        "scipy>=1.2.1",
        "toml>=0.10.0",
        "typing>=3.6.4",
    ],
    extras_require={
        "monitor": [],
        ":python_version < '3.4'": ["pathlib>=1.0.1"],
        "gui": ["pyqt5>=5.9.2", "pyqtgraph>=0.10.0"],
    },
    entry_points={
        "console_scripts": ["onda_monitor.py=onda.monitor:main"],
        "gui_scripts": [
            "onda_crystallography_gui.py=onda.graphical_interfaces."
            "crystallography_gui:main",
            "onda_crystallography_frame_viewer.py=onda.graphical_interfaces."
            "crystallography_frame_viewer:main",
        ],
    },
    ext_modules=extensions,
    packages=[
        "onda",
        "onda.algorithms",
        "onda.algorithms.peakfinder8_extension",
        "onda.data_retrieval_layer",
        "onda.data_retrieval_layer.data_sources",
        "onda.data_retrieval_layer.frameworks",
        "onda.data_retrieval_layer.frameworks.hidra_api",
        "onda.data_retrieval_layer.frameworks.hidra_api.utils",
        "onda.data_retrieval_layer.frameworks.karabo_api",
        "onda.data_retrieval_layer.profiles",
        "onda.graphical_interfaces",
        "onda.parallelization_layer",
        "onda.processing_layer",
        "onda.utils",
    ],
    include_package_data=True,
    platforms="any",
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 2",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Natural Language :: English",
        "Intended Audience :: Science/Research",
    ],
)
