"""
@author: qiudeliang

All rights reserved.
"""

import wx
from ObjectListView import GroupListView, ColumnDefn

from ble_assistant.config import settings
from .decorators import show_exception_in_dialog, show_warning_message


class MyGroupView(GroupListView):
    def __init__(self, args, **kwargs):
        super().__init__(*args, **kwargs)
        self.left_down_handle = None

    def _HandleLeftDownOnImage(self, row_index, sub_item_index):
        super()._HandleLeftDownOnImage(row_index, sub_item_index)
        if self.left_down_handle:
            self.left_down_handle()


class TestCasePanel(wx.Panel):
    def __init__(self, notebook, parent):
        super().__init__(notebook, -1)
        self.cases = []
        self.parent = parent
        self.test_platform = parent.test_platform
        self.app = parent.app
        for case in parent.app.cases.values():
            self.cases.append(case)
        self.case_olv = None
        self.check_all = None
        self.circle = None
        self.associate = None
        self.group = None
        self.project = None
        self.version = None
        self.add_button = None
        self.project_version = {}
        self.create_ui()
        self.Layout()
        self.Centre()
        self.on_ossociate()
        self.expanded = False

    def create_ui(self):
        self.SetBackgroundColour(settings.BACKGROUND_COLOR)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.check_all = wx.CheckBox(self, -1, 'ALL', size=(-1, 25))
        self.check_all.SetValue(1)
        self.Bind(wx.EVT_CHECKBOX, self.on_check_all, self.check_all)
        with_select = wx.Button(self,
                                label='Toggle selected',
                                )
        self.Bind(wx.EVT_BUTTON, self.on_taggle, with_select)
        expand_collapse = wx.Button(self,
                                    label='Expand/collapse')
        self.Bind(wx.EVT_BUTTON, self.on_expand_collapse, expand_collapse)
        self.circle = wx.TextCtrl(self, -1, str(self.parent.circle), size=(50, -1))
        self.circle.Bind(wx.EVT_TEXT, self.on_circle_change)
        self.associate = wx.CheckBox(self, -1, 'Test platform',
                                     size=(-1, 25))
        self.associate.SetValue(self.parent.associate)
        self.Bind(wx.EVT_CHECKBOX, self.on_associate, self.associate)
        self.group = wx.ComboBox(self, -1,
                                 choices=['BLE'])
        self.Bind(wx.EVT_COMBOBOX, self.on_group_select, self.group)
        self.project = wx.ComboBox(self, -1,
                                   size=(150, -1))
        self.Bind(wx.EVT_COMBOBOX, self.on_project_select, self.project)
        self.version = wx.ComboBox(self, -1,
                                   size=(200, -1))
        self.add_button = wx.Button(self, label='Add')
        self.Bind(wx.EVT_BUTTON, self.add_cases, self.add_button)
        sizer.Add(self.check_all, 0, wx.ALL, border=7)
        sizer.Add(with_select, 0, wx.ALL, border=7)
        sizer.Add(expand_collapse, 0, wx.ALL, border=7)
        sizer.Add(wx.StaticText(self, label='Circle:'), 0, wx.ALL, border=10)
        sizer.Add(self.circle, 0, wx.ALL, border=7)
        sizer.Add(self.associate, 0, wx.ALL, border=7)
        sizer.Add(self.group, 0, wx.ALL, border=7)
        sizer.Add(self.project, 0, wx.ALL, border=7)
        sizer.Add(self.version, 0, wx.ALL, border=7)
        sizer.Add(self.add_button, 0, wx.ALL, border=7)
        main_sizer.Add(sizer, -1, wx.ALL | wx.EXPAND)
        self.case_olv = MyGroupView(
            self, sortable=False,
            style=wx.LC_REPORT | wx.SUNKEN_BORDER)
        self.case_olv.left_down_handle = self.refresh_check
        self.case_olv.SetEmptyListMsg('No Test Case Found')
        self.case_olv.SetColumns([
            ColumnDefn('NO', 'left', 200, 'no', groupKeyGetter=self.group_key),
            ColumnDefn('Name', 'left', 300, 'name'),
            ColumnDefn('Description', 'left', 250, 'description'),
            ColumnDefn('Environment', 'left', 250, 'environment'),
            ColumnDefn('Steps', 'left', 400, 'test_steps'),
            ColumnDefn('Expect result', 'left', 300, 'expect_result'),
            ColumnDefn('Expect time', 'left', 100, 'expect_time'),
        ])
        self.case_olv.SetObjects(self.cases)
        self.case_olv.InstallCheckStateColumn(self.case_olv.columns[0])
        self.init_check()
        self.case_olv.CollapseAll()
        main_sizer.Add(self.case_olv, 3, wx.ALL | wx.EXPAND)
        self.SetSizer(main_sizer)
        main_sizer.Fit(self)

    @show_exception_in_dialog
    def on_circle_change(self, event):
        event.Skip()
        value = self.circle.GetValue()
        if value:
            self.parent.circle = int(value)

    def init_check(self):
        for model in self.case_olv.modelObjects:
            selected = self.app.selected.get(model.case_set)
            if selected:
                selected = [case.name for case in selected]
                if model.name in selected:
                    self.check_model(model, True)
                    continue
            self.check_model(model, False)
            self.check_all.SetValue(0)

    def on_close(self):
        self.on_check()

    def on_check(self):
        checked = {}
        self.case_olv.ExpandAll()
        for model in self.case_olv.GetCheckedObjects():
            checked.setdefault(model.case_set, []).append(model)
        self.app.selected = checked

    def on_toggle(self, event):
        event.Skip()
        selected = self.case_olv.GetSelectedObjects()
        groups = self.case_olv.GetSelectedGroups()
        if groups:
            for grp in groups:
                for model in grp.modelObjects:
                    self.toggle_check(model)
                    if model in selected:
                        selected.remove(model)
        for model in selected:
            self.toggle_check(model)
        self.refresh_check()

    def toggle_check(self, model):
        self.case_olv.ToggleCheck(model)
        self.case_olv.RefreshObject(model)

    def on_expand_collapse(self, event):
        event.Skip()
        if self.expanded:
            self.case_olv.CollapseAll()
        else:
            self.case_olv.ExpandAll()
        self.expanded = not self.expanded

    def on_associate(self, event=None):
        if event is not None:
            event.Skip()
        state = self.associate.IsChecked()
        self.parent.associate = state
        self.group.Show(state)
        self.project.Show(state)
        self.version.Show(state)
        self.add_button.Show(state)

    def check_model(self, model, state):
        self.case_olv.SetCheckState(model, state)
        self.case_olv.RefreshObject(model)

    def on_check_all(self, event):
        clicked = event.GetEventObject()
        checked = clicked.GetValue() == 1
        for model in self.case_olv.modelObjects:
            self.check_model(model, checked)

    def refresh_check(self, event=None):
        if event is not None:
            event.Skip()
        for model in self.case_olv.modelObjects:
            if not self.case_olv.IsChecked(model):
                self.check_all.SetValue(0)
                return
        self.check_all.SetValue(1)

    @staticmethod
    def group_key(info):
        return info.case_set
