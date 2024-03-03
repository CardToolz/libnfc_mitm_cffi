#!/usr/bin/python3
#
#  pn532mitm.py - NXP PN532 Man-In-The_Middle - log conversations between TAG and external reader
#
'''
IP = 172.16.0.1
pi:raspberry
Initiator must be connected to SPI
Target must be connected to UART
config file:
/etc/nfc/libnfc.conf

allow_autoscan = true
allow_intrusive_scan = false
log_level = 1

device.name = "_PN532_SPI"
device.connstring = "pn532_spi:/dev/spidev0.0:1953000"

#device.name = "_PN532_I2c"
#device.connstring = "pn532_i2c:/dev/i2c-1"

device.name = "_PN532_UART"
device.connstring = "pn532_uart:/dev/ttyS0"
'''
from nfc_wrapper import *
from nfc_helper import *
from NFCRelay import *
from libnfc_ffi.libnfc_ffi import libnfc as nfc
from datetime import datetime
import argparse, os, sys
import random

import logging

logger = logging.getLogger(__name__)

fname_main = os.path.basename(__file__)
cwd = os.getcwd()

fname_date = datetime.now().strftime('%H_%M_%S_%d_%m_%Y')
log_fname_default = "%s_%s_log.json" % (fname_main, fname_date)

logs_path = "{}/logs/".format(cwd)
if not os.path.exists(logs_path):
    os.mkdir(logs_path)

easy_framing = True
# target_dev_num_default = 1  # make it command line params
# initiator_dev_num_default = 0  # make it command line params
target_dev_num_default = 0  # make it command line params
initiator_dev_num_default = 1  # make it command line params


def data_hook(direction, data, easy_framing):
    send_fragmented = False

    print ("Data hook, send_fragmented: %s" % send_fragmented)
    return send_fragmented, data

def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', 
                        datefmt='%Y-%m-%d:%H:%M:%S', level=logging.INFO)
    parser = argparse.ArgumentParser(description='LibNFC relay tool')
    parser.add_argument("-l", "--list-devices", dest="list_devices", action='store_true', help="List devices and exit")
    parser.add_argument("-o", "--log-filename", dest="log_fname", default=log_fname_default, type=str, help="Output JSON log filename")
    parser.add_argument("-i", "--initiator", dest="initiator_dev_num", default=initiator_dev_num_default, type=int, help="Reader device number")
    parser.add_argument("-t", "--target", dest="target_dev_num", default=target_dev_num_default, type=int, help="Emulator device number")
    parser.add_argument("-n", "--no-easy-framing", dest="no_easy_framing", action='store_true', help="Do not use easy framing. transfer data as frames instead of APDUs")    
    parser.add_argument("-p", "--print-log", dest="print_log", action='store_true', help="Print log to stdout")   
    parser.add_argument("-H", "--hook-data", dest="hook_data", action='store_true', help="Use data hook function for data processing")
    args = parser.parse_args()

    log_fname = logs_path + args.log_fname
    initiator_dev_num = args.initiator_dev_num
    target_dev_num = args.target_dev_num
    easy_framing = not args.no_easy_framing
    print_log = args.print_log
    list_devs = args.list_devices
    hook_data = args.hook_data

    print ("                   *** LibNFC relay tool ***")
    print ("tag <---> initiator (relay) <---> target (relay) <---> original reader\n")
    print ("%s uses LibNFC ver %s" % (fname_main, get_version_str()))
    if list_devs:
        devs_list = list_devices(True)
        if len(devs_list) < 2:
            print ("Found ", len(devs_list), "... Needed 2.\nExitng...")
        else:
            print ("Initiator dev num:", initiator_dev_num_default)
            print ("Target dev num:", target_dev_num_default)
        nfc.nfc_exit()
        sys.exit()

    r = NFCRelay(initiator_dev_num, target_dev_num, easy_framing=easy_framing, log_fname=log_fname)
    if r is None:
        print ("Can't create NFCRelay object with provided device numbers")
        nfc.nfc_exit()
        sys.exit()

    if hook_data:
        print ("Using data hook")
        r.set_data_hook(data_hook)

    r.reader_setup()
    if r.pndReader is None:
        print ("Can't open reader")
        nfc.nfc_exit()
        sys.exit()

    print ("****** Waiting for source tag/device ******\n")
    tag_count = r.reader_get_targets()
    if tag_count == 0:
        print ("No tag/device found. Exiting...")
        nfc.nfc_exit()
        sys.exit()
    else:
        print ("Found ", tag_count, " tag(s)/device(s)")
        for target in r.passive_targets_list:
            print ("\tTag info:")
            print_target(target)
        print("Selecting 1st target by default")

    r.select_target()
    print("Real target:")
    print_target(r.real_target)

    # r.emulator_prepare_from_target()
    # print("Emulated target:")
    # print_target(r.emulated_target)

    print ("****** Waiting for reader ******\n")    
    r.emulator_setup()
    if r.pndTag is None or r.pndTag.get_last_err() < 0:
        err = r.pndTag.get_last_err()
        print("Can't open emulator: {}, {}".format(err, sErrorMessages[err]))
        # nfc_exit()
        sys.exit()
    print("Emulated target:")
    print_target(r.emulated_target)

    print ("Done, relaying frames now...\n")
    r.relay_frames()

    print("Saving log to file: %s" % log_fname)
    r.fl.save()
    if print_log:
        print ("\n!************** Log Out ***************")
        r.log_print()
    


if __name__ == "__main__":
    main()