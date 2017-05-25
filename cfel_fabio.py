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
Utilities based on the fabio python module.

This module contains utilities based on the fabio python module.
files.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import numpy
import fabio.cbfimage


def read_cbf_from_stream(stream):
    """Reads a cbfimage object out of a data string buffer.

    Read a data string buffer received as a payload from the PETRAIII P11 sender, and creates a cbfimage object from
    it (See the documentation of the fabio python module).

    Args:

       stream (str): a data string buffer received from the PETRAIII P11 sender.

    Returns:

        cbf_obj (fabio.cbfimage): a cbfimage object containing the data extracted
            from the string buffer.
    """

    cbf_obj = fabio.cbfimage.cbfimage()

    cbf_obj.header = {}
    cbf_obj.resetvals()

    infile = stream
    cbf_obj._readheader(infile)
    if cbf_obj.CIF_BINARY_BLOCK_KEY not in cbf_obj.cif:
        err = "Not key %s in CIF, no CBF image in stream" % fabio.cbfobj.CIF_BINARY_BLOCK_KEY
        logger.error(err)
        for kv in cbf_obj.cif.items():
            print("%s: %s" % kv)
        raise RuntimeError(err)
    if cbf_obj.cif[cbf_obj.CIF_BINARY_BLOCK_KEY] == "CIF Binary Section":
        cbf_obj.cbs += infile.read(len(cbf_obj.STARTER) + int(cbf_obj.header["X-Binary-Size"])
                                   - len(cbf_obj.cbs) + cbf_obj.start_binary)
    else:
        if len(cbf_obj.cif[cbf_obj.CIF_BINARY_BLOCK_KEY]) > int(
                cbf_obj.header["X-Binary-Size"]) + cbf_obj.start_binary + len(cbf_obj.STARTER):
            cbf_obj.cbs = cbf_obj.cif[cbf_obj.CIF_BINARY_BLOCK_KEY][:int(cbf_obj.header["X-Binary-Size"]) +
                                                                    cbf_obj.start_binary +
                                                                    len(cbf_obj.STARTER)]
        else:
            cbf_obj.cbs = cbf_obj.cif[cbf_obj.CIF_BINARY_BLOCK_KEY]
    binary_data = cbf_obj.cbs[cbf_obj.start_binary + len(cbf_obj.STARTER):]

    if "Content-MD5" in cbf_obj.header:
        ref = numpy.string_(cbf_obj.header["Content-MD5"])
        obt = fabio.cbfimage.md5sum(binary_data)
        if ref != obt:
            logger.error("Checksum of binary data mismatch: expected %s, got %s" % (ref, obt))

    if cbf_obj.header["conversions"] == "x-CBF_BYTE_OFFSET":
        cbf_obj.data = cbf_obj._readbinary_byte_offset(binary_data).astype(cbf_obj.bytecode).reshape(
            (cbf_obj.dim2, cbf_obj.dim1))
    else:
        raise Exception(IOError, "Compression scheme not yet supported, please contact the author")

    cbf_obj.resetvals()
    # ensure the PIL image is reset
    cbf_obj.pilimage = None
    return cbf_obj
