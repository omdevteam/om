#!/usr/bin/env python

import zmq
import time
import json
import numpy
import socket
import click

from collections import deque
import threading


def listen(url, data_buffer, max_buffer_len, panel_id):
    # Connect to socket
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.setsockopt_string(option=zmq.SUBSCRIBE, optval="")
    socket.connect(url)

    # Get first message, store timestamp and clock value
    msg = socket.recv_multipart()
    timestamp_start = time.time()
    header = json.loads(msg[0])
    clock_start = header["timestamp"]

    clock_period = 1.0e-7  # seconds
    i = 0
    while True:
        if len(msg) < 2:
            # JF is sending some BS
            msg = socket.recv_multipart()
            continue

        # msg is a list of two strings: [header in json, data in binary]
        header = json.loads(msg[0])
        data = msg[1]

        # internal clock value
        clock = header["timestamp"]

        # frame timestamp from internal clock value
        timestamp = timestamp_start + (clock - clock_start) * clock_period

        # seems like we need to match "acqIndex" to synchronize panels
        acq_index = header["acqIndex"]

        frame_number = header["frameNumber"]

        # keep last max_buffer_len frames in buffer list
        if len(data_buffer) == max_buffer_len:
            data_buffer.pop(0)
        data_buffer.append(
            {
                "data": data,
                "timestamp": timestamp,
                "acq_index": acq_index,
                "frame_number": frame_number,
            }
        )

        # speed reporting
        i += 1
        if i % 100 == 0:
            print(
                "Worker %d: %d frames, %.1f s since start timestamp, %.2f s delay"
                % (panel_id, i, timestamp - timestamp_start, time.time() - timestamp)
            )

        # Receive next message
        msg = socket.recv_multipart()


@click.command(context_settings=dict(help_option_names=["-h", "--help"]))
@click.argument(
    "input_url",
    nargs=2,
    type=str,
    metavar="INPUT_URL0 INPUT_URL1",
)
@click.argument(
    "output_url",
    nargs=1,
    type=str,
    required=False,
)
def main(input_url, output_url):
    """
    JUNGFRAU 1M ZMQ receiver. This script reads data from two ZMQ streams at INPUT_URL0
    and INPUT_URL1 produced by Jungfrau 1M detector (one stream for each detector
    module), assembles images from two modules matching their acqIndex and distributes
    latest assembled frames to the OM monitor processing nodes via output ZMQ socket.
    If the OUTPUT_URL is not provided, it defaults to "tcp://127.0.0.1:12321"
    """
    if output_url is None:
        output_url = "tcp://127.0.0.1:12321"

    context = zmq.Context()
    socket = context.socket(zmq.PUSH)
    socket.setsockopt(zmq.CONFLATE, 1)
    socket.bind(output_url)

    data_buffer_p0 = []
    data_buffer_p1 = []

    max_buffer_len = 10

    # Start listening process for each panel, process keeps last max_buffer_len frames in buffer list
    p0 = threading.Thread(
        target=listen, args=(input_url[0], data_buffer_p0, max_buffer_len, 0)
    )
    p1 = threading.Thread(
        target=listen, args=(input_url[1], data_buffer_p1, max_buffer_len, 1)
    )
    p0.start()
    p1.start()

    matched = deque(maxlen=1000)
    i = 0
    while True:
        time.sleep(0.05)

        frames_p0 = data_buffer_p0[:]
        frames_p1 = data_buffer_p1[:]

        for fr0 in frames_p0:
            for fr1 in frames_p1:
                if (
                    fr0["acq_index"] == fr1["acq_index"]
                    and fr0["frame_number"] not in matched
                ):
                    if i % 200 == 0:
                        print(
                            "Master: last matched frame id %d, %.2f s delay"
                            % (fr0["acq_index"], time.time() - fr0["timestamp"])
                        )
                    i += 1
                    matched.append(fr0["frame_number"])
                    socket.send_pyobj((fr0, fr1))


if __name__ == "__main__":
    main()
