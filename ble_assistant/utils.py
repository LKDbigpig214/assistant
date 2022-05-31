"""
@author: qiudeliang

All rights reserved.
"""

import sys
import pkgutil
import importlib


def check_sum(data: bytes, length: int = 1) ->bytes:
    res = (0x100 - sum(data) % 256) % 256
    return res.to_bytes(length, 'little')


def import_module(name):
    module = importlib.import_module(name)
    if name in sys.modules:
        importlib.reload(module)
    return module


def load_modules(pkg):
    if isinstance(pkg, str):
        pkg = import_module(pkg)
    res = []
    for _, mode, ispkg in pkgutil.walk_packages(path=pkg.__path__,
                                                prefix=pkg.__name__ + '.',
                                                onerror=lambda x: None):
        if not ispkg:
            module = import_module(mode)
            res.append(module)
    return res
