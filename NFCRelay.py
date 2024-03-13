# from nfc_ctypes import *
from nfc_wrapper import *
from nfc_helper import *
from libnfc_ffi import nfc
from time import time, sleep
from enum import Enum

import logging
logger = logging.getLogger(__name__)

hex2str = lambda x: bytearray.fromhex(x.replace(" ", ""))

apple_frame_sequence = []  # Apple specific frame sequence
apple_frame_sequence.append(hex2str('6a  02  c8  01  00  03  00  02  79  00  00  00  00  c2  d8'))
apple_frame_sequence.append(hex2str('52'))
apple_frame_sequence.append(hex2str('93  20'))
apple_frame_sequence.append(hex2str('93  70  00  00  00  00  00  9c  d9'))

def time_ms():
    return int(time() * 1000)

def data_hook_default(direction, data, easy_framing):
    send_fragmented = False
    return send_fragmented, data

class MitmState(Enum):
    FromReader = 0
    ReaderCardHook = 1
    TransceiveCard = 2
    CardReaderHook = 3
    ToReader = 4
    FromReaderFragment = 5


class NFCRelay:
    def __init__(self, initiator_dev_num, target_dev_num, easy_framing=True, log_fname=None):
        self.data_hook = data_hook_default
        self.initiator_dev_num = initiator_dev_num 
        self.target_dev_num = target_dev_num 
        self.easy_framing = easy_framing
        self.pndReader = None # NfcInitiator
        self.pndTag = None # NfcTarget
        self.passive_targets_list = None 
        self.real_target = None 
        self.emulated_target = None
        self.target_modulation = None
        self.targettype = None
        self.timeout = 2000
        self.fl = FrameLogger(easy_framing=easy_framing, log_fname=log_fname)
        self.apple_transport = False
        self.dev_list = list_devices(False)
        if len(self.dev_list) < 2:
            assert False, "Not enough devices found"
        self.initiator_dev = self.dev_list[self.initiator_dev_num]
        self.target_dev = self.dev_list[self.target_dev_num]

    def __del__(self):
        nfc_exit()

    def set_data_hook(self, data_hook):
        self.data_hook = data_hook

    def reader_setup(self):
        self.pndReader = NfcInitiator(self.initiator_dev, verbosity=0)
        self.pndReader.set_property_bool(nfc.NP_EASY_FRAMING, self.easy_framing)
        # self.pndReader.configure(NP_AUTO_ISO14443_4, True)
        # self.pndReader.configure_int(NP_TIMEOUT_COMMAND, self.timeout)
        return True
        
    def reader_get_targets(self, timeout_ms=0):
        tags_count = 0
        start_time = time_ms() 
        while (start_time + timeout_ms > time_ms()) or (timeout_ms == 0):
            if self.apple_transport: # TODO: fix apple transport activation. Transceive bits is not working
                # print ("Apple specific transport(travel) card activation")
                # self.pndReader.configure(nfc.nfc.NP_HANDLE_CRC, False)
                for x in range(0, 2):
                    self.pndReader.transceive_bytes(apple_frame_sequence[0])
                    self.pndReader.transceive_bits(apple_frame_sequence[1], 7)
                self.pndReader.transceive_bytes(apple_frame_sequence[2])
                # # pndReader.initiator_transceive_bytes(str4) # is not necessary

            tags_count, self.passive_targets_list = self.pndReader.list_passive_targets()
            print("Passive targets list: {}".format(self.passive_targets_list))
            # tags_count = len(self.passive_targets_list)
            if tags_count > 0:
                break

        if (start_time + timeout_ms < time_ms()) and (timeout_ms != 0):
            print("Timeout", start_time, time_ms())
        
        return tags_count

    def select_target(self, tag_index=0):
        if tag_index >= len(self.passive_targets_list):
            logger.warning("Wrong tag index")
            return False
        nt = self.passive_targets_list[tag_index]
        initdata = nt.nti.nai.abtUid[0:nt.nti.nai.szUidLen]
        ret, self.real_target = self.pndReader.select_passive_target(initdata=initdata)
        if ret < nfc.NFC_SUCCESS: 
            logger.info('libnfc error, trying again')
            ret, self.real_target = self.pndReader.select_passive_target()
        if ret < nfc.NFC_SUCCESS:
            raise IOError("NFC Error whilst selecting target")
    
    # def emulator_prepare_from_target(self):
    #     target_info = nfc_target_info(self.real_target.nti.nai)
    #     target_modulation = nfc_modulation(self.relay_modtype, self.relay_baud)
    #     self.emulated_target = nfc_target(target_info, target_modulation)
    #     # self.emulated_target = nfc_target()
    #     self.emulated_target.nti.nai.abtAtqa[0] = 0x03
    #     self.emulated_target.nti.nai.abtAtqa[1] = 0x44
    #     self.emulated_target.nti.nai.abtUid[0] = 0x08  # Needed for PN532 emulation start
    #     self.emulated_target.nti.nai.szUidLen = 0x04;  # Shrink UID to eliminate SEGFAULTs
    #     # self.emulated_target.nti.nai.btSak = 0x20
    #     # https://de.wikipedia.org/wiki/Answer_to_Select
    #     # ATS = (05) 75 33 92 03
    #     #       (TL) T0 TA TB TC
    #     #             |  |  |  +-- CID supported, NAD supported
    #     #             |  |  +----- FWI=9 SFGI=2 => FWT=154ms, SFGT=1.21ms
    #     #             |  +-------- DR=2,4 DS=2,4 => supports 106, 212 & 424bps in both directions
    #     #             +----------- TA,TB,TC, FSCI=5 => FSC=64
    #     # It seems hazardous to tell we support NAD if the tag doesn't support NAD but I don't know how to disable it
    #     # PC/SC pseudo-ATR = 3B 80 80 01 01 if there is no historical bytes

    #     self.emulated_target.nti.nai.abtAts[0] = 0x75
    #     self.emulated_target.nti.nai.abtAts[1] = 0x11  # supports 106 baud only if ATS presented on source
    #     self.emulated_target.nti.nai.abtAts[2] = 0x92
    #     self.emulated_target.nti.nai.abtAts[3] = 0x03
    #     self.emulated_target.nti.nai.szAtsLen = 0x04
    #     # self.emulated_target.nti.nai.abtAts[0] = 0x78
    #     # self.emulated_target.nti.nai.abtAts[1] = 0x77 
    #     # self.emulated_target.nti.nai.abtAts[2] = 0x88
    #     # self.emulated_target.nti.nai.abtAts[3] = 0x02
    #     # self.emulated_target.nti.nai.abtAts[4] = 0x80
    #     # self.emulated_target.nti.nai.szAtsLen = 0x05


    #     # if self.real_target.nti.nai.szAtsLen < 4:
    #     #     self.emulated_target.nti.nai.szAtsLen = 0x04
    #     # self.emulated_target.nti.nai.szAtsLen = 0x00;

    #     # print("Target type: " + str(self.targettype))
    #     # if self.targettype == 0x44:
    #     #     self.relay_modtype = NMT_ISO14443B
    #     #     self.relay_baud = NBR_106
    #     # elif self.targettype == 0x04:
    #     #     self.relay_modtype = NMT_ISO14443A
    #     #     self.relay_baud = NBR_106
    #     # elif self.targettype == 0x02:
    #     #     self.relay_modtype = NMT_ISO14443A
    #     #     self.relay_baud = NBR_106
    #     # elif self.targettype == 0x52:
    #     #     self.relay_modtype = NMT_ISO14443A
    #     #     self.relay_baud = NBR_106
    #     #     self.apple_transport = True
    #     # else:
    #     #     print("Unsupported target type")
    #     #     return False
    #     return True

    def emulator_setup(self):
        self.pndTag = NfcTarget(self.target_dev, self.emulated_target)
        if self.pndTag.get_last_err():
            logger.warning("Failed to create target")
            return False
        self.emulated_target = self.pndTag.get_target()
        self.pndTag.set_property_bool(nfc.NP_EASY_FRAMING, self.easy_framing)
        # self.pndTag.configure(nfc.NP_AUTO_ISO14443_4, True)
        # self.pndTag.configure_int(nfc.NP_TIMEOUT_COMMAND, self.timeout) # TODO: Does not work
        return True

    def relay_frames(self, timeout_ms=0):
        if self.pndReader is None or self.pndTag is None:
            logger.warning("Reader or tag not initialized")
            return False
        is_done = False
        index = 0
        state = MitmState.FromReader
        fragmented = False
        self.fl.clear()
        # print("Starting relay")
        self.pndTag.set_property_bool(nfc.NP_EASY_FRAMING, self.easy_framing)
        start_time = time_ms()
        try:
            while (start_time + timeout_ms > time_ms()) or (timeout_ms == 0) and not is_done:
                logger.info("State = {}".format(state))
                self.pndTag.set_property_bool(nfc.NP_EASY_FRAMING, self.easy_framing)
                self.pndReader.set_property_bool(nfc.NP_EASY_FRAMING, self.easy_framing)

                # sleep(0.1)
                if state == MitmState.FromReader:
                    target_recvd, ret = self.pndTag.receive_bytes(timeout=timeout_ms)
                    self.fl.add_frame_by_data(index=index, time=time(), data=target_recvd, result=ret, direction=FrameDirection.FromReader)
                    if ret <= nfc.NFC_SUCCESS:
                        print ("Receive from reader result: ({}) {}".format(ret, sErrorMessages[ret]))
                        is_done = True
                        continue
                    state = MitmState.ReaderCardHook

                elif state == MitmState.ReaderCardHook:
                    if self.data_hook is not None:
                        fragmented, target_recvd = self.data_hook(FrameDirection.FromReader, target_recvd, self.easy_framing)
                    state = MitmState.TransceiveCard

                elif state == MitmState.TransceiveCard: # TODO: implement fragmented transceive
                    self.fl.add_frame_by_data(index=index, time=time(), data=target_recvd, result=ret, direction=FrameDirection.ToCard, easy_framing=self.easy_framing)
                    reader_recvd, ret = self.pndReader.transceive_bytes(target_recvd)
                    index += 1
                    self.fl.add_frame_by_data(index=index, time=time(), data=reader_recvd, result=ret, direction=FrameDirection.FromCard, easy_framing=self.easy_framing)
                    if ret <= nfc.NFC_SUCCESS:
                        print ("Tag/device transceive result: ({}) {}".format(ret, sErrorMessages[ret]))
                        is_done = True
                        continue
                    state = MitmState.CardReaderHook
                elif state == MitmState.CardReaderHook:
                    if self.data_hook is not None:
                        fragmented, reader_recvd = self.data_hook(FrameDirection.FromCard, reader_recvd, self.easy_framing)
                    state = MitmState.ToReader

                elif state == MitmState.ToReader:                
                    if fragmented:
                        ret = self.target_send_fragmented(index=index, data=reader_recvd)
                        # state = MitmState.FromReaderFragment
                        state = MitmState.FromReader
                        # print("fragmented send is done")
                    else:
                        ret = self.pndTag.send_bytes(reader_recvd)
                        self.fl.add_frame_by_data(index=index, time=time(), data=reader_recvd, result=ret, direction=FrameDirection.ToReader, easy_framing=self.easy_framing)
                        state = MitmState.FromReader

                    index += 1
                    # print("ToReader next state: {}".format(state))
                    if ret <= nfc.NFC_SUCCESS:
                        print ("Send to reader result: ({}) {}".format(ret, sErrorMessages[ret]))
                        is_done = True
                        continue

                elif state == MitmState.FromReaderFragment:
                    # print("FromReaderFragment")
                    target_recvd, ret = self.target_receive_fragmented(timeout=timeout_ms)
                    self.fl.add_frame_by_data(index=index, time=time(), data=target_recvd, result=ret, direction=FrameDirection.FromReader, easy_framing=self.easy_framing)
                    # print_frame(self.fl.get_frame_list()[-1])
                    if ret <= nfc.NFC_SUCCESS:
                        print ("Receive from reader result: ({}) {}".format(ret, sErrorMessages[ret]))
                        is_done = True
                        continue
                    # self.pndTag.configure(NP_EASY_FRAMING, self.easy_framing)
                    # sleep(0.05)
                    state = MitmState.ReaderCardHook
                else:
                    print("Unknown state")
                    is_done = True
                    continue

        except AssertionError as error:
            logger.error('???? WTF with the radio frontend ????')
            logger.error(error)

    def log_print(self):
        self.fl.print()

    def target_receive_fragmented(self, timeout=0):
        chunks = []
        is_last_chunk = False

        pcb = ISO14443_PCB()
        pcb.asbyte = 0xA2
        print("XUIIII")
        self.pndTag.set_property_bool(nfc.NP_EASY_FRAMING, False)
        while not is_last_chunk:
            recvd, ret = self.pndTag.target_receive_bytes(timeout)
            # print("Received frame: {}".format(recvd))
            if ret <= nfc.NFC_SUCCESS:
                print ("Receive from reader result: ({}) {}".format(ret, sErrorMessages[ret]))
                return b'', ret
            # pcb.asbyte = recvd[0]
            chunks.append(recvd[1:])
            is_last_chunk = pcb.iblock.chaining == 0
            if not is_last_chunk:
                pcb.iblock.block_num = pcb.iblock.block_num ^ 1 
                self.pndTag.target_send_bytes(bytearray([pcb.asbyte]))
                # print("Sent frame: {}".format(bytearray([pcb.asbyte])))
        # self.pndTag.configure(NP_EASY_FRAMING, self.easy_framing)
        data = b''.join(chunks)
        return data, len(data)


    def target_send_fragmented(self, index, data, fragment_size=200):
        # if fragment_size > 128:
        #     print("Fragment size can't be more than 0x80")
        #     return False
        if len(data) > fragment_size:
            data_chunks = [data[i:i + fragment_size] for i in range(0, len(data), fragment_size)]
        else:
            data_chunks = [data]
        # print("Source data: {}".format(data))
        # print("Data chunks: {}".format(data_chunks))
        # print("Sending {} fragments".format(len(data_chunks)))
        self.easy_framing = False
        self.pndTag.set_property_bool(nfc.NP_EASY_FRAMING, self.easy_framing)

        pcb = ISO14443_PCB(asbyte=0x12) # 0x12/0x13 for phone testing
        # block_num = 0
        for chunk in data_chunks:
            is_last_chunk = chunk == data_chunks[-1]
            pcb.iblock.block_num = pcb.iblock.block_num ^ 1 
            if is_last_chunk: # last chunk
                pcb.iblock.chaining = 0
            # else:

            frame = bytearray([pcb.asbyte]) + chunk
            # print("Sending frame: {}".format(frame))
            # self.pndTag.configure(NP_EASY_FRAMING, False)
            ret = self.pndTag.send_bytes(frame)

            self.fl.add_frame_by_data(index=index, time=time(), data=frame, result=ret, direction=FrameDirection.ToReader, easy_framing=False)
            # print_frame(self.fl.get_frame_list()[-1])
            if ret <= nfc.NFC_SUCCESS:
                print ("Send to reader result: ({}) {}".format(ret, sErrorMessages[ret]))
                return ret
            
            # pcb.iblock.block_num = pcb.iblock.block_num ^ 1 
            # self.pndTag.configure(NP_EASY_FRAMING, False)
            if not is_last_chunk:
                # sleep(0.1)
                recvd, ret = self.pndTag.receive_bytes(timeout=0)
                self.fl.add_frame_by_data(index=index, time=time(), data=recvd, result=ret, direction=FrameDirection.FromReader, easy_framing=False)
                # print_frame(self.fl.get_frame_list()[-1])
                if ret <= nfc.NFC_SUCCESS:
                    print ("Receive from reader result: ({}) {}".format(ret, sErrorMessages[ret]))
                    return ret
            else:
                pass
            
            # sleep fo 0.1 sec to avoid "RF transmission error" on PN532
            sleep(0.05)

        return len(data_chunks)



