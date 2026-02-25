from __future__ import annotations

from contextlib import contextmanager
from types import ModuleType
from unittest.mock import patch


class _Dummy:
    def __init__(self, *args, **kwargs) -> None:
        self._text = ""

    def __call__(self, *args, **kwargs):
        return self

    def __getattr__(self, _name):
        return self

    def __or__(self, _other):
        return 0

    def setText(self, value: str) -> None:
        self._text = value

    def text(self) -> str:
        return self._text


class _QtDummy:
    Horizontal = 1
    Vertical = 2
    AlignRight = 4
    AlignVCenter = 8
    UserRole = 32


def _module(name: str) -> ModuleType:
    return ModuleType(name)


@contextmanager
def fake_pyside():
    pyside6 = _module("PySide6")

    qt_core = _module("PySide6.QtCore")
    qt_core.Qt = _QtDummy

    qt_gui = _module("PySide6.QtGui")
    qt_gui.QFont = _Dummy

    qt_widgets = _module("PySide6.QtWidgets")
    qt_widgets.QApplication = _Dummy
    qt_widgets.QGroupBox = _Dummy
    qt_widgets.QHBoxLayout = _Dummy
    qt_widgets.QHeaderView = _Dummy
    qt_widgets.QInputDialog = _Dummy
    qt_widgets.QLabel = _Dummy
    qt_widgets.QLineEdit = _Dummy
    qt_widgets.QListWidget = _Dummy
    qt_widgets.QMainWindow = _Dummy
    qt_widgets.QMessageBox = _Dummy
    qt_widgets.QPushButton = _Dummy
    qt_widgets.QSplitter = _Dummy
    qt_widgets.QTableWidget = _Dummy
    qt_widgets.QTableWidgetItem = _Dummy
    qt_widgets.QVBoxLayout = _Dummy
    qt_widgets.QWidget = _Dummy

    modules = {
        "PySide6": pyside6,
        "PySide6.QtCore": qt_core,
        "PySide6.QtGui": qt_gui,
        "PySide6.QtWidgets": qt_widgets,
    }
    with patch.dict("sys.modules", modules):
        yield
