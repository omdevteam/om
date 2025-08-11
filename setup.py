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
    name="om.algorithms._crystallography_cython",
    include_dirs=[numpy.get_include()],
    libraries=["stdc++"],
    sources=(
        [
            "src/cython/peakfinder8.cpp",
            "src/cython/_crystallography_cython.pyx",
        ]
        if OM_USE_CYTHON
        else [
            "src/cython/_crystallography_cython.cpp",
            "src/cython/peakfinder8.cpp",
        ]
    ),
    language="c++",
)
peakfinder8_ext.cython_directives = {"embedsignature": True}

binning_ext = Extension(
    name="om.algorithms._generic_cython",
    libraries=["stdc++"],
    sources=(
        [
            "src/cython/binning.cpp",
            "src/cython/_generic_cython.pyx",
        ]
        if OM_USE_CYTHON
        else [
            "src/cython/_generic_cython.cpp",
            "src/cython//binning.cpp",
        ]
    ),
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
    ext_modules=extensions,
)
