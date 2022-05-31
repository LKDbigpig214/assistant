"""
@author: qiudeliang

All rights reserved.
"""
import xml.etree.ElementTree as ElementTree

from ble_assistant.blenamedtuple import FrameTuple
from ble_assistant.utils import check_sum
from ble_assistant.config import settings

LOG_HEADERS = [settings.HEADER_LOG, settings.HEADER_BALI_LOG]
HEADERS = [settings.HEADER_DOWNLINK] + LOG_HEADERS + settings.HEADER_UPLINK

BYTE_ORDER = settings.BYTE_ORDER
HEADER_SIZE = settings.HEADER_SIZE
MODEL_SIZE = settings.MODEL_SIZE
OPCODE_SIZE = settings.OPCODE_SIZE
PROTOCOL_SIZE = settings.PROTOCOL_SIZE
DATA_LEN_INDEX = settings.DATA_LEN_INDEX
DATA_LEN_SIZE = settings.DATA_LEN_SIZE
PAYLOAD_INDEX = settings.PAYLOAD_INDEX
CHECKSUM_SIZE = settings.CHECKSUM_SIZE
FRAME_MIN_SIZE = settings.FRAME_MIN_SIZE


class LogParser:
    def __init__(self, config_file):
        self.file = config_file
        self.bali_log_type = {}
        self.bali_log_info = {}
        self.bali_log_para = {}
        self.value_type_map = {}
        self.value_type_dict = {'RAW_VALUE_TYPE_U8': 1,
                                'RAW_VALUE_TYPE_U16': 2,
                                'RAW_VALUE_TYPE_U32': 4,
                                'RAW_VALUE_TYPE_S8': 1,
                                'RAW_VALUE_TYPE_S16': 2,
                                'RAW_VALUE_TYPE_S32': 4,
                                'RAW_VALUE_TYPE_FLOAT': 4,
                                'RAW_VALUE_TYPE_ENUM8': 1,
                                'RAW_VALUE_TYPE_ENUM16': 2,
                                'RAW_VALUE_TYPE_ENUM32': 4,
                                'RAW_VALUE_TYPE_BITMAP8': 1,
                                'RAW_VALUE_TYPE_BITMAP16': 2,
                                'RAW_VALUE_TYPE_BITMAP32': 4}
        tree = ElementTree.ElementTree(file=self.file)
        for log_type in tree.findall('./auto/log_type'):
            item = log_type.attrib
            self.bali_log_type[item.get('value')] = item.get('key')

        for i in tree.findall('*/log_info'):
            for j in i.findall('*'):
                item = {**i.attrib, **j.attrib}
                key = f"{item.get('name')}{item.get('value')}"
                self.bali_log_info[key] = item.get('key')

        for i in tree.findall('.//para'):
            for j in i.findall('filed'):
                i.attrib.update(j.attrib)
                value_type = i.attrib.get('log_type') + i.attrib.get('log_info')
                self.value_type_map[value_type] = j.attrib.get('type')
                if 'ENUM' in j.attrib.get('type'):
                    for v in j.findall('item'):
                        key = value_type + v.attrib.get('value')
                        self.bali_log_para[key] = i.get('description') + v.attrib.get('key')
                else:
                    self.bali_log_para[value_type] = i.get('description')

    def parse_log(self, log):
        """parse and return log info"""
        log_type = self.bali_log_type.get(str(log[2] >> 2), '')
        key = f"{log_type}{int.from_bytes(log[2:4], 'big') & 0x3ff}"
        log_info = self.bali_log_info.get(key, '')
        key = log_type + log_info
        value_type = self.value_type_map.get(key)
        log_para = ''
        if value_type:
            desc_len = self.value_type_dict.get(value_type)
            cursor = desc_len
            if 'ENUM' in value_type:
                _ = key + str(int.from_bytes(log[5:5+cursor], 'little'))
                para = self.bali_log_para.get(_, '')
                #
                #
                #
                #
                #
            else:
                para = self.bali_log_para.get(key, '') + str(hex(int.from_bytes(log[5:5+cursor], 'little')))
            log_para = para
        text = []
        for item in [log_type, log_info, log_para]:
            if item:
                text.append(f'[{item}]')
        text.append(f'[raw_data:{log.hex()}]')
        return ''.join(text)

    def parser_raw_data(self, data):
        header = settings.HEADER_BALI_LOG
        if data[1] == 0xd8:
            raw_data = data[:5]
            data_len = 4
        elif data[1] == 0xd9:
            data_len = data[4]
            raw_data = data[:(4 + data_len + 2)]
        else:
            return b''
        payload = self.parse_log(raw_data)
        frame = FrameTuple(header=header,
                           data_len=data_len,
                           payload=payload,
                           checksum=b'',
                           length=len(raw_data),
                           raw_data=raw_data)
        return frame


log_parser = LogParser(settings.BALI_LOG_DESCRIPT)


def is_log_frame(frame):
    header = frame.header[:HEADER_SIZE]
    return header in LOG_HEADERS


def make_frame(header: bytes,
               data: bytes = None) -> bytes:
    if data is None:
        data = b''
    data_len = len(data)
    data_len = data_len.to_bytes(DATA_LEN_SIZE,
                                 BYTE_ORDER)
    data = header + data_len + data
    frame = data + check_sum(data,
                             CHECKSUM_SIZE)
    return frame


def is_ble_dongle_info(header: bytes) -> bool:
    if settings.DEVICE != 'ble':
        return False
    return header == b'\xbb\x00\x00'


def ble_dongle_info_parser(data: bytes):
    st = settings.FRAME_MIN_SIZE - 1
    for i in range(st, len(data)):
        checksum = data[i: i + CHECKSUM_SIZE]
        if checksum == check_sum(data[:i], CHECKSUM_SIZE):
            protocol = data[: PROTOCOL_SIZE]
            data_len = len(data) - PROTOCOL_SIZE - CHECKSUM_SIZE
            payload = data[PROTOCOL_SIZE: -CHECKSUM_SIZE]
            frame = FrameTuple(header=protocol,
                               data_len=data_len,
                               payload=payload,
                               checksum=checksum,
                               length=i + 1,
                               raw_data=data[:i+1])
            return frame
    return b''


def frame_parser(data: bytes):
    if data[:HEADER_SIZE] == settings.HEADER_BALI_LOG:
        return log_parser.parser_raw_data(data)
    if len(data) < settings.FRAME_MIN_SIZE:
        return b''
    protocol = data[: PROTOCOL_SIZE]
    if is_ble_dongle_info(protocol):
        return ble_dongle_info_parser(data)
    data_len = int.from_bytes(data[DATA_LEN_INDEX: PAYLOAD_INDEX],
                              byteorder=BYTE_ORDER)
    check_sum_index = data_len + PAYLOAD_INDEX
    if check_sum_index >= len(data):
        return b''
    end = check_sum_index + CHECKSUM_SIZE
    checksum = data[check_sum_index: end]
    line = data[:check_sum_index]
    if checksum == check_sum(line, CHECKSUM_SIZE):
        payload = data[PAYLOAD_INDEX: PAYLOAD_INDEX + data_len]
        frame = FrameTuple(header=protocol,
                           data_len=data_len,
                           payload=payload,
                           checksum=checksum,
                           length=len(line),
                           raw_data=line)
        return frame
    return b''


def line_parser(data: bytes):
    cursor = 0
    end = len(data)
    res = []
    remain = data
    while cursor < end:
        if cursor + FRAME_MIN_SIZE > end:
            break
        if data[cursor: cursor+HEADER_SIZE] in HEADERS:
            frame = frame_parser(data[cursor:])
            if frame:
                cursor = frame.length + cursor
                remain = data[cursor:]
                res.append(frame)
                continue
        cursor = cursor + 1
    return res, remain


def custom_value_parser(value):
    """get custom value param"""
    length = len(value)
    param = [int(value[i:i+2], base=16)
             for i in range(0, length, 2)]
    return param
