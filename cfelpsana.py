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
Utilities based on the psana python module.

This module provides utilities that build on the functionality provided by the
psana python module.
"""


def psana_obj_from_string(name):
    """Converts a string into a psana object type.

    Takes a string and returns the python object type described by the string.

    Args:

        name (str): a string describing a python type.

    Returns:

        mod (type): the python type described by the string.
    """

    components = name.split('.')
    mod = __import__(components[0])
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


def psana_event_inspection(source):
    """Prints the structure of psana events.

    Takes a psana source string (e.g. exp=CXI/cxix....) and inspects the
    structure of the first event in the data, printing information about
    the the content of the event.

    Args:

        source (str): a psana source string (e.g. exp=CXI/cxix....).
    """

    import psana

    def my_import(name):
        mod = __import__(name)
        components = name.split('.')
        for comp in components[1:]:
            mod = getattr(mod, comp)
        return mod

    def my_psana_from_string(name):
        components = name.split('.')
        mod = __import__(components[0])
        for comp in components[1:]:
            mod = getattr(mod, comp)
        return mod

    print('\n\n')
    print('data source : %s' % source)

    print('\n')
    print('Opening dataset...')
    ds = psana.DataSource(source)

    print('\n')
    print('Epics pv Names (the confusing ones):')
    print(ds.env().epicsStore().pvNames())

    print('\n')
    print('Epics aliases (the not so confusing ones):')
    print(ds.env().epicsStore().aliases())

    print('\n')
    print('Event structure:')
    itr = ds.events()
    evt = itr.next()
    for k in evt.keys():
        print('Type: %s   Source: %s   Alias: %s   Key: %s') % (k.type(), k.src(), k.alias(), k.key())
        print('\n')

    for k in evt.keys():
        print(k)

    beam = evt.get(psana.Bld.BldDataEBeamV7, psana.Source('BldInfo(EBeam)'))
    print('Photon energy: %f' % beam.ebeamPhotonEnergy())


def dirname_from_source_runs(source):
    """Returns a directory name based on a psana source string.

    Takes a psana source string (e.g exp=CXI/cxix....) and returns
    a string that can be used as a subdirectory name or a prefix for files and
    directories.

    Args:

        source (str): a psana source string (e.g. exp=CXI/cxi....).

    Returns:

        dirname (str): a string that can be used as a filename or a prefix .
    """

    start = source.find('run=') + 4
    stop = source.find(':idx')
    if stop == -1:
        stop = len(source)
    runs = source[start:stop]
    nums = runs.split(',')
    if len(nums) == 0:
        nums = runs
    dirname = 'run_' + "_".join(nums)
    return dirname
