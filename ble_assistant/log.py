#!/user/bin/env python3
"""
@author: qiudeliang

All rights reserved.
"""
import logging
import ctypes
import platform
import sys
import os
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

from .config import settings


def add_coloring_to_windows(fn):
    """add color for the log in windows"""
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

        # STD_INPUT_HANDLE = -10
        # STD_OUTPUT_HANDLE = -11
        # STD_ERROR_HANDLE = -12

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


def add_coloring_to_emit_ansi(fn):
    """add color for the log in other system"""
    def new(*args):
        red = '\x1b[31m'
        normal = '\x1b[0m'
        levelno = args[1].levelno
        if levelno >= 30:
            color = red
        else:
            color = normal
        args[1].msg = color + args[1].msg + normal
        return fn(*args)

    return new


def setup_dongle_log(name=None):
    """set dongle log"""
    if name is None:
        name = settings.DONGLE_LOG_NAME
    log = logging.getLogger(name)
    if not settings.DONGLE_LOG_ENABLE:
        return log
    log.setLevel(settings.LOG_LEVEL)

    formatter = logging.Formatter(settings.DONGLE_LOG_FORMATTER)
    log_path = os.path.join(settings.LOG_PATH,
                            name,
                            )
    if not os.path.exists(log_path):
        os.makedirs(log_path)
    filename = os.path.join(log_path, 'logger')
    handler = TimedRotatingFileHandler(filename=filename,
                                       backupCount=settings.DONGLE_LOG_BACKUP_COUNT)
    handler.setLevel(settings.LOG_LEVEL)
    handler.setFormatter(formatter)
    log.addHandler(handler)
    return log


def setup_serial_log(name=None):
    """serial log"""
    if name is None:
        name = settings.SERIAL_LOG_NAME
    log = logging.getLogger(name)
    if not settings.SERIAL_LOG_ENABLE:
        return log
    log.setLevel(settings.LOG_LEVEL)

    formatter = logging.Formatter(settings.SERIAL_LOG_FORMATTER)
    log_path = os.path.join(settings.LOG_PATH,
                            name,
                            )
    if not os.path.exists(log_path):
        os.makedirs(log_path)
    filename = os.path.join(log_path, 'logger')
    handler = TimedRotatingFileHandler(filename=filename,
                                       backupCount=settings.SERIAL_LOG_BACKUP_COUNT)
    handler.setLevel(settings.LOG_LEVEL)
    handler.setFormatter(formatter)
    log.addHandler(handler)
    return log


def set_file_handler(filename, log=None):
    """
    Remove exist file handler and add new file handler.
    """
    if log is None:
        log = logging.getLogger(settings.LOG_NAME)
    formatter = logging.Formatter(settings.LOG_FORMATTER)
    for handler in log.handlers:
        if isinstance(handler, logging.FileHandler):
            log.removeHandler(handler)
    # handler = logging.FileHandler(filename)
    handler = RotatingFileHandler(filename=filename,
                                  maxBytes=100*1024*1024,
                                  backupCount=settings.SERIAL_LOG_BACKUP_COUNT)
    handler.setLevel(settings.LOG_LEVEL)
    handler.setFormatter(formatter)
    log.addHandler(handler)
    return log


def setup_logging(filename=None):
    """setup logging"""
    if platform.system() == 'Windows':
        logging.StreamHandler.emit = add_coloring_to_windows(logging.StreamHandler.emit)
    else:
        logging.StreamHandler.emit = add_coloring_to_emit_ansi(logging.StreamHandler.emit)
    log = logging.getLogger(settings.LOG_NAME)
    log.setLevel(settings.LOG_LEVEL)

    formatter = logging.Formatter(settings.LOG_FORMATTER)

    if filename is not None:
        set_file_handler(filename, log)

    if settings.LOG_STDOUT:
        ch = logging.StreamHandler(stream=sys.stdout)
        ch.setLevel(settings.LOG_LEVEL)
        ch.setFormatter(formatter)
        log.addHandler(ch)

    return log
