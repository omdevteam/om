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

from argparse import ArgumentParser
from os.path import exists


def parse_onda_cmdline_args():
    parser = ArgumentParser(prog='mpirun [MPI OPTIONS] onda.py', description='OnDA - Online Data Analysis')
    parser.add_argument('source', type=str, help="data source (file list, psana source string, etc.")
    parser.add_argument('-i', '--ini', type=str, default='monitor.ini',
                        help="monitor.ini file (default: monitor.ini), see monitor.ini.template for an example")
    parser.add_argument('-d', '--debug', action='store_true', default=False,
                        help='debug mode, shows full traceback and additional information for errors.')
    args = parser.parse_args()

    # check that args.ini exists
    if not exists(args.ini):
        raise NameError('ini file does not exist: {0}'.format(args.ini))
    return args
