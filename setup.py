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
"""
Setup file for OnDA.
"""

from distutils.core import Extension, setup

import numpy
from Cython.Build import cythonize

peakfinder8_ext = Extension(  # pylint: disable=C0103
    name='peakfinder8_extension',
    include_dirs=[numpy.get_include()],
    libraries=['stdc++'],
    sources=[
        'ondacython/peakfinder8/peakfinder8_extension.pyx',
        'ondacython/peakfinder8/peakfinder8.cpp'
    ],
    language='c++'
)

setup(
    ext_modules=cythonize([peakfinder8_ext])
)
