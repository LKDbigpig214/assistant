"""
@author: qiudeliang

All rights reserved.
"""

import os
import asyncio
import pickle
from pathlib import Path

import wx
import wxasync
from ObjectListView import ObjectListView, ColumnDefn
from logzero import LOGZERO_DEFAULT_LOGGER

from ble_assistant.app import App
from ble_assistant.config import settings

from .utils import (dump_history, update_history,
                    ID_OPEN_FILE, ID_PAUSE,
                    ID_LOGOUT, ID_LOGIN,
                    ID_OPEN_DIR, ID_CASE_CONFIG,
                    ID_OPEN_REPORT, AUTH_FILE,
                    HISTORY, ID_DISCONNECT,
                    ID_CONNECT)
from .report import ReportHandler
from .log_ctrl import LogCtrl
from .login import LoginDialog
from .config_window import ConfigWindow
from .args import ArgsDialog, Param
from .decorators import show_exception_in_dialog, show_warning_message


async def get_adb_devices():
    proc = await asyncio.create_subprocess_shell(
        'adv devices',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if stderr:
        return []
    res = []
    for line in stdout.decode().splitlines():
        parts = line.strip().split('\t')
        if len(parts) != 2:
            continue
        if parts[1] == 'device':
            res.append(parts[0])
    return res


class SearchResult:
    def __init__(self, name, args, doc=None, func=None):
        self.name = name
        self.args = self.handle_args(args)
        self.doc = doc
        self.func = func

    @staticmethod
    def handle_args(args):
        args = [str(v) for k, v in args.item()
                if k not in ['args', 'kwargs']]
        args = ', '.join(args)
        if not args:
            args = 'None'
        return args


class MainFrame(wx.Frame):
    def __init__(self, parent=None, pos=None, title=None):
        if pos is None:
            pos = (0, 0)
        self.pos = pos
        _, _, self.width, height = wx.ClientDisplayRect()
        super().__init__(parent,
                         size=(self.width, height),
                         pos=pos,
                         title=title)
        if parent is None:
            self.app = App()
            self.Bind(wx.EVT_CLOSE, self.on_close)
        else:
            self.app = parent.app
        self.dongle = None
        self.loop = asyncio.get_event_loop()
        self.file_history = None
        self.history_config = wx.Config(
            'ble_assistant',
            style=wx.CONFIG_USE_LOCAL_FILE,
        )
        self.user_menu = None
        self.create_menu_bar()
        self.case_combo = None
        self.adb_devices = None
        self.view_search = None
        self.view_report = None
        self.tool_bar = None
        self.create_tool_bar()
        self.status_bar = None
        self.create_status_bar()
        self.search_ctrl = None
        self.refresh = None
        self.search_results_olv = None
        self.report_olv = None
        self.dongle_port = None
        self.display = None
        self.history_olv = None
        self.olv_sizer = None
        self.create_ui()
        self.Layout()
        self.search_results = []
        # wxasync.StartCoroutine(self.get_dongles(), self)
        coro = self.loop.create_task(self.get_dongles())
        self.loop.run_until_complete(coro)
        self.update_history_olv()
        #
        self.circle = 3
        self.task_total = 0
        self.task_finish = 0
        self.associate = False
        #
        #
        #
        self.paused = False
        self.login()
        report_handler = ReportHandler(self.report_olv)
        self.app.report.add_handler(report_handler)

    def show_more(self):
        pos = (self.pos[0] + 20, self.pos[1] + 20)
        sub_frame = MainFrame(self, pos)
        sub_frame.Show()

    def create_menu_bar(self):
        menu_bar = wx.MenuBar()
        # file
        recent_file = wx.Menu()
        self.file_history = wx.FileHistory(8)
        self.file_history.Load(self.history_config)
        self.file_history.UseMenu(recent_file)
        self.file_history.AddFilesToMenu()
        file_menu = wx.Menu()
        file_menu.Append(ID_OPEN_FILE,
                         '&Open File',
                         'Open a python file')
        file_menu.AppendSubMenu(recent_file,
                                '&Recent Files/Dirs')
        file_menu.Append(ID_OPEN_REPORT,
                         '&Open Report',
                         'Open report')
        self.Bind(wx.EVT_MENU, self.on_choose_file, id=ID_OPEN_FILE)
        self.Bind(wx.EVT_MENU_RANGE, self.on_select_history,
                  id=wx.ID_FILE1, id2=wx.ID_FILE9)
        menu_bar.Append(file_menu, '&File')
        # user
        self.user_menu = wx.Menu()
        self.user_menu.Append(ID_LOGIN, 'login', '')
        self.user_menu.AppendSeparator()
        logout = wx.MenuItem(self.user_menu,
                             ID_LOGOUT,
                             'Logout',
                             '')
        logout.SetBitmap(
            wx.Iamge(
                './images/logout.jpg',
                wx.BITMAP_TYPE_JPEG,
            ).Scale(12, 12).ConvertToBitmap()
        )
        self.user_menu.Append(logout)
        self.Bind(wx.EVT_MENU, self.show_login_dialog, id=ID_LOGIN)
        self.Bind(wx.EVT_MENU, self.on_logout, id=ID_LOGOUT)
        menu_bar.Append(self.user_menu, '&User')
        # devices
        device_menu = wx.Menu()
        device_menu.Append(ID_CONNECT, 'Connect', '')
        device_menu.Append(ID_DISCONNECT, 'Disconnect', '')
        menu_bar.Append(device_menu, '&Devices')
        self.Bind(wx.EVT_MENU, self.on_disconnect, id=ID_DISCONNECT)
        self.Bind(wx.EVT_MENU, self.menu_get_dongles, id=ID_CONNECT)
        #
        self.SetMenuBar(menu_bar)

    def create_tool_bar(self):
        self.tool_bar = self.CreateToolBar((wx.TB_HORIZONTAL |
                                           wx.NO_BORDER |
                                           wx.TB_FLAT |
                                           wx.TB_TEXT))
        self.tool_bar.AddSeparator()
        img = wx.Image('./images/open-file.jpg',
                       wx.BITMAP_TYPE_JPEG).Scale(22, 22)
        img = img.ConvertToBitmap()
        self.tool_bar.AddTool(ID_OPEN_DIR,
                              '',
                              img,
                              wx.NullBitmap,
                              wx.ITEM_NORMAL,
                              'Open package',
                              )
        self.Bind(wx.EVT_TOOL, self.on_choose_dir, id=ID_OPEN_DIR)
        count = self.file_history.GetCount()
        choices = [self.file_history.GetHistoryFile(i) for i in range(count)]
        value = ''
        if choices:
            value = choices[0]
        self.case_combo = wx.ComboBox(self.tool_bar,
                                      -1,
                                      value=value,
                                      choices=choices,
                                      size=(350, -1))
        self.Bind(wx.EVT_COMBOBOX, self.on_case_select, self.case_combo)
        self.tool_bar.AddControl(self.case_combo)
        self.tool_bar.AddSeparator()
        img = wx.Image('./images/start.png',
                       wx.BITMAP_TYPE_PNG).Scale(22, 22)
        img = img.ConvertToBitmap()
        self.tool_bar.AddTool(wx.ID_SETUP,
                              '',
                              img,
                              wx.NullBitmap,
                              wx.ITEM_NORMAL,
                              'Start',
                              )
        wxasync.AsyncBind(wx.EVT_TOOL,
                          self.on_run,
                          self,
                          id=wx.ID_SETUP)
        img = wx.Image('./images/stop.png',
                       wx.BITMAP_TYPE_PNG).Scale(22, 22)
        img = img.ConvertToBitmap()
        self.tool_bar.AddTool(wx.ID_STOP,
                              '',
                              img,
                              wx.NullBitmap,
                              wx.ITEM_NORMAL,
                              'Stop',
                              )
        self.tool_bar.EnableTool(wx.ID_STOP, False)
        self.Bind(wx.EVT_TOOL, self.on_stop, id=wx.ID_STOP)

        img = wx.Image('./images/pause.png',
                       wx.BITMAP_TYPE_PNG).Scale(22, 22)
        img = img.ConvertToBitmap()
        self.tool_bar.AddTool(ID_PAUSE,
                              '',
                              img,
                              wx.NullBitmap,
                              wx.ITEM_NORMAL,
                              'Pause',
                              )
        self.tool_bar.EnableTool(ID_PAUSE, False)
        self.Bind(wx.EVT_TOOL, self.on_pause, id=ID_PAUSE)

        img = wx.Image('./images/settings.jpeg',
                       wx.BITMAP_TYPE_JPEG).Scale(22, 22)
        img = img.ConvertToBitmap()
        self.tool_bar.AddTool(ID_CASE_CONFIG,
                              '',
                              img,
                              wx.NullBitmap,
                              wx.ITEM_NORMAL,
                              'Settings',
                              )
        self.Bind(wx.EVT_TOOL, self.on_config, id=ID_CASE_CONFIG)
        self.tool_bar.AddControl(wx.StaticText(self.tool_bar, size=(25, -1)))
        self.tool_bar.AddSeparator()
        self.tool_bar.AddSeparator()
        label = wx.StaticText(self.tool_bar, label='adb devices: ')
        self.adb_devices = wx.ComboBox(self.tool_bar,
                                       value='',
                                       size=(150, -1),
                                       choices=[])
        refresh = wx.BitmapButton(self.tool_bar, -1,
                                  wx.Bitmap('./images/refresh.png'))
        wxasync.AsyncBind(wx.EVT_BUTTON,
                          self.on_get_adb_devices,
                          refresh)
        self.tool_bar.AddControl(label)
        self.tool_bar.AddControl(self.adb_devices)
        self.tool_bar.AddControl(refresh)
        wxasync.StartCoroutine(self.on_get_adb_deviecs(), self)
        self.view_search = wx.RadioButton(self.tool_bar,
                                          -1,
                                          'Search board',
                                          tyle=wx.RB_GROUP)
        self.view_report = wx.RadioButton(self.tool_bar,
                                          -1,
                                          'Report board')
        self.tool_bar.AddStretchableSpace()
        self.tool_bar.AddControl(self.view_search)
        self.tool_bar.AddControl(self.view_report)
        self.Bind(wx.EVT_RADIOBUTTON, self.update_olv_sizer, self.view_search)
        self.Bind(wx.EVT_RADIOBUTTON, self.update_olv_sizer, self.view_report)
        self.tool_bar.Realize()

    def create_ui(self):
        splitter = wx.SplitterWindow(self, -1)
        panel = wx.Panel(splitter, -1)
        panel.SetBackgroundColour(settings.BACKGROUND_COLOR)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.search_ctrl = wx.SearchCtrl(
            panel, style=wx.TE_PROCESS_ENTER, size=(500, 25))
        self.search_ctrl.Bind(wx.EVT_SEARCHCTRL_SEARCH_BTN, self.on_search)
        self.search_ctrl.Bind(wx.EVT_TEXT, self.on_search)
        sizer.Add(self.search_ctrl, 0, wx.ALL, border=5)
        sizer.Add((10, -1), 0, wx.ALL)
        self.dongle_port = wx.ComboBox(panel, -1,
                                       '',
                                       size=(80, -1),
                                       choices=[],
                                       style=wx.CB_DROPDOWN)
        self.dongle_port.Bind(wx.EVT_COMBOBOX, self.on_dongle_select)
        sizer.Add(self.dongle_port, 0, wx.ALL, border=5)
        self.refresh = wx.BitmapButton(panel, -1,
                                       wx.Bitmap('/imgages/refresh.png'))
        wxasync.AsyncBind(wx.EVT_BUTTON, self.get_dongles, self.refresh)
        sizer.Add(self.refresh, 0, wx.ALL, border=5)
        sizer.Add((20, -1), 0, wx.ALL)
        self.display = wx.StaticText(panel, -1, '',
                                     style=wx.ALIGN_LEFT)
        self.display.SetFont(wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL))
        sizer.Add(self.display, 0, wx.ALL | wx.EXPAND, border=5)
        main_sizer.Add(sizer)

        self.olv_sizer = wx.BoxSizer(wx.HORIZONTAL)
        size = (self.width * 2.5 // 4, -1)
        self.search_results_olv = ObjectListView(
            panel,
            size=size,
            style=wx.LC_REPORT | wx.SUNKEN_BORDER,
        )
        self.search_results_olv.SetEmptyListMsg('No Results Found')
        wxasync.AsyncBind(wx.EVT_LIST_ITEM_SELECTED,
                          self.on_search_result_select,
                          self.search_results_olv)
        self.report_olv = wx.ListCtrl(
            panel,
            size=size,
            style=wx.LC_REPORT | wx.LC_HRULES | wx.LC_VRULES,
        )
        self.history_olv = ObjectListView(
            panel,
            style=wx.LC_REPORT,
        )
        self.history_olv.SetColumns([
            ColumnDefn('History', 'left', self.width // 4, 'func'),
            ColumnDefn('Port', 'left', 100, 'port'),
        ])
        self.history_olv.SetEmptyListMsg('History empty')
        wxasync.AsyncBind(wx.EVT_LIST_ITEM_SELECTED,
                          self.on_history_select,
                          self.history_olv)
        self.update_olv_sizer()

        main_sizer.Add(self.olv_sizer, -1, wx.ALL | wx.EXPAND, 5)
        panel.SetSizer(main_sizer)

        log_nb = wx.Notebook(splitter)
        test_log = LogCtrl(log_nb, [settings.LOG_NAME,
                                    LOGZERO_DEFAULT_LOGGER])
        dongle_log = LogCtrl(log_nb, settings.DONGLE_LOG_NAME)
        log_nb.AddPage(test_log, 'tool log')
        log_nb.AddPage(dongle_log, 'dongles log')
        splitter.SplitHorizontally(panel, log_nb, 450)

    def update_olv_sizer(self, event=None):
        if event is not None:
            event.Skip()
        if self.olv_sizer is not None:
            self.olv_sizer.Clear()
        if self.view_search.GetValue():
            self.search_results_olv.Show(True)
            self.report_olv.Show(False)
            self.olv_sizer.Add(self.search_results_olv, 3, wx.ALL | wx.EXPAND)
        else:
            self.search_results_olv.Show(False)
            self.report_olv.Show(True)
            self.olv_sizer.Add(self.report_olv, 3, wx.ALL | wx.EXPAND)

        self.olv_sizer.Add(self.report_olv, 1, wx.ALL | wx.EXPAND)
        self.olv_sizer.Layout()

    async def on_get_adb_devices(self, event=None):
        if event is not None:
            event.Skip()
        self.adb_devices.Clear()
        devices = await get_adb_devices()
        self.adb_devices.Append('')
        for device in devices:
            self.adb_devices.Append(device)
        if devices:
            self.adb_devices.SetValue(devices[0])

    def on_choose_dir(self, event):
        msg = wx.DirDialog(self)
        if msg.ShowModal() == wx.ID_OK:
            fpath = msg.GetPath()
            self.case_combo.SetValue(fpath)
            self.add_history(fpath)
        else:
            msg.Destroy()
        event.Skip(False)

    def on_case_select(self, event):
        event.Skip()
        path = self.case_combo.GetValue()
        self.add_histroy(path)

    @show_exception_in_dialog
    def login(self):
        with Path(AUTH_FILE) as file:
            if file.exists():
                data = pickle.load(file.open('rb'))
                try:
                    account = data['account']
                    # login
                    # ...
                    self.user_menu.SetLabel(ID_LOGIN, account)
                except Exception:
                    self.show_login_dialog()
            else:
                self.show_login_dialog()

    def show_login_dialog(self, event=None):
        if event is not None:
            event.Skip()
        dlg = LoginDialog(self, 'Login')
        dlg.ShowModal()

    @show_exception_in_dialog
    def on_logout(self, event):
        event.Skip()
        # logout
        if os.path.exists(AUTH_FILE):
            os.remove(AUTH_FILE)
        self.user_menu.SetLabel(ID_LOGIN, 'Login')
        self.show_login_dialog()

    @show_exception_in_dialog
    def on_config(self, event):
        event.Skip()
        self.on_load_cases()
        window = ConfigWindow(self, 'settings')
        window.Show()
        self.enable_config(False)

    def enable_config(self, enable):
        self.tool_bar.EnableTool(ID_CASE_CONFIG, enable)

    def on_choose_file(self, event):
        msg = wx.FileDialog(self)
        if msg.ShowModal() == wx.ID_OK:
            fpath = msg.GetPath()
            self.case_combo.SetValue(fpath)
            self.add_history(fpath)
        else:
            msg.Destroy()
        event.Skip(False)

    def on_select_history(self, event):
        file_num = event.GetId() - wx.ID_FILE1
        path = self.file_history.GetHistoryFile(file_num)
        self.add_history(path)
        self.case_combo.SetValue(path)

    def add_history(self, path):
        self.file_history.AddFileToHistory(path)
        self.file_history.Save(self.history_config)
        self.history_config.Flush()
        self.file_history.Load(self.history_config)

    def on_disconnect(self, event):
        event.Skip()
        self.app.disconnect()

    def menu_get_dongles(self, event):
        event.Skip()
        wxasync.StartCoroutine(self.get_dongles(), self)

    async def get_dongles(self, event=None):
        self.refresh.Enable(False)
        self.status_bar.SetStatusText('Get dongles...', 0)
        self.display.SetLabel('')
        if event is not None:
            event.Skip()
        await self.app.get_dongles()
        ports = self.app.get_ports()
        default_port = self.dongle_port.GetValue()
        self.dongle_port.Clear()
        if ports:
            for port in ports:
                self.dongle_port.Append(port)
            if default_port not in ports:
                default_port = ports[0]
        else:
            default_port = ''
        self.dongle_port.SetValue(default_port)
        self.dongle = self.app.get_dongles(default_port)
        self.on_dongle_change()
        self.refresh.Enable(True)
        self.status_bar.SetStatusText('idle', 0)

    def on_dongle_change(self):
        if self.dongle is None:
            return
        info = self.dongle.info
        #
        #
        #
        #
        #
        #
        self.display.SetLabel(str(info))
        self.on_search()

    def create_status_bar(self):
        self.status_bar = self.CreateStatusBar()
        self.status_bar.SetFieldsCount(3)
        self.status_bar.SetStatusWidths([-4, -2, -1])
        self.status_bar.SetStatusText('idle', 0)
        self.status_bar.SetStatusText(
            'Copyright (c) 2022. All rights reserved.',
            1,
        )
        self.status_bar.SetStatusText('Email: ', 2)

    def on_dongle_select(self, event):
        event.Skip()
        port = self.dongle_port.GetValue()
        self.dongle = self.app.get_dongle(port)
        self.on_dongle_change()

    def on_search(self, event=None):
        if event is not None:
            event.Skip()
        if self.view_report.GetValue():
            self.view_search.SetValue(True)
            self.view_report.SetValue(False)
            self.update_olv_sizer()
        if self.dongle is None:
            return
        name = self.search_ctrl.GetValue()
        show_cancel = not self.search_ctrl.IsEmpty()
        self.search_ctrl.ShowCancelButton(show_cancel)
        self.search_results = self.dongle.search(name)
        cols = [SearchResult(*item) for item in self.search_results]
        self.search_results_olv.SetColumns([
            ColumnDefn('Name', 'left', self.width // 5, 'name'),
            ColumnDefn('Args', 'left', self.width // 4, 'args'),
            ColumnDefn('Doc', 'left', self.width // 3, 'doc'),
        ])
        self.search_results_olv.SetObjects(cols)

    async def on_search_result_select(self, evt):
        evt.Skip()
        index = self.search_results_olv.GetFocusedItem()
        func_name, args, _, func = self.search_results[index]
        args = [Param(v) for k, v in args.item()
                if k not in ['args', 'kwargs']]
        if args:
            self.show_args_dialog(func_name, args, func)
        else:
            await self.send_cmd(func_name)

    async def on_history_select(self, evt):
        if self.dongle is None:
            return
        item = evt.GetItem()
        value = item.GetText()
        port = self.history_olv.GetItem(item.GetId(), 1).GetText()
        if port in self.app.get_ports():
            self.dongle_port.SetValue(port)
            self.dongle = self.app.get_dongle(port)
            self.on_dongle_change()
        func_name, args_str = value.strip(')').split('(', 1)
        if args_str:
            params = []
            args = args_str.split(', ')
            for arg in args:
                k, v = arg.split('=')
                params.append(Param({'name': k, 'default': v}))
            func = self.dongle.get_function(func_name)
            self.show_args_dialog(func_name, params, func)
        else:
            await self.send_cmd(func_name)

    @show_exception_in_dialog
    async def send_cmd(self, func_name, **kwargs):
        self.status_bar.SetStatusText('sending', 0)
        self.search_ctrl.SetValue(func_name)
        func = getattr(self.dongle, func_name)
        if func:
            await func(**kwargs)
        self.status_bar.SetStatusText('idle', 0)
        self.update_history(func_name, **kwargs)
        if func_name.find('information_get') != -1:
            self.on_dongle_change()

    def update_history(self, func_name, **kwargs):
        args = [f'{k}={kwargs[k]}' for k in kwargs]
        args = ', '.join(args)
        item = (f'{func_name}({args})', self.dongle_port.GetValue())
        update_history(item)
        self.update_history_olv()

    def update_history_olv(self):
        class History:
            def __init__(self, func, port):
                self.func = func
                self.port = port
        history = [History(*item) for item in HISTORY]
        self.history_olv.SetObjects(history)

    def show_args_dialog(self, func_name, args, func):
        dlg = ArgsDialog(self, func_name, args, func)
        dlg.ShowModal()

    def after_single_task(self):
        self.task_finish += 1
        self.update_task_state()

    def update_task_state(self):
        msg = f'running(finished/total): {self.task_finish} / {self.task_total}'
        self.status_bar.SetStatusText(msg, 0)

    def get_tasks_num(self):
        n = 0
        for k in self.app.selected:
            n += len(self.app.selected[k])
        return n

    async def on_run(self, event):
        event.Skip()
        if self.paused:
            self.on_resume()
            return
        if self.app.running:
            raise RuntimeError('Already running')
        try:
            self.on_load_cases()
            self.view_search.SetValue(False)
            self.view_report.SetValue(True)
            self.update_olv_sizer()
            self.task_total = self.get_tasks_num()
            self.task_finish = 0
            self.set_running_state()
            await self.on_connect_adb_app()
            await self.app.run(self.circle, self.after_single_task)
        except Exception as exc:
            show_warning_message(str(exc))
        finally:
            self.set_idle_state()

    async def on_connect_adb_app(self):
        await self.loop.run_in_executor(None, self.connect_adb_app)

    def connect_adb_app(self):
        adb_serial = self.adb_devices.GetValue()
        if not adb_serial:
            return
        #
        #
        #
        #

    def set_running_state(self):
        self.update_task_state()
        self.tool_bar.EnableTool(wx.ID_SETUP, False)
        self.tool_bar.EnableTool(wx.ID_STOP, True)
        self.tool_bar.EnableTool(ID_PAUSE, True)

    def set_idle_state(self):
        self.tool_bar.EnableTool(wx.ID_SETUP, True)
        self.tool_bar.EnableTool(wx.ID_STOP, False)
        self.tool_bar.EnableTool(ID_PAUSE, False)
        self.status_bar.SetStatusText('idle', 0)

    def on_load_cases(self, event=None):
        if event is not None:
            event.Skip()
        path = self.case_combo.GetValue()
        self.app.load_tests(path)

    @show_exception_in_dialog
    def on_stop(self, event):
        event.Skip()
        if self.paused:
            self.on_resume()
        self.app.stop()
        self.set_idle_state()

    @show_exception_in_dialog
    def on_pause(self, event):
        event.Skip()
        self.app.pause()
        self.paused = True
        self.tool_bar.EnableTool(ID_PAUSE, False)
        self.tool_bar.EnableTool(wx.ID_SETUP, True)
        self.status_bar.SetStatusText('paused', 0)

    def on_resume(self):
        self.app.resume()
        self.paused = False
        self.set_running_state()

    def on_close(self, event):
        event.Skip()
        dump_history()
        self.app.close()
        self.Destroy()
