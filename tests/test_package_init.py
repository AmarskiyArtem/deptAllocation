import app
import unittest


class PackageInitTests(unittest.TestCase):
    def test_package_docstring_exists(self) -> None:
        self.assertIn("Debt allocation", app.__doc__)


if __name__ == "__main__":
    unittest.main()
