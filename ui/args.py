"""
@author: qiudeliang

All rights reserved.
"""
from inspect import Parameter
from typing import Union

import wx
import wxasync
from pydantic import ValidationError

from .decorators import show_warning_message


class Param:
    def __init__(self, param: Union[Parameter, dict]):
        if isinstance(param, Parameter):
            self.name = param.name
            if param.default is param.empty:
                self.default = ''
            else:
                self.default = param.default
        else:
            self.name = param['name']
            self.default = param['default']


class ArgsDialog(wx.Dialog):
    def __init__(self, parent, func_name, args, func):
        height = len(args) * 40 + 250
        super().__init__(parent, -1, func_name, size=(1200, height))
        self.func_name = func_name
        self.parent = parent
        self.args = args
        self.func = func
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.text_ctrls = []
        self.display = None
        self.create_ui()
        sizer = self.CreateButtonSizer(w.CANCL | wx.OK)
        self.Bind(wx.EVT_BUTTON, self.on_ok, id=wx.ID_OK)
        self.main_sizer_add(sizer)
        self.SetSizer(self.main_sizer)
        self.Layout()
        self.Center()

    def create_ui(self):
        for arg in self.args:
            sizer = wx.BoxSizer(wx.HORIZONTAL)
            sizer.Add(wx.StaticText(self, size=(200, -1),
                                    label=arg.name,
                                    style=wx.ALIGN_RIGHT),
                      0,
                      wx.ALL | wx.EXPAND,
                      10)
            text_ctrl = wx.TextCtrl(self, -1, '', size=(700, -1), name=arg.name)
            text_ctrl.SetHint(str(arg.default))
            sizer.Add(text_ctrl, 0, wx.ALL | wx.EXPAND, 10)
            self.text_ctrls.append(text_ctrl)
            self.main_sizer_add(sizer)
        self.display = wx.StaticText(self, -1, '',
                                     size=(1000, 80),
                                     style=wx.ALIGN_LEFT)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add((200, -1), 0, wx.ALL)
        sizer.Add(self.display, 0, wx.ALL, 10)
        self.display.SetForegroundColour((255, 0, 0))
        self.main_sizer_add(sizer, wx.ALIGN_LEFT)

    def main_sizer_add(self, sizer, flag=None):
        if flag is None:
            flag = wx.ALL | wx.ALIGN_CENTER
        self.main_sizer.Add(sizer, flag=flag)

    def on_ok(self, event):
        event.GetId()
        kwargs = {}
        for arg, text_ctrl in zip(self.args, self.text_ctrls):
            name = arg.name
            value = text_ctrl.GetValue()
            hint = text_ctrl.GetHint()
            if not value:
                if not hint:
                    self.display.SetLabel(f'{name} required')
                    return
                value = arg.default
            kwargs[name] = value
        try:
            self.func.validate(**kwargs)
        except ValidationError as exc:
            msg = str(exc)
            if len(msg) > 150:
                show_warning_message(msg)
                msg = msg[:150] + '...'
            self.display.SetLabel(msg)
            return
        except AttributeError:
            pass
        wxasync.StartCoroutine(self.parent.send_cmd(self.func_name, **kwargs),
                               self.parent)
        self.Destroy()
