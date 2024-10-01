#!/usr/bin/python3
from argparse import ArgumentParser

from nfc_helper import FrameLogger

# from nfc_ctypes import *
# from nfc_wrapper import *
# from NFCReplay import *


def main():
    parser = ArgumentParser()
    parser.add_argument(
        "-f",
        "--filename",
        dest="log_fname",
        default=0,
        type=str,
        help="Input JSON log filename",
    )
    arguments = parser.parse_args()
    fl = FrameLogger(easy_framing=True, log_fname=arguments.log_fname)
    print(f"Log file name: {fl.log_fname}")
    fl.load()
    print(f"Loaded {len(fl.frames)} frames")
    fl.print()


if __name__ == "__main__":
    main()
