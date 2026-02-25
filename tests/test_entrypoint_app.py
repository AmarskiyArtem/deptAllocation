import runpy
from types import ModuleType
import unittest
from unittest.mock import MagicMock, patch


class AppEntrypointTests(unittest.TestCase):
    def test_app_py_calls_main_when_run_as_script(self) -> None:
        fake_main_module = ModuleType("app.main")
        fake_main_module.main = MagicMock()

        with patch.dict("sys.modules", {"app.main": fake_main_module}):
            runpy.run_path("app.py", run_name="__main__")

        fake_main_module.main.assert_called_once()


if __name__ == "__main__":
    unittest.main()
