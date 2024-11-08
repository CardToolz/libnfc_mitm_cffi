#!/usr/bin/python3

# libnfc ffi bindings test based on nfc-poll example

import multiprocessing
import argparse
import os, time, signal

from libnfc_ffi.libnfc_ffi import ffi, libnfc as nfc


## rudimentary stuff
# max_targets_length = 16
# nt = ffi.new("nfc_target[{}]".format(max_targets_length))
# nm_p = ffi.new("nfc_modulation*", {'nmt': nfc.NMT_ISO14443A, 'nbr': nfc.NBR_106})
# nm = nm_p[0]
# ret = nfc.nfc_initiator_list_passive_targets(device, nm, nt, max_targets_length)
# print("nfc_initiator_list_passive_targets", ret)


nmModulations = ffi.new("nfc_modulation[]", [{'nmt': nfc.NMT_ISO14443A, 'nbr': nfc.NBR_106},
                                              {'nmt': nfc.NMT_ISO14443B, 'nbr': nfc.NBR_106},
                                              {'nmt': nfc.NMT_FELICA, 'nbr': nfc.NBR_212},
                                              {'nmt': nfc.NMT_FELICA, 'nbr': nfc.NBR_424},
                                              {'nmt': nfc.NMT_JEWEL, 'nbr': nfc.NBR_106},
                                              {'nmt': nfc.NMT_ISO14443BICLASS, 'nbr': nfc.NBR_106},])

szModulations = len(nmModulations)
ctx = ffi.new("nfc_context**")
conn_strings = ffi.new("nfc_connstring[16]")
nt_p = ffi.new("nfc_target*")
nfc_target_str = ffi.new("char**")
p = None

nfc.nfc_init(ctx)
c = ctx[0]
if not c:
    print("Unable to initialize libnfc")
    exit(1)

def main():
    global c
    parser = argparse.ArgumentParser(description=os.path.basename(__file__))
    poll_group = parser.add_argument_group('poll options', )
    poll_group.add_argument('--poll', action='store_true', help='Act as '"'nfc-poll utility'"', otherwise just list tags')
    poll_group.add_argument('-p', '--poll-period', type=int, default=150, help='Polling period in ms (0xFF indefinitely)')
    poll_group.add_argument('-n', '--poll-number', type=int, default=5, help='Number of polling attempts')
    parser.add_argument('-v', '--verbosity', action='store_true', help='Increase output verbosity')
    parser.add_argument('-r', '--reader-number', type=int, default=0, help='Reader number to use')
    args = parser.parse_args()

    poll = args.poll
    uiPollNr = args.poll_number
    uiPeriod = args.poll_period // 150 # resulting count of 150ms periods
    verbosity = args.verbosity
    reader_number = args.reader_number
    
    ver_str = ffi.string(nfc.nfc_version()).decode("utf-8")
    print("LibNFC version:", ver_str)

    d = nfc.nfc_list_devices(c, conn_strings, len(conn_strings))
    print("nfc_list_devices", d)
    print("Conn strings:")
    for i in range(d):
        print("\t" + ffi.string(conn_strings[i]).decode('utf-8'))
        


    device = nfc.nfc_open(c, conn_strings[reader_number])
    print("nfc_open", device) 
    nfc.nfc_device_set_property_int(device, nfc.NP_TIMEOUT_COMMAND , 1000)

    device_name = ffi.string(nfc.nfc_device_get_name(device)).decode('utf-8')
    print("NFC reader name:", device_name)

    ret = nfc.nfc_initiator_init(device)
    print("nfc_initiator_init", ret)


    if not poll:
        max_targets_length = 16
        nt = ffi.new("nfc_target[{}]".format(max_targets_length))
        nm_p = ffi.new("nfc_modulation*", {'nmt': nfc.NMT_ISO14443A, 'nbr': nfc.NBR_106})
        nm = nm_p[0]
        ret = nfc.nfc_initiator_list_passive_targets(device, nm, nt, max_targets_length)
        print("nfc_initiator_list_passive_targets", ret)
        dev_count = ret
        for i in range(dev_count):
            _nt = nt[i:i+1]
            print(f"NFC target {i+1} details:")
            nfc.str_nfc_target(nfc_target_str, _nt, verbosity)
            nfc_target_str_str = ffi.string(nfc_target_str[0]).decode('utf-8')
            
            for line in nfc_target_str_str.split('\n'):
                print("\t" + line)
    else:
        print(f"NFC device will poll during {uiPollNr * szModulations * uiPeriod * 150} ms ({uiPollNr} pollings of {uiPeriod * 150} ms for {szModulations} modulations)")
        ret = nfc.nfc_initiator_poll_target(device, nmModulations, szModulations, uiPollNr, uiPeriod, nt_p)
        print("nfc_initiator_poll_target", ret)
        
        if ret > 0:
            nfc.str_nfc_target(nfc_target_str, nt_p, verbosity)
            nfc_target_str_str = ffi.string(nfc_target_str[0]).decode('utf-8')
            
            print("NFC target details:")
            for line in nfc_target_str_str.split('\n'):
                print("\t" + line)

            print("Waiting for tag to be removed...")
            ret = nfc.nfc_initiator_target_is_present(device, nt_p)
            while ret == 0:
                time.sleep(0.05)
                ret = nfc.nfc_initiator_target_is_present(device, nt_p)
                print(".", end="", flush=True)
                time.sleep(0.05)

    print("\nDone")
    nfc.nfc_close(device)
    nfc.nfc_exit(c)



def stop_polling(signum, frame):
    global p
    print("Aborted by signal", signum)
    if p and p.is_alive():
        p.terminate()
        p.join()
    # nfc.nfc_abort_command(dev)

    # nfc.nfc_close(device)
    # print("nfc_close")
    nfc.nfc_exit(ctx[0])

    p.terminate()
    p.join()



if __name__ == "__main__":
    # main()
    # use multiprocessing to handle signals
    # https://stackoverflow.com/questions/492519/timeout-on-a-function-call/14924210#14924210
    signal.signal(signal.SIGINT, stop_polling)
    p = multiprocessing.Process(target=main)
    p.start()
    p.join()

    exit(0)
