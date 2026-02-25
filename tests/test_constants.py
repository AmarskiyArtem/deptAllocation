from decimal import Decimal
import unittest

from app.constants import MONEY_Q, PERCENT_Q


class ConstantsTests(unittest.TestCase):
    def test_quantizers(self) -> None:
        self.assertEqual(MONEY_Q, Decimal("0.01"))
        self.assertEqual(PERCENT_Q, Decimal("0.01"))


if __name__ == "__main__":
    unittest.main()
