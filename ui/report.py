"""
@author: qiudeliang

All rights reserved.
"""
import wx

from ble_assistant.report import Handler


class MyPopupMenu(wx.Menu):
    def __init__(self, list_ctrl):
        super().__init__()
        self.lc = list_ctrl
        item = wx.MenuItem(self, -1, 'Clear')
        self.Append(item)
        self.Bind(wx.EVT_MENU, self.on_clear, item)

    def on_clear(self, event):
        event.Skip()
        self.lc.DeleteAllItems()


class ReportHandler(Handler):
    def __init__(self, list_ctrl):
        super().__init__()
        self.lc = list_ctrl
        self.lc.InsertColumn(0, 'NO')
        self.lc.InsertColumn(1, 'Name')
        self.lc.InsertColumn(2, 'Result')
        self.lc.InsertColumn(3, 'Comment')
        self.lc.InsertColumn(4, 'Description')
        self.lc.SetColumnWidth(0, 200)
        self.lc.SetColumnWidth(1, 400)
        self.lc.SetColumnWidth(2, 70)
        self.lc.SetColumnWidth(3, 490)
        self.lc.SetColumnWidth(4, 150)
        self.lc.Bind(wx.EVT_RIGHT_DOWN, self.on_right_down)

    def emit(self, data):
        n = self.lc.GetItemCount()
        self.lc.InsertItem(n, data['no'])
        self.lc.SetItem(n, 1, data['name'])
        result = data['result']
        self.lc.SetItem(n, 2, result)
        if str(result).lower() in ['fail', 'block']:
            self.lc.SetItemTextColour(n, 'RED')
        if data.get('msg'):
            self.lc.SetItem(n, 3, data.get('msg'))
        if data.get('description'):
            self.lc.SetItem(n, 4, data.get('description'))
        self.lc.Focus(n)

    def on_right_down(self, event):
        self.lc.PopupMenu(MyPopupMenu(self.lc), event.GetPosition())
