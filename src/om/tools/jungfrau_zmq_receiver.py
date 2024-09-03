#!/usr/bin/env python

import json
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, List

import typer
import zmq
from typing_extensions import Annotated

from om.lib.logging import log


def listen(
    url: str, data_buffer: List[Dict[str, Any]], max_buffer_len: int, panel_id: int
) -> None:
    # Connect to socket
    context: Any = zmq.Context()
    socket: Any = context.socket(zmq.SUB)
    socket.setsockopt_string(option=zmq.SUBSCRIBE, optval="")
    socket.connect(url)

    # Get first message, store timestamp and clock value
    msg: List[str] = socket.recv_multipart()
    timestamp_start: float = time.time()
    header: Dict[str, Any] = json.loads(msg[0])
    clock_start: int = header["timestamp"]

    clock_period: float = 1.0e-7  # seconds
    i: int = 0
    while True:
        if len(msg) < 2:
            # JF is sending some BS
            msg = socket.recv_multipart()
            continue

        # msg is a list of two strings: [header in json, data in binary]
        header = json.loads(msg[0])
        data: str = msg[1]

        # internal clock value
        clock: int = header["timestamp"]

        # frame timestamp from internal clock value
        timestamp = timestamp_start + (clock - clock_start) * clock_period

        # seems like we need to match "acqIndex" to synchronize panels
        acq_index: int = header["acqIndex"]

        frame_number: int = header["frameNumber"]

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
            log.info(
                f"Worker {panel_id}: {i} frames, {timestamp-timestamp_start}, s since"
                f"start timestamp, {time.time()-timestamp} s delay"
            )

        # Receive next message
        msg = socket.recv_multipart()


def main(
    input_url: Annotated[List[Path], typer.Argument(help="input_url")],
    output_url: Annotated[str, typer.Argument(help="output_url")],
) -> None:
    """
    JUNGFRAU 1M ZMQ receiver. This script reads data from two ZMQ streams at INPUT_URL0
    and INPUT_URL1 produced by Jungfrau 1M detector (one stream for each detector
    module), assembles images from two modules matching their acqIndex and distributes
    latest assembled frames to the OM monitor processing nodes via output ZMQ socket.
    If the OUTPUT_URL is not provided, it defaults to "tcp://127.0.0.1:12321"
    """
    if output_url is None:
        output_url = "tcp://127.0.0.1:12321"

    context: Any = zmq.Context()
    socket: Any = context.socket(zmq.PUSH)
    socket.setsockopt(zmq.CONFLATE, 1)
    socket.bind(output_url)

    data_buffer_p0: List[Dict[str, Any]] = []
    data_buffer_p1: List[Dict[str, Any]] = []

    max_buffer_len: int = 10

    # Start listening process for each panel, process keeps last max_buffer_len frames
    # in buffer list
    p0: Any = threading.Thread(
        target=listen, args=(input_url[0], data_buffer_p0, max_buffer_len, 0)
    )
    p1: Any = threading.Thread(
        target=listen, args=(input_url[1], data_buffer_p1, max_buffer_len, 1)
    )
    p0.start()
    p1.start()

    matched: Deque[Dict[str, Any]] = deque(maxlen=1000)
    i: int = 0
    while True:
        time.sleep(0.05)
        frames_p0: List[Dict[str, Any]] = data_buffer_p0[:]
        frames_p1: List[Dict[str, Any]] = data_buffer_p1[:]

        fr0: Dict[str, Any]
        fr1: Dict[str, Any]
        for fr0 in frames_p0:
            for fr1 in frames_p1:
                if (
                    fr0["acq_index"] == fr1["acq_index"]
                    and fr0["frame_number"] not in matched
                ):
                    if i % 200 == 0:
                        log.info(
                            f'Master: last matched frame id {fr0["acq_index"]}, '
                            f'{time.time() - fr0["timestamp"]} s delay'
                        )
                    i += 1
                    matched.append(fr0["frame_number"])
                    socket.send_pyobj((fr0, fr1))


if __name__ == "__main__":
    typer.run(main)
