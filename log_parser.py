#!/usr/bin/python3

# from nfc_ctypes import *
# from nfc_wrapper import *
from nfc_helper import *
# from NFCReplay import *
from argparse import ArgumentParser

def main():
    parser = ArgumentParser()
    parser.add_argument("-f", "--filename", dest="log_fname", default=0, type=str, help="Input JSON log filename")
    fl = FrameLogger(easy_framing=True, log_fname=parser.parse_args().log_fname)
    print ("Log file name: %s" % fl.log_fname)
    fl.load()
    print ("Loaded %d frames" % fl.get_frame_list_len())
    fl.print()

if __name__ == "__main__":
    main()