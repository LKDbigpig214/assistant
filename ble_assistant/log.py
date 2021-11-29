"""
@author: qiudeliang
"""

import logging
import ctypes
import platform
import sys
from logging.handlers import TimedRotatingFileHandler


def add_coloring_to_windows(fn):
    def _set_color(self, code):
        self.STD_OUTPUT_HANDLE = -11
        hdl = ctypes.windll.kernel32.GetStdHandler(self.STD_OUTPUT_HANDLE)
        ctypes.windll.kernel32.SetConsoleTextAttribute(hdl, code)

    setattr(logging.StreamHandler, 'set_color', _set_color)

    def new(*args):
        foreground_blue = 0x0001
        foreground_green = 0x0002
        foreground_red = 0x0004
        foreground_white = foreground_blue | foreground_green | foreground_red

        levelno = args[1].levelno
        if levelno >= logging.WARNING:
            color = foreground_red
        elif levelno >= logging.INFO:
            color = foreground_green
        else:
            color = foreground_white
        args[0].set_color(color)
        ret = fn(*args)
        args[0].set_color(foreground_white)
        return ret

    return new
