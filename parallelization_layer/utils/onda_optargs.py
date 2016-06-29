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


import argparse
import os


def parse_onda_cmdline_args():

    parser = argparse.ArgumentParser(prog='mpirun [MPI OPTIONS] onda.py', description='OnDA - Online Data Analysis')
    parser.add_argument('source', type=str, help="data source (file list, psana source string, etc.")
    parser.add_argument('-i', '--ini', type=str, default='monitor.ini',
                        help="monitor.ini file (default: monitor.ini), see monitor.ini.template for an example")

    args = parser.parse_args()

    # check that args.ini exists
    if not os.path.exists(args.ini):
        raise NameError('ini file does not exist: ' + args.ini)
    return args
