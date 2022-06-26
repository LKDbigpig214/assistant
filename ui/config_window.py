"""
@author: qiudeliang

All rights reserved.
"""

import pickle
import wx

from .test_case import TestCasePanel
from .decorators import show_exception_in_dialog
from .utils import ID_OPEN_FILE, ID_SAVE_FILE


class ConfigWindow(wx.Frame):
    def __init__(self, parent, title):
        _, _, width, height = wx.ClientDisplayRect()
        width = width // 10 * 9
        super().__init__(parent, -1, title,
                         size=(width, height - 50),
                         pos=(20, 20))
        self.parent = parent
        nb = wx.Notebook(self)
        self.case_panel = TestCasePanel(nb, parent)
        nb.AddPage(self.case_panel, 'test cases settings')
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.create_menu_bar()

    def on_close(self, event):
        self.case_panel.on_close()
        event.Skip()
        self.parent.enable_config(True)

    def create_menu_bar(self):
        menu_bar = wx.MenuBar()
        file_menu = wx.Menu()
        file_menu.Append(ID_OPEN_FILE,
                         '&Open File',
                         'Open config file')
        self.Bind(wx.EVT_MENU, self.on_choose_file, id=ID_OPEN_FILE)
        file_menu.Append(ID_SAVE_FILE,
                         '&Save File',
                         'Save config file')
        self.Bind(wx.EVT_MENU, self.on_save_file, id=ID_SAVE_FILE)
        menu_bar.Append(file_menu, '&File')
        self.SetMenuBar(menu_bar)

    @show_exception_in_dialog
    def handle_file(self, callback):
        msg = wx.FileDialog(self)
        if msg.ShowModel() == wx.ID_OK:
            fpath = msg.GetPath()
            callback(fpath)
        else:
            msg.Destroy()

    def on_choose_file(self, event):
        self.handle_file(self.load_config)
        event.Skip(False)

    def load_config(self, fpath):
        self.SetLabel(fpath)
        with open(fpath, 'rb') as f:
            self.case_panel.app.selected = pickle.load(f)
            self.case_panel.init_check()

    def on_save_file(self, event):
        event.Skip(False)
        self.handle_file(self.dump_config)

    def dump_config(self, fpath):
        with open(fpath, 'wb') as f:
            self.case_panel.on_check()
            pickle.dump(self.case_panel.app.selected, f)
