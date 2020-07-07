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
# Copyright 2020 SLAC National Accelerator Laboratory
#
# Based on OnDA - Copyright 2014-2019 Deutsches Elektronen-Synchrotron DESY,
# a research centre of the Helmholtz Association.
"""
ZMQ utilities for broadcasting data from an OnDA monitor.

This module contains classes and functions that allow OnDA monitors to broadcast data
to external programs over a network connection.
"""
from __future__ import absolute_import, division, print_function

import socket
import sys

from typing import Optional

import msgpack
import msgpack_numpy
import numpy
import zmq


class ZmqDataBroadcaster(object):
    """
    See documentation of the '__init__' function.
    """

    def __init__(self, hostname=None, port=None):
        # type: (Optional[str], Optional[int]) -> None
        """
        ZMQ-based data-broadcasting socket for OnDA monitors.

        This class implements a ZMQ PUB socket that can be used to broadcast data. The
        socket supports multiple clients and broadcasts the data using the MessagePack
        protocol. The data is tagged with a label. The socket has no queuing system:
        data that has not been picked up by a receiver will be lost when the next
        broadcast takes place.

        Args:

            hostname (Optional[str]): the hostname or IP address where the socket will
                be opened. If None it will be autodetected. Defaults to None.

            port(Optional[int]): the port where the socket will be opened. If None, the
                socket will be opened at port 12321. Defaults to None.
        """
        self._context = zmq.Context()
        self._sock = self._context.socket(zmq.PUB)
        if hostname is not None:
            bhostname = hostname
        else:
            # If required, uses the python socket module to autodetect the hostname of
            # the machine where the OnDA monitor is running.
            # TODO: Check mypy output for these lines.
            bhostname = [
                (s.connect(("8.8.8.8", 80)), s.getsockname()[0], s.close())
                for s in [socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)]
            ][0][1]
        if port is not None:
            bport = port
        else:
            bport = 12321
        # Sets a high water mark of 1 (A messaging queue that is 1 message long, so no
        # queuing).
        self._sock.set_hwm(1)
        self._sock.bind("tcp://%s:%d" % (bhostname, bport))
        print("Broadcasting data at {0}:{1}".format(bhostname, bport))
        sys.stdout.flush()

    def send_data(self, tag, message):
        # type (str, Hashable) -> None
        """
        Broadcasts data from the ZMQ PUB socket.

        This function broadcasts the data in the form of a MessagePack object. The data
        must be tagged with a label.

        Arguments:

            tag (str): the label that will be attached to the broadcasted data.

            message (Any): a MessagePack-compatible python object.
        """
        self._sock.send(tag.encode(), zmq.SNDMORE)
        msgpack_message = msgpack.packb(message)
        self._sock.send(msgpack_message)


def _patched_encode(obj, chain=None):
    # This function is the 'encode' function from msgpack-numpy, patched to use the
    # 'tobytes' method as opposed to the 'data' one. This is needed for python 2
    # compatibility.
    if isinstance(obj, numpy.ndarray):
        # If the dtype is structured, store the interface description; otherwise,
        # store the corresponding array protocol type string:
        if obj.dtype.kind == "V":
            kind = b"V"
            descr = obj.dtype.descr
        else:
            kind = b""
            descr = obj.dtype.str
        return {
            b"nd": True,
            b"type": descr,
            b"kind": kind,
            b"shape": obj.shape,
            b"data": obj.tobytes(),
        }
    elif isinstance(obj, (numpy.bool_, numpy.number)):
        return {b"nd": False, b"type": obj.dtype.str, b"data": obj.tobytes()}
    elif isinstance(obj, complex):
        return {b"complex": True, b"data": obj.__repr__()}
    else:
        return obj if chain is None else chain(obj)


# Monkey-patches the encode function in msgpack_numpy for python 2 compatibility.
msgpack_numpy.encode = _patched_encode
msgpack_numpy.patch()
