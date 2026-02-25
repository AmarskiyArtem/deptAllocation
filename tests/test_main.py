import importlib
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

from tests._qt_stubs import fake_pyside


class MainTests(unittest.TestCase):
    def test_main_creates_store_window_and_starts_qt_loop(self) -> None:
        with fake_pyside():
            main_module = importlib.import_module("app.main")

        app_instance = MagicMock()
        app_instance.exec.return_value = 77

        with (
            patch.object(main_module, "QApplication", return_value=app_instance) as app_cls,
            patch.object(main_module, "DebtStore") as store_cls,
            patch.object(main_module, "MainWindow") as window_cls,
            patch.object(main_module.sys, "exit") as sys_exit,
        ):
            main_module.main()

        app_cls.assert_called_once()
        store_cls.assert_called_once()
        store_path = store_cls.call_args.args[0]
        self.assertIsInstance(store_path, Path)
        self.assertEqual(store_path.name, "debt_data.json")

        window_cls.assert_called_once_with(store_cls.return_value)
        window_cls.return_value.show.assert_called_once()
        app_instance.exec.assert_called_once()
        sys_exit.assert_called_once_with(77)


if __name__ == "__main__":
    unittest.main()
