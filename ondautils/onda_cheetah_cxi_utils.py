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


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import h5py


class OpenFile:

    def __init__(self, filename):

        self.filename = filename

        try:
            self.fh = h5py.File(filename, 'w')
        except IOError:
            raise RuntimeError('Error opening {0} file'.format(filename))

        self.index = 0

        self.initialized = False

    def __del__(self):

        self.fh.close()


class CXIWriter:

    def __init__(self):

        self.open_files = []






