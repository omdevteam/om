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


import os
import numpy

from distutils.core import setup, Extension

cheetah_include_dir = os.environ['ONDA_CHEETAH_INCLUDE_DIR']
cheetah_library_dir = os.environ['ONDA_CHEETAH_LIBRARY_DIR']

peakfinder8_ext = Extension("peakfinder8_extension", sources=["processing_layer/algorithms/cython/peakfinder8_extension.cpp"],
                            include_dirs=[cheetah_include_dir, numpy.get_include()],
                            library_dirs=[cheetah_library_dir],
                            libraries=["cheetah"],
                            language="c++")

peakfinder9_ext = Extension("peakfinder9_extension", sources=["processing_layer/algorithms/cython/peakfinder9_extension.cpp"],
                            include_dirs=[cheetah_include_dir, os.path.join(cheetah_include_dir, 'cheetah_extensions_yaroslav'), numpy.get_include()],
                            library_dirs=[cheetah_library_dir],
                            libraries=["cheetah"],
                            language="c++")

streakfinder_ext = Extension("streakfinder_extension", sources=["processing_layer/algorithms/cython/streakfinder_extension.cpp"],
                             include_dirs=[cheetah_include_dir, os.path.join(cheetah_include_dir, 'cheetah_extensions_yaroslav'), numpy.get_include()],
                             library_dirs=[cheetah_library_dir],
                             libraries=["cheetah"],
                             language="c++")


setup(name="peakfinder8_extension", ext_modules=[peakfinder8_ext])
setup(name="peakfinder9_extension", ext_modules=[peakfinder9_ext])
setup(name="streakfinder_extension", ext_modules=[streakfinder_ext])
