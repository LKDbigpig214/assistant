"""
@author: qiudeliang


All rights reserved.
"""

import asyncio
import traceback
import time
from types import FunctionType
from functools import wraps

from .config import settings
from .device import DeviceManager


def format_case(name: str = None,
                description: str = None,
                case_no: str = None,
                environment: str = None,
                test_steps: list = None,
                expect_result: list = None,
                expect_time: float = None):
    def decorate(func):
        no = case_no or func.__name__
        case_info = {
            'name': name or no,
            'no': no,
            'description': description,
            'environment': environment,
            'test_steps': test_steps,
            'expect_result': expect_result,
            'expect_time': expect_time,
            'cost_time': None,
        }

        @wraps(func)
        async def async_wrapper(cls, *args, **kwargs):
            try:
                cls.current_case = case_info
                cls.logger.info('=' * 10 + no + '=' * 10)
                start = time.time()
                await cls.setup()
                res = await func(cls, *args, **kwargs)
                cost_time = time.time() - start
                case_info['cost_time'] = cost_time
                cls.logger.info('=' * 10 + f'end, cost: {cost_time}s' + '=' * 10)
                return res
            except Exception as exc:
                cls.logger.exception(traceback.format_exc())
                cls.save_result(False, msg=str(exc), exc=exc)
                if settings.DEVICE == 'ble':
                    await cls.devices.reset()
                return False

        @wraps(func)
        def wrapper(cls, *args, **kwargs):
            try:
                cls.current_case = case_info
                cls.logger.info('=' * 10 + no + '=' * 10)
                start = time.time()
                res = func(cls, *args, **kwargs)
                cost_time = time.time() - start
                case_info['cost_time'] = cost_time
                cls.logger.info('=' * 10 + f'end, cost: {cost_time}s' + '=' * 10)
                return res
            except Exception as exc:
                cls.logger.exception(traceback.format_exc())
                cls.save_result(False, msg=str(exc), exc=exc)
                return False

        async_wrapper.case_info = case_info
        wrapper.case_info = case_info
        if asyncio.iscoroutinefunction(func):
            case = async_wrapper
        else:
            case = wrapper
        return case

    return decorate


class BleTest:
    """
    Test case base case.
    """

    def __init__(self, *,
                 device=None,
                 logger=None,
                 report=None,
                 **kwargs):
        self._devices = DeviceManager(device)
        self.logger = logger
        self.report = report
        self.current_case = None
        loop = asyncio.get_event_loop()
        self.loop = loop

    async def setup(self):
        pass

    @property
    def devices(self):
        return self._devices

    @devices.setter
    def devices(self, value):
        self._devices = DeviceManager(value)

    def save_result(self, result: bool,
                    *, msg=None, exc=None):
        """
        Save result.
        :param result:
        :param msg:
        :param exc:
        :return:
        """
        if result:
            result = 'PASS'
        elif exc is not None:
            result = 'Block'
        else:
            result = 'Fail'
        result = {'result': result,
                  'time': time.strftime('%Y-%m-%d %H:%M:%S'),
                  'msg': msg}
        self.current_case.update(result)
        self.logger.info(self.current_case)
        self.report.write(self.current_case)

    @classmethod
    def get_test_cases(cls):
        """
        Get test cases.
        :return:
        """
        cases = []
        for obj in cls.__dict__.values():
            if cls.is_test_case(obj):
                cases.append(obj)
        return cases

    @staticmethod
    def is_test_case(obj):
        if isinstance(obj, FunctionType):
            return hasattr(obj, 'case_info')
        return False

    def handle_errcode(self, errcode, msg, expect=None):
        if expect is None:
            expect = b'\x00\x00'
        if errcode.code != expect:
            self.save_result(False,
                             msg=f'{msg},errcode:{errcode}',
                             )
            return False
        return True
