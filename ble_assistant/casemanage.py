"""
@author: qiudeliang

All rights reserved.
"""

import sys
import inspect
from pathlib import Path

from .utils import import_module, load_modules
from .testcase import BleTest


class CaseInfo:
    def __init__(self, case, case_set):
        info = case.case_info
        self.case_set = case_set
        self.name = info['name']
        self.description = info['description']
        self.environment = info['environment']
        steps = ''
        if info['test_steps']:
            for i, step in enumerate(info['test_steps']):
                steps += f'{i+1}.{step}'
        self.test_steps = steps
        expect = info['expect_result']
        if expect:
            expect = '  '.join(expect)
        self.expect_result = expect
        self.no = info['no']
        self.expect_time = info['expect_time']


class CaseManage:
    def __init__(self, path=None):
        self.path = path
        self.tests = []
        self.cases = {}
        self.selected = {}
        self.in_setup = True
        if path:
            self.load_tests()

    def load_tests(self, path=None):
        if path is not None:
            self.path = path
        if self.path is None:
            return
        self.tests = []
        self.cases = {}
        p = Path(self.path)
        dirname = p.parent
        if dirname not in sys.path:
            sys.path.append(str(dirname))
        if p.is_dir():
            modules = load_modules(p.name)
        elif p.suffix != '.py':
            raise ImportError('A python file required')
        else:
            name = p.name.rstrip(p.suffix)
            modules = [import_module(name)]
        for module in modules:
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, BleTest):
                    self.tests.append(obj)
        if self.in_setup:
            self.selected = {}
        for test in self.tests:
            cases = test.get_test_cases()
            case_set = test.__name__
            cases = [CaseInfo(case, case_set) for case in cases]
            self.cases.setdefault(case_set, []).extend(cases)
            if self.in_setup:
                self.selected.setdefault(case_set, []).extend(cases)
        self.in_setup = False
