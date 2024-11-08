#!/usr/bin/python3
#
#  nfc_mitm.py - NXP PN532 Man-In-The_Middle - APDU log recorder/mutator/replayer between TAG and external reader
#
'''
IP = 172.16.0.1
pi:raspberry
Initiator (card reader) must be connected to SPI
Target (card emulator) must be connected to UART

libnfc config file example:
/etc/nfc/libnfc.conf

allow_autoscan = true
allow_intrusive_scan = false
log_level = 1

device.name = "_PN532_SPI"
device.connstring = "pn532_spi:/dev/spidev0.0:1953000"

device.name = "_PN532_UART"
device.connstring = "pn532_uart:/dev/ttyS0"
'''
# from nfc_ctypes import *
import output_redirect
from nfc_wrapper import *
from nfc_helper import *
from NFCRelay import *
from libnfc_ffi.libnfc_ffi import libnfc as nfc
import apdu_processor

from datetime import datetime
import os
import threading
import argparse 


logger = logging.getLogger(__name__)

fname_main = os.path.basename(__file__)
cwd = os.getcwd()

fname_date = datetime.now().strftime('%H_%M_%S_%d_%m_%Y')
log_fname_default = "%s_%s_APDU_log.json" % (fname_main, fname_date)

logs_path = "{}/logs/".format(cwd)
if not os.path.exists(logs_path):
    os.mkdir(logs_path)


target_dev_num_default = 0  # make it command line params
initiator_dev_num_default = 1  # make it command line params




def main():
    parser = argparse.ArgumentParser(description='LibNFC APDU re(p)lay tool')
    parser.add_argument("-l", "--list-devs", dest="list_devs", action='store_true', help="List devices and exit")
    parser.add_argument("-o", "--log-fname", dest="log_fname", default=log_fname_default, type=str, help=f"Output JSON log filename. Default: {log_fname_default}")
    parser.add_argument("-n", "--no-easy-framing", dest="no_easy_framing", action='store_true', help="Do not use easy framing. Transfer data as frames instead of APDUs")    
    parser.add_argument("-p", "--print-log", dest="print_log", action='store_false', help="Print APDU log to stdout after completion")   
    parser.add_argument("-H", "--hook-data", dest="hook_data", action='store_true', help="Use data hook function for data processing")
    parser.add_argument("-L", "--log-level", dest="log_level", default="ERROR", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Set the logging level")
    parser.add_argument("-t", "--target", dest="target_dev_num", default=target_dev_num_default, type=int, help=f"Emulator device number. Default: {target_dev_num_default}")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-i", "--initiator", dest="initiator_dev_num", default=initiator_dev_num_default, type=int, help=f"Reader device number. Default: {initiator_dev_num_default}")
    group.add_argument("-r", "--replay", dest="log_replay", type=str, help="Replay APDU data from a recorded log file instead of using a reader. exclusive with -i option")
    args = parser.parse_args()

    log_level = getattr(logging, args.log_level)
    logging.getLogger().setLevel(log_level)

    current_log_level = logging.getLogger().getEffectiveLevel()
    logger.info(f"Current log level: {logging.getLevelName(current_log_level)}")

    log_fname = logs_path + args.log_fname
    easy_framing = not args.no_easy_framing
    print_log = args.print_log
    list_devs = args.list_devs
    hook_data = args.hook_data
    target_dev_num = args.target_dev_num

    if args.log_replay:
        log_replay = args.log_replay
        initiator_dev_num = -1 # for log replay mode
        if not os.path.exists(log_replay):
            print ("Replay log file not found: %s" % log_replay)
            return
    else:
        initiator_dev_num = args.initiator_dev_num
        log_replay = None


    print ("                   *** LibNFC re(p)lay tool ***")
    print ("tag <---> initiator (relay) <---> target (relay) <---> original reader\n")
    print ("%s uses LibNFC ver %s" % (fname_main, get_version_str()))
    if list_devs:
        devs_list = list_devices(True)
        if len(devs_list) < 2:
            print ("Found ", len(devs_list), "... Needed 2.\nExitng...")
        else:
            print ("Initiator dev num:", initiator_dev_num_default)
            print ("Target dev num:", target_dev_num_default)
        return
    

    r = NFCRelay(initiator_dev_num, target_dev_num, easy_framing=easy_framing, log_fname=log_fname)
    if r is None:
        print ("Can't create NFCRelay object with provided device numbers")
        return

    if hook_data:
        print ("Using data hook")
        r.set_data_hook(apdu_processor.data_hook)

    ret = r.reader_setup(log_fname=log_replay)
    if r.pndReader is None:
        print ("Can't open reader/source file")
        return

    if ret:
        print ("****** Waiting for source tag/device ******")
        tag_count = r.reader_get_targets()
        if tag_count == 0:
            print ("No tag/device found. Exiting...")
            return
        else:
            print ("Found ", tag_count, " tag(s)/device(s)")
            for target in r.passive_targets_list:
                print ("\tTag info: " + print_target(target), flush=True)
            print("Selecting 1st target by default")

            r.select_target()
            print("Real target:" + print_target(r.real_target), flush=True)
    else:
        print("Using log file: %s as a data source" % log_replay)
        
    print ("****** Waiting for a reader ******\n")    
    ret = r.emulator_setup()
    if (r.pndTag is None) or (not ret):
        print ("Can't open emulator or poll timeout")
        return

    print("Emulated target:" + print_target(r.emulated_target), flush=True)

    print("Done, relaying frames now...\n")

    try:
        r.relay_frames()
    except Exception as e:
        logger.error(f"Error relaying frames: {e}")

    print("Relaying finished")
    print("Tag emulator reported:", r.pndTag.get_last_err(), sErrorMessages[r.pndTag.get_last_err()])
    print("Reader reported:", r.pndReader.get_last_err(), sErrorMessages[r.pndReader.get_last_err()])

    print("Saving log to file: %s" % log_fname)
    r.fl.save()
    if print_log:
        print ("\n************** Log Out ***************")
        r.log_print()


class MainThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        main()


if __name__ == "__main__":
    
    main_thread = MainThread()
    main_thread.daemon = True
    main_thread.start()

    try:
        while main_thread.is_alive():
            main_thread.join(1)
    # while True:
    #     sleep(0.1)
    except KeyboardInterrupt:
        print("Exiting...")
        exit(0)
    except Exception as e:
        print("Exiting due to exception: %s" % e)
        exit(1)
    finally:
        print("Exiting...")