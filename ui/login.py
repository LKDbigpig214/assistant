"""
@author: qiudeliang

All rights reserved.
"""
import getpass
import pickle

import wx

from .decorators import show_exception_in_dialog
from .utils import ID_LOGIN, AUTH_FILE


class LoginDialog(wx.Dialog):
    def __init__(self, parent, title, user=None, password=None):
        super().__init__(parent, -1, title, size=(350, 270))
        self.parent = parent
        wx.StaticText(self, -1, 'Account', (30, 60))
        wx.StaticText(self, -1, 'Password', (30, 100))

        self.account = wx.TextCtrl(self, -1, '', (110, 55), (140, -1))
        self.password = wx.TextCtrl(self, -1, '', (110, 95), (140, -1),
                                    style=wx.TE_PASSWORD)
        if user is None:
            self.account.SetValue(getpass.getuser())
        else:
            self.account.SetValue(user)
            if password is not None:
                self.password.SetValue(password)
        self.display = wx.StaticText(self, -1, '', (120, 130),
                                     style=wx.ALIGN_RIGHT)
        self.display.SetForegroundColour((255, 0, 0))
        self.disconn = wx.Button(self, -1, 'Cacenl', (50, 160))
        self.conn = wx.Button(self, -1, 'Login', (160, 160))
        self.Bind(wx.EVT_BUTTON, self.on_connect, self.conn)
        self.Bind(wx.EVT_BUTTON, self.on_cancel, self.disconn)
        self.Centre()

    @show_exception_in_dialog
    def on_connect(self, event):
        account = self.account.GetValue()
        password = self.password.GetValue()
        try:
            # do login
            # ...
            self.parent.user_menu.SetLabel(ID_LOGIN, account)
            with open(AUTH_FILE, 'wb') as file:
                data = {'account': account,
                        'password': password}
                pickle.dump(data, file)
            self.Destroy()
        except Exception as e:
            self.display.SetLabel(str(e))

    def on_cancel(self, event):
        event.Skip()
        self.Destroy()
