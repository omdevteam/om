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


from distutils.core import setup, Extension
from Cython.Build import cythonize
import numpy

peakfinder8_ext = Extension(name='peakfinder8_extension',
                            include_dirs=[numpy.get_include()],
                            libraries=['stdc++'],
                            sources=['cython/peakfinder8/peakfinder8_extension.pyx',
                                     'cython/peakfinder8/peakfinder8.cpp'],
                            language='c++')

streakfinder_ext = Extension(name='streakfinder_extension',
                            include_dirs=[numpy.get_include(), 
                                          'cython/fast_diffraction_image_processing/include',
                                          'cython/fast_diffraction_image_processing/include/Eigen'],
                            libraries=['stdc++'],
                            sources=['cython/fast_diffraction_image_processing/streakfinder_extension.pyx',
                                     'cython/fast_diffraction_image_processing/src/adaptions/onda/streakFinder_wrapper.cpp',
                                     'cython/fast_diffraction_image_processing/src/streakFinder.cpp'],
                            language='c++',
                            extra_compile_args=["-std=c++11"])

radial_background_subtraction_ext = Extension(name='radial_background_subtraction_extension',
                            include_dirs=[numpy.get_include(),
                                          'cython/fast_diffraction_image_processing/include',
                                          'cython/fast_diffraction_image_processing/include/Eigen'],
                            libraries=['stdc++'],
                            sources=['cython/fast_diffraction_image_processing/radial_background_subtraction.pyx',
                                     'cython/fast_diffraction_image_processing/src/adaptions/onda/radialBackgroundSubtraction_wrapper.cpp',
                                     'cython/fast_diffraction_image_processing/src/radialBackgroundSubtraction.cpp'],
                            language='c++',
                            extra_compile_args=["-std=c++11"])

setup(ext_modules=cythonize([peakfinder8_ext, streakfinder_ext, radial_background_subtraction_ext]))
