"""
@author: qiudeliang

All rights reserved.
"""

import asyncio
from functools import wraps

import wx


def show_warning_message(message):
    dlg = wx.MessageDialog(None,
                           message,
                           'Warning',
                           wx.OK)
    dlg.ShowModal()
    dlg.Destroy()


def show_exception_in_dialog(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            r = func(*args, **kwargs)
            return r
        except Exception as exc:
            show_warning_message(str(exc))

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            r = await func(*args, **kwargs)
            return r
        except Exception as exc:
            show_warning_message(str(exc))

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return wrapper


def show_progress(message='Progressing'):
    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            progress = wx.ProgressDialog('Process', message,
                                         style=wx.PD_APP_MODAL | wx.PD_AUTO_HIDE)
            r = func(*args, **kwargs)
            progress.Destroy()
            return r

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            progress = wx.ProgressDialog('Process', message,
                                         style=wx.PD_APP_MODAL | wx.PD_AUTO_HIDE)
            r = func(*args, **kwargs)
            # progress.ShowModal()
            progress.Destroy()
            return r

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper

    return decorate
