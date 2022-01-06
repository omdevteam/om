#!/usr/bin/env python

import h5py
import numpy
import re
import click
from typing import Any, List, TextIO, Tuple


@click.command(context_settings=dict(help_option_names=["-h", "--help"]))
@click.argument(
    "input",
    nargs=1,
    type=click.Path(exists=True),
)
@click.argument(
    "output",
    nargs=1,
    type=click.Path(),
)
@click.option(
    "--start-from",
    "-s",
    "s",
    default=100,
    show_default=True,
    type=int,
    metavar="i",
    help="skip first i images in the file",
)
def main(input: str, output: str, s: int) -> None:
    """
    Make dark calibration files from raw Jungfrau data.

    INPUT: text file containing list of dark files for one panel \n
    OUTPUT: output .h5 file
    """
    const_dark: Tuple[int] = (0, 0, 0)
    fn: str
    try:
        fhandle: TextIO
        with open(input, "r") as fhandle:
            filelist: List[str] = [fn.strip() for fn in fhandle]
    except (IOError, OSError) as exc:
        raise RuntimeError(f"Error reading the {input} source file.") from exc

    n: int = 1024 * 512
    sd: numpy.ndarray = numpy.zeros((3, n), dtype=numpy.float64)
    nd: numpy.ndarray = numpy.zeros((3, n))
    for fn in filelist:
        h5_data_path: str = "/data_" + re.findall("_(f\d+)_", fn)[0]
        f: Any
        with h5py.File(fn, "r") as f:
            n_frames: int = f[h5_data_path].shape[0]
            print("%s frames in %s" % (n_frames, fn))
            frame: numpy.ndarray
            for frame in f[h5_data_path][s:]:
                d: numpy.ndarray = frame.flatten()
                where_gain: List[Tuple[numpy.ndarray]] = [
                    numpy.where((d & 2 ** 14 == 0) & (d > 0)),
                    numpy.where((d & (2 ** 14) > 0) & (d & 2 ** 15 == 0)),
                    numpy.where(d & 2 ** 15 > 0),
                ]
                i: int
                for i in range(3):
                    sd[i][where_gain[i]] += d[where_gain[i]]
                    nd[i][where_gain[i]] += 1

    dark: numpy.ndarray = (sd / nd).astype(numpy.float32)

    if numpy.any(nd == 0):
        print("Some pixels don't have data in all gains:")
        for i in range(3):
            where: List[Tuple[numpy.ndarray]] = numpy.where(nd[i] == 0)
            dark[i][where] = const_dark[i]
            print(f"{len(where[0])} pixels in gain {i} are set to {const_dark[i]}")

    with h5py.File(output, "w") as f:
        f.create_dataset("/gain0", data=dark[0].reshape(512, 1024))
        f.create_dataset("/gain1", data=dark[1].reshape(512, 1024))
        f.create_dataset("/gain2", data=dark[2].reshape(512, 1024))


if __name__ == "__main__":
    main()
