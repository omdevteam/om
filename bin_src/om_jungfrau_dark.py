#!/usr/bin/env python

import h5py
import numpy as np
import re
import click

CONST_DARK = [0, 0, 0]


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
def main(input, output, s):
    """
    Make dark calibration files from raw Jungfrau data.

    INPUT: text file containing list of dark files for one panel \n
    OUTPUT: output .h5 file
    """

    with open(input) as f:
        fns = [fn.strip() for fn in f.readlines()]

    n = 1024 * 512
    sd = np.zeros((3, n), dtype=np.float64)
    nd = np.zeros((3, n))
    for fn in fns:
        h5_data_path = "/data_" + re.findall("_(f\d+)_", fn)[0]
        with h5py.File(fn) as f:
            n_frames = f[h5_data_path].shape[0]

            print("%s frames in %s" % (n_frames, fn))
            for frame in f[h5_data_path][s:]:
                d = frame.flatten()
                where_gain = [
                    np.where((d & 2 ** 14 == 0) & (d > 0)),
                    np.where((d & (2 ** 14) > 0) & (d & 2 ** 15 == 0)),
                    np.where(d & 2 ** 15 > 0),
                ]
                for i in range(3):
                    sd[i][where_gain[i]] += d[where_gain[i]]
                    nd[i][where_gain[i]] += 1

    dark = (sd / nd).astype(np.float32)

    if np.any(nd == 0):
        print("Some pixels don't have data in all gains: ([gains], [pixels])")
        print(np.where(nd == 0))
        for i in range(3):
            dark[i][np.where(nd[i] == 0)] = CONST_DARK[i]

    with h5py.File(output, "w") as f:
        f.create_dataset("/gain0", data=dark[0].reshape(512, 1024))
        f.create_dataset("/gain1", data=dark[1].reshape(512, 1024))
        f.create_dataset("/gain2", data=dark[2].reshape(512, 1024))


if __name__ == "__main__":
    main()
