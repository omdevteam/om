#    This file is part of cfelpyutils.
#
#    cfelpyutils is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    cfelpyutils is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with cfelpyutils.  If not, see <http://www.gnu.org/licenses/>.
"""
Utilities for writing multi-event files in the CXIDB format.

This module contains utilities to write files that adhere to the CXIDB file format: 

http://www.cxidb.org/cxi.html .
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import namedtuple
import h5py
import numpy

_CXISimpleEntry = namedtuple('SimpleEntry', ['path', 'data', 'overwrite'])


def _assign_data_type(data):
    if isinstance(data, numpy.ndarray):
        data_type = data.dtype
    elif isinstance(data, bytes):
        data_type = numpy.dtype('S256')
    else:
        data_type = type(data)

    return data_type


class _Stack:
    def __init__(self, path, data, axes, compression, chunk_size):

        self._data_type = _assign_data_type(data)

        if isinstance(data, (bytes, int, float)):
            self._data_shape = (1,)
        else:
            self._data_shape = data.shape

        self._data_to_write = data
        self.path = path
        self._axes = axes
        self._compression = compression

        if chunk_size is None:
            self._chunk_size = (1,) + self._data_shape
        else:
            self._chunk_size = chunk_size

    def is_there_data_to_write(self):

        if self._data_to_write is not None:
            return True
        else:
            return False

    def write_initial_slice(self, file_handle, max_num_slices):

        file_handle.create_dataset(self.path, shape=(max_num_slices,) + self._data_shape,
                                   dtype=self._data_type,
                                   maxshape=(max_num_slices,) + self._data_shape,
                                   compression=self._compression, chunks=self._chunk_size)

        dataset = file_handle[self.path]
        dataset[0] = self._data_to_write

        if self._axes is not None:
            file_handle[self.path].attrs['axes'] = self._axes

        self._data_to_write = None

    def write_slice(self, file_handle, curr_slice):

        file_handle[self.path][curr_slice] = self._data_to_write

        self._data_to_write = None

    def append_data(self, data):

        if self._data_to_write is not None:
            raise RuntimeError('Cannot append data to the stack entry at {}. The previous slice has not been written '
                               'yet.'.format(self.path))

        data_type = _assign_data_type(data)

        if data_type != self._data_type:
            raise RuntimeError('The type of the input data does not match what is already present in the stack.')

        if isinstance(data, (bytes, int, float)):
            curr_data_shape = (1,)
        else:
            curr_data_shape = data.shape

        if curr_data_shape != self._data_shape:
            raise RuntimeError('The shape of the input data does not match what is already present in the stack.')

        self._data_to_write = data

    def finalize(self, file_handle, curr_slice):

        if self._data_to_write is not None:
            raise RuntimeError('Cannot finalize the stack at {}, there is data waiting to be '
                               'written.'.format(self.path))

        final_size = curr_slice

        file_handle[self.path].resize((final_size,) + self._data_shape)


def _validate_data(data):
    if not isinstance(data, (bytes, int, float, numpy.ndarray)):
        raise RuntimeError('The CXI Writer only accepts numpy objects, numbers and ascii strings.')


class CXIWriter:
    """Writing of multi-event CXIDB files.

    Implements a simple low-level CXIDB file format writer for multi event files. it allows the user to write data
    "stacks" in the CXIDB files, making sure that the entries in all stacks are synchronized. 
    
    A CXI Writer instance manages one file. A user can add a stack to a CXI Writer instance with the
    add_stack_to_writer function, which also writes the first entry in the stack. The user can then add to the writer 
    all the stacks that he wants in the file. Once all stacks are added, the user initializes them  with the
    initialize_stacks function. After initialization, no more stacks can be added. Instead, entries can be appended to
    the existing stacks, using the append_data_to_stack function. 
    
    A "slice" (a set of synced entries in all the stacks in the file) can be written to the a file only after an entry
    has been appended to all stacks in the file. Conversely, after an entry has been appended to a stack, the user
    cannot append another entry before a slice is written. This ensures synchronization of the data in all the stacks.
    
    A file can be closed at any time. In any case, the writer will not allow a file to contain more than the
    number_of_entries specified during instantiation.
    
    Simple non-stack entries can be written to the file at any time, before or after stack initialization (provided of
    course that the file is open). Entries and stacks will general never be overwritten unless the overwrite parameter
    is set to True.
    
    Example of usage of the stack API:
    
    c1 = 0
    c2 = 0

    f1 = CXIWriter('test1.h5', )
    f2 = CXIWriter('test2.h5', )

    f1.add_stack_to_writer('detector1', '/entry_1/detector_1/data', numpy.random.rand(2, 2),
                           'frame:y:x')
    f2.add_stack_to_writer('detector2', '/entry_1/detector_1/data', numpy.random.rand(3, 2),
                           'frame:y:x', compression=False, chunk_size=(1,3,2))

    f1.add_stack_to_writer('counter1', '/entry_1/detector_1/count', c1)
    f2.add_stack_to_writer('counter2', '/entry_1/detector_1/count', c2)

    f1.write_simple_entry('detectorname1', '/entry_1/detector_1/name', 'FrontCSPAD')
    f2.write_simple_entry('detectorname2', '/entry_1/detector_1/name', 'BackCSPAD')

    f1.initialize_stacks()
    f2.initialize_stacks()

    a = numpy.random.rand(2, 2)
    b = numpy.random.rand(3, 2)

    c1 += 1
    c2 += 2

    f1.append_data_to_stack('detector1', a)
    f2.append_data_to_stack('detector2', b)

    f1.append_data_to_stack('counter1', c1)
    f2.append_data_to_stack('counter2', c2)

    f1.write_stack_slice_and_increment()
    f2.write_stack_slice_and_increment()

    f1.create_link('detectorname1', '/name')
    f2.create_link('detectorname2', '/name')

    f1.close_file()
    f2.close_file()
    """

    def __init__(self, filename, max_num_slices=5000):
        """Instantiates a CXI Writer, managing one file.
        
        Instantiates a CXI Writer, responsible for writing data into one file.
        
        Args:
            
            filename (str): name of the file managed by the CXI Writer
            
            max_num_slices (int): maximum number of slices for the stacks in the file (default 5000)
        """

        self._cxi_stacks = {}
        self._pending_simple_entries = []
        self._simple_entries = {}
        self._intialized = False
        self._curr_slice = 0
        self._max_num_slices = max_num_slices
        self._file_is_open = False
        self._initialized = False

        try:
            self._fh = h5py.File(filename, 'w')
            self._file_is_open = True

        except OSError:
            raise RuntimeError('Error opening the cxi file: ', filename)

    def _write_simple_entry(self, entry):

        if entry.path in self._fh:
            if entry.overwrite is True:
                del self._fh[entry.path]
            else:
                raise RuntimeError('Cannot write the entry. Data is already present at the specified path.')

        self._fh.create_dataset(entry.path, data=entry.data)

    def add_stack_to_writer(self, name, path, initial_data, axes=None, compression=True, chunk_size=None,
                            overwrite=True):
        """Adds a new stack to the file.
        
        Adds a new stack to the CXI Writer instance. The user must provide a name for the stack, that will identify
        the stack in all subsequents operations. The user must also provide the data that will be written as the
        initial entry in the stack (initial_data). This initial entry is used to set the size and type of data that the
        stack will hold and these parameters are in turn be used to validate all data that is subsequently appended to
        the stack.
        
        Args:
            
            name (str): stack name.
            
            path (str): path in the hdf5 file where the stack will be written.
            
            initial_data (Union[numpy.ndarray, bytes, int, float]: initial entry in the stack. It gets written to the 
            stack as slice 0. Its characteristics are used to validate all data subsequently appended to the stack.
            
            axes (bytes): the 'axes' attribute for the stack, as defined by the CXIDB file format.
            
            compression (Union[None, bool,str]): compression parameter for the stack. This parameters works in the same
            way as the normal compression parameter from h5py. The default value of this parameter is True.
            
            chunk_size (Union[None, tuple]): HDF5 chuck size for the stack. If this parameter is set to None, the
            CXI writer will compute a chuck size automatically (this is the default behavior). Otherwise, the writer 
            will use the provided tuple to set the chunk size.
            
            overwrite (bool): if set to True, a stack already existing at the same location will be overwritten. If set
            to False, an attempt to overwrite a stack will raise an error.
        """

        _validate_data(initial_data)

        if name in self._cxi_stacks:
            raise RuntimeError('A stack with the provided name already exists.')

        if self._initialized is True:
            raise RuntimeError('Adding stacks to the writer is not possible after initialization.')

        for entry in self._cxi_stacks:
            if path == self._cxi_stacks[entry].path:
                if overwrite is True:
                    del (self._cxi_stacks[entry])
                else:
                    raise RuntimeError('Cannot write the entry. Data is already present at the specified path.')

        new_stack = _Stack(path, initial_data, axes, compression, chunk_size)
        self._cxi_stacks[name] = new_stack

    def write_simple_entry(self, name, path, data, overwrite=False):
        """Writes a simple, non-stack entry in the file.
        
        Writes a simple, non-stack entry in the file, at the specified path. A simple entry can be written at all times,
        before or after the stack initialization. THe user must provide a name that identifies the entry for further
        operations (for example, creating a link).
        
        Args:
        
            name (str): entry name
        
            path (str): path in the hdf5 file where the entry will be written.
            
            data (Union[numpy.ndarray, bytes, int, float]): data to write
            
            overwrite (bool): if set to True, an entry already existing at the same location will be overwritten. If set
            to False, an attempt to overwrite an entry will raise an error.
        """

        _validate_data(data)

        if name in self._simple_entries:
            raise RuntimeError('An entry with the provided name already exists.')

        if path in self._fh:
            if overwrite is True:
                del (self._fh[path])
            else:
                raise RuntimeError('Cannot create the the entry. An entry already exists at the specified path.')

        new_entry = _CXISimpleEntry(path, data, overwrite)

        if self._initialized is not True:
            self._pending_simple_entries.append(new_entry)
        else:
            self._write_simple_entry(new_entry)

        self._simple_entries[name] = new_entry

    def create_link(self, name, path, overwrite=False):
        """Creates a link to a stack or entry.
         
        Creates a link in the file, at the path specified, pointing to the stack or the entry identified by the
        provided name. If a link or entry already exists at the specified path, it is deleted and replaced only if the
        value of the overwrite parameter is True.
         
        Args:
             
            name (str): name of the stack or entry to which the link points.
        
            path (str): path in the hdf5 where the link is created.
             
            overwrite (bool): if set to True, an entry already existing at the same location will be overwritten. If set
            to False, an attempt to overwrite an entry will raise an error.
        """

        if path in self._fh:
            if overwrite is True:
                del (self._fh[path])
            else:
                raise RuntimeError('Cannot create the link. An entry already exists at the specified path.')

        try:
            link_target = self._fh[self._cxi_stacks[name].path]
        except KeyError:
            try:
                link_target = self._fh[self._simple_entries[name].path]
            except:
                raise RuntimeError('Cannot find an entry or stack with the proveded name.')

        self._fh[path] = link_target

    def create_link_to_group(self, group, path, overwrite=False):
        """Creates a link to an HDF5 group.
        
        Creates a link to an HDF5 group (as opposed to a simple entry or stack). If a link or entry already exists at
        the specified path, it is deleted and replaced only if the value of the overwrite parameter is True.

        Args: 

            group (str): internal HDF5 path of the group to which the link points.
        
            path (str): path in the hdf5 where the link is created.
             
            overwrite (bool): if set to True, an entry already existing at the same location will be overwritten. If set
            to False, an attempt to overwrite an entry will raise an error.
        """

        if path in self._fh:
            if overwrite is True:
                del (self._fh[path])
            else:
                raise RuntimeError('Cannot create the link. An entry already exists at the specified path.')

        try:
            link_target = self._fh[group]
        except KeyError:
            raise RuntimeError('Cannot create the link. The group to which the link points does not exist.')

        self._fh[path] = link_target

    def initialize_stacks(self):
        """Initializes the stacks.
        
        Initializes the stacks in the CXI Writer instance. This fixes the number and type of stacks in the file. No 
        stacks can be added to the CXI Writer after initialization.
        """

        if self._file_is_open is not True:
            raise RuntimeError('The file is closed. Cannot initialize the file.')

        if self._initialized is True:
            raise RuntimeError('The file is already initialized. Cannot initialize file.')

        for entry in self._cxi_stacks.values():
            entry.write_initial_slice(self._fh, self._max_num_slices)

        self._curr_slice += 1

        for entry in self._pending_simple_entries:
            self._write_simple_entry(entry)
        self._pending_simple_entries = []

        self._initialized = True

    def append_data_to_stack(self, name, data):
        """Appends data to a stack.
        
        Appends data to a stack, validating the data to make sure that the data type and size match the previous entries
        in the stack. Only one entry can be appended to each stack before writing a slice across all stacks with
        the write_slice_and_increment.
        
        Args:
            
            name (str): stack name, defining the stack to which the data will be appended.
            
            data (Union[numpy.ndarray, bytes, int, float]: data to write. The data will be validated against the type
            and size of previous entries in the stack.
        """

        _validate_data(data)

        if self._initialized is False:
            raise RuntimeError('Cannot append to a stack before initialization of the file.')

        if name not in self._cxi_stacks:
            raise RuntimeError('Cannot append to stack {}. The stack does not exists.'.format(name))

        try:
            self._cxi_stacks[name].append_data(data)
        except RuntimeError as e:
            raise RuntimeError('Error appending to stack {}: {}'.format(name, e))

    def write_stack_slice_and_increment(self):
        """Writes a slice across all stacks and resets the writer for the next slice.
        
        Writes a slice across all stacks in the file. It checks that an entry has been appended to each stack, and
        writes all the entries on top of the relevant stacks in one go. If an entry is missing in a stack, the function
        will raise an error. After writing the slice, the function resets the writer to allow again appending data to 
        the stacks.
        """

        if self._file_is_open is not True:
            raise RuntimeError('The file is closed. The slice cannot be written.')

        if self._initialized is False:
            raise RuntimeError('Cannot write slice. The file is not initialized.')

        if self._curr_slice >= self._max_num_slices:
            raise RuntimeError('The file already holds the maximum allowed number of slices, and should be closed')

        for entry in self._cxi_stacks.values():
            if entry.is_there_data_to_write is False:
                raise RuntimeError('The slice is incomplete and will not be written. The following stack is not '
                                   'present in the current slice:', entry.path)

        for entry in self._cxi_stacks.values():
            entry.write_slice(self._fh, self._curr_slice)

        self._curr_slice += 1

    def get_file_handle(self):
        """Access to the naked h5py file handle.
        
        This function allows access to the a naked h5py handle for the file managed by the CXI Writer. This allowa
        operations on the file that are not covered by  CXI Writer API. Use it at your own risk.
        
        Returns:
            
            fh (h5py.File): an h5py file handle to the file managed by the writer.
        """

        if self._file_is_open is not True:
            raise RuntimeError('The file is closed. Cannot get the file handle.')

        return self._fh

    def stacks_are_initialized(self):
        """Checks if stacks are initialized.
        
        Checks the status of the stacks in the file and returns the status to the user.
        
        Returns:
            
            status (bool): True if the stacks are initialized, False otherwise
        """

        return self._initialized

    def file_is_full(self):
        """Checks if the file is full.
        
        Checks if the file is full (i.e. the maximum number of slices have already been written), and returns the
        information to the user.
        
        Returns:
            
            status (bool): True if the file is full, False otherwise.
        """

        return self._curr_slice >= self._max_num_slices

    def close_file(self):
        """Closes the file.
        
        Closes the file for writing, ending all writing operations.
        """

        if self._file_is_open is not True:
            raise RuntimeError('The file is already closed. Cannot close the file.')

        for entry in self._cxi_stacks.values():
            entry.finalize(self._fh, self._curr_slice)

        self._fh.close()

        self._file_is_open = False
