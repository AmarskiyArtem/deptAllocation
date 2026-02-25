from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from .store import DebtStore
from .ui import MainWindow


def _resolve_data_path() -> Path:
    # Keep one stable location independent of run mode (dev/frozen).
    if sys.platform == "darwin":
        base_dir = Path.home() / "Library" / "Application Support" / "DeptAllocation"
    elif sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA")
        base_dir = Path(appdata) / "DeptAllocation" if appdata else Path.home() / "AppData" / "Roaming" / "DeptAllocation"
    else:
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        base_dir = Path(xdg_data_home) / "dept_allocation" if xdg_data_home else Path.home() / ".local" / "share" / "dept_allocation"

    return base_dir / "debt_data.json"


def main() -> None:
    qt_app = QApplication(sys.argv)
    data_path = _resolve_data_path()
    store = DebtStore(data_path)
    window = MainWindow(store)
    window.show()
    sys.exit(qt_app.exec())
