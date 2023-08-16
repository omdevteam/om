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
# You should have received a copy of the GNU General Public License along with OnDA.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2020 -2023 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
.PHONY: default build_ext clean docs

default: build_ext

build_ext:
	python setup.py build_ext --inplace

clean:
	rm -rf build
	find src/om/lib/peakfinder8_extension \
		-name "peakfinder8_extension*.so" -delete

#docs:
#	sphinx-apidoc -fMeF --ext-githubpages -o docs src/om
