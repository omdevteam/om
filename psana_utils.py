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
Utilities for the psana python module.

This module provides utilities that build on the functionality provided by the
psana python module (developed at the SLAC National Laboratories).
"""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)


def first_event_inspection(source):
    """Inspect the content of the first psana event.

    Takes  psana source string (e.g. exp=CXI/cxix....) and inspect the
    content in the first event in the data described by the string.
    Print information about the the content of the event.

    Args:

        source (str): a psana source string (e.g. exp=CXI/cxix....).
    """

    # Import the psana module.
    import psana

    # Print the name of the source.
    print('\n\n')
    print('data source :{}'.format(source))

    print('\n')
    print('Opening dataset...')

    # Open the psana data source.
    dsource = psana.DataSource(source)

    # Print the content of the Epics portion of the data.

    # First the Epics names.
    print('\n')
    print('Epics pv Names:')
    print(dsource.env().epicsStore().pvNames())

    # Then the Epics aliases.
    print('\n')
    print('Epics aliases (the not so confusing ones):')
    print(dsource.env().epicsStore().aliases())

    # Move to the first event in the data.
    print('\n')
    print('Event structure:')
    itr = dsource.events()
    evt = itr.next()

    # Print the content of the first event.
    for k in evt.keys():
        print(
            'Type: {0}   Source: {1}   Alias: {2}'
            'Key: {3}'.format(
                k.type(),
                k.src(),
                k.alias(),
                k.key()
            )
        )

        print('')

    for k in evt.keys():
        print(k)

    # Extract and print the photon energy.
    beam = evt.get(psana.Bld.BldDataEBeamV7, psana.Source('BldInfo(EBeam)'))
    print('Photon energy: %f' % beam.ebeamPhotonEnergy())
