#!/usr/bin/python3
import ctypes
import json
import logging
from binascii import hexlify
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Generator

from hexdump import hexdump

logger = logging.getLogger(__name__)

hex_to_str = lambda x: bytearray.fromhex(x.replace(" ", ""))
str_to_hex = lambda x: x.hex()
int32_to_le = lambda x: x.to_bytes(4, byteorder="little")

c_uint8 = ctypes.c_uint8


class ISO14443_PCB_bits(ctypes.LittleEndianStructure):
    _fields_ = [
        ("b1", c_uint8, 1),
        ("b2", c_uint8, 1),
        ("b3", c_uint8, 1),
        ("b4", c_uint8, 1),
        ("b5", c_uint8, 1),
        ("b6", c_uint8, 1),
        ("b7_b8", c_uint8, 2),
    ]


class ISO14443_PCB_IBlock(ctypes.LittleEndianStructure):
    _fields_ = [
        ("block_num", c_uint8, 1),
        ("b2_const_1", c_uint8, 1),
        ("hasNAD", c_uint8, 1),
        ("hasCID", c_uint8, 1),
        ("chaining", c_uint8, 1),
        ("b6_const_0", c_uint8, 1),
        ("blockType", c_uint8, 2),
    ]


class ISO14443_PCB_RBlock(ctypes.LittleEndianStructure):
    _fields_ = [
        ("block_num", c_uint8, 1),
        ("b2_const_1", c_uint8, 1),
        ("b3_const_0", c_uint8, 1),
        ("hasCID", c_uint8, 1),
        ("ACK_NAK", c_uint8, 1),
        ("b6_const_1", c_uint8, 1),
        ("b7_b8_blockType", c_uint8, 2),
    ]


class ISO14443_PCB_SBlock(ctypes.LittleEndianStructure):
    _fields_ = [
        ("b1_const_0", c_uint8, 1),
        ("b2_const_1", c_uint8, 1),
        ("b3_const_0", c_uint8, 1),
        ("b4_hasCID", c_uint8, 1),
        ("DESELECT_WTX", c_uint8, 2),
        ("b7_b8_blockType", c_uint8, 2),
    ]


class ISO14443_PCB(ctypes.Union):
    _fields_ = [
        ("bits", ISO14443_PCB_bits),
        ("iblock", ISO14443_PCB_IBlock),
        ("rblock", ISO14443_PCB_RBlock),
        ("sblock", ISO14443_PCB_SBlock),
        ("asbyte", c_uint8),
    ]


class FrameDirection(str, Enum):
    FROM_READER = "FromReader"
    TO_READER = "ToReader"
    FROM_CARD = "FromCard"
    TO_CARD = "ToCard"


def print_target(target) -> str:
    uid = hexlify(bytearray(target.nti.nai.abtUid)[: target.nti.nai.szUidLen])
    atqa = hexlify(bytearray(target.nti.nai.abtAtqa))
    sak = hexlify(bytearray(target.nti.nai.btSak)[:1])
    ats = hexlify(bytearray(target.nti.nai.abtAts)[: target.nti.nai.szAtsLen])
    result = (
        f"\n\tUID \t: {uid}"
        f"\n\tATQA\t: {atqa}"
        f"\n\tSAK \t: {sak}"
        f"\n\tATS \t: {ats}"
    )
    return result


def print_frame(frame: "Frame") -> None:
    frame_data = frame.data
    if frame_data is None:
        print("frame_data is None")
        frame_data = bytearray()

    print(
        f"{frame.index} - {frame.direction} ({frame.time}):"
        f"\tlen: {len(frame_data)} \tret: {frame.result}"
    )
    if len(frame_data) > 0:
        if not frame.easy_framing:
            PCB = ISO14443_PCB(asbyte=frame_data[0])
            if PCB.bits.b7_b8 == 0b00:
                print(
                    f"\tI-Block"
                    f"\n\t\tPCB: block_num: {PCB.iblock.block_num}"
                    f"\n\t\tb2_const_1: {PCB.iblock.b2_const_1}"
                    f"\n\t\thasNAD: {PCB.iblock.hasNAD}"
                    f"\n\t\thasCID: {PCB.iblock.hasCID}"
                    f"\n\t\tchaining: {PCB.iblock.chaining}"
                    f"\n\t\tb6_const_0: {PCB.iblock.b6_const_0}"
                    f"\n\t\tblockType: {PCB.iblock.blockType}"
                )
            elif PCB.bits.b7_b8 == 0b01:
                print(
                    f"\tRFU"
                    f"\n\t\tPCB: b1: {PCB.bits.b1}"
                    f"\n\t\tb2: {PCB.bits.b2}"
                    f"\n\t\tb3: {PCB.bits.b3}"
                    f"\n\t\tb4: {PCB.bits.b4}"
                    f"\n\t\tb5: {PCB.bits.b5}"
                    f"\n\t\tb6: {PCB.bits.b6}"
                    f"\n\t\tb7_b8: {PCB.bits.b7_b8}"
                )
            elif PCB.bits.b7_b8 == 0b10:
                print(
                    f"\tR-Block"
                    f"\n\t\tPCB: block_num: {PCB.rblock.block_num}"
                    f"\n\t\tb2_const_1: {PCB.rblock.b2_const_1}"
                    f"\n\t\tb3_const_0: {PCB.rblock.b3_const_0}"
                    f"\n\t\thasCID: {PCB.rblock.hasCID}"
                    f"\n\t\tACK_NAK: {PCB.rblock.ACK_NAK}"
                    f"\n\t\tb6_const_1: {PCB.rblock.b6_const_1}"
                    f"\n\t\tb7_b8_blockType: {PCB.rblock.b7_b8_blockType}"
                )
            elif PCB.bits.b7_b8 == 0b11:
                print(
                    f"\tS-Block"
                    f"\n\t\tPCB: b1_const_0: {PCB.sblock.b1_const_0}"
                    f"\n\t\tb2_const_1: {PCB.sblock.b2_const_1}"
                    f"\n\t\tb3_const_0: {PCB.sblock.b3_const_0}"
                    f"\n\t\tb4_hasCID: {PCB.sblock.b4_hasCID}"
                    f"\n\t\tDESELECT_WTX: {PCB.sblock.DESELECT_WTX}"
                    f"\n\t\tb7_b8_blockType: {PCB.sblock.b7_b8_blockType}"
                )
    print(hexdump(frame_data, result="return"))

    # print ("\tPCB \t:", hexlify(bytearray(frame[:1])))
    # print ("\tCID \t:", hexlify(bytearray(frame[1:2])))
    # print ("\tNAD \t:", hexlify(bytearray(frame[2:3])))
    # print ("\tINF \t:", hexlify(bytearray(frame[3:-2])))
    # print ("\tCRC \t:", hexlify(bytearray(frame[-2:])))
    # print ("\tCRC OK \t:", bool(frame[-1] == 0x00 and frame[-2] == 0x00))


class BytearrayEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, bytearray) or isinstance(obj, bytes):
            # bytearray decode to hex string
            return obj.hex()
        return json.JSONEncoder.default(self, obj)


@dataclass
class Frame:
    index: int
    time: int
    data: bytearray
    result: int
    direction: FrameDirection
    easy_framing: bool = True

    def print_data(self) -> None:
        print_frame(self)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        data = self.to_dict()
        return json.dumps(data, cls=BytearrayEncoder)

    def __str__(self) -> str:
        return self.to_json()

    def __repr__(self) -> str:
        return self.to_json()


class FrameLogger:

    def __init__(self, log_fname: str = None, easy_framing: bool = True) -> None:
        self._frames: list[Frame] = []
        self.easy_framing = easy_framing
        self.log_fname = log_fname

    @property
    def frames(self) -> list[Frame]:
        return self._frames

    def add_frame(self, frame: Frame) -> None:
        self._frames.append(frame)

    def add_frame_by_data(
        self, index, time, data, result, direction, easy_framing=None
    ) -> None:
        if easy_framing is None:
            easy_framing = self.easy_framing
        frame = Frame(index, time, data, result, direction, easy_framing)
        self.add_frame(frame)

    def clear(self) -> None:
        self._frames.clear()

    def print(self) -> None:
        for frame in self.frames:
            frame.print_data()

    def save(self) -> None:
        if self.log_fname is None:
            return
        self.save_to(self.log_fname)

    def save_to(self, log_path: str, pretty: bool = False) -> None:
        with open(log_path, "w") as f:
            f.write(self.to_json(pretty))

    def load(self) -> None:
        if self.log_fname is None:
            return
        self.load_from(self.log_fname)

    def load_from(self, log_path: str) -> None:
        self.clear()
        with open(log_path, "r") as f:
            data = json.load(f)
        for item in data:
            item["data"] = bytearray.fromhex(item["data"])
            self.frames.append(Frame(**item))

    def to_json(self, pretty: bool = False) -> str:
        data = [frame.to_dict() for frame in self.frames]
        return json.dumps(data, cls=BytearrayEncoder, indent=4 if pretty else None)


@dataclass
class TargetData:
    abtUid: bytearray
    abtAtqa: bytearray
    btSak: bytearray

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        data = self.to_dict()
        return json.dumps(data, cls=BytearrayEncoder)

    def __str__(self) -> str:
        return self.to_json()

    def __repr__(self) -> str:
        return self.to_json()


class EmulatedInitiator(FrameLogger):

    # for backward compatibility from relay as data source
    def configure(self, option, value) -> None:
        pass

    # for backward compatibility from relay as data source
    def initiator_transceive_bytes(self, data, timeout=0) -> tuple:
        # print("initiator_transceive_bytes: ", data)
        for req in self.frames:
            if req.direction == FrameDirection.FROM_READER and req.data[:5] == data[:5]:
                idx = req.index
                # print("Found req frame: ", idx, req)
                for resp in self.frames:
                    if (
                        resp.direction == FrameDirection.FROM_CARD
                        and resp.index == idx + 1
                    ):
                        # print("Found resp frame: ", resp)
                        return resp.data, resp.result
        print("Can't find frame for request: ", data)
        return b"", 0


def chunks(lst: list, n: int) -> Generator:
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


# class BytearrayDecoder(json.JSONDecoder):


# def cstruct_pprint(s):
#     return "{}: {\t{\t\t{}}}".format(s.__class__.__name__,
#                            ", ".join(["{}: {}".format(field[0],
#                                                       getattr(s,
#                                                               field[0]))
#                                       for field in s._fields_]))


# class FrameEncoder(json.JSONEncoder):
#     def default(self, obj):
#         if isinstance(obj, Frame):
#             return obj.to_json()
#         return json.JSONEncoder.default(self, obj)


# def frame_from_json(json_str: str) -> Frame:
#     j = json.loads(json_str)
#     index = j['index']
#     time = j['time']
#     data = bytearray.fromhex(j['data'])
#     result = j['result']
#     direction = j['direction']
#     easy_framing = j['easy_framing']
#     return Frame(index, time, data, result, direction, easy_framing)
