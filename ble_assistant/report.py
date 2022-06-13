"""
@author: qiudeliang


All rights reserved.
"""

import os
import time
from typing import Dict, Union

from openpyxl import Workbook


class Handler:
    """
    Base handler
    """
    def __init__(self):
        self.name = None

    def handle(self, data):
        """
        Handle data.
        :param data:
        :return:
        """
        self.emit(data)

    def emit(self, data):
        """
        Emit data.
        :param data:
        :return:
        """
        raise NotImplementedError('Emit must be implemented '
                                  'by handler subclass')

    def close(self):
        """
        Close.
        :return:
        """


class ExcelHandler(Handler):
    """
    Openpyxl handler.
    """
    def __init__(self, filename: str = None,
                 pathname: str = None,
                 headers: list = None,
                 fields: list = None,
                 col_width: Union[list, Dict[str, float]] = None):
        super().__init__()
        if pathname is not None:
            if not os.path.exists(pathname):
                os.makedirs(pathname)
            if filename is not None:
                filename = os.path.join(pathname, filename)
        if filename is not None:
            if not filename.endswith('.xlsx'):
                filename = f'{filename}.xlsx'
        self.pathname = pathname
        self.filename = filename
        self.wb = None
        self.ws = None
        self.headers = headers
        self.col_width = col_width
        self.fields = fields
        self.create_worksheet()

    def create_worksheet(self):
        self.wb = Workbook()
        self.ws = self.wb.active
        if self.headers:
            self.add_headers()
        if self.col_width:
            self.set_col_width(self.col_width)

    def add_headers(self):
        """
        Add headers to excel.
        :return:
        """
        for header in self.headers:
            self.ws.append(header)

    def set_col_width(self, width: Union[list, Dict[str, float]]):
        """
        Set column width.

        :param width:
        :return:
        """
        if isinstance(width, list):
            start = ord('A')
            width = {chr(start+i): val for i, val in enumerate(width)}
        for col in width:
            self.ws.column_dimensions[col.upper()].width = width[col]

    def format_data(self, data):
        """
        Covert dict data to list.
        :param data:
        :return:
        """
        if isinstance(data, dict):
            if self.fields:
                data = [data.get(key) for key in self.fields]
            else:
                data = [str(data)]
        return data

    def emit(self, data):
        """
        Emit row data.
        :param data:
        :return:
        """
        data = self.format_data(data)
        if self.ws is None:
            self.create_worksheet()
        self.ws.append(data)
        self.save()

    def save(self):
        """
        Save file.
        :return:
        """
        filename = self.filename
        if filename is None:
            filename = '{}.xlsx'.format(time.strftime('%Y-%m-%d-%H-%M'))
            if self.pathname is not None:
                filename = os.path.join(self.pathname, filename)
            self.filename = filename
        self.wb.save(filename)

    def close(self):
        """
        Close.
        :return:
        """
        # .
        # .
        if self.wb:
            self.wb.close()
        self.wb = None
        self.ws = None
        self.filename = None


class Report:
    """
    Report object
    """
    def __init__(self):
        self.handlers = []
        self.data = []

    def add_handler(self, handler):
        """
        Add handler.
        :param handler:
        :return:
        """
        if handler not in self.handlers:
            self.handlers.append(handler)

    def remove_handler(self, handler):
        """
        Remove handler.
        :param handler:
        :return:
        """
        if handler in self.handlers:
            self.handlers.remove(handler)

    def write(self, data):
        """
        Write data.
        :param data:
        :return:
        """
        self.data.append(data)
        for handler in self.handlers:
            handler.handle(data)

    def close(self):
        """
        Close handlers.
        :return:
        """
        for handler in self.handlers:
            handler.close()
        self.data = []

    def clear_data(self):
        """
        Clear data.
        :return:
        """
        self.data = []

    def get_data(self, filter_func=None):
        """
        Get data.
        :param filter_func:
        :return:
        """
        if filter_func:
            return filter(filter_func, self.data)
        return self.data
