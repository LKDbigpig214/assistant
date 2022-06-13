"""
@author: qiudeliang

All rights reserved.
"""

import inspect
import asyncio

from ble_assistant.config import settings
from ble_assistant.comm import BleComm
from ble_assistant.finder import fuzzy_finder
from ble_assistant.utils import load_modules


class Device:
    def __init__(self, loop, port,
                 *args, **kwargs):
        self.ser = BleComm(loop, port,
                           *args, **kwargs)
        self.port = port
        self.payloads = {}
        pkg = f'ble_assistant.payload.{settings.DEVICE}'
        self.modules = load_modules(pkg)
        self.load_payload()
        self.info = None
        coro = loop.create_task(self.device_information_get())
        loop.run_until_complete(coro)

    @property
    def name(self):
        return self.ser.protocol.name

    @name.setter
    def name(self, value):
        self.ser.protocol.name = value

    def serial_clear(self):
        self.ser.protocol.queue.queue.clear()

    def close(self):
        self.ser.close()

    def load_payload(self):
        for module in self.modules:
            self._load_payload(module)

    def _load_payload(self, module):
        for _, obj in inspect.getmembers(module):
            if inspect.isclass(obj):
                name = getattr(obj, 'name', None)
                if name is None or self.info is None:
                    continue
                if name in self.payloads:
                    msg = f'Name "{name}" conflict: {obj}, {self.payloads[name]}'
                    raise NameError(msg)
                self.ser.update_payload(obj)
                self.payloads[name] = obj
                refer = getattr(obj, 'refer', None)
                if refer:
                    if refer in self.payloads:
                        msg = f'Refer name "{refer}" conflict: {obj}, {self.payloads[refer]}'
                        raise NameError(msg)
                    self.payloads[refer] = obj

    async def device_information_get(self):
        func = self.__getattr__('device_information_get')
        info = await func(timeout=1)
        if info:
            self.info = info
        return info

    def search(self, api_name):
        collections = self.payloads.keys()
        results = fuzzy_finder(api_name, collections)
        res = []
        for name in results:
            cls = self.payloads[name]
            func = cls.downlink_payload
            args = inspect.signature(func).parameters
            doc = cls.__doc__
            if doc:
                doc = doc.strip().replace('\n', ' ')
            res.append((name, args, doc, func))
        return res

    def get_function(self, name):
        cls = self.payloads.get(name, None)
        if cls is None:
            return None
        return cls.downlink_payload

    def __getattr__(self, name):
        async def write_and_read(*args, **kwargs):
            timeout = kwargs.pop('timeout', settings.TIMEOUT)
            num = kwargs.pop('num', 1)
            item = self.payloads.get(name)
            if not item:
                raise AttributeError('method not found')
            downlink = item.downlink(*args, **kwargs)
            if downlink is not None:
                await self.ser.write(downlink)
            header = item.get_uplink_header()
            payload = await self.ser.get_frame(header,
                                               timeout=timeout,
                                               num=num)
            return payload

        return write_and_read

    async def receive_indication(self, names: list, timeout=2):
        headers = []
        for name in names:
            item = self.payloads.get(name)
            if not item:
                raise KeyError('method not found')
            header = item.get_uplink_header()
            header.append(header)
        payloads = await self.ser.get_frame(headers, timeout, -1)
        return payloads

    def pause(self):
        self.ser.protocol.flow.pause_writing()
        self.ser.protocol.flow.pause_reading()

    def resume(self):
        self.ser.protocol.flow.resume_writing()
        self.ser.protocol.flow.resume_reading()


class DeviceManager:
    def __init__(self, devices):
        self.deivces = devices

    def __getattr__(self, item):
        async def call(*args, **kwargs):
            coros = []
            result = []
            for device in self.devices:
                method = getattr(device, item)
                if asyncio.iscoroutinefunction(method):
                    coros.append(method(*args, **kwargs))
                elif inspect.ismethod(method):
                    # coros.append(asyncio.to_thread(method, *args, **kwargs)) # 3.9+
                    result.append(method(*args, **kwargs))
            return await asyncio.gather(*coros) or result

        return call

    def __getitem__(self, index):
        return self.devices[index]

    def __len__(self):
        return len(self.devices)

