import importlib
import unittest

from tests._qt_stubs import fake_pyside


class UiTests(unittest.TestCase):
    def test_ui_module_imports_with_stubbed_qt(self) -> None:
        with fake_pyside():
            ui = importlib.import_module("app.ui")

        self.assertTrue(hasattr(ui, "MainWindow"))


if __name__ == "__main__":
    unittest.main()
