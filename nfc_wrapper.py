#!/usr/bin/python3
# to trace shared lib calls use "ltrace --library="*libnfc*" python3 ./nfc_wrapper.py"
import logging
import time
from inspect import getmembers
from pprint import pprint

from hexdump import *

import nfc_helper
from libnfc_ffi import ffi, nfc

logger = logging.getLogger(__name__)

# def eprint(*args, **kwargs):
#     print('\033[91m', *args, '\033[0m', file=sys.stderr, **kwargs)

# def log(*args, **kwargs):
#     print(*args, **kwargs)


def cdata_dict(cd):
    if isinstance(cd, ffi.CData):
        try:
            return ffi.string(cd)
        except TypeError:
            try:
                return [cdata_dict(x) for x in cd]
            except TypeError:
                return {k: cdata_dict(v) for k, v in getmembers(cd)}
    else:
        return cd


def pprint_cdata(cd, print_hex=False):
    logger.debug("cdata info: {}, sizeof()={}".format(cd, ffi.sizeof(cd)))
    logger.debug(cdata_dict(cd))
    if print_hex:
        c = ffi.buffer(cd)
        logger.debug(hexdump(c, result="return"))


def hexbytes(data):
    return " ".join(["{:02x}".format(x) for x in data])


sErrorMessages = {
    # /* Chip-level errors (internal errors, RF errors, etc.) */
    nfc.NFC_SUCCESS: "Success",
    nfc.NFC_EIO: "Input / Output Error",
    nfc.NFC_EINVARG: "Invalid argument(s)",
    nfc.NFC_EDEVNOTSUPP: "Not Supported by Device",
    nfc.NFC_ENOTSUCHDEV: "No Such Device",
    nfc.NFC_EOVFLOW: "Buffer Overflow",
    nfc.NFC_ETIMEOUT: "Timeout",
    nfc.NFC_EOPABORTED: "Operation Aborted",
    nfc.NFC_ENOTIMPL: "Not (yet) Implemented",
    nfc.NFC_ETGRELEASED: "Target Released",
    nfc.NFC_EMFCAUTHFAIL: "Mifare Authentication Failed",
    nfc.NFC_ERFTRANS: "RF Transmission Error",
    nfc.NFC_ECHIP: "Device's Internal Chip Error",
}

cffi_chars_to_str = lambda c: ffi.string(c).decode("utf-8")

NFC_DEVICE_LIST_SIZE = 10
NFC_DEVICE_LIST = ffi.new("nfc_connstring[{0}]".format(NFC_DEVICE_LIST_SIZE))
MAX_FRAME_LEN = 264

ctx = ffi.new("nfc_context**")
nfc.nfc_init(ctx)
c = ctx[0]


def get_version_str():
    return cffi_chars_to_str(nfc.nfc_version())


def nfc_exit():
    nfc.nfc_exit(c)


def list_devices(verbose=False):
    result = []
    num_devices = nfc.nfc_list_devices(c, NFC_DEVICE_LIST, NFC_DEVICE_LIST_SIZE)
    for i in range(num_devices):
        result.append(NFC_DEVICE_LIST[i])
    if verbose:
        print("libNFC devices ({}):".format(num_devices))
        for i in range(num_devices):
            dev = nfc.nfc_open(c, result[i])
            devname = cffi_chars_to_str(nfc.nfc_device_get_name(dev))
            print("\tNo: {}\t\t{}".format(i, devname))
            # nfc.nfc_close(dev)
    return result


class NfcDevice(object):
    def __init__(
        self,
        devdesc=None,
        verbosity=0,
        modtype=nfc.NMT_ISO14443A,
        baudrate=nfc.NBR_106,
        timeout=5000,
    ):
        logger.debug("NfcDevice init")
        self._device = nfc.nfc_open(c, devdesc)
        self._device_name = cffi_chars_to_str(nfc.nfc_device_get_name(self._device))
        self._txbytes = ffi.new("uint8_t[{}]".format(MAX_FRAME_LEN))
        self._rxbytes = ffi.new("uint8_t[{}]".format(MAX_FRAME_LEN))
        self.verbosity = verbosity
        self.nm = ffi.new("nfc_modulation*")
        self.nm.nmt = modtype
        self.nm.nbr = baudrate
        self.timeout = timeout
        self.last_err = nfc.NFC_SUCCESS
        # time.sleep(0.5) # 50ms removes error "libnfc.driver.pn532_spi Unable to wait for SPI data. (RX)"

    def get_last_err(self):
        logger.debug(
            "get_lasst_err: {}, {}".format(self.last_err, sErrorMessages[self.last_err])
        )
        return self.last_err

    def set_modulation(self, modtype, baudrate):
        logger.debug("set_modulation")
        self.nm.nmt = modtype
        self.nm.nbr = baudrate

    def set_property_bool(self, option, value: bool):
        logger.debug("set_property_bool")
        """Configures the NFC device options"""
        ret = nfc.nfc_device_set_property_bool(self._device, option, value)
        self.last_err = ret
        if ret < nfc.NFC_SUCCESS:
            logger.warning(
                "set_property_bool() setting option {0} to {1}".format(option, value)
            )
        return ret

    def set_property_int(self, option, value: int):
        logger.debug("set_property_int")
        """Configures the NFC device options"""
        ret = nfc.nfc_device_set_property_int(self._device, option, value)
        self.last_err = ret
        if ret < nfc.NFC_SUCCESS:
            logger.warning(
                "set_property_int() setting option {0} to {1}".format(option, value)
            )
        return ret


class NfcTarget(NfcDevice):
    def __init__(self, devdesc, targettype=None, timeout=5000, verbosity=0):
        super().__init__(devdesc, verbosity)
        ret = self.init(targettype, timeout)
        logger.debug("Target dev name: {}".format(self._device_name))
        self.last_err = ret

    def init(self, targettype=None, timeout=0):
        logger.debug("NfcTarget init")
        if targettype == None:
            targettype = self.prepare_emulated_target()

        ret = nfc.nfc_target_init(
            self._device, targettype, self._rxbytes, MAX_FRAME_LEN, timeout
        )
        self.last_err = ret

        if ret < nfc.NFC_SUCCESS:
            logger.warning("init() error: {}, {}".format(ret, sErrorMessages[ret]))
        self._nt = targettype
        return ret

    def get_target(self):
        return self._nt

    def prepare_emulated_target(self):
        logger.debug("prepare_emulated_target")
        abtAtqa = [0x03, 0x04]
        abtUid = [0x08, 0xba, 0xdf, 0x0d] # abtUid[0] = 0x08 Needed for PN532 emulation 
        abtAts = [0x75, 0x33, 0x92, 0x03]
        # https://de.wikipedia.org/wiki/Answer_to_Select
        # ATS = (05) 75 33 92 03
        #       (TL) T0 TA TB TC
        #             |  |  |  +-- CID supported, NAD supported
        #             |  |  +----- FWI=9 SFGI=2 => FWT=154ms, SFGT=1.21ms
        #             |  +-------- DR=2,4 DS=2,4 => supports 106, 212 & 424bps in both directions
        #             +----------- TA,TB,TC, FSCI=5 => FSC=64
        # It seems hazardous to tell we support NAD if the tag doesn't support NAD but I don't know how to disable it
        # PC/SC pseudo-ATR = 3B 80 80 01 01 if there is no historical bytes

        nti = ffi.new("nfc_target_info*")
        nti.nai.abtAtqa = abtAtqa
        nti.nai.abtUid = abtUid
        nti.nai.szUidLen = len(abtUid)
        nti.nai.btSak = 0x20
        nti.nai.abtAts = abtAts
        nti.nai.szAtsLen = len(abtAts)

        nt = ffi.new("nfc_target*")
        nt.nm = self.nm[0]
        nt.nti = nti[0]
        logger.info("Emulated target:")
        logger.info(nfc_helper.print_target(nt))
        return nt

    def receive_bytes(self, timeout=None):
        logger.debug("receive_bytes")
        if timeout is None:
            timeout = self.timeout
        ret = nfc.nfc_target_receive_bytes(
            self._device, self._rxbytes, MAX_FRAME_LEN, timeout
        )
        self.last_err = ret

        if ret < nfc.NFC_SUCCESS:
            logger.warning("receive_bytes() error{}: ".format(ret))
        data = bytearray(ffi.buffer(self._rxbytes, ret))
        logger.info("T<I[%2X]: %s" % (len(data), hexbytes(data)))
        return data, ret

    def send_bytes(self, txbytes, timeout=None):
        logger.debug("send_bytes")
        if timeout is None:
            timeout = self.timeout
        logger.info("T>I[%2X]: %s" % (len(txbytes), hexbytes(txbytes)))
        tx_len = len(txbytes)
        self._txbytes[0:tx_len] = txbytes
        ret = nfc.nfc_target_send_bytes(self._device, self._txbytes, tx_len, timeout)
        self.last_err = ret

        if ret < nfc.NFC_SUCCESS:
            logger.warning("send_bytes() error: {}".format(ret))
        return ret

    def receive_bits(self, *args, **kwargs):
        raise NotImplementedError("receive_bits() not implemented")

    def send_bits(self, *args, **kwargs):
        raise NotImplementedError("send_bits() not implemented")


class NfcInitiator(NfcDevice):
    def __init__(self, devdesc=None, verbosity=0):
        super().__init__(devdesc, verbosity)
        ret = self.init()
        logger.info("Initiator dev name:{}".format(self._device_name))
        self.last_err = ret

    def init(self):
        logger.debug("NfcInitiator init()")
        ret = nfc.nfc_initiator_init(self._device)
        self.last_err = ret

        if ret < nfc.NFC_SUCCESS:
            logger.warning("init() error{}: ".format(ret))

        # self.set_property_bool(nfc.NP_HANDLE_CRC, False)
        # self.set_property_bool(nfc.NP_ACCEPT_INVALID_FRAMES, True)
        # self.set_property_bool(nfc.NP_AUTO_ISO14443_4, False)
        # self.set_property_bool(nfc.NP_EASY_FRAMING, False)
        self.set_property_int(nfc.NP_TIMEOUT_COMMAND, 5000)
        self.set_property_int(nfc.NP_TIMEOUT_COM, 1000)
        self.set_property_int(nfc.NP_TIMEOUT_ATR, 1000)
        # self.set_property_bool(nfc.NP_INFINITE_SELECT, False)

    def list_passive_targets(self):
        logger.debug("list_passive_targets()")
        result = []
        max_targets_length = 16
        nt = ffi.new("nfc_target[{}]".format(max_targets_length))
        # time.sleep(0.5) # 50ms removes error "libnfc.driver.pn532_spi Unable to wait for SPI data. (RX)"
        ret = nfc.nfc_initiator_list_passive_targets(
            self._device, self.nm[0], nt, max_targets_length
        )
        self.last_err = ret

        if ret < nfc.NFC_SUCCESS:
            logger.warning(
                "list_passive_targets() error: {}".format(sErrorMessages[ret])
            )
        for target_n in range(ret):
            result.append(nt[target_n])
        logger.info("list_passive_targets() num_targets: {}".format(ret))
        logger.info(*(nfc_helper.print_target(target) for target in result))
        # time.sleep(0.5) # 50ms removes error "libnfc.driver.pn532_spi Unable to wait for SPI data. (RX)"
        return ret, result

    def select_passive_target(self, initdata=None):
        logger.debug("select_passive_target")
        nt = ffi.new("nfc_target*")
        if initdata is None:
            ret = nfc.nfc_initiator_select_passive_target(
                self._device, self.nm[0], ffi.NULL, 0, nt
            )
        else:
            ret = nfc.nfc_initiator_select_passive_target(
                self._device, self.nm[0], initdata, len(initdata), nt
            )
        self.last_err = ret

        if ret < nfc.NFC_SUCCESS:
            logger.warning(
                "select_passive_target() error: {}, {}".format(ret, sErrorMessages[ret])
            )
        return ret, nt

    def deselect_target(self, *args, **kwargs):
        raise NotImplementedError("deselect_target() not implemented")

    def select_dep_target(self, *args, **kwargs):
        raise NotImplementedError("select_dep_target() not implemented")

    def poll_targets(self, *args, **kwargs):
        raise NotImplementedError("poll_targets() not implemented")

    def transceive_bytes(self, txbytes, timeout=None):
        logger.debug("transceive_bytes()")
        if timeout is None:
            timeout = self.timeout
        logger.info("I>T[%2X]: %s" % (len(txbytes), hexbytes(txbytes)))
        tx_len = len(txbytes)
        self._txbytes[0:tx_len] = txbytes
        rx_len = MAX_FRAME_LEN
        ret = nfc.nfc_initiator_transceive_bytes(
            self._device, self._txbytes, tx_len, self._rxbytes, rx_len, timeout
        )
        self.last_err = ret

        data = bytearray(ffi.buffer(self._rxbytes, ret))
        logger.info("I<T[%2X]: %s" % (len(data), hexbytes(data)))
        return data, ret

    def transceive_bits(self, *args, **kwargs):
        raise NotImplementedError("transceive_bits() not implemented")


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")
    print("logger.level: ", logger.level)
    print(__name__)
    print("logger.name: ", logger.name)

    version = get_version_str()
    print("libNfc version:", version)
    dev_list = list_devices(verbose=True)

    i = NfcInitiator(dev_list[1], verbosity=1)
    # print(i._device_name)
    # try:
    #     i.set_property_bool(nfc.NP_HANDLE_PARITY+100, True)
    # except Exception as e:
    #     print("Exception test:", e)

    res, nt = i.list_passive_targets()
    # for k in range(res):
    #     nfc_helper.print_target(nt[k])
    # print("list_passive_targets() res: ", res)
    # pprint_cdata(nt)
    if res == 0:
        print("No tags found")
        exit(0)
    initdata = nt[0].nti.nai.abtUid[0 : nt[0].nti.nai.szUidLen]
    # print("initdata: ", initdata, len(initdata))
    try:
        res = i.select_passive_target(initdata=initdata)
    except Exception as e:
        print("Exception test:", e)
        res = i.select_passive_target()

    # res = i.select_passive_target()
    print("select_passive_target() res: ", res)
    nt = res
    # print("nt: ", nt)
    # print("nt.nti.nai.abtUid: ", nt.nti.nai.abtUid)
    # print("nt.nti.nai.szUidLen: ", nt.nti.nai.szUidLen)
    # print("nt.nti.nai.abtAtqa: ", nt.nti.nai.abtAtqa)
    # print("nt.nti.nai.btSak: ", nt.nti.nai.btSak)
    # print("nt.nti.nai.abtAts: ", nt.nti.nai.abtAts)
    # print("nt.nti.nai.szAtsLen: ", nt.nti.nai.szAtsLen)
    print("select_passive_target: nt: ", nt, type(nt))
    # pprint_cdata(nt)
    # for i in range(nt.nti.nai.szAtsLen):
    #     print("nt.nti.nai.szAtsLen[{}]: {:02x}".format(i, nt.nti.nai.abtAts[i]))
    # for i in range(nt.nti.nai.szUidLen):
    #     print("nt.nti.nai.szUidLen[{}]: {:02x}".format(i, nt.nti.nai.abtUid[i]))

    t = NfcTarget(dev_list[0], verbosity=1)
    data, data_len = t.receive_bytes()
    # print("receive_bytes() ret: ", data, len)
    data, data_len = i.transceive_bytes(data)
    # print("transceive_bytes() ret: ", ret)
    data_len = t.send_bytes(data)
