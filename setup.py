# pylint: disable=C0111
#    This file is part of OnDA.
#
#    OnDA is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    OnDA is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with OnDA.  If not, see <http://www.gnu.org/licenses/>.
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from setuptools import Extension, setup

import numpy

import onda

USE_CYTHON = 0

ext = '.pyx' if USE_CYTHON else '.c'  # pylint: disable=C0103

peakfinder8_ext = Extension(  # pylint: disable=C0103
    name='onda.algorithms.peakfinder8_extension.peakfinder8_extension',
    include_dirs=[numpy.get_include()],
    libraries=['stdc++'],
    sources=[
        'src/peakfinder8_extension/peakfinder8.cpp',
        'src/peakfinder8_extension/peakfinder8_extension.pyx',
    ] if USE_CYTHON else [
        'src/peakfinder8_extension/peakfinder8_extension.cpp',
        'src/peakfinder8_extension/peakfinder8.cpp',
    ],
    language='c++'
)

extensions = [peakfinder8_ext]  # pylint: disable=C0103

if USE_CYTHON:
    from Cython.Build import cythonize
    extensions = cythonize(peakfinder8_ext)  # pylint: disable=C0103


setup(
    name='onda',
    version=onda.__version__,
    url="https://github.com/ondateam/cfelpyutils",
    license="GNU General Public License v3.0",
    author="OnDA Team",
    author_email="valerio.mariani@desy.de",
    description="Real-time monitoring of x-ray imaging experiments",
    long_description=(
        """
        OnDA (Online Data Analysis) is a software framework for the
        development of programs that can monitor of X-ray imaging
        experiments in real-time.

        OnDA provides users with a set of stable and efficient
        real-time monitors for the most common types of x-ray
        imaging experiments. These can be used immediately without
        modifications or can be easily adapted to meet the users'
        requirements. In addition, the project provides a set of
        modules that can be used to easily develop other monitoring
        programs tailored to the characteristics of specific
        experiments.

        OnDA can process imaging data in the broadest sense:
        multidimensional and multiple-pixel data (for example, a
        diffraction pattern or a photoemission spectrum, but also an
        image coming from a camera or a microscope), but also any kind
        of digital output from an instrument or sensor (for example, a
        temperature readout, beam and pulse energies, etc.).

        OnDA focuses on scalability and portability, in order to
        facilitate its adoption for a wide array of current and future
        instruments. It also strives for stability and performance.
        In order to achieve these goals, OnDA implements a
        master/worker parallelization paradigm using free and
        open-source libraries and protocols.

        OnDA is written in Python. The use of the Python programming
        language, which is particularly suited to prototyping and
        rapid development, makes OnDA easy to modify and to adapt to
        the requirements of specific experiments.

        OnDA also aims to keep the code base simple and as small as
        possible. The focus is on providing a core set of functions,
        while allowing the framework to be expanded with external
        software when possible, avoiding the need to reimplement
        already optimized algorithms.
        """
    ),
    install_requires=[
        'cfelpyutils>=0.9',
        'h5py>=2.7.0',
        'numpy>=1.11.3',
        'scipy>=1.1.0',
        'mpi4py>=2.0.0'],
    extras_require={
        'gui-qt5': ['pyqt>=5.9.2', 'pyqtgraph>=0.10.0'],
        'gui-qt4': ['pyqt>=4.11.4', 'pyqtgraph>=0.10.0'],
        'monitor': [],
        'monitor-cbf': ['fabio>=0.6.0'],
        'monitor-psana': ['psana>=1.3.54']
    },
    scripts=[
        'bin/onda_crystallography_gui.py',
        'bin/onda_crystallography_hit_viewer.py',
        'bin/onda_monitor.py'
    ],
    ext_modules=extensions,
    packages=[
        'onda',
        'onda.algorithms',
        'onda.algorithms.peakfinder8_extension',
        'onda.data_retrieval_layer',
        'onda.data_retrieval_layer.data_sources',
        'onda.data_retrieval_layer.event_sources',
        'onda.data_retrieval_layer.event_sources.hidra_api',
        'onda.data_retrieval_layer.event_sources.karabo_api',
        'onda.data_retrieval_layer.facility_profiles',
        'onda.data_retrieval_layer.file_formats',
        'onda.data_retrieval_layer.filters',
        'onda.graphical_interfaces',
        'onda.parallelization_layer',
        'onda.processing_layer',
        'onda.utils'
    ],
    include_package_data=True,
    platforms='any',
    classifiers=[
        "Programming Language :: Python",

        "Development Status :: 4 - Beta",

        "Programming Language :: Python :: 3",

        "Programming Language :: Python :: 2",

        "Operating System :: OS Independent",

        "Topic :: Software Development :: Libraries :: Python Modules",

        "License :: OSI Approved :: GNU General Public License v3 "
        "or later (GPLv3+)",

        "Natural Language :: English",

        "Intended Audience :: Science/Research",
    ],
)
