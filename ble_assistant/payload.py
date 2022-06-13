"""
@author: qiudeliang


All rights reserved.
"""
from pydantic import validate_arguments

from ble_assistant.parser import make_frame
from ble_assistant.config import settings
from ble_assistant.blenamedtuple import ErrorCodeTuple


class BasePayload:
    model_id = b''
    opcode = b''
    uplink = None
    uplink_header = None
    uplink_code = b'\xbb'

    @classmethod
    def model_id_just(cls):
        return cls.model_id.ljust(settings.MODEL_SIZE,
                                  b'\x00')

    @classmethod
    def opcode_just(cls):
        return cls.opcode.ljust(settings.OPCODE_SIZE,
                                b'\x00')

    @classmethod
    def downlink(cls, *args, **kwargs):
        model_id = cls.model_id_just()
        opcode = cls.opcode_just()
        header = settings.HEADER_DOWNLINK + model_id + opcode
        payload = cls.downlink_payload(*args, **kwargs)
        return make_frame(header, payload)

    @staticmethod
    @validate_arguments
    def downlink_payload(*args, **kwargs):
        return b''

    @classmethod
    def get_uplink_header(cls):
        if cls.uplink_header:
            return cls.uplink_header
        model_id = cls.model_id_just()
        if cls.uplink:
            opcode = cls.uplink.ljust(
                settings.OPCODE_SIZE,
                b'\x00',
            )
        else:
            opcode = cls.opcode_just()
        header = cls.uplink_code + model_id + opcode
        return header

    @staticmethod
    def uplink_payload(payload: bytes):
        code = int.from_bytes(payload,
                              byteorder=settings.BYTE_ORDER)
        return ErrorCodeTuple(payload.hex(), code)
