"""
@author: qiudeliang

All rights reserved.
"""

import os
import time
import asyncio
import inspect

import serial
from serial.tools import list_ports
from openpyxl.styles import Alignment

from . import logger
from .config import settings
from . import parser
from .report import Report, ExcelHandler
from .device import Device
from .log import set_file_handler
from .casemanage import CaseManage


class App:
    def __init__(self, *,
                 baudrate: int = None,
                 timeout: int = None,
                 case_path: str = None,
                 mesh_app=None,
                 ):
        self.log_path = None
        self.config_log()
        self.report = Report()
        self.excel_handler = None
        self.baudrate = baudrate or settings.BAUDRATE
        self.timeout = timeout or settings.TIMEOUT
        self.dongles = []
        self.mesh_app = mesh_app
        self.tasks = []
        self.case_manage = CaseManage(case_path)
        self.running = False
        self.costtime = None

    def get_dongle(self, port_name):
        for dongle in self.dongles:
            if dongle.port == port_name:
                return dongle
        return None

    def get_ports(self):
        ports = [dongle.port for dongle in self.dongles]
        return ports

    def disconnect(self):
        for dongle in self.dongles:
            dongle.close()
        self.dongles = []

    async def get_dongles(self):
        """"""
        self.disconnect()
        loop = asyncio.get_event_loop()
        for com_port in list_ports.comports():
            port = com_port.device
            try:
                dongle = Device(loop, port,
                                baudrate=self.baudrate,
                                timeout=self.timeout)
                if dongle.info:
                    self.dongles.append(dongle)
                    await dongle.reset()
                else:
                    dongle.close()
            except serial.serialutil.SerialException as exc:
                print("SerialException: can't configure port {}".format(port))
                print(str(exc))

    def config_log(self):
        """

        :return:
        """
        #
        self.log_path = os.path.join(settings.LOG_PATH,
                                     logger.name,
                                     time.strftime('%Y-%m-%d-%H-%M'))

    def config_report(self):
        """

        :return:
        """
        report_path = settings.REPORT_PATH
        if not os.path.exists(report_path):
            os.makedirs(report_path)
        info = ''
        for dongle in self.dongles:
            info = str(dongle.info)
        headers = [[info],
                   [''],
                   ['no', 'name', 'time', 'result']]
        fields = ['no', 'name', 'time', 'result']
        col_width = [30, 30, 30, 10]
        excel_handler = ExcelHandler(pathname=report_path,
                                     headers=headers,
                                     fields=fields,
                                     col_width=col_width)
        excel_handler.ws.merge_cells('A1:E1')
        excel_handler.ws.row_dimensions[1].height = 30
        excel_handler.ws['A1'].alignment = Alignment(vertical='center')
        self.excel_handler = excel_handler
        self.report.add_handler(excel_handler)

    def load_tests(self, path):
        self.case_manage.load_tests(path)

    @property
    def cases(self):
        return self.case_manage.cases

    @property
    def selected(self):
        return self.case_manage.selected

    @selected.setter
    def selected(self, value):
        self.case_manage.selected = value

    @property
    def tests(self):
        return self.case_manage.tests

    @staticmethod
    async def task(task, after_callback):
        res = await task
        if after_callback:
            after_callback()
        return res

    async def run(self, circle=3, after_single_task=None):
        """

        :param circle:
        :param after_single_task:
        :return:
        """
        try:
            self.running = True
            self.tasks = []
            if not os.path.exists(self.log_path):
                os.makedirs(self.log_path)
            self.config_report()
            if settings.COSTTIME:
                self.costtime = open('./costtime.txt', 'wt')
            for test in self.tests:
                case_set = test.__name__
                if case_set not in self.selected.keys():
                    continue
                filename = os.path.join(self.log_path, case_set + '.log')
                set_file_handler(filename, logger)
                ble_test = test(device=self.dongles,
                                logger=logger,
                                report=self.report,
                                mesh_app=self.mesh_app)
                for case in self.selected[case_set]:
                    func = getattr(ble_test, case.no)
                    if 'circle' in inspect.signature(func).parameters:
                        call = func(circle=circle)
                    else:
                        call = func()
                    task = asyncio.create_task(
                        self.task(call,
                                  after_single_task),
                    )
                    self.tasks.append(task)
                    await task
                    if self.costtime:
                        raw = f"{func.case_info['no']}: {func.case_info['cost_time']}\n"
                        self.costtime.write(raw)
        finally:
            self.running = False
            self.report.close()
            self.report.remove_handler(self.excel_handler)
            if self.costtime:
                self.costtime.close()
                self.costtime = None

    def stop(self):
        for task in self.tasks:
            task.cancel()
        self.running = False

    def pause(self):
        for dongle in self.dongles:
            dongle.pause()

    def resume(self):
        for dongle in self.dongles:
            dongle.resume()

    def close(self):
        self.stop()
        self.report.close()
