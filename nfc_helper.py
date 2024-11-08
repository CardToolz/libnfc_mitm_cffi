#!/usr/bin/python3
import ctypes
import binascii
from hexdump import *
from typing import List, Callable, Generic, TypeVar
from enum import Enum
from dataclasses import dataclass
import dataclasses
import json

import functools
import logging



logger = logging.getLogger(__name__)

def log_debug(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        args_repr = [repr(a) for a in args]
        kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
        signature = ", ".join(args_repr + kwargs_repr)
        logger.debug(f"function {func.__name__}() called with args {signature}")
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            logger.exception(f"Exception raised in {func.__name__}. exception: {str(e)}")
            raise e
    return wrapper


hex2str = lambda x: bytearray.fromhex(x.replace(" ", ""))
str2hex = lambda x: x.hex()
int32tole = lambda x: x.to_bytes(4, byteorder='little')

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
    _fields_ = [("bits", ISO14443_PCB_bits),
                ("iblock", ISO14443_PCB_IBlock),
                ("rblock", ISO14443_PCB_RBlock),
                ("sblock", ISO14443_PCB_SBlock),                
                ("asbyte", c_uint8)]

def cstruct_pprint(s):
    return "{}: {\t{\t\t{}}}".format(s.__class__.__name__,
                           ", ".join(["{}: {}".format(field[0],
                                                      getattr(s,
                                                              field[0]))
                                      for field in s._fields_]))

def print_target(target):
    ret = '\n'
    ret += ("\tUID \t: {}\n".format(binascii.hexlify(bytearray(target.nti.nai.abtUid)[:target.nti.nai.szUidLen])))
    ret += ("\tATQA\t: {}\n".format(binascii.hexlify(bytearray(target.nti.nai.abtAtqa))))
    ret += ("\tSAK \t: {}\n".format(binascii.hexlify(bytearray(target.nti.nai.btSak)[:1])))
    ret += ("\tATS \t: {}\n".format(binascii.hexlify(bytearray(target.nti.nai.abtAts)[:target.nti.nai.szAtsLen])))
    return str(ret)

def print_frame(frame):
        # frame_data = frame['data'].encode('utf-8')
        # frame_len = len(frame_data)
        # result = frame['result']
        if frame.data == None:
            print('frame_data is None')
            frame_data = bytearray()
        frame_data = frame.data
        frame_len = len(frame_data)
        result = frame.result
        time = frame.time
        direction = frame.direction
        index = frame.index
        print('{} - {} ({}):\tlen: {} \tret: {}'.format(index, direction, time, frame_len, result))
        if frame_len != 0:
            if not frame.easy_framing:
                PCB = ISO14443_PCB(asbyte=frame_data[0])
                if PCB.bits.b7_b8 == 0b00:
                    print('\tI-Block')
                    print('\t\tPCB: block_num: {}\n\t\tb2_const_1: {}\n\t\thasNAD: {}\n\t\thasCID: {}\n\t\tchaining: {}\n\t\tb6_const_0: {}\n\t\tblockType: {}'.format(
                        PCB.iblock.block_num, PCB.iblock.b2_const_1, PCB.iblock.hasNAD, PCB.iblock.hasCID, PCB.iblock.chaining, PCB.iblock.b6_const_0, PCB.iblock.blockType
                    ))
                elif PCB.bits.b7_b8 == 0b01:
                    print('\tRFU')
                    print('\t\tPCB: b1: {}\n\t\tb2: {}\n\t\tb3: {}\n\t\tb4: {}\n\t\tb5: {}\n\t\tb6: {}\n\t\tb7_b8: {}'.format(
                        PCB.bits.b1, PCB.bits.b2, PCB.bits.b3, PCB.bits.b4, PCB.bits.b5, PCB.bits.b6, PCB.bits.b7_b8
                    ))
                elif PCB.bits.b7_b8 == 0b10:
                    print('\tR-Block')
                    print('\t\tPCB: block_num: {}\n\t\tb2_const_1: {}\n\t\tb3_const_0: {}\n\t\thasCID: {}\n\t\tACK_NAK: {}\n\t\tb6_const_1: {}\n\t\tb7_b8_blockType: {}'.format(
                        PCB.rblock.block_num, PCB.rblock.b2_const_1, PCB.rblock.b3_const_0, PCB.rblock.hasCID, PCB.rblock.ACK_NAK, PCB.rblock.b6_const_1, PCB.rblock.b7_b8_blockType
                    ))
                elif PCB.bits.b7_b8 == 0b11:
                    print('\tS-Block')            
                    print('\t\tPCB: b1_const_0: {}\n\t\tb2_const_1: {}\n\t\tb3_const_0: {}\n\t\tb4_hasCID: {}\n\t\tDESELECT_WTX: {}\n\t\tb7_b8_blockType: {}'.format(
                        PCB.sblock.b1_const_0, PCB.sblock.b2_const_1, PCB.sblock.b3_const_0, PCB.sblock.b4_hasCID, PCB.sblock.DESELECT_WTX, PCB.sblock.b7_b8_blockType
                    ))
        print(hexdump(frame_data, result='return'))
 
    # print ("\tPCB \t:", binascii.hexlify(bytearray(frame[:1])))
    # print ("\tCID \t:", binascii.hexlify(bytearray(frame[1:2])))
    # print ("\tNAD \t:", binascii.hexlify(bytearray(frame[2:3])))
    # print ("\tINF \t:", binascii.hexlify(bytearray(frame[3:-2])))
    # print ("\tCRC \t:", binascii.hexlify(bytearray(frame[-2:])))
    # print ("\tCRC OK \t:", bool(frame[-1] == 0x00 and frame[-2] == 0x00))

def obj_dict(obj):
    return obj.__dict__

class BytearrayEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytearray) or isinstance(obj, bytes):
            # bytearray decode to hex string
            return obj.hex()
        return json.JSONEncoder.default(self, obj)

# class BytearrayDecoder(json.JSONDecoder):


class FrameDirection(str, Enum):
    FromReader = "FromReader"
    ToReader = "ToReader"
    FromCard = "FromCard"
    ToCard = "ToCard"


@dataclass
class Frame:
    index: int
    time : int
    data: bytearray
    result: int
    direction: FrameDirection
    easy_framing: bool = True
    def print_data(self):
        print_frame(self)
        # print_frame(self, 0)
        pass
    def __iter__(self): 
        yield from{
            'index': self.index,
            'time': self.time,
            'data': self.data,
            'result': self.result,
            'direction': self.direction,
            'easy_framing': self.easy_framing
        }.items()
    def __dict__(self) -> dict:
        return dataclasses.asdict(self)
    def to_json(self):
        d = dict(self)
        print(d)
        return json.dumps(d, cls=BytearrayEncoder)
    def __str__(self) -> str:
        return self.to_json()
    def __repr__(self) -> str:
        return self.to_json()

class FrameEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Frame):
            return obj.to_json()
        return json.JSONEncoder.default(self, obj)
    
# def frame_from_json(self, json_str):
#     j = json.loads(json_str)
#     self.index = j['index']
#     self.time = j['time']
#     self.data = j['data']
#     self.result = j['result']
#     self.direction = j['direction']
#     return self


def frame_from_json(json_str):
    j = json.loads(json_str)
    index = j['index']
    time = j['time']
    data = bytearray.fromhex(j['data'])
    result = j['result']
    direction = j['direction']
    easy_framing = j['easy_framing']
    return Frame(index, time, data, result, direction, easy_framing)

class FrameList:
    def __init__(self, easy_framing=True):
        self.frame_list: List[Frame] = []
        # self.easy_framing = False
        self.easy_framing = easy_framing
        pass

    def clear(self):
        self.frame_list.clear()
        
    def add_frame(self, frame):
        self.frame_list.append(frame)

    def add_frame_by_data(self, index, time, data, result, direction, easy_framing=None):
        if easy_framing == None:
            easy_framing = self.easy_framing
        frame = Frame(index, time, data, result, direction, easy_framing)
        self.add_frame(frame)

    def get_frame(self, index):
        return self.frame_list[index]
    
    def get_frame_list(self):
        return self.frame_list
        
    def get_frame_list_len(self):
        return len(self.frame_list)
    


@dataclass
class TargetData:
    abtUid: bytearray
    abtAtqa: bytearray
    btSak: bytearray
    def __iter__(self): 
        yield from{
            'abtUid': self.abtUid,
            'abtAtqa': self.abtAtqa,
            'btSak': self.btSak
        }.items()
    def __dict__(self) -> dict:
        return dataclasses.asdict(self)
    def to_json(self):
        d = dict(self)
        print(d)
        return json.dumps(d, cls=BytearrayEncoder)
    def __str__(self) -> str:
        return self.to_json()
    def __repr__(self) -> str:
        return self.to_json()

class FrameLogger(FrameList):
    log_fname: str = None

    def __init__(self, easy_framing=True, log_fname=None):
        FrameList.__init__(self, easy_framing)
        self.easy_framing = easy_framing
        self.log_fname = log_fname

    def print(self):
        for frame in self.frame_list:
            # print(type(frame))
            frame.print_data()

    def to_json(self):
        return json.dumps([frame.__dict__() for frame in self.frame_list], cls=BytearrayEncoder)
    
    def to_json_pretty(self):
        return json.dumps([frame.__dict__() for frame in self.frame_list], cls=BytearrayEncoder, indent=4)
        
    def save_to(self, log_fname):
        with open(log_fname, 'w') as f:
            j = self.to_json_pretty()
            f.write(j)

    def save(self):
        if self.log_fname == None:
            return
        self.save_to(self.log_fname)

    def load_from(self, log_fname):
        self.clear()
        with open(log_fname, 'r') as f:
            j = f.read()
            a = json.loads(j)
            for frame in a:
                self.add_frame(frame_from_json(json.dumps(frame)))

    def load(self):
        if self.log_fname == None:
            return
        self.load_from(self.log_fname)


class EmulatedInitiator(FrameLogger):
    def configure(self, option, value): # for backward compatibility from relay as data source
        pass 

    def transceive_bytes(self, data, timeout=0): # for backward compatibility from relay as data source
        # print("initiator_transceive_bytes: ", data)
        for req in self.frame_list:
            if (req.direction == FrameDirection.FromReader) and (req.data[:5] == data[:5]):
                idx = req.index
                # print("Found req frame: ", idx, req)
                for resp in self.frame_list:
                    if resp.direction == FrameDirection.FromCard and resp.index == idx+1:
                        # print("Found resp frame: ", resp)
                        return resp.data, resp.result
        print("Can't find frame for request: ", data)
        return b'', 0

    def set_property_bool(self, option, value: bool):
        logger.debug("set_property_bool")
        pass
    
    def set_property_int(self, option, value: int):
        logger.debug("set_property_int")
        pass

    def get_last_err(self):
        return 0

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]
