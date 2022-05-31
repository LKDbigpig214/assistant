"""
@author: qiudeliang

All rights reserved.
"""

import asyncio
import time
import queue

import serial_asyncio

from ble_assistant import logger, dongle_logger, serial_logger
from ble_assistant.parser import (line_parser, is_log_frame,
                                  settings)
from ble_assistant.payload import BasePayload


def info_scan_data(frame):
    if settings.SCAN_PRINT:
        return True
    if settings.DEVCE != 'ble':
        return True
    return frame.header != b'\xdd\x01\x02'


class FlowControl:
    def __init__(self, transport):
        self._transport = transport
        self.read_paused = False
        self.write_paused = False
        self._is_writable_event = asyncio.Event()
        self._is_writable_event.set()

    async def drain(self):
        await self._is_writable_event.wait()

    def pause_reading(self):
        if not self.read_paused:
            self.read_paused = True
            self._transport.pause_reading()

    def resume_reading(self):
        if self.read_paused:
            self.read_paused = False
            self._transport.resume_reading()

    def pause_writing(self):
        if not self.write_paused:
            self.write_paused = True
            self._is_writable_event.clear()

    def resume_writing(self):
        if self.write_paused:
            self.write_paused = False
            self._is_writable_event.set()


class BleProtocol(asyncio.Protocol):
    def __init__(self):
        super().__init__()
        self.queue = queue.Queue()
        self.data = b''
        self.log_text = ''
        self.transport = None
        self.flow = None
        self.port = None
        self.name = None
        self.payload = dict()

    @property
    def info(self):
        if self.name:
            return f'[{self.port}][{self.name}]'
        return f'[{self.port}]'

    def connection_mode(self, transport):
        self.transport = transport
        self.flow = FlowControl(transport)

    def add_payload_to_log(self, frame):
        if isinstance(frame.payload, str):
            payload = frame.payload
        else:
            try:
                payload = frame.payload.decode('utf8')
            except UnicodeDecodeError:
                payload = str(frame.payload)
        self.log_text += payload
        self.log_text = self.log_text[-6000:]
        dongle_logger.info('%s %s', self.info, payload)

    def payload_handle(self, frame):
        item = self.payload.get(frame.header)
        if item:
            payload = item.uplink_payload(frame.payload)
            if hasattr(item, 'name'):
                info = f'{self.info}[{item.name}]'
            else:
                info = self.info
        else:
            payload = frame.payload
            info = self.info
        return info, payload

    def data_received(self, data: bytes):
        serial_logger.info('%s %s', self.info, repr(data))
        self.data += data
        frames, remain = line_parser(self.data)
        self.data = remain
        for frame in frames:
            if is_log_frame(frame):
                self.add_payload_to_log(frame)
                continue
            info, payload = self.payload_handle(frame)
            if info_scan_data(frame):
                logger.info('%s<<< %s', self.info, frame.raw_data.hex())
                if not isinstance(payload, bytes):
                    logger.info('%s<<< %s', info, payload)
            self.queue.put_nowait((payload, frame))

    def connection_lost(self, exc):
        logger.info('%sport closed', self.info)
        if self.flow is not None:
            self.flow.resume_writing()

    def data_write(self, data: bytes):
        logger.info('%s>>> %s', self.info, data.hex())
        self.transport.write(data)

    def pause_writing(self) -> None:
        """
        Called by the transport when the write buffer
        exceeds the high water mark.
        """
        self.flow.pause_writing()

    def resume_writing(self) -> None:
        """
        Called by the transport when the write buffer
        drops below the low water mark.
        """
        self.flow.resume_writing()


class BleComm:
    def __init__(self, loop, port,
                 *args, **kwargs):
        self.loop = loop
        coro = serial_asyncio.create_serial_connection(loop,
                                                       BleProtocol,
                                                       port,
                                                       *args,
                                                       **kwargs)
        transport, protocol = loop.run_until_complete(coro)
        protocol.port = port
        self.transport = transport
        self.protocol = protocol

    def close(self):
        if self.transport.serial:
            self.transport.serial.close()

    def update_payload(self, obj):
        headers = obj.get_uplink_header()
        if isinstance(headers, list):
            for header in headers[:-1]:
                if header not in self.protocol.payload:
                    self.protocol.payload[header] = BasePayload
            self.protocol.payload[headers[-1]] = obj
        else:
            self.protocol.payload[headers] = obj

    async def write(self, data: bytes):
        if self.protocol.flow.write_paused:
            await self.protocol.flow.drain()
        self.protocol.data_write(data)

    async def maybe_waiting(self, endtime):
        while self.protocol.flow.read_paused:
            await asyncio.sleep(0.001)
            endtime += 0.001
        await asyncio.sleep(0.001)
        return endtime

    async def get_frame(self, opcode=None, timeout=2, num=1, or_=False):
        endtime = time.time() + timeout
        res = []
        while True:
            remaining = endtime - time.time()
            if remaining <= 0.0:
                if or_ or not isinstance(opcode, list):
                    return None
                if len(res) < len(opcode):
                    _ = [None] * (len(opcode) - len(res))
                    res.extend(_)
                return res
            endtime = await self.maybe_waiting(endtime)
            if self.protocol.queue.empty():
                continue
            payload, frame = self.protocol.queue.get()
            if not opcode:
                return payload
            if isinstance(opcode, list):
                if frame.header in opcode:
                    if or_:
                        return payload
                    res.append(payload)
                if num == 1 and frame.header == opcode[-1]:
                    if len(res) < len(opcode):
                        _ = [None] * (len(opcode) - len(res))
                        res.pop(-1)
                        res.extend(_)
                        res.append(payload)
                    return res
            elif frame.header == opcode:
                return payload

    def clear_dongle_log(self):
        self.protocol.log_text = ''

    async def get_dongle_log(self):
        res = self.protocol.log_text
        self.clear_dongle_log()
        return res
