"""
@author: qiudeliang

All rights reserved.
"""

import pickle
from pathlib import Path
from collections import deque

import wx


AUTH_FILE = './auth.pkl'

ID_OPEN_FILE = wx.NewIdRef()
ID_SAVE_FILE = 102
ID_OPEN_REPORT = 103
ID_LOGIN = 104
ID_LOGOUT = 105
ID_CONNECT = 106
ID_DISCONNECT = 107

ID_OPEN_DIR = 201
ID_CASE_CONFIG = 202
ID_PAUSE = 203

ID_COPY_ITEM = 301

HISTORY = deque([], 20)
HISTORY_FILE = 'history'


with Path(HISTORY_FILE) as f:
    if f.exists():
        HISTORY = pickle.load(f.open('rb'))


def dump_history():
    with Path(HISTORY_FILE) as file:
        pickle.dump(HISTORY, file.open('wb'))


def update_history(item):
    if item in HISTORY:
        HISTORY.remove(item)
    HISTORY.appendleft(item)
