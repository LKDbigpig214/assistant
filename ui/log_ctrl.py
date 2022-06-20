"""
@author: qiudeliang

All rights reserved.
"""

import logging
from logging import CRITICAL, ERROR, WARNING, INFO, DEBUG

import wx
from wx.lib import newevent

from ble_assistant.config import settings
from .utils import ID_COPY_ITEM


DEFAULT_COLORS = {
    DEBUG: 'dim grey',
    INFO: wx.BLACK,
    WARNING: 'oragne red',
    ERROR: wx.RED,
    CRITICAL: wx.RED,
}


class WxLogHandler(logging.Handler):
    """
    Handler.
    """
    def __init__(self, wx_dest, wx_log_event):
        """
        Init.
        :param wx_dest: the destination object to post the
        event to type wx_dest: wx.Window
        """
        super().__init__()
        self.wx_dest = wx_dest
        self.wx_log_event = wx_log_event
        self.level = settings.LOG_LEVEL
        formatter = logging.Formatter('[%(asctime)s]%(message)s')
        self.setFormatter(formatter)

    def flush(self):
        """
        Does nothing for this handler.
        :return:
        """

    def emit(self, record):
        """
        Emit a record.
        :param record:
        :return:
        """
        try:
            msg = self.format(record)
            evt = self.wx_log_event(message=msg,
                                    levelname=record.levelname,
                                    levelno=record.levelno)
            wx.PostEvent(self.wx_dest, evt)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            print('emit exception: ' + str(e))
            self.handleError(record)


class MyPopupMenu(wx.Menu):
    def __init__(self, text_ctrl):
        super().__init__()
        self.tc = text_ctrl
        item = wx.MenuItem(self, -1, 'Clear')
        self.Append(item)
        self.Bind(wx.EVT_MENU, self.on_clear, item)
        item = wx.MenuItem(self, ID_COPY_ITEM, 'Copy')
        self.Append(item)
        self.Bind(wx.EVT_MENU, self.on_copy, item)
        self.Enable(ID_COPY_ITEM, self.tc.CanCopy())

    def on_clear(self, event):
        event.Skip()
        self.tc.Clear()

    def on_copy(self, event):
        event.Skip()
        self.tc.Copy()


class LogCtrl(wx.TextCtrl):
    def __init__(self, parent,
                 logger_name,
                 size=None,
                 style=None,
                 **kwargs):
        if size is None:
            size = (800, 540)
        if style is None:
            style = wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH
        super().__init__(parent, size=size, style=style, **kwargs)
        (wx_log_event, EVT_WX_LOG_EVENT) = newevent.NewEvent()
        if isinstance(logger_name, str):
            logger_name = [logger_name]
        for name in logger_name:
            logger = logging.getLogger(name)
            handler = WxLogHandler(self, wx_log_event)
            logger.addHandler(handler)
        self.Bind(EVT_WX_LOG_EVENT, self.on_log_event)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_right_down)

    def on_log_event(self, event):
        msg = event.message.strip('\r') + '\n'
        color = DEFAULT_COLORS.get(event.levelno, wx.BLACK)
        self.SetDefaultStyle(wx.TextAttr(color))
        if self.GetNumberOfLines() > 10000:
            self.Clear()
        self.AppendText(msg)
        event.Skip()

    def on_right_down(self, event):
        self.PopupMenu(MyPopupMenu(self), event.GetPosition())
